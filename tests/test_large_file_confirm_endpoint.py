"""Regression test for the cross-tenant IDOR in POST /documents/confirm:
without validating that a storage_key actually belongs to the requesting
org+bundle, any authenticated user could register another org's uploaded
S3 object into their own bundle for the pipeline to ingest."""

from __future__ import annotations

import time
from unittest.mock import patch

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


def _create_bundle(client: TestClient, token: str) -> str:
    resp = client.post("/pipeline/bundles", json={"name": "test-bundle"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201, resp.text
    return str(resp.json()["bundle_id"])


def test_confirm_rejects_storage_key_from_a_different_orgs_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)
    token_a, org_a = _signup(client, "orga")
    bundle_a = _create_bundle(client, token_a)

    bundle_b_token, _org_b = _signup(client, "orgb")
    bundle_b = _create_bundle(client, bundle_b_token)

    # A storage key shaped exactly like a real presign for org A's bundle —
    # org B never legitimately received this key.
    org_a_storage_key = f"draft-uploads/{org_a}/{bundle_a}/abc123-secret.pdf"

    resp = client.post(
        f"/pipeline/bundles/{bundle_b}/documents/confirm",
        json={"storage_key": org_a_storage_key, "filename": "stolen.pdf"},
        headers={"Authorization": f"Bearer {bundle_b_token}"},
    )
    assert resp.status_code == 403
    assert "does not belong to this bundle" in resp.json()["detail"]


def test_confirm_accepts_storage_key_matching_own_org_and_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)
    token, org_id = _signup(client, "ownorg")
    bundle_id = _create_bundle(client, token)
    own_key = f"draft-uploads/{org_id}/{bundle_id}/abc123-file.pdf"

    with patch("insureflow.storage.object_storage.head_object", return_value={"size_bytes": 12345, "content_type": "application/pdf"}):
        resp = client.post(
            f"/pipeline/bundles/{bundle_id}/documents/confirm",
            json={"storage_key": own_key, "filename": "file.pdf"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["document_count"] == 1
