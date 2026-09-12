"""Direct-to-S3 upload path for files too large for the inline JSON path.

``DraftBundleStore.add_documents`` (the default intake path) embeds file
content as base64 inside a JSON blob stored in Redis — fine for the ~25MB
cap it enforces (``MAX_DOCUMENT_BYTES``), wrong for anything GB-scale: the
bytes would transit as one giant HTTP request body, sit twice in server
memory, then fail outright against Redis's 512MB single-value ceiling.

For large files, the browser instead uploads straight to S3 using a
short-lived presigned POST (``presign_upload``) — the bytes never pass
through this application server or Redis at all. The draft bundle only ever
stores a reference (``storage_key``); ingestion downloads the object at
pipeline-run time, one document at a time (``download_object_bytes``), so
memory use stays bounded by "one document" rather than "the whole bundle."

Not PySpark/Databricks territory — this is a plumbing fix (where do the
bytes live while nobody's processing them), not a compute-scale one.
"""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path
from typing import Any

# S3's own presigned-POST ceiling is much higher, but 5GB is a sane practical
# cap for a single underwriting-submission attachment (e.g. a full-resolution
# drone roof survey or a multi-year claims data export).
MAX_UPLOAD_BYTES = 5 * 1024 * 1024 * 1024
PRESIGN_EXPIRY_SECONDS = 900  # 15 minutes to complete the browser upload

# Separate, much lower ceiling: "safe to store" (above) vs. "safe to
# automatically OCR/parse in this process's memory" (this one). Ingestion
# needs the whole file in memory the same way the inline base64 path always
# has — that path topped out at 25MB by construction; this cap keeps
# large-file ingestion in the same safe range instead of trying to OCR a
# multi-GB file synchronously. Files over this line are stored and visible,
# just not auto-parsed — see loader._resolve_content's "s3_ref" branch.
MAX_PROCESSABLE_BYTES = 200 * 1024 * 1024


def object_storage_configured() -> bool:
    return bool(_bucket())


def _bucket() -> str:
    return (os.getenv("S3_UPLOADS_BUCKET") or os.getenv("S3_SUBMISSIONS_BUCKET") or os.getenv("AWS_S3_BUCKET") or "").strip()


def _client() -> Any:
    import boto3

    return boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))


def presign_upload(
    *,
    bundle_id: str,
    org_id: str,
    filename: str,
    content_type: str = "",
    max_bytes: int = MAX_UPLOAD_BYTES,
    prefix: str = "draft-uploads",
) -> dict[str, Any]:
    """Return a presigned POST the browser can submit the file to directly.

    S3 enforces ``max_bytes`` itself via the POST policy's
    content-length-range condition — an oversized upload is rejected by S3
    before a single byte reaches this application, so the server never has
    to trust the client's claimed size.

    ``prefix`` namespaces the key by caller (``draft-uploads`` for the
    insurance draft-bundle flow, ``mortgage-uploads`` for mortgage) — callers
    that later validate ownership (e.g. ``main._reject_oversized_inline_documents``)
    check the storage key starts with ``{prefix}/{org_id}/``.
    """
    bucket = _bucket()
    if not bucket:
        raise ConnectionError("Object storage not configured — set S3_UPLOADS_BUCKET (or S3_SUBMISSIONS_BUCKET)")

    key = f"{prefix}/{org_id}/{bundle_id}/{uuid.uuid4().hex[:12]}-{Path(filename).name}"
    conditions: list[Any] = [["content-length-range", 0, max_bytes]]
    fields: dict[str, str] = {}
    if content_type:
        conditions.append({"Content-Type": content_type})
        fields["Content-Type"] = content_type

    post = _client().generate_presigned_post(
        Bucket=bucket,
        Key=key,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=PRESIGN_EXPIRY_SECONDS,
    )
    return {
        "url": post["url"],
        "fields": post["fields"],
        "storage_key": key,
        "bucket": bucket,
        "expires_in": PRESIGN_EXPIRY_SECONDS,
        "max_bytes": max_bytes,
    }


def head_object(storage_key: str) -> dict[str, Any] | None:
    """Confirm the object actually landed in S3 (and read its real size)
    before trusting a client's "I finished uploading" claim."""
    bucket = _bucket()
    if not bucket:
        return None
    try:
        resp = _client().head_object(Bucket=bucket, Key=storage_key)
    except Exception:
        return None
    return {"size_bytes": int(resp.get("ContentLength") or 0), "content_type": str(resp.get("ContentType") or "")}


def download_object_bytes(storage_key: str, *, max_bytes: int = MAX_PROCESSABLE_BYTES) -> bytes:
    """Stream an uploaded object down to bytes at ingestion time.

    Called once per document by the loader, not once per bundle — memory use
    stays bounded by the size of whichever single file is being processed
    right now, not the sum of everything in the bundle.

    Enforces ``max_bytes`` itself rather than trusting every caller to have
    already checked — the loader checks size against ``MAX_PROCESSABLE_BYTES``
    before calling this (to produce a friendly "needs manual review" message),
    but that check living only in one caller means a future caller that skips
    it would silently buffer an arbitrarily large object into memory.
    """
    bucket = _bucket()
    if not bucket:
        raise ConnectionError("Object storage not configured — set S3_UPLOADS_BUCKET (or S3_SUBMISSIONS_BUCKET)")
    meta = head_object(storage_key)
    size = int((meta or {}).get("size_bytes") or 0)
    if size > max_bytes:
        raise ValueError(f"Object {storage_key} is {size:,} bytes, exceeds the {max_bytes:,}-byte processing limit")
    buf = io.BytesIO()
    _client().download_fileobj(bucket, storage_key, buf)
    return buf.getvalue()


def delete_object(storage_key: str) -> None:
    bucket = _bucket()
    if not bucket:
        return
    try:
        _client().delete_object(Bucket=bucket, Key=storage_key)
    except Exception:
        pass
