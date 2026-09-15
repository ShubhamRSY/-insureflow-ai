"""Regression test for the unauthenticated, cross-tenant /api/resubmit/*
endpoints: without an auth dependency and org-scoped ownership check, any
caller (even unauthenticated) could list every org's pending resubmit
requests, or waive another org's document requirement, by bundle_id."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient


def _make_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("BANK_MODE", "false")
    monkeypatch.setenv("ALLOW_OPEN_REGISTRATION", "true")
    monkeypatch.setenv("INSUREFLOW_AUTH_TESTING", "1")
    from insureflow.api import main as _main

    _main.limiter.enabled = False
    from insureflow.api.main import app

    return TestClient(app, raise_server_exceptions=False)


def _unique(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000) % 100000}"


def _signup(client: TestClient, prefix: str) -> tuple[str, str]:
    """Returns (token, org_id) for a freshly created org."""
    uname = _unique(prefix)
    resp = client.post(
        "/auth/signup",
        json={
            "username": uname,
            "email": f"{uname}@example.com",
            "password": "StrongPass1!",
            "company_name": f"{prefix} Co",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["token"], body["org_id"]


def _seed_job(bundle_id: str, org_id: str) -> None:
    from insureflow.storage.job_store import get_job_store

    get_job_store().set("insurance", bundle_id, {"status": "completed"}, org_id=org_id)


def _seed_resubmit_request(bundle_id: str) -> None:
    from insureflow.ingestion.resubmit import ResubmitManager

    ResubmitManager().create_resubmit_request(bundle_id=bundle_id, filename="dec-page.pdf", reason="illegible scan")


def test_resubmit_endpoints_reject_unauthenticated_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)
    bundle_id = f"bundle-{_unique('anon')}"
    _seed_job(bundle_id, "some-org")
    _seed_resubmit_request(bundle_id)

    assert client.get("/api/resubmit/pending").status_code in (401, 403)
    assert client.get(f"/api/resubmit/{bundle_id}/summary").status_code in (401, 403)
    assert client.post(f"/api/resubmit/{bundle_id}/waive", params={"filename": "dec-page.pdf"}).status_code in (401, 403)


def test_resubmit_endpoints_reject_a_different_orgs_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)
    token_a, org_a = _signup(client, "resuborga")
    bundle_a = f"bundle-{_unique('a')}"
    _seed_job(bundle_a, org_a)
    _seed_resubmit_request(bundle_a)

    token_b, _org_b = _signup(client, "resuborgb")

    resp = client.get(f"/api/resubmit/{bundle_a}/summary", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404

    resp = client.post(
        f"/api/resubmit/{bundle_a}/waive",
        params={"filename": "dec-page.pdf"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404

    # Org B's unscoped "list pending" must not surface org A's request.
    resp = client.get("/api/resubmit/pending", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 200
    assert all(r.get("bundle_id") != bundle_a for r in resp.json()["pending"])


def test_resubmit_endpoints_accept_the_owning_org(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)
    token, org_id = _signup(client, "resubown")
    bundle_id = f"bundle-{_unique('own')}"
    _seed_job(bundle_id, org_id)
    _seed_resubmit_request(bundle_id)

    resp = client.get(f"/api/resubmit/{bundle_id}/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["bundle_id"] == bundle_id

    resp = client.get("/api/resubmit/pending", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert any(r.get("bundle_id") == bundle_id for r in resp.json()["pending"])

    resp = client.post(
        f"/api/resubmit/{bundle_id}/waive",
        params={"filename": "dec-page.pdf"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True
