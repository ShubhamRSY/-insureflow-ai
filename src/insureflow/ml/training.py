"""Training pipeline — bootstrap all ML models with synthetic data, manage retraining."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from insureflow.ml.features import generate_synthetic_dataset
from insureflow.ml.models import ModelType, TrainingResult
from insureflow.ml.registry import get_ml_registry

logger = logging.getLogger(__name__)

TRAINING_CONFIGS: dict[ModelType, dict[str, Any]] = {
    ModelType.LOSS_PREDICTION: {"n_samples": 2000, "seed": 42},
    ModelType.FRAUD_DETECTION: {"n_samples": 3000, "seed": 43},
    ModelType.PREMIUM_OPTIMIZER: {"n_samples": 2000, "seed": 44},
    ModelType.CHURN_PREDICTION: {"n_samples": 2500, "seed": 45},
}


def train_all_models(force: bool = False) -> list[TrainingResult]:
    """Train (or retrain) all ML models with synthetic data."""
    registry = get_ml_registry()
    results: list[TrainingResult] = []

    for model_type, config in TRAINING_CONFIGS.items():
        model = registry.get(model_type)
        if model is None:
            continue
        if hasattr(model, "is_trained") and model.is_trained and not force:
            logger.info("Skipping %s — already trained", model_type.value)
            continue

        logger.info("Training %s with %d samples...", model_type.value, config["n_samples"])
        X, y = generate_synthetic_dataset(
            n_samples=config["n_samples"],
            model_type=model_type.value,
            seed=config["seed"],
        )
        result = registry.train_model(model_type, X, y)
        if result:
            results.append(result)
            logger.info("  %s: %s", model_type.value, result.metrics)

    for model_type in [ModelType.LOSS_PREDICTION, ModelType.FRAUD_DETECTION]:
        registry.promote_to_champion(model_type)

    return results


def retrain_model(model_type: ModelType, n_samples: int = 2000, seed: int | None = None) -> TrainingResult | None:
    """Retrain a single model with fresh synthetic data."""
    registry = get_ml_registry()
    X, y = generate_synthetic_dataset(
        n_samples=n_samples,
        model_type=model_type.value,
        seed=seed or np.random.randint(0, 10000),
    )
    return registry.train_model(model_type, X, y)


def get_training_status() -> dict[str, Any]:
    """Get current status of all ML models."""
    registry = get_ml_registry()
    return {
        "models": registry.get_status(),
        "history": registry.history,
        "training_configs": {k.value: v for k, v in TRAINING_CONFIGS.items()},
    }
