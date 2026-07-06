from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, cast

from insureflow.config import settings
from insureflow.exceptions import StorageError
from insureflow.models.audit import AuditTrail, ReconciliationResult, SynthesisOutput
from insureflow.models.provenance import ProvenanceRecord
from insureflow.models.submissions import SubmissionBundle


class AuditStore:
    def __init__(self, base_path: Optional[Path] = None) -> None:
        self.base_path = base_path or settings.audit_log_path
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create audit log directory: {e}")

    def persist_bundle(self, bundle: SubmissionBundle) -> Path:
        output = self.base_path / bundle.bundle_id
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create bundle directory: {e}")
        self._write_json(output / "submission_bundle.json", bundle.model_dump())
        return output

    def persist_provenance(self, record: ProvenanceRecord) -> Path:
        output = self.base_path / record.bundle_id
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create provenance directory: {e}")
        self._write_json(output / "provenance_record.json", record.model_dump())
        return output

    def persist_reconciliation(self, result: ReconciliationResult) -> Path:
        output = self.base_path / result.bundle_id
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create reconciliation directory: {e}")
        self._write_json(output / "reconciliation.json", result.model_dump())
        return output

    def persist_synthesis(self, output: SynthesisOutput) -> Path:
        dir_path = self.base_path / output.bundle_id
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create synthesis directory: {e}")
        self._write_json(dir_path / "synthesis.json", output.model_dump())
        return dir_path

    def persist_audit_trail(self, trail: AuditTrail) -> Path:
        dir_path = self.base_path / trail.bundle_id
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create audit trail directory: {e}")
        self._write_json(
            dir_path / "audit_trail.json",
            trail.model_dump(),
        )
        return dir_path

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        try:
            path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
        except OSError as e:
            raise StorageError(f"Failed to write JSON to {path}: {e}")

    def load_json(self, bundle_id: str, filename: str, org_id: str | None = None) -> Optional[dict[str, Any]]:
        candidates = []
        if org_id:
            candidates.append(self.base_path / org_id / bundle_id / filename)
        candidates.append(self.base_path / bundle_id / filename)

        for path in candidates:
            if path.exists():
                try:
                    from insureflow.storage.encryption import EnvelopeEncryption

                    enc = EnvelopeEncryption()
                    if enc.enabled and path.read_text(encoding="utf-8").startswith("ENC:v1:"):
                        return enc.read_encrypted_file(str(path))
                    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
                except (json.JSONDecodeError, OSError, ValueError):
                    return None
        return None

    def save_json(self, bundle_id: str, filename: str, data: Any, org_id: str | None = None) -> Path:
        base = self.base_path / org_id / bundle_id if org_id else self.base_path / bundle_id
        base.mkdir(parents=True, exist_ok=True)
        path = base / filename
        if isinstance(data, dict):
            payload: dict[str, Any] = data
        elif isinstance(data, list):
            payload = {"items": data}
        else:
            payload = {"data": data}
        self._write_json(path, payload)
        return path
