"""80+ marketplace catalog + connect registry."""

from __future__ import annotations

from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import clear_user_store, get_user_store
from insureflow.marketplace.catalog import MARKETPLACE_SOURCES, get_source, list_marketplace_sources
from insureflow.marketplace.registry import connect_source, disconnect_source, list_connected_sources

client = TestClient(app)


def _headers(role: Role = Role.VIEWER, org_id: str = "acme") -> dict[str, str]:
    clear_user_store()
    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=role, org_id=org_id)
    token = create_access_token({"sub": "uw", "role": role.value, "org_id": org_id})
    return {"Authorization": f"Bearer {token}"}


def test_catalog_has_at_least_80_sources() -> None:
    assert len(MARKETPLACE_SOURCES) >= 80
    ids = [s["id"] for s in MARKETPLACE_SOURCES]
    assert len(ids) == len(set(ids))
    assert "bold-penguin" in ids
    assert "ofac-sdn" in ids
    assert "plaid" in ids
    assert "guidewire-policycenter" in ids


def test_filter_by_vertical_and_query() -> None:
    kyc = list_marketplace_sources(category="kyc")
    assert kyc
    assert all(s["type"] == "kyc" for s in kyc)
    mortgage = list_marketplace_sources(vertical="mortgage")
    assert any(s["id"] == "fannie-mae" for s in mortgage)
    clue = list_marketplace_sources(q="clue")
    assert any(s["id"] == "clue" for s in clue)
    assert get_source("missing-source") is None


def test_connect_registry_roundtrip() -> None:
    rec = connect_source("clue", config={"api_key": "k"}, label="CLUE prod", org_id="acme")
    assert rec["connected"] is True
    assert rec["id"] == "clue"
    connected = list_connected_sources(org_id="acme")
    assert any(c["id"] == "clue" for c in connected)
    assert disconnect_source("clue", org_id="acme") is True
    assert disconnect_source("clue", org_id="acme") is False


def test_connect_unknown_source_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="Unknown marketplace source"):
        connect_source("not-a-vendor", org_id="acme")


def test_marketplace_api_list_and_connect() -> None:
    h = _headers()
    listed = client.get("/marketplace/sources", headers=h)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 80
    assert body["count"] >= 80

    detail = client.get("/marketplace/sources/plaid", headers=h)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Plaid"

    missing = client.get("/marketplace/sources/nope", headers=h)
    assert missing.status_code == 404

    connected = client.post("/marketplace/connect/plaid", headers=h, json={"config": {"api_key": "pk"}, "label": "Plaid sandbox"})
    assert connected.status_code == 200
    assert connected.json()["connected"] is True

    conns = client.get("/marketplace/connections", headers=h)
    assert conns.status_code == 200
    assert any(c["id"] == "plaid" for c in conns.json()["connections"])

    gone = client.delete("/marketplace/connect/plaid", headers=h)
    assert gone.status_code == 200
