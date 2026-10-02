"""Password-protected uploads: flagged when no password is given, unlocked when one is."""

import base64
from typing import Any

import pytest
from fastapi import HTTPException

from insureflow.api.main import InsuranceDocumentPayload
from insureflow.e2e import documents
from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader
from insureflow.ingestion.lending.loader import load_lending_documents_from_payloads
from insureflow.ingestion.locked_docs import LOCKED_ENGINE, WrongPasswordError, is_locked, unlock
from insureflow.ingestion.mortgage.loader import MortgageDocumentParser

_pdf = documents.pdf
_xlsx = documents.xlsx


def test_detects_only_files_that_need_a_password():
    assert not is_locked(_pdf(), "a.pdf")
    assert not is_locked(_pdf(user_password=""), "a.pdf")  # permissions-only: opens without a password
    assert is_locked(_pdf(user_password="secret"), "a.pdf")
    assert not is_locked(_xlsx(), "a.xlsx")
    assert is_locked(_xlsx("secret"), "a.xlsx")


@pytest.mark.parametrize("make,name", [(_pdf, "a.pdf"), (_xlsx, "a.xlsx")])
def test_unlock(make, name):
    locked = make("secret")
    assert not is_locked(unlock(locked, name, "secret"), name)
    with pytest.raises(WrongPasswordError):
        unlock(locked, name, "nope")


def test_api_payload_unlocks_and_forgets_the_password():
    doc = InsuranceDocumentPayload(filename="a.pdf", content=base64.b64encode(_pdf("secret")).decode(), encoding="base64", password="secret")
    assert doc.password is None
    assert "password" not in doc.model_dump()
    assert not is_locked(base64.b64decode(doc.content), "a.pdf")

    with pytest.raises(HTTPException, match="Wrong password"):
        InsuranceDocumentPayload(filename="a.pdf", content=base64.b64encode(_pdf("secret")).decode(), encoding="base64", password="nope")


@pytest.mark.parametrize("make,name", [(_pdf, "a.pdf"), (_xlsx, "a.xlsx")])
def test_insurance_loader_flags_locked_and_reads_unlocked(make, name):
    loader = InsuranceDocumentLoader()
    text, engine, *_ = loader._process_binary(make("secret"), name)
    assert engine == LOCKED_ENGINE and "Password protected" in text

    text, engine, *_ = loader._process_binary(unlock(make("secret"), name, "secret"), name)
    assert engine != LOCKED_ENGINE and ("Acme Widgets" in text or "4500000" in text)


def test_mortgage_and_lending_loaders_flag_locked():
    [doc] = MortgageDocumentParser().parse_upload(_pdf("secret"), "statement.pdf", "m-1")
    assert any(f.value == LOCKED_ENGINE for f in doc.extracted_fields.get("ocr_engine", []))

    [lend] = load_lending_documents_from_payloads([{"filename": "statement.pdf", "content": base64.b64encode(_pdf("secret")).decode(), "encoding": "base64"}], use_llm=False)
    assert lend.ocr_engine == LOCKED_ENGINE


def test_wrong_password_over_http_does_not_echo_the_password():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.post("/doc")
    def _doc(doc: InsuranceDocumentPayload) -> dict[str, Any]:
        return doc.model_dump()

    client = TestClient(app)
    body = {"filename": "a.pdf", "content": base64.b64encode(_pdf("secret")).decode(), "encoding": "base64"}

    bad = client.post("/doc", json={**body, "password": "hunter2"})
    assert bad.status_code == 422 and bad.json()["detail"] == "Wrong password for 'a.pdf'"
    assert "hunter2" not in bad.text

    ok = client.post("/doc", json={**body, "password": "secret"})
    assert ok.status_code == 200 and "secret" not in ok.text
    assert not is_locked(base64.b64decode(ok.json()["content"]), "a.pdf")


def test_lock_check_endpoint_and_presigned_upload_unlock(monkeypatch):
    from unittest.mock import patch

    from tests.test_large_file_confirm_endpoint import _create_bundle, _make_client, _signup

    client = _make_client(monkeypatch)
    token, org_id = _signup(client, "lockorg")
    auth = {"Authorization": f"Bearer {token}"}

    def b64(data):
        return base64.b64encode(data).decode()

    resp = client.post(
        "/pipeline/documents/lock-check",
        json={
            "documents": [
                {"filename": "locked.pdf", "content": b64(_pdf("secret")), "encoding": "base64"},
                {"filename": "perms_only.pdf", "content": b64(_pdf("")), "encoding": "base64"},
                {"filename": "sov.xlsx", "content": b64(_xlsx("secret")), "encoding": "base64"},
            ]
        },
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"locked": ["locked.pdf", "sov.xlsx"]}

    bundle_id = _create_bundle(client, token)
    key = f"draft-uploads/{org_id}/{bundle_id}/abc-statement.pdf"
    locked = _pdf("secret")
    with (
        patch("insureflow.storage.object_storage.head_object", return_value={"size_bytes": len(locked), "content_type": "application/pdf"}),
        patch("insureflow.storage.object_storage.download_object_bytes", return_value=locked),
        patch("insureflow.storage.object_storage.put_object_bytes") as put,
    ):
        bad = client.post(f"/pipeline/bundles/{bundle_id}/documents/confirm", json={"storage_key": key, "filename": "statement.pdf", "password": "hunter2"}, headers=auth)
        assert bad.status_code == 422 and "hunter2" not in bad.text
        put.assert_not_called()

        ok = client.post(f"/pipeline/bundles/{bundle_id}/documents/confirm", json={"storage_key": key, "filename": "statement.pdf", "password": "secret"}, headers=auth)
        assert ok.status_code == 200, ok.text
        put.assert_called_once()
        stored_key, stored = put.call_args.args
        assert stored_key == key and not is_locked(stored, "statement.pdf")
