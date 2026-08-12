"""LOB-scoped ML model registry — one trained model per insurance line × model type."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from insureflow.insurance.commercial_lobs import list_production_insurance_lines
from insureflow.ml.base import MODEL_DIR, BaseMLModel
from insureflow.ml.churn import ChurnPredictionModel
from insureflow.ml.fraud_detection import FraudDetectionModel
from insureflow.ml.lob_profiles import INSURANCE_LOB_MODEL_TYPES
from insureflow.ml.loss_prediction import LossPredictionModel
from insureflow.ml.models import ModelStatus, ModelType
from insureflow.ml.premium_optimizer import PremiumOptimizerModel
from insureflow.ml.registry import get_ml_registry

logger = logging.getLogger(__name__)

_MODEL_CLASS: dict[ModelType, type[BaseMLModel]] = {
    ModelType.LOSS_PREDICTION: LossPredictionModel,
    ModelType.FRAUD_DETECTION: FraudDetectionModel,
    ModelType.PREMIUM_OPTIMIZER: PremiumOptimizerModel,
    ModelType.CHURN_PREDICTION: ChurnPredictionModel,
}


def lob_model_dir(insurance_line: str, model_type: ModelType) -> Path:
    safe = insurance_line.replace("/", "_").strip().lower()
    return MODEL_DIR / "lines" / safe / model_type.value


class LOBModelRegistry:
    """Caches and serves per-LOB insurance ML models."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, ModelType], BaseMLModel] = {}

    def _create(self, model_type: ModelType) -> BaseMLModel:
        cls = _MODEL_CLASS[model_type]
        return cls()

    def get(self, model_type: ModelType, insurance_line: str | None) -> BaseMLModel | None:
        """Return LOB-scoped model when trained; else global champion; else None."""
        global_registry = get_ml_registry()
        if not insurance_line:
            model = global_registry.get(model_type)
            return model if isinstance(model, BaseMLModel) else None

        key = (insurance_line.strip().lower(), model_type)
        if key not in self._cache:
            inst = self._create(model_type)
            inst.load(path=lob_model_dir(insurance_line, model_type))
            self._cache[key] = inst

        lob_model = self._cache[key]
        if isinstance(lob_model, BaseMLModel) and lob_model.is_trained:
            return lob_model

        global_model = global_registry.get(model_type)
        if isinstance(global_model, BaseMLModel) and global_model.is_trained and global_model.gate_passed is True:
            return global_model
        return lob_model if isinstance(lob_model, BaseMLModel) else global_model if isinstance(global_model, BaseMLModel) else None

    def train_and_save(
        self,
        model_type: ModelType,
        insurance_line: str,
        X: Any,
        y: Any,
        *,
        gate_passed: bool,
    ) -> BaseMLModel | None:
        model = self._create(model_type)
        result = model.train(X, y)
        model.gate_passed = gate_passed
        if gate_passed:
            model.status = ModelStatus.CHAMPION
        model.save(path=lob_model_dir(insurance_line, model_type))
        key = (insurance_line.strip().lower(), model_type)
        self._cache[key] = model
        logger.info(
            "LOB model %s/%s v%s gate=%s metrics=%s",
            insurance_line,
            model_type.value,
            result.model_version,
            gate_passed,
            result.metrics,
        )
        return model

    def status(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in list_production_insurance_lines():
            for mt_name in INSURANCE_LOB_MODEL_TYPES:
                mt = ModelType(mt_name)
                path = lob_model_dir(line, mt)
                latest = path / "latest.json"
                if not latest.exists():
                    rows.append(
                        {
                            "insurance_line": line,
                            "model_type": mt_name,
                            "trained": False,
                            "gate_passed": None,
                        }
                    )
                    continue
                model = self._create(mt)
                model.load(path=path)
                rows.append(
                    {
                        "insurance_line": line,
                        "model_type": mt_name,
                        "trained": model.is_trained,
                        "gate_passed": model.gate_passed,
                        "version": model.version,
                        "status": model.status.value,
                        "metrics": model.metrics,
                    }
                )
        return rows


_lob_registry: LOBModelRegistry | None = None


def get_lob_registry() -> LOBModelRegistry:
    global _lob_registry
    if _lob_registry is None:
        _lob_registry = LOBModelRegistry()
    return _lob_registry


def get_insurance_model(model_type: ModelType, insurance_line: str | None = None) -> BaseMLModel | None:
    """Primary entry point: LOB model when available, else global."""
    return get_lob_registry().get(model_type, insurance_line)
