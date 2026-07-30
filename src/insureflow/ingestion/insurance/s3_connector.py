"""Real S3 submission drop-bucket fetch (when AWS credentials are present)."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TEXT_EXT = {".xml", ".json", ".txt", ".md", ".csv", ".html"}
BINARY_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}


def s3_configured(bucket: str | None = None) -> bool:
    bucket_name = bucket or os.getenv("S3_SUBMISSIONS_BUCKET") or os.getenv("AWS_S3_BUCKET")
    return bool(bucket_name)


def pull_s3_submissions(
    *,
    bucket: str | None = None,
    prefix: str = "",
    max_files: int = 40,
    region: str | None = None,
) -> dict[str, Any]:
    """List and download objects from an S3 intake bucket.

    Uses default boto3 credential chain (env, profile, instance role).
    """
    try:
        import boto3
    except ImportError as exc:
        raise ConnectionError("boto3 not installed — cannot fetch from S3") from exc

    bucket_name = (bucket or os.getenv("S3_SUBMISSIONS_BUCKET") or os.getenv("AWS_S3_BUCKET") or "").strip()
    if not bucket_name:
        raise ConnectionError("S3 bucket not configured — set bucket on request or S3_SUBMISSIONS_BUCKET")

    client = boto3.client("s3", region_name=region or os.getenv("AWS_REGION", "us-east-1"))
    paginator = client.get_paginator("list_objects_v2")
    documents: list[dict[str, str]] = []
    listed = 0

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix or ""):
        for obj in page.get("Contents") or []:
            key = obj.get("Key") or ""
            if not key or key.endswith("/"):
                continue
            ext = Path(key).suffix.lower()
            if ext not in TEXT_EXT | BINARY_EXT:
                continue
            listed += 1
            body = client.get_object(Bucket=bucket_name, Key=key)["Body"].read()
            filename = Path(key).name
            if ext in BINARY_EXT:
                documents.append(
                    {
                        "filename": filename,
                        "content": base64.b64encode(body).decode("ascii"),
                        "encoding": "base64",
                        "s3_key": key,
                    }
                )
            else:
                documents.append(
                    {
                        "filename": filename,
                        "content": body.decode("utf-8", errors="replace"),
                        "encoding": "utf-8",
                        "s3_key": key,
                    }
                )
            if len(documents) >= max_files:
                break
        if len(documents) >= max_files:
            break

    return {
        "bucket": bucket_name,
        "prefix": prefix,
        "objects_considered": listed,
        "documents": documents,
        "documents_found": len(documents),
        "simulated": False,
    }
