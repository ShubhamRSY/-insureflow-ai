"""In-product platform stack — not GKE / Lambda / Datadog / LaunchDarkly."""

from __future__ import annotations

from pytest import MonkeyPatch

from insureflow.flags import current_flags
from insureflow.ops.stack import platform_stack


def test_flags_read_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_MODE", "true")
    monkeypatch.setenv("SSO_REQUIRED", "true")
    monkeypatch.setenv("ALLOW_VISION_EGRESS", "false")
    flags = current_flags()
    assert flags["BANK_MODE"] is True
    assert flags["SSO_REQUIRED"] is True
    assert flags["ALLOW_VISION_EGRESS"] is False


def test_platform_stack_shape() -> None:
    stack = platform_stack()
    assert stack["compute"]["bank"] == "ecs_fargate"
    assert "gke" in stack["compute"]["not_required"]
    assert "lambda" in stack["compute"]["not_required"]
    assert "admin" in stack["identity"]["app_rbac"]
    assert stack["security"]["pii_redaction"] is True
    assert "bind_gates" in stack["security"]["policy_checks"]
    assert stack["communication"]["sync"] == "rest_fastapi"
    assert "kafka" in stack["communication"]["not_required"]
    assert "launchdarkly" in stack["supporting"]["not_required"]
    assert stack["observability"]["cost"] == "GET /billing/usage"
    assert "datadog" in stack["observability"]["not_required"]
    assert "BANK_MODE" in stack["flags"]


def test_platform_stack_authenticated() -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app
    from insureflow.auth import Role
    from insureflow.auth.jwt import create_access_token
    from insureflow.auth.models import User
    from insureflow.auth.store import clear_user_store, get_user_store

    clear_user_store()
    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=Role.VIEWER, org_id="acme")
    token = create_access_token({"sub": "uw", "role": Role.VIEWER.value, "org_id": "acme"})
    client = TestClient(app)
    resp = client.get("/platform/stack", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["org_id"] == "acme"
    assert body["ci_cd"]["github_actions"] is True


def test_cloudwatch_metric_noop_without_bank(monkeypatch: MonkeyPatch) -> None:
    from insureflow.observability.cloudwatch import emit_metric

    monkeypatch.delenv("BANK_MODE", raising=False)
    monkeypatch.delenv("CLOUDWATCH_METRICS", raising=False)
    emit_metric("PipelineRuns", 1.0)  # must not raise
