from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insureflow.audit.store import AuditStore
from insureflow.storage.encryption import EnvelopeEncryption


REGULATORY_ARTIFACTS = [
    "submission_bundle.json",
    "underwriting_memo.json",
    "audit_trail.json",
    "provenance_record.json",
    "reconciliation.json",
    "pipeline_summary.json",
    "workflow.json",
    "quote.json",
    "sign_off.json",
]


class RegulatoryPackageBuilder:
    """Assemble examiner-ready audit ZIP with manifest and SHA-256 checksums."""

    def __init__(self, store: AuditStore | None = None, encryption: EnvelopeEncryption | None = None) -> None:
        self.store = store or AuditStore()
        self.encryption = encryption or EnvelopeEncryption()

    def build(self, bundle_id: str, org_id: str = "default", output_dir: Path | None = None) -> dict[str, Any]:
        bundle_dir = self.store.base_path / org_id / bundle_id
        if not bundle_dir.exists():
            bundle_dir = self.store.base_path / bundle_id
        if not bundle_dir.exists():
            raise FileNotFoundError(f"No audit bundle found for {bundle_id}")

        out_dir = output_dir or self.store.base_path / org_id / "packages"
        out_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        zip_path = out_dir / f"{bundle_id}_regulatory_{timestamp}.zip"

        manifest: dict[str, Any] = {
            "bundle_id": bundle_id,
            "org_id": org_id,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "package_version": "1.0",
            "encryption_at_rest": self.encryption.enabled,
            "artifacts": [],
        }

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for artifact in REGULATORY_ARTIFACTS:
                src = bundle_dir / artifact
                if not src.exists():
                    continue
                raw = src.read_bytes()
                sha256 = hashlib.sha256(raw).hexdigest()
                arcname = f"{bundle_id}/{artifact}"
                zf.writestr(arcname, raw)
                manifest["artifacts"].append({
                    "filename": artifact,
                    "sha256": sha256,
                    "size_bytes": len(raw),
                    "encrypted": raw.decode("utf-8", errors="replace").startswith("ENC:v1:"),
                })

            manifest_bytes = json.dumps(manifest, indent=2, default=str).encode("utf-8")
            manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
            zf.writestr(f"{bundle_id}/MANIFEST.json", manifest_bytes)
            zf.writestr(f"{bundle_id}/MANIFEST.sha256", manifest_hash.encode("utf-8"))

        return {
            "bundle_id": bundle_id,
            "org_id": org_id,
            "package_path": str(zip_path),
            "artifact_count": len(manifest["artifacts"]),
            "manifest_sha256": manifest_hash,
            "generated_at": manifest["generated_at"],
        }

    def load_artifact(self, bundle_id: str, filename: str, org_id: str = "default") -> dict[str, Any] | None:
        bundle_dir = self.store.base_path / org_id / bundle_id
        if not bundle_dir.exists():
            bundle_dir = self.store.base_path / bundle_id
        path = bundle_dir / filename
        if not path.exists():
            return None
        if self.encryption.enabled:
            return self.encryption.read_encrypted_file(str(path))
        return json.loads(path.read_text(encoding="utf-8"))
