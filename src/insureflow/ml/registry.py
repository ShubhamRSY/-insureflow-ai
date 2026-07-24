"""ML model registry — tracks all trained models, versions, champion/challenger status."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from insureflow.ml.base import BaseMLModel
from insureflow.ml.behavioral import BehavioralScoringModel
from insureflow.ml.churn import ChurnPredictionModel
from insureflow.ml.fraud_detection import FraudDetectionModel
from insureflow.ml.loss_prediction import LossPredictionModel
from insureflow.ml.models import ModelStatus, ModelType, TrainingResult
from insureflow.ml.portfolio_risk import PortfolioRiskModel
from insureflow.ml.premium_optimizer import PremiumOptimizerModel

logger = logging.getLogger(__name__)

_MODEL_DIR = Path("ml_models")


class MLModelRegistry:
    """Central registry for all ML models — manages lifecycle from training to production."""

    def __init__(self) -> None:
        self._models: dict[ModelType, BaseMLModel | PortfolioRiskModel | BehavioralScoringModel] = {}
        self._history: list[dict[str, Any]] = []
        self._initialize_models()

    def _initialize_models(self) -> None:
        trainable: list[type[BaseMLModel]] = [
            LossPredictionModel,
            FraudDetectionModel,
            PremiumOptimizerModel,
            ChurnPredictionModel,
        ]
        for model_cls in trainable:
            model = model_cls()
            model.load()
            self._models[model.model_type] = model

        self._models[ModelType.PORTFOLIO_RISK] = PortfolioRiskModel()
        self._models[ModelType.BEHAVIORAL_SCORING] = BehavioralScoringModel()

    def get(self, model_type: ModelType) -> BaseMLModel | PortfolioRiskModel | BehavioralScoringModel | None:
        return self._models.get(model_type)

    def train_model(self, model_type: ModelType, X: Any, y: Any, **kwargs: Any) -> TrainingResult | None:
        model = self._models.get(model_type)
        if model is None or not isinstance(model, BaseMLModel):
            logger.warning("Cannot train %s — not a trainable model", model_type.value)
            return None

        result = model.train(X, y, **kwargs)
        model.save()
        self._history.append(
            {
                "model_type": model_type.value,
                "version": result.model_version,
                "metrics": result.metrics,
                "trained_at": result.trained_at.isoformat(),
            }
        )
        return result

    def promote_to_champion(self, model_type: ModelType) -> bool:
        model = self._models.get(model_type)
        if model is None or not isinstance(model, BaseMLModel):
            return False
        for m in self._models.values():
            if isinstance(m, BaseMLModel) and m.model_type == model_type and m.status == ModelStatus.CHAMPION:
                m.status = ModelStatus.RETIRED
        model.status = ModelStatus.CHAMPION
        model.save()
        return True

    def get_status(self) -> list[dict[str, Any]]:
        statuses = []
        for model_type, model in self._models.items():
            info: dict[str, Any] = {
                "model_type": model_type.value,
                "model_name": getattr(model, "model_name", model_type.value),
                "version": getattr(model, "version", "N/A"),
                "is_trained": getattr(model, "is_trained", True),
                "status": getattr(model, "status", ModelStatus.READY).value if hasattr(model, "status") else "ready",
            }
            if isinstance(model, BaseMLModel):
                info["metrics"] = model.metrics
            statuses.append(info)
        return statuses

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)


_registry: MLModelRegistry | None = None


def get_ml_registry() -> MLModelRegistry:
    global _registry
    if _registry is None:
        _registry = MLModelRegistry()
    return _registry
