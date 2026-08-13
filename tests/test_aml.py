"""Sanctions screening + SAR filing."""

from __future__ import annotations

from fastapi.testclient import TestClient

from insureflow.aml.sanctions import screen_name
from insureflow.aml.sar import SarService
from insureflow.api import app
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import clear_user_store, get_user_store
from insureflow.storage.job_store import MemoryJobStore

client = TestClient(app)


def _headers(role: Role = Role.VIEWER, org_id: str = "acme") -> dict[str, str]:
    clear_user_store()
    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=role, org_id=org_id)
    token = create_access_token({"sub": "uw", "role": role.value, "org_id": org_id})
    return {"Authorization": f"Bearer {token}"}


def test_clean_name_clears() -> None:
    result = screen_name("Pacific Coast Distributors LLC")
    assert result.cleared is True
    assert result.recommended_action == "clear"
    assert result.hits == []


def test_sdn_hit_blocks() -> None:
    result = screen_name("Rytera Sanctioned Test Person")
    assert result.cleared is False
    assert result.recommended_action == "block_and_file_sar"
    assert result.hits[0].matched_name == "Rytera Sanctioned Test Person"
    assert result.hits[0].score >= 0.92


def test_alias_hit_refers() -> None:
    result = screen_name("El Chapo")
    assert result.cleared is False
    assert result.hits
    assert result.hits[0].matched_name == "Joaquin Guzman Loera"


def test_sar_service_roundtrip() -> None:
    svc = SarService(store=MemoryJobStore())
    filing = svc.file(
        subject_name="Acme Blocked Holdings LLC",
        org_id="acme",
        activity_type="sanctions_evasion",
        amount=250_000,
        narrative="Wire attempted after SDN hit.",
        status="draft",
        filed_by="uw",
    )
    assert filing.sar_id.startswith("SAR-")
    fetched = svc.get(filing.sar_id, org_id="acme")
    assert fetched is not None
    assert fetched.subject_name == "Acme Blocked Holdings LLC"
    listed = svc.list(org_id="acme")
    assert len(listed) == 1
    updated = svc.update_status(filing.sar_id, "filed", org_id="acme")
    assert updated.status == "filed"


def test_sar_requires_subject() -> None:
    import pytest

    svc = SarService(store=MemoryJobStore())
    with pytest.raises(ValueError, match="subject_name"):
        svc.file(subject_name="  ", org_id="acme")


def test_aml_api() -> None:
    h = _headers()
    screen = client.post("/aml/sanctions/screen", headers=h, json={"name": "SANCTIONED PERSON TEST"})
    assert screen.status_code == 200
    assert screen.json()["cleared"] is False

    created = client.post(
        "/aml/sar",
        headers=h,
        json={"subject_name": "Test Subject", "activity_type": "fraud", "amount": 12000, "narrative": "Structuring deposits"},
    )
    assert created.status_code == 200
    sar_id = created.json()["sar_id"]

    listed = client.get("/aml/sar", headers=h)
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1

    got = client.get(f"/aml/sar/{sar_id}", headers=h)
    assert got.status_code == 200
    assert got.json()["subject_name"] == "Test Subject"

    status = client.post(f"/aml/sar/{sar_id}/status", headers=h, json={"status": "filed"})
    assert status.status_code == 200
    assert status.json()["status"] == "filed"

    missing = client.get("/aml/sar/SAR-MISSING", headers=h)
    assert missing.status_code == 404
