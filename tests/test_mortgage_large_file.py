from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import clear_user_store, get_user_store
from insureflow.ingestion.mortgage.loader import MortgageSubmissionLoader
from insureflow.storage.object_storage import MAX_PROCESSABLE_BYTES


@pytest.fixture(autouse=True)
def reset_users() -> None:
    clear_user_store()


def _auth_headers(role: Role = Role.ADMIN) -> dict[str, str]:
    get_user_store()["admin"] = User(username="admin", hashed_password="unused", role=role, org_id="acme")
    token = create_access_token({"sub": "admin", "role": role.value, "org_id": "acme"})
    return {"Authorization": f"Bearer {token}"}


def test_presign_requires_object_storage_configured() -> None:
    client = TestClient(app)
    with patch("insureflow.storage.object_storage.object_storage_configured", return_value=False):
        resp = client.post(
            "/mortgage/pipeline/documents/presign",
            json={"bundle_id": "b1", "filename": "closing.pdf"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 400


def test_presign_uses_mortgage_uploads_prefix() -> None:
    client = TestClient(app)
    with (
        patch("insureflow.storage.object_storage.object_storage_configured", return_value=True),
        patch(
            "insureflow.storage.object_storage.presign_upload",
            return_value={"url": "https://x", "fields": {}, "storage_key": "mortgage-uploads/acme/b1/x-closing.pdf", "bucket": "b", "expires_in": 900, "max_bytes": 1},
        ) as mock_presign,
    ):
        resp = client.post(
            "/mortgage/pipeline/documents/presign",
            json={"bundle_id": "b1", "filename": "closing.pdf"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 200
    assert resp.json()["storage_key"].startswith("mortgage-uploads/acme/b1/")
    assert mock_presign.call_args.kwargs["prefix"] == "mortgage-uploads"


def test_confirm_rejects_storage_key_from_another_org_or_bundle() -> None:
    client = TestClient(app)
    resp = client.post(
        "/mortgage/pipeline/documents/confirm",
        json={"bundle_id": "b1", "storage_key": "mortgage-uploads/other-org/b1/x.pdf", "filename": "closing.pdf"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 403


def test_confirm_accepts_matching_key_and_returns_s3_ref_document() -> None:
    client = TestClient(app)
    headers = _auth_headers()
    org_id = client.get("/auth/me", headers=headers).json()["org_id"]
    storage_key = f"mortgage-uploads/{org_id}/b1/x-closing.pdf"
    with patch("insureflow.storage.object_storage.head_object", return_value={"size_bytes": 123, "content_type": "application/pdf"}):
        resp = client.post(
            "/mortgage/pipeline/documents/confirm",
            json={"bundle_id": "b1", "storage_key": storage_key, "filename": "closing.pdf"},
            headers=headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["encoding"] == "s3_ref"
    assert body["content"] == storage_key
    assert body["size_bytes"] == 123


def test_confirm_404s_when_upload_never_landed() -> None:
    client = TestClient(app)
    headers = _auth_headers()
    org_id = client.get("/auth/me", headers=headers).json()["org_id"]
    with patch("insureflow.storage.object_storage.head_object", return_value=None):
        resp = client.post(
            "/mortgage/pipeline/documents/confirm",
            json={"bundle_id": "b1", "storage_key": f"mortgage-uploads/{org_id}/b1/x-closing.pdf", "filename": "closing.pdf"},
            headers=headers,
        )
    assert resp.status_code == 400


def test_loader_flags_oversized_s3_ref_document_without_downloading() -> None:
    loader = MortgageSubmissionLoader()
    with (
        patch("insureflow.storage.object_storage.head_object", return_value={"size_bytes": 3_000_000_000, "content_type": "application/pdf"}),
        patch("insureflow.storage.object_storage.download_object_bytes") as mock_download,
    ):
        docs = loader.load_from_texts(
            [{"filename": "huge.pdf", "content": "mortgage-uploads/acme/b1/huge.pdf", "encoding": "s3_ref"}],
            bundle_id="b1",
        )
    assert mock_download.called is False
    assert "too large to auto-process" in docs[0].raw_text


def test_loader_downloads_and_parses_processable_s3_ref_document() -> None:
    loader = MortgageSubmissionLoader()
    with (
        patch("insureflow.storage.object_storage.head_object", return_value={"size_bytes": 100, "content_type": "text/plain"}),
        patch("insureflow.storage.object_storage.download_object_bytes", return_value=b"borrower income statement") as mock_download,
    ):
        docs = loader.load_from_texts(
            [{"filename": "income.txt", "content": "mortgage-uploads/acme/b1/income.txt", "encoding": "s3_ref"}],
            bundle_id="b1",
        )
    assert mock_download.called is True
    assert "borrower income statement" in docs[0].raw_text


def test_loader_boundary_size_is_downloaded() -> None:
    loader = MortgageSubmissionLoader()
    with (
        patch("insureflow.storage.object_storage.head_object", return_value={"size_bytes": MAX_PROCESSABLE_BYTES, "content_type": "text/plain"}),
        patch("insureflow.storage.object_storage.download_object_bytes", return_value=b"ok") as mock_download,
    ):
        loader.load_from_texts(
            [{"filename": "boundary.txt", "content": "mortgage-uploads/acme/b1/boundary.txt", "encoding": "s3_ref"}],
            bundle_id="b1",
        )
    assert mock_download.called is True
