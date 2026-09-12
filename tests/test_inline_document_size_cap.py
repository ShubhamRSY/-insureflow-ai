from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import clear_user_store, get_user_store
from insureflow.storage.draft_bundle_store import MAX_DOCUMENT_BYTES

_OVERSIZED_BASE64 = base64.b64encode(b"x" * (MAX_DOCUMENT_BYTES + 1024)).decode()


@pytest.fixture(autouse=True)
def reset_users() -> None:
    clear_user_store()


def _auth_headers(org_id: str = "acme", role: Role = Role.ADMIN) -> dict[str, str]:
    get_user_store()["admin"] = User(username="admin", hashed_password="unused", role=role, org_id=org_id)
    token = create_access_token({"sub": "admin", "role": role.value, "org_id": org_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/pipeline/run", {"documents": [{"filename": "huge.pdf", "content": _OVERSIZED_BASE64, "encoding": "base64"}]}),
        ("/v2/pipeline/run", {"documents": [{"filename": "huge.pdf", "content": _OVERSIZED_BASE64, "encoding": "base64"}]}),
        ("/pipeline/v2/run", {"documents": [{"filename": "huge.pdf", "content": _OVERSIZED_BASE64, "encoding": "base64"}]}),
        ("/mortgage/pipeline/run", {"documents": [{"filename": "huge.pdf", "content": _OVERSIZED_BASE64, "encoding": "base64"}]}),
    ],
)
def test_oversized_inline_document_rejected(path: str, payload: dict) -> None:
    client = TestClient(app)
    resp = client.post(path, json=payload, headers=_auth_headers())
    assert resp.status_code == 413
    assert "MB inline-upload limit" in resp.json()["detail"]


def test_s3_ref_document_within_own_org_skips_the_inline_size_check() -> None:
    """s3_ref documents are references, not inline content — the size lives
    in S3/object_storage, so the inline check must not (mis)apply to them,
    as long as the storage key belongs to the caller's own org."""
    client = TestClient(app)
    headers = _auth_headers()
    org_id = client.get("/auth/me", headers=headers).json()["org_id"]
    resp = client.post(
        "/pipeline/run",
        json={"documents": [{"filename": "huge.pdf", "content": f"draft-uploads/{org_id}/b1/huge.pdf", "encoding": "s3_ref"}], "use_celery": False},
        headers=headers,
    )
    assert resp.status_code == 202


def test_s3_ref_document_from_another_org_is_rejected() -> None:
    """Cross-tenant IDOR guard: a caller must not be able to submit another
    org's storage key and have the pipeline download/process that file."""
    client = TestClient(app)
    resp = client.post(
        "/pipeline/run",
        json={"documents": [{"filename": "huge.pdf", "content": "draft-uploads/some-other-org/b1/huge.pdf", "encoding": "s3_ref"}], "use_celery": False},
        headers=_auth_headers(),
    )
    assert resp.status_code == 403


def test_mortgage_s3_ref_document_from_another_org_is_rejected() -> None:
    client = TestClient(app)
    resp = client.post(
        "/mortgage/pipeline/run",
        json={"documents": [{"filename": "huge.pdf", "content": "mortgage-uploads/some-other-org/b1/huge.pdf", "encoding": "s3_ref"}]},
        headers=_auth_headers(),
    )
    assert resp.status_code == 403


def test_doc_quality_check_requires_auth() -> None:
    client = TestClient(app)
    resp = client.post("/api/doc-quality/check", json=[{"filename": "a.txt", "content": "hello world", "encoding": "utf-8"}])
    assert resp.status_code in (401, 403)


def test_doc_quality_check_rejects_oversized_document() -> None:
    client = TestClient(app)
    resp = client.post(
        "/api/doc-quality/check",
        json=[{"filename": "huge.pdf", "content": _OVERSIZED_BASE64, "encoding": "base64"}],
        headers=_auth_headers(),
    )
    assert resp.status_code == 413
    assert "MB inline-upload limit" in resp.json()["detail"]


def test_doc_quality_check_passes_small_document_when_authed() -> None:
    client = TestClient(app)
    resp = client.post(
        "/api/doc-quality/check",
        json=[{"filename": "a.txt", "content": "hello world " * 20, "encoding": "utf-8"}],
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    assert "decision" in resp.json()
