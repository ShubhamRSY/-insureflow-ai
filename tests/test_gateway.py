"""Tests for the bundled Rytera integration gateway."""

from __future__ import annotations

from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.config import settings

client = TestClient(app)
GATEWAY_KEY = settings.integration_gateway_api_key
AUTH = {"Authorization": f"Bearer {GATEWAY_KEY}"}


def test_gateway_health_requires_auth() -> None:
    resp = client.get("/integrations/oracles/clue/v2/health")
    assert resp.status_code == 401


def test_gateway_clue_health_ok() -> None:
    resp = client.get("/integrations/oracles/clue/v2/health", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["service"] == "clue"


def test_gateway_clue_query() -> None:
    resp = client.post(
        "/integrations/oracles/clue/v2/queries",
        headers=AUTH,
        json={"legal_name": "Pacific Marine LLC"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_claims_found"] >= 1


def test_gateway_ncci_experience() -> None:
    resp = client.post(
        "/integrations/oracles/ncci/v2/experience",
        headers=AUTH,
        json={"legal_name": "Pacific Marine LLC", "fein": "12-3456789"},
    )
    assert resp.status_code == 200
    assert resp.json()["experience_mods"]


def test_integration_health_service_live_with_local_gateway() -> None:
    from insureflow.integrations.health import IntegrationHealthService

    clue = next(f for f in IntegrationHealthService().check_all()["feeds"] if f["name"] == "CLUE")
    assert clue["configured"] is True
    assert clue["reachable"] is True
    assert clue["mode"] == "live"


def test_landing_page_html() -> None:
    resp = client.get("/", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert "Rytera" in resp.text
