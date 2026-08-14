"""Live intake connectors — IMAP / S3 / SFTP, not Airbyte or Kafka."""

from __future__ import annotations

from pytest import MonkeyPatch

from insureflow.ingestion.insurance.s3_connector import s3_configured
from insureflow.ingestion.insurance.sftp_connector import sftp_configured
from insureflow.ingestion.status import ingestion_status


def test_sftp_configured_requires_host_user_and_secret(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SFTP_HOST", raising=False)
    monkeypatch.delenv("SFTP_USERNAME", raising=False)
    monkeypatch.delenv("SFTP_PASSWORD", raising=False)
    monkeypatch.delenv("SFTP_KEY_PATH", raising=False)
    assert sftp_configured() is False
    monkeypatch.setenv("SFTP_HOST", "sftp.broker.test")
    monkeypatch.setenv("SFTP_USERNAME", "uw")
    assert sftp_configured() is False
    monkeypatch.setenv("SFTP_PASSWORD", "secret")
    assert sftp_configured() is True
    assert sftp_configured("other.broker.test") is True


def test_s3_configured_from_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("S3_SUBMISSIONS_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    assert s3_configured() is False
    monkeypatch.setenv("S3_SUBMISSIONS_BUCKET", "carrier-subs")
    assert s3_configured() is True
    assert s3_configured("override-bucket") is True


def test_ingestion_status_shape(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("IMAP_HOST", raising=False)
    monkeypatch.delenv("S3_SUBMISSIONS_BUCKET", raising=False)
    monkeypatch.delenv("SFTP_HOST", raising=False)
    status = ingestion_status()
    assert set(status["connectors"]) == {"imap", "s3", "sftp", "folder"}
    assert status["connectors"]["folder"]["live"] is True
    assert "acord_xml" in status["parsers"]
    assert status["events"] == "https_webhooks"
    assert "airbyte" in status["not_required"]
    assert status["workflow"] in {"celery", "in_process"}
    assert status["ocr"]["pdfminer"] is True


def test_s3_pull_uses_live_path_not_demo(monkeypatch: MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app
    from insureflow.auth import Role
    from insureflow.auth.jwt import create_access_token
    from insureflow.auth.models import User
    from insureflow.auth.store import clear_user_store, get_user_store

    monkeypatch.setenv("BANK_MODE", "true")
    monkeypatch.setenv("S3_SUBMISSIONS_BUCKET", "carrier-subs")

    def fake_pull(*, bucket=None, prefix="", **_kwargs):
        return {
            "bucket": bucket or "carrier-subs",
            "prefix": prefix,
            "documents": [{"filename": "acord.xml", "content": "<ACORD/>", "encoding": "utf-8"}],
            "documents_found": 1,
            "objects_considered": 1,
        }

    monkeypatch.setattr("insureflow.ingestion.insurance.s3_connector.pull_s3_submissions", fake_pull)
    monkeypatch.setattr("insureflow.ingestion.insurance.s3_connector.s3_configured", lambda bucket=None: True)

    clear_user_store()
    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=Role.VIEWER, org_id="acme")
    token = create_access_token({"sub": "uw", "role": Role.VIEWER.value, "org_id": "acme"})
    client = TestClient(app)
    resp = client.post(
        "/api/insurance/sources/s3-bucket/pull",
        headers={"Authorization": f"Bearer {token}"},
        json={"bucket": "carrier-subs"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["simulated"] is False
    assert data["file_count"] == 1
    assert data["documents"][0]["filename"] == "acord.xml"


def test_sftp_pull_uses_live_path_not_demo(monkeypatch: MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app
    from insureflow.auth import Role
    from insureflow.auth.jwt import create_access_token
    from insureflow.auth.models import User
    from insureflow.auth.store import clear_user_store, get_user_store

    monkeypatch.setenv("BANK_MODE", "true")
    monkeypatch.setenv("SFTP_HOST", "sftp.broker.test")
    monkeypatch.setenv("SFTP_USERNAME", "uw")
    monkeypatch.setenv("SFTP_PASSWORD", "secret")

    def fake_pull(*, host=None, remote_dir=None, **_kwargs):
        return {
            "host": host or "sftp.broker.test",
            "remote_dir": remote_dir or "inbound",
            "documents": [{"filename": "sov.md", "content": "SOV", "encoding": "utf-8"}],
            "documents_found": 1,
            "objects_considered": 1,
        }

    monkeypatch.setattr("insureflow.ingestion.insurance.sftp_connector.pull_sftp_submissions", fake_pull)
    monkeypatch.setattr("insureflow.ingestion.insurance.sftp_connector.sftp_configured", lambda host=None: True)

    clear_user_store()
    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=Role.VIEWER, org_id="acme")
    token = create_access_token({"sub": "uw", "role": Role.VIEWER.value, "org_id": "acme"})
    client = TestClient(app)
    resp = client.post(
        "/api/insurance/sources/sftp/pull",
        headers={"Authorization": f"Bearer {token}"},
        json={"host": "sftp.broker.test"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["simulated"] is False
    assert data["file_count"] == 1


def test_bank_mode_unconfigured_s3_is_400_not_demo(monkeypatch: MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app
    from insureflow.auth import Role
    from insureflow.auth.jwt import create_access_token
    from insureflow.auth.models import User
    from insureflow.auth.store import clear_user_store, get_user_store

    monkeypatch.setenv("BANK_MODE", "true")
    monkeypatch.delenv("S3_SUBMISSIONS_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)

    clear_user_store()
    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=Role.VIEWER, org_id="acme")
    token = create_access_token({"sub": "uw", "role": Role.VIEWER.value, "org_id": "acme"})
    client = TestClient(app)
    resp = client.post(
        "/api/insurance/sources/s3-bucket/pull",
        headers={"Authorization": f"Bearer {token}"},
        json={"bucket": ""},
    )
    assert resp.status_code == 400
    assert "S3 not configured" in resp.json()["detail"]


def test_ingestion_status_authenticated(monkeypatch: MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app
    from insureflow.auth import Role
    from insureflow.auth.jwt import create_access_token
    from insureflow.auth.models import User
    from insureflow.auth.store import clear_user_store, get_user_store

    clear_user_store()
    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=Role.VIEWER, org_id="acme")
    token = create_access_token({"sub": "uw", "role": Role.VIEWER.value, "org_id": "acme"})
    client = TestClient(app)
    resp = client.get("/ingestion/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["connectors"]["folder"]["live"] is True
    assert "acord_xml" in body["parsers"]
