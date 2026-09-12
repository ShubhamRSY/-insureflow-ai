from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from insureflow.storage import object_storage as osmod


def test_not_configured_without_bucket_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("S3_UPLOADS_BUCKET", raising=False)
    monkeypatch.delenv("S3_SUBMISSIONS_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    assert osmod.object_storage_configured() is False


def test_configured_when_bucket_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_UPLOADS_BUCKET", "my-bucket")
    assert osmod.object_storage_configured() is True


def test_presign_upload_raises_clean_error_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("S3_UPLOADS_BUCKET", raising=False)
    monkeypatch.delenv("S3_SUBMISSIONS_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    with pytest.raises(ConnectionError):
        osmod.presign_upload(bundle_id="b1", org_id="org1", filename="f.pdf")


def test_presign_upload_enforces_size_cap_via_s3_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_UPLOADS_BUCKET", "my-bucket")
    fake_client = MagicMock()
    fake_client.generate_presigned_post.return_value = {
        "url": "https://my-bucket.s3.amazonaws.com/",
        "fields": {"key": "draft-uploads/org1/b1/x-roof.mp4"},
    }
    with patch.object(osmod, "_client", return_value=fake_client):
        result = osmod.presign_upload(bundle_id="b1", org_id="org1", filename="roof.mp4", content_type="video/mp4")

    assert result["storage_key"].startswith("draft-uploads/org1/b1/")
    assert result["max_bytes"] == osmod.MAX_UPLOAD_BYTES
    conditions = fake_client.generate_presigned_post.call_args.kwargs["Conditions"]
    assert ["content-length-range", 0, osmod.MAX_UPLOAD_BYTES] in conditions


def test_presign_upload_supports_a_custom_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mortgage uploads use their own mortgage-uploads/ namespace (distinct
    from insurance's draft-uploads/) so ownership checks can tell them apart."""
    monkeypatch.setenv("S3_UPLOADS_BUCKET", "my-bucket")
    fake_client = MagicMock()
    fake_client.generate_presigned_post.return_value = {"url": "https://my-bucket.s3.amazonaws.com/", "fields": {}}
    with patch.object(osmod, "_client", return_value=fake_client):
        result = osmod.presign_upload(bundle_id="b1", org_id="org1", filename="closing.pdf", prefix="mortgage-uploads")
    assert result["storage_key"].startswith("mortgage-uploads/org1/b1/")


def test_head_object_returns_real_size(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_UPLOADS_BUCKET", "my-bucket")
    fake_client = MagicMock()
    fake_client.head_object.return_value = {"ContentLength": 2_147_483_648, "ContentType": "video/mp4"}
    with patch.object(osmod, "_client", return_value=fake_client):
        meta = osmod.head_object("draft-uploads/org1/b1/roof.mp4")
    assert meta == {"size_bytes": 2_147_483_648, "content_type": "video/mp4"}


def test_head_object_returns_none_when_object_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_UPLOADS_BUCKET", "my-bucket")
    fake_client = MagicMock()
    fake_client.head_object.side_effect = Exception("404 Not Found")
    with patch.object(osmod, "_client", return_value=fake_client):
        assert osmod.head_object("nonexistent-key") is None


def test_download_object_bytes_raises_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("S3_UPLOADS_BUCKET", raising=False)
    monkeypatch.delenv("S3_SUBMISSIONS_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    with pytest.raises(ConnectionError):
        osmod.download_object_bytes("some-key")


def test_download_object_bytes_enforces_size_cap_even_without_caller_precheck(monkeypatch: pytest.MonkeyPatch) -> None:
    """The loader already checks size before calling this, but the guard must
    live here too — a future caller that skips that check must not be able to
    buffer an arbitrarily large object into memory."""
    monkeypatch.setenv("S3_UPLOADS_BUCKET", "my-bucket")
    with patch.object(osmod, "head_object", return_value={"size_bytes": 999_999_999, "content_type": "application/pdf"}):
        with pytest.raises(ValueError, match="exceeds"):
            osmod.download_object_bytes("draft-uploads/org1/b1/huge.pdf", max_bytes=osmod.MAX_PROCESSABLE_BYTES)


def test_download_object_bytes_succeeds_under_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_UPLOADS_BUCKET", "my-bucket")
    fake_client = MagicMock()

    def fake_download_fileobj(bucket: str, key: str, buf: MagicMock) -> None:
        buf.write(b"file contents")

    fake_client.download_fileobj.side_effect = fake_download_fileobj
    with (
        patch.object(osmod, "head_object", return_value={"size_bytes": 13, "content_type": "text/plain"}),
        patch.object(osmod, "_client", return_value=fake_client),
    ):
        data = osmod.download_object_bytes("draft-uploads/org1/b1/small.txt")
    assert data == b"file contents"
