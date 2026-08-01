"""Training pipeline — bootstrap ML models from real datasets when present, else synthetic."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

import numpy as np

from insureflow.ml.base import BaseMLModel
from insureflow.ml.features import DEFAULT_FEATURE_NAMES, generate_synthetic_dataset, get_model_feature_names
from insureflow.ml.models import ModelType, TrainingResult
from insureflow.ml.registry import get_ml_registry

logger = logging.getLogger(__name__)

TRAINING_CONFIGS: dict[ModelType, dict[str, Any]] = {
    ModelType.LOSS_PREDICTION: {"n_samples": 2000, "seed": 42},
    ModelType.FRAUD_DETECTION: {"n_samples": 3000, "seed": 43},
    ModelType.PREMIUM_OPTIMIZER: {"n_samples": 2000, "seed": 44},
    ModelType.CHURN_PREDICTION: {"n_samples": 2500, "seed": 45},
    ModelType.MORTGAGE_DEFAULT_RISK: {"n_samples": 2500, "seed": 46},
    ModelType.LENDING_DEFAULT_RISK: {"n_samples": 3000, "seed": 47},
}

# Default layout: ml_data/<model_type>.csv with feature columns + target
DEFAULT_DATA_ROOT = Path("ml_data")

# Minimum production thresholds. Models trained on real data that fail these stay
# on their deterministic fallbacks instead of serving weak predictions.
QUALITY_GATES: dict[ModelType, dict[str, float]] = {
    ModelType.LOSS_PREDICTION: {"val_r2": 0.0, "min_samples": 50.0},
    ModelType.FRAUD_DETECTION: {"val_roc_auc": 0.70, "min_samples": 50.0},
    ModelType.PREMIUM_OPTIMIZER: {"val_r2": 0.0, "min_samples": 50.0},
    ModelType.CHURN_PREDICTION: {"val_roc_auc": 0.70, "min_samples": 50.0},
    ModelType.MORTGAGE_DEFAULT_RISK: {"val_roc_auc": 0.70, "min_samples": 50.0},
    ModelType.LENDING_DEFAULT_RISK: {"val_roc_auc": 0.70, "min_samples": 50.0},
}


def passes_quality_gate(model_type: ModelType, metrics: dict[str, float], n_samples: int) -> tuple[bool, str]:
    """Check a trained model against production quality thresholds.

    Returns (passed, reason). A model failing the gate must not serve predictions.
    """
    gate = QUALITY_GATES.get(model_type)
    if gate is None:
        return True, "no gate configured"
    if n_samples < gate.get("min_samples", 0.0):
        return False, f"insufficient samples ({n_samples} < {gate.get('min_samples', 0.0):.0f})"
    if "val_roc_auc" in gate and metrics.get("val_roc_auc", 0.0) < gate["val_roc_auc"]:
        return False, f"val_roc_auc {metrics.get('val_roc_auc', 0.0):.3f} < {gate['val_roc_auc']:.2f}"
    if "val_r2" in gate and metrics.get("val_r2", -1.0) <= gate["val_r2"]:
        return False, f"val_r2 {metrics.get('val_r2', -1.0):.3f} <= {gate['val_r2']:.2f}"
    return True, "passed"


def resolve_dataset_path(model_type: ModelType, data_root: Path | None = None) -> Path | None:
    root = data_root or DEFAULT_DATA_ROOT
    candidates = [
        root / f"{model_type.value}.csv",
        root / model_type.value / "train.csv",
        root / "train.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def load_training_csv(
    path: Path | str,
    *,
    target_column: str = "target",
    feature_columns: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Load a labeled training CSV.

    Expected: numeric feature columns matching DEFAULT_FEATURE_NAMES (or subset)
    plus a ``target`` column. Missing features are zero-filled.
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError(f"Empty CSV: {path}")
        fields = list(reader.fieldnames)
        if target_column not in fields:
            raise ValueError(f"CSV missing target column '{target_column}': {path}")

        wanted = feature_columns or DEFAULT_FEATURE_NAMES
        rows: list[list[float]] = []
        targets: list[float] = []
        for row in reader:
            vec = []
            for name in wanted:
                raw = row.get(name, "")
                try:
                    vec.append(float(raw) if raw not in (None, "") else 0.0)
                except ValueError:
                    vec.append(0.0)
            try:
                targets.append(float(row[target_column]))
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Bad target in {path}: {row.get(target_column)!r}") from exc
            rows.append(vec)

    if not rows:
        raise ValueError(f"No data rows in {path}")

    meta = {
        "path": str(path),
        "n_samples": len(rows),
        "n_features": len(wanted),
        "feature_columns": wanted,
        "target_column": target_column,
        "source": "csv",
    }
    return np.asarray(rows, dtype=np.float64), np.asarray(targets, dtype=np.float64), meta


def load_dataset_for_model(
    model_type: ModelType,
    *,
    data_root: Path | None = None,
    csv_path: Path | str | None = None,
    allow_synthetic: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Prefer real CSV under ml_data/; fall back to synthetic only if allowed.

    A real CSV whose target is degenerate (single class/value) is never used for
    production training — it either falls back to synthetic (demo/tests) or raises
    FileNotFoundError so callers skip the model gracefully.
    """
    feature_columns = get_model_feature_names(model_type.value)
    path = Path(csv_path) if csv_path else resolve_dataset_path(model_type, data_root)
    if path is not None:
        X, y, meta = load_training_csv(path, feature_columns=feature_columns)
        meta["model_type"] = model_type.value
        if len(np.unique(y)) < 2:
            if not allow_synthetic:
                raise FileNotFoundError(
                    f"Training CSV {path} is degenerate (single class/value in target) — not usable for production training"
                )
            logger.warning("Dataset %s is degenerate (single target class) — falling back to synthetic", path)
        else:
            meta["synthetic"] = False
            return X, y, meta

    if not allow_synthetic:
        raise FileNotFoundError(f"No training CSV for {model_type.value}. Place labeled data at ml_data/{model_type.value}.csv (features + target column).")

    config = TRAINING_CONFIGS.get(model_type, {"n_samples": 2000, "seed": 42})
    X, y = generate_synthetic_dataset(
        n_samples=config["n_samples"],
        model_type=model_type.value,
        seed=config["seed"],
    )
    return (
        X,
        y,
        {
            "model_type": model_type.value,
            "n_samples": len(y),
            "source": "synthetic",
            "synthetic": True,
            "warning": "Trained on synthetic data — replace with ml_data/*.csv for production models",
        },
    )


def train_all_models(
    force: bool = False,
    *,
    data_root: Path | None = None,
    allow_synthetic: bool = True,
) -> list[TrainingResult]:
    """Train (or retrain) all ML models — real CSV preferred over synthetic.

    In production (``allow_synthetic=False``) models without a labeled dataset are
    skipped (they stay on deterministic fallbacks) and only models that pass the
    quality gate are promoted to champion. Synthetic training keeps the legacy
    promotion behavior so tests and demos are unchanged.
    """
    registry = get_ml_registry()
    results: list[TrainingResult] = []

    for model_type, _config in TRAINING_CONFIGS.items():
        model = registry.get(model_type)
        if model is None:
            continue
        if not isinstance(model, BaseMLModel):
            continue
        if hasattr(model, "is_trained") and model.is_trained and not force:
            logger.info("Skipping %s — already trained", model_type.value)
            continue

        try:
            X, y, meta = load_dataset_for_model(
                model_type,
                data_root=data_root,
                allow_synthetic=allow_synthetic,
            )
        except FileNotFoundError as exc:
            if not allow_synthetic:
                logger.warning("Skipping %s — no real dataset: %s", model_type.value, exc)
                continue
            raise

        logger.info(
            "Training %s from %s (%d samples)...",
            model_type.value,
            meta.get("source"),
            meta.get("n_samples"),
        )
        result = registry.train_model(model_type, X, y)
        if result is None:
            continue
        if hasattr(registry, "_history") and registry._history:
            registry._history[-1]["data_source"] = meta.get("source")
            registry._history[-1]["synthetic"] = meta.get("synthetic")
            registry._history[-1]["dataset_path"] = meta.get("path")
        results.append(result)
        logger.info("  %s: %s (%s)", model_type.value, result.metrics, meta.get("source"))

        if meta.get("synthetic"):
            model.gate_passed = True
            if model_type in (ModelType.LOSS_PREDICTION, ModelType.FRAUD_DETECTION):
                registry.promote_to_champion(model_type)
            continue

        passed, reason = passes_quality_gate(model_type, result.metrics, meta.get("n_samples", 0))
        model.gate_passed = passed
        model.save()
        if passed:
            registry.promote_to_champion(model_type)
            logger.info("  ✓ %s passed quality gate — promoted to champion", model_type.value)
        else:
            logger.warning("  ✗ %s failed quality gate (%s) — keeping deterministic fallback", model_type.value, reason)

    return results


def retrain_model(
    model_type: ModelType,
    n_samples: int = 2000,
    seed: int | None = None,
    *,
    csv_path: Path | str | None = None,
    allow_synthetic: bool = True,
) -> TrainingResult | None:
    """Retrain a single model from CSV when provided, else synthetic."""
    registry = get_ml_registry()
    if csv_path or resolve_dataset_path(model_type):
        X, y, meta = load_dataset_for_model(
            model_type,
            csv_path=csv_path,
            allow_synthetic=allow_synthetic,
        )
    else:
        if not allow_synthetic:
            raise FileNotFoundError(f"No CSV for {model_type.value} and synthetic disabled")
        X, y = generate_synthetic_dataset(
            n_samples=n_samples,
            model_type=model_type.value,
            seed=seed or np.random.randint(0, 10000),
        )
        meta = {"source": "synthetic", "synthetic": True}
    result = registry.train_model(model_type, X, y)
    if result and hasattr(registry, "_history") and registry._history:
        registry._history[-1]["data_source"] = meta.get("source")
        registry._history[-1]["synthetic"] = meta.get("synthetic")
    return result


def get_training_status() -> dict[str, Any]:
    """Get current status of all ML models."""
    registry = get_ml_registry()
    datasets = {}
    for model_type in TRAINING_CONFIGS:
        path = resolve_dataset_path(model_type)
        datasets[model_type.value] = {
            "csv_path": str(path) if path else None,
            "has_real_data": path is not None,
        }
    return {
        "models": registry.get_status(),
        "history": registry.history,
        "training_configs": {k.value: v for k, v in TRAINING_CONFIGS.items()},
        "datasets": datasets,
        "data_root": str(DEFAULT_DATA_ROOT),
    }
