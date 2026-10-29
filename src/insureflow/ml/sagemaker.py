"""Serve ML predictions from a SageMaker endpoint instead of in-process.

Set SAGEMAKER_ML_ENDPOINT on the app and get_insurance_model() returns a
SageMakerModel. The endpoint runs this same package (scripts/sagemaker_serve.py ->
handle_invocation), so the LOB lookup, production gate and heuristic fallback
behave exactly as they do locally. A failed endpoint call raises
MLServiceUnavailableError (a plain 503), never a silent heuristic answer.
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np

from insureflow.ml.base import BaseMLModel
from insureflow.ml.models import FeatureVector, ModelType


class MLServiceUnavailableError(RuntimeError):
    pass


def sagemaker_endpoint() -> str:
    return os.getenv("SAGEMAKER_ML_ENDPOINT", "").strip()


_client: Any = None


def _invoke(payload: dict[str, Any]) -> dict[str, Any]:
    global _client
    try:
        if _client is None:
            import boto3
            from botocore.config import Config

            # Serverless cold starts can take a while; one retry covers a throttle.
            _client = boto3.client("sagemaker-runtime", config=Config(read_timeout=70, retries={"max_attempts": 2}))
        resp = _client.invoke_endpoint(
            EndpointName=sagemaker_endpoint(),
            ContentType="application/json",
            Body=json.dumps(payload, default=str),
        )
        return json.loads(resp["Body"].read())
    except Exception as exc:  # noqa: BLE001 - any AWS/network failure means "service unavailable"
        raise MLServiceUnavailableError(f"ML prediction service unavailable: {type(exc).__name__}") from exc


class SageMakerModel(BaseMLModel):
    """Stand-in for a local model; predict/explain run on the endpoint."""

    def __init__(self, model_type: ModelType, insurance_line: str | None) -> None:
        super().__init__()
        self.model_type = model_type
        self.model_name = f"sagemaker:{model_type.value}"
        self.insurance_line = insurance_line

    def _call(self, op: str, fv: FeatureVector) -> dict[str, Any]:
        return _invoke({"op": op, "model_type": self.model_type.value, "insurance_line": self.insurance_line, "features": fv.model_dump(mode="json")})

    def predict(self, fv: FeatureVector) -> dict[str, Any]:
        return self._call("predict", fv)

    def explain(self, fv: FeatureVector) -> dict[str, Any]:
        return self._call("explain", fv)

    # Training and feature work happen on the endpoint side, never here.
    def _build_model(self) -> Any:
        raise NotImplementedError

    def _extract_features(self, fv: FeatureVector) -> np.ndarray:
        raise NotImplementedError

    def _get_feature_names(self) -> list[str]:
        raise NotImplementedError

    def _compute_feature_importance(self) -> dict[str, float]:
        raise NotImplementedError

    def _compute_metrics(self, y_train: np.ndarray, train_pred: np.ndarray, y_val: np.ndarray, val_pred: np.ndarray) -> dict[str, float]:
        raise NotImplementedError

    def _fallback_prediction(self, fv: FeatureVector) -> dict[str, Any]:
        raise NotImplementedError

    def _format_prediction(self, fv: FeatureVector, raw_prediction: Any) -> dict[str, Any]:
        raise NotImplementedError


def handle_invocation(payload: dict[str, Any]) -> dict[str, Any]:
    """Endpoint side: run the request against the local model files."""
    from insureflow.ml.lob_registry import get_lob_registry

    model_type = ModelType(payload["model_type"])
    model = get_lob_registry().get(model_type, payload.get("insurance_line"))
    if model is None:
        return {"error": f"No {model_type.value} model available"}
    fv = FeatureVector(**payload.get("features", {}))
    return model.explain(fv) if payload.get("op") == "explain" else model.predict(fv)
