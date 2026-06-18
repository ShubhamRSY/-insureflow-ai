from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from insureflow.config import settings
from insureflow.workflow.models import WorkflowRecord, WorkflowState


class WorkflowStore:
    """Persist UW workflow and sign-off records."""

    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or settings.audit_log_path / "workflows"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _path(self, bundle_id: str, org_id: str) -> Path:
        org_dir = self.base_path / org_id
        org_dir.mkdir(parents=True, exist_ok=True)
        return org_dir / f"{bundle_id}.json"

    def get(self, bundle_id: str, org_id: str = "default") -> WorkflowRecord | None:
        path = self._path(bundle_id, org_id)
        if not path.exists():
            return None
        return WorkflowRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, record: WorkflowRecord) -> None:
        record.updated_at = datetime.now(tz=timezone.utc)
        self._path(record.bundle_id, record.org_id).write_text(
            record.model_dump_json(indent=2), encoding="utf-8"
        )

    def list_pending(self, org_id: str = "default") -> list[str]:
        org_dir = self.base_path / org_id
        if not org_dir.exists():
            return []
        pending: list[str] = []
        for path in org_dir.glob("*.json"):
            rec = WorkflowRecord.model_validate_json(path.read_text(encoding="utf-8"))
            if rec.state == WorkflowState.PENDING_REVIEW:
                pending.append(rec.bundle_id)
        return sorted(pending)
