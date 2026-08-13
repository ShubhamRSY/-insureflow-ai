"""Prometheus /metrics + OpenObserve shipper + path normalization."""

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.observability.openobserve import enabled, ingest_url, status
from insureflow.observability.pipeline_hooks import record_pipeline_observability
from insureflow.observability.prometheus_metrics import (
    available,
    normalize_path,
    observe_bind,
    observe_http,
    observe_pipeline,
    render_metrics,
)


class TestPathNormalize:
    def test_uuid_and_numeric(self) -> None:
        assert "{id}" in normalize_path("/pipeline/workflow/550e8400-e29b-41d4-a716-446655440000/bind")
        assert normalize_path("/jobs/12345") == "/jobs/{n}"
        assert normalize_path("/demo-abc123def") == "/{id}"


class TestPrometheusMetrics:
    def test_client_available(self) -> None:
        assert available() is True

    def test_render_contains_help(self) -> None:
        observe_http("GET", "/health", 200, 0.01)
        observe_pipeline(
            {
                "insurance_line": "gl",
                "ai_decision": "refer",
                "status": "complete",
                "quote": {"eligible": True},
            }
        )
        observe_bind("success")
        body, ctype = render_metrics()
        text = body.decode("utf-8")
        assert "text/plain" in ctype
        assert "rytera_http_requests_total" in text
        assert "rytera_pipeline_runs_total" in text
        assert "rytera_quotes_total" in text
        assert "rytera_binds_total" in text

    def test_metrics_endpoint_public(self) -> None:
        client = TestClient(app)
        with patch.dict(os.environ, {"METRICS_BEARER": ""}, clear=False):
            resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "rytera_http_requests_total" in resp.text or "prometheus" in resp.text.lower()

    def test_metrics_bearer_rejects(self) -> None:
        client = TestClient(app)
        with patch.dict(os.environ, {"METRICS_BEARER": "secret-token"}, clear=False):
            denied = client.get("/metrics")
            assert denied.status_code == 401
            ok = client.get("/metrics", headers={"Authorization": "Bearer secret-token"})
            assert ok.status_code == 200


class TestOpenObserve:
    def test_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {"OPENOBSERVE_URL": ""}, clear=False):
            assert enabled() is False
            assert status()["enabled"] is False

    def test_ingest_url_shape(self) -> None:
        with patch.dict(
            os.environ,
            {"OPENOBSERVE_URL": "http://openobserve:5080", "OPENOBSERVE_ORG": "default"},
            clear=False,
        ):
            assert ingest_url("rytera_logs") == "http://openobserve:5080/api/default/rytera_logs/_json"

    def test_pipeline_hook_does_not_raise(self) -> None:
        record_pipeline_observability({"insurance_line": "life", "ai_decision": "refer", "status": "complete", "quote": {"eligible": False}})
