"""Base ML model class with training, prediction, and serialization."""

from __future__ import annotations

import json
import logging
import pickle
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from insureflow.ml.models import (
    FeatureVector,
    ModelStatus,
    ModelType,
    TrainingResult,
)

logger = logging.getLogger(__name__)

MODEL_DIR = Path("ml_models")


class BaseMLModel(ABC):
    """Abstract base class for all ML models in Rytera."""

    model_type: ModelType
    model_name: str

    def __init__(self) -> None:
        self.model: Any = None
        self.scaler: Any = None
        self.version: str = "0.1.0"
        self.status: ModelStatus = ModelStatus.DRAFT
        self.trained_at: datetime | None = None
        self.feature_names: list[str] = []
        self.metrics: dict[str, float] = {}
        self.feature_importance: dict[str, float] = {}

    @abstractmethod
    def _build_model(self) -> Any:
        """Build and return the underlying ML model."""

    @abstractmethod
    def _extract_features(self, fv: FeatureVector) -> np.ndarray:
        """Extract model-specific feature array from FeatureVector."""

    @abstractmethod
    def _get_feature_names(self) -> list[str]:
        """Return ordered list of feature names."""

    @abstractmethod
    def _compute_feature_importance(self) -> dict[str, float]:
        """Compute feature importance from trained model."""

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str] | None = None,
        validation_split: float = 0.2,
        **kwargs: Any,
    ) -> TrainingResult:
        """Train the model with automatic validation split."""
        from sklearn.model_selection import train_test_split

        self.status = ModelStatus.TRAINING
        start = time.time()

        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=validation_split, random_state=42)

        self.feature_names = feature_names or self._get_feature_names()
        self.model = self._build_model()
        self._fit_model(X_train, y_train, **kwargs)

        train_pred = self.model.predict(X_train)
        val_pred = self.model.predict(X_val)

        self.metrics = self._compute_metrics(y_train, train_pred, y_val, val_pred)
        self.feature_importance = self._compute_feature_importance()
        self.trained_at = datetime.now(tz=timezone.utc)
        self.status = ModelStatus.READY
        self.version = self._bump_version()

        duration = time.time() - start
        logger.info(
            "Trained %s v%s in %.1fs — metrics: %s",
            self.model_type.value,
            self.version,
            duration,
            self.metrics,
        )

        return TrainingResult(
            model_type=self.model_type,
            model_version=self.version,
            metrics=self.metrics,
            feature_importance=self.feature_importance,
            training_samples=len(X_train),
            validation_samples=len(X_val),
            duration_seconds=duration,
        )

    def _fit_model(self, X: np.ndarray, y: np.ndarray, **kwargs: Any) -> None:
        """Default fit — override for models with special training logic."""
        if hasattr(self.model, "fit"):
            self.model.fit(X, y, **kwargs)

    @abstractmethod
    def _compute_metrics(
        self,
        y_train: np.ndarray,
        train_pred: np.ndarray,
        y_val: np.ndarray,
        val_pred: np.ndarray,
    ) -> dict[str, float]:
        """Compute training and validation metrics."""

    def predict(self, fv: FeatureVector) -> dict[str, Any]:
        """Run prediction on a single feature vector."""
        if self.model is None or self.status not in (ModelStatus.READY, ModelStatus.CHAMPION, ModelStatus.CHALLENGER):
            return self._fallback_prediction(fv)

        start = time.time()
        features = self._extract_features(fv).reshape(1, -1)
        prediction = self.model.predict(features)[0]
        latency = (time.time() - start) * 1000

        result = self._format_prediction(fv, prediction)
        result["model_version"] = self.version
        result["latency_ms"] = round(latency, 2)
        return result

    def predict_batch(self, vectors: list[FeatureVector]) -> list[dict[str, Any]]:
        """Run prediction on multiple feature vectors."""
        return [self.predict(fv) for fv in vectors]

    @abstractmethod
    def _fallback_prediction(self, fv: FeatureVector) -> dict[str, Any]:
        """Deterministic fallback when no trained model is available."""

    @abstractmethod
    def _format_prediction(self, fv: FeatureVector, raw_prediction: Any) -> dict[str, Any]:
        """Format raw model prediction into domain-specific output."""

    def explain(self, fv: FeatureVector) -> dict[str, Any]:
        """Generate prediction explanation (feature contributions)."""
        if self.model is None:
            return {"method": "fallback", "top_factors": []}

        features = self._extract_features(fv).reshape(1, -1)
        contributions = {}

        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
            for i, name in enumerate(self.feature_names[: len(importances)]):
                contributions[name] = round(float(features[0][i] * importances[i]), 4)
        elif hasattr(self.model, "coef_"):
            coefs = self.model.coef_.flatten()
            for i, name in enumerate(self.feature_names[: len(coefs)]):
                contributions[name] = round(float(features[0][i] * coefs[i]), 4)

        sorted_factors = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
        return {
            "method": "feature_contribution",
            "top_factors": [{"feature": k, "contribution": v} for k, v in sorted_factors[:10]],
            "all_contributions": contributions,
        }

    def save(self, path: Path | None = None) -> Path:
        """Save model artifacts to disk."""
        save_dir = path or MODEL_DIR / self.model_type.value
        save_dir.mkdir(parents=True, exist_ok=True)

        model_path = save_dir / f"model_v{self.version}.pkl"
        meta_path = save_dir / f"meta_v{self.version}.json"

        with open(model_path, "wb") as f:
            pickle.dump({"model": self.model, "scaler": self.scaler, "feature_names": self.feature_names}, f)

        meta = {
            "model_type": self.model_type.value,
            "version": self.version,
            "status": self.status.value,
            "trained_at": self.trained_at.isoformat() if self.trained_at else None,
            "metrics": self.metrics,
            "feature_importance": self.feature_importance,
        }
        meta_path.write_text(json.dumps(meta, indent=2))

        latest_link = save_dir / "latest.json"
        latest_link.write_text(json.dumps({"version": self.version, "meta": str(meta_path), "model": str(model_path)}))
        return model_path

    def load(self, path: Path | None = None) -> bool:
        """Load model artifacts from disk."""
        load_dir = path or MODEL_DIR / self.model_type.value
        latest_link = load_dir / "latest.json"

        if not latest_link.exists():
            return False

        try:
            latest = json.loads(latest_link.read_text())
            model_path = Path(latest["model"])

            with open(model_path, "rb") as f:
                artifacts = pickle.load(f)  # noqa: S301

            self.model = artifacts["model"]
            self.scaler = artifacts.get("scaler")
            self.feature_names = artifacts.get("feature_names", [])

            meta = json.loads(Path(latest["meta"]).read_text())
            self.version = meta["version"]
            self.status = ModelStatus(meta["status"])
            self.trained_at = datetime.fromisoformat(meta["trained_at"]) if meta.get("trained_at") else None
            self.metrics = meta.get("metrics", {})
            self.feature_importance = meta.get("feature_importance", {})

            logger.info("Loaded %s v%s from %s", self.model_type.value, self.version, load_dir)
            return True
        except Exception as exc:
            logger.warning("Failed to load %s model: %s", self.model_type.value, exc)
            return False

    def _bump_version(self) -> str:
        """Increment patch version."""
        parts = self.version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
        return ".".join(parts)

    @property
    def is_trained(self) -> bool:
        return self.model is not None and self.status in (ModelStatus.READY, ModelStatus.CHAMPION, ModelStatus.CHALLENGER)
