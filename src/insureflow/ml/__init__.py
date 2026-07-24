"""Rytera ML module — predictive analytics for insurance underwriting.

All heavy imports (numpy, sklearn) are deferred to avoid startup memory spikes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from insureflow.ml.base import BaseMLModel
    from insureflow.ml.behavioral import BehavioralScoringModel
    from insureflow.ml.churn import ChurnPredictionModel
    from insureflow.ml.fraud_detection import FraudDetectionModel
    from insureflow.ml.loss_prediction import LossPredictionModel
    from insureflow.ml.models import (
        BehavioralScore,
        ChurnPrediction,
        FeatureVector,
        FraudScore,
        LossPrediction,
        ModelStatus,
        ModelType,
        PortfolioRiskResult,
        PredictionRequest,
        PredictionResponse,
        PremiumRecommendation,
        TrainingResult,
    )
    from insureflow.ml.portfolio_risk import PortfolioRiskModel
    from insureflow.ml.premium_optimizer import PremiumOptimizerModel
    from insureflow.ml.registry import MLModelRegistry, get_ml_registry
    from insureflow.ml.training import get_training_status, retrain_model, train_all_models


def __getattr__(name: str) -> object:
    """Lazy import — only loads sklearn/numpy when an ML attribute is accessed."""
    from importlib import import_module

    _LAZY_MAP: dict[str, tuple[str, str]] = {
        "BaseMLModel": ("insureflow.ml.base", "BaseMLModel"),
        "BehavioralScoringModel": ("insureflow.ml.behavioral", "BehavioralScoringModel"),
        "ChurnPredictionModel": ("insureflow.ml.churn", "ChurnPredictionModel"),
        "FraudDetectionModel": ("insureflow.ml.fraud_detection", "FraudDetectionModel"),
        "LossPredictionModel": ("insureflow.ml.loss_prediction", "LossPredictionModel"),
        "PortfolioRiskModel": ("insureflow.ml.portfolio_risk", "PortfolioRiskModel"),
        "PremiumOptimizerModel": ("insureflow.ml.premium_optimizer", "PremiumOptimizerModel"),
        "MLModelRegistry": ("insureflow.ml.registry", "MLModelRegistry"),
        "get_ml_registry": ("insureflow.ml.registry", "get_ml_registry"),
        "get_training_status": ("insureflow.ml.training", "get_training_status"),
        "retrain_model": ("insureflow.ml.training", "retrain_model"),
        "train_all_models": ("insureflow.ml.training", "train_all_models"),
        "FeatureVector": ("insureflow.ml.models", "FeatureVector"),
        "ModelType": ("insureflow.ml.models", "ModelType"),
        "ModelStatus": ("insureflow.ml.models", "ModelStatus"),
        "LossPrediction": ("insureflow.ml.models", "LossPrediction"),
        "FraudScore": ("insureflow.ml.models", "FraudScore"),
        "PremiumRecommendation": ("insureflow.ml.models", "PremiumRecommendation"),
        "PortfolioRiskResult": ("insureflow.ml.models", "PortfolioRiskResult"),
        "ChurnPrediction": ("insureflow.ml.models", "ChurnPrediction"),
        "BehavioralScore": ("insureflow.ml.models", "BehavioralScore"),
        "TrainingResult": ("insureflow.ml.models", "TrainingResult"),
        "PredictionRequest": ("insureflow.ml.models", "PredictionRequest"),
        "PredictionResponse": ("insureflow.ml.models", "PredictionResponse"),
    }

    if name in _LAZY_MAP:
        mod_path, attr = _LAZY_MAP[name]
        mod = import_module(mod_path)
        return getattr(mod, attr)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseMLModel",
    "BehavioralScoringModel",
    "BehavioralScore",
    "ChurnPrediction",
    "ChurnPredictionModel",
    "FeatureVector",
    "FraudDetectionModel",
    "FraudScore",
    "LossPrediction",
    "LossPredictionModel",
    "MLModelRegistry",
    "ModelStatus",
    "ModelType",
    "PortfolioRiskModel",
    "PortfolioRiskResult",
    "PremiumOptimizerModel",
    "PremiumRecommendation",
    "PredictionRequest",
    "PredictionResponse",
    "TrainingResult",
    "get_ml_registry",
    "get_training_status",
    "retrain_model",
    "train_all_models",
]
