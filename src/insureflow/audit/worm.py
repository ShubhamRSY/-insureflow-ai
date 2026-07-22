"""WORM-style immutable audit retention for bank / examiner simulation."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class WormAuditStore:
    """Append-only audit archive with content hashes (Object-Lock / WORM simulation).

    Local mode writes to a retention directory that refuses overwrite/delete via
    API. In AWS, point RETENTION_S3_BUCKET at an S3 bucket with Object Lock.
    """

    def __init__(
        self,
        base_path: Path | str | None = None,
        retention_days: int | None = None,
    ) -> None:
        raw_base = base_path if base_path is not None else os.getenv("WORM_AUDIT_PATH", "./audit_logs/worm")
        self.base_path = Path(raw_base or "./audit_logs/worm")
        self.retention_days = retention_days or int(os.getenv("AUDIT_RETENTION_DAYS", "2555"))  # ~7 years
        self.s3_bucket = os.getenv("RETENTION_S3_BUCKET", "")
        self.base_path.mkdir(parents=True, exist_ok=True)

    def seal(self, org_id: str, bundle_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Write an immutable sealed artifact; raises if the object already exists."""
        stamp = datetime.now(tz=timezone.utc)
        body = {
            "sealed_at": stamp.isoformat(),
            "org_id": org_id,
            "bundle_id": bundle_id,
            "retention_days": self.retention_days,
            "payload": payload,
        }
        raw = json.dumps(body, sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        body["sha256"] = digest

        rel = Path(org_id) / f"{bundle_id}_{stamp.strftime('%Y%m%dT%H%M%SZ')}_{digest[:12]}_{uuid4().hex[:8]}.json"
        dest = self.base_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise FileExistsError(f"WORM object already sealed: {dest}")
        dest.write_bytes(json.dumps(body, indent=2, default=str).encode("utf-8"))
        # Best-effort immutability on local FS
        try:
            dest.chmod(0o444)
        except OSError:
            pass

        s3_uri = None
        if self.s3_bucket:
            s3_uri = self._put_s3(str(rel), dest.read_bytes())

        record = {
            "path": str(dest),
            "sha256": digest,
            "retention_days": self.retention_days,
            "s3_uri": s3_uri,
            "sealed": True,
        }
        logger.info("WORM sealed audit org=%s bundle=%s sha256=%s", org_id, bundle_id, digest[:16])
        return record

    def _put_s3(self, key: str, data: bytes) -> str | None:
        try:
            import boto3
        except ImportError:
            logger.warning("boto3 missing — WORM S3 upload skipped")
            return None
        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("s3", region_name=region)
        client.put_object(
            Bucket=self.s3_bucket,
            Key=f"worm/{key}",
            Body=data,
            ContentType="application/json",
            ObjectLockMode=os.getenv("S3_OBJECT_LOCK_MODE", "GOVERNANCE"),
            ObjectLockRetainUntilDate=datetime.now(tz=timezone.utc).replace(year=datetime.now(tz=timezone.utc).year + 7),
        )
        return f"s3://{self.s3_bucket}/worm/{key}"

    def verify(self, path: str | Path) -> bool:
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        expected = data.pop("sha256", None)
        raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        result = bool(expected == hashlib.sha256(raw).hexdigest())
        data["sha256"] = expected
        return result

    def list_sealed(self, org_id: str) -> list[str]:
        d = self.base_path / org_id
        if not d.exists():
            return []
        return sorted(str(p) for p in d.glob("*.json"))
