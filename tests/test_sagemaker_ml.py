"""SageMaker ML serving: endpoint side matches local, app side forwards, failure is a 503."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from insureflow.ml import sagemaker as sm
from insureflow.ml.lob_registry import get_insurance_model
from insureflow.ml.models import FeatureVector, ModelType

FEATURES = {"tiv": 2_500_000, "loss_ratio": 0.42, "prior_claims_count": 1, "credit_score": 710, "product_line": "commercial_property"}


SERVED = [
    (ModelType.LOSS_PREDICTION, "commercial_property"),
    (ModelType.FRAUD_DETECTION, "commercial_property"),
    (ModelType.PREMIUM_OPTIMIZER, "commercial_property"),
    (ModelType.CHURN_PREDICTION, "commercial_property"),
    (ModelType.LOSS_PREDICTION, None),
    (ModelType.MORTGAGE_DEFAULT_RISK, None),
    (ModelType.LENDING_DEFAULT_RISK, None),
]


@pytest.mark.parametrize(("mt", "line"), SERVED)
def test_endpoint_side_matches_local(monkeypatch: pytest.MonkeyPatch, mt: ModelType, line: str | None) -> None:
    monkeypatch.delenv("SAGEMAKER_ML_ENDPOINT", raising=False)
    local = get_insurance_model(mt, line)
    if local is None:
        pytest.skip(f"no {mt.value} model on this machine")
    want = local.predict(FeatureVector(**FEATURES))
    got = sm.handle_invocation({"op": "predict", "model_type": mt.value, "insurance_line": line, "features": FEATURES})
    want.pop("latency_ms", None)
    got.pop("latency_ms", None)
    assert got == want


def test_app_side_forwards_to_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict[str, Any]] = []
    monkeypatch.setenv("SAGEMAKER_ML_ENDPOINT", "rytera-ml")
    monkeypatch.setattr(sm, "_invoke", lambda payload: sent.append(payload) or {"ok": True})
    model = get_insurance_model(ModelType.FRAUD_DETECTION, "auto")
    assert isinstance(model, sm.SageMakerModel)
    assert model.predict(FeatureVector(tiv=1)) == {"ok": True}
    assert sent[0]["op"] == "predict" and sent[0]["model_type"] == "fraud_detection" and sent[0]["insurance_line"] == "auto"


def test_endpoint_failure_is_a_plain_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAGEMAKER_ML_ENDPOINT", "rytera-ml")
    monkeypatch.setenv("INSUREFLOW_AUTH_TESTING", "1")

    class Down:
        def invoke_endpoint(self, **_: Any) -> Any:
            raise TimeoutError("cold start")

    monkeypatch.setattr(sm, "_client", Down())
    from insureflow.api.main import app
    from insureflow.auth import Role
    from insureflow.auth.dependencies import get_current_user
    from insureflow.auth.models import TokenData

    app.dependency_overrides[get_current_user] = lambda: TokenData(username="t", role=Role.ADMIN, org_id="o")
    try:
        r = TestClient(app, raise_server_exceptions=False).post("/ml/predict/fraud", json={"tiv": 1, "insurance_line": "auto"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert "Nothing was scored" in r.json()["detail"]
