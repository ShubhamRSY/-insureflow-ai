from __future__ import annotations

from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.health.diagnostics import SystemDiagnostics


class TestSystemDiagnostics:
    def test_run_all_returns_checks(self) -> None:
        report = SystemDiagnostics().run_all()
        assert "overall" in report
        assert "llm_mode" in report
        assert len(report["checks"]) >= 8
        components = {c["component"] for c in report["checks"]}
        assert "llm_api_key" in components
        assert "job_store" in components

    def test_never_exposes_full_api_key(self) -> None:
        report = SystemDiagnostics().run_all()
        raw = str(report)
        assert "sk-" not in raw or "..." in raw  # masked if present


class TestDiagnosticsAPI:
    def test_system_diagnostics_public(self) -> None:
        client = TestClient(app)
        resp = client.get("/system/diagnostics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall"] in ("healthy", "degraded", "missing", "error")

    def test_root_points_to_dashboard(self) -> None:
        client = TestClient(app)
        resp = client.get("/")
        assert resp.json()["dashboard"] == "/dashboard"

    def test_dashboard_has_system_tab(self) -> None:
        client = TestClient(app)
        resp = client.get("/dashboard")
        assert "System Status" in resp.text
        assert "llm_api_key" in resp.text or "LLM Mode" in resp.text
