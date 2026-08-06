"""Persistent store for in-force policy monitoring records."""

from __future__ import annotations

import logging
from pathlib import Path

from insureflow.config import settings
from insureflow.monitoring.models import PolicyMonitoringRecord

logger = logging.getLogger(__name__)


class MonitoringStore:
    """Persist per-org policy monitoring records to JSON.

    One file per org under ``audit_log_path/monitoring/`` so monitors
    survive restarts without coupling to the PAS.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or settings.audit_log_path / "monitoring"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _org_file(self, org_id: str) -> Path:
        return self.base_path / f"{org_id}.json"

    def _load_all(self, org_id: str) -> dict[str, PolicyMonitoringRecord]:
        import json

        path = self._org_file(org_id)
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return {}
            records: dict[str, PolicyMonitoringRecord] = {}
            for pid, data in raw.items():
                try:
                    records[pid] = PolicyMonitoringRecord.model_validate(data)
                except Exception:
                    continue
            return records
        except Exception as exc:
            logger.warning("Skipping corrupt monitoring store %s: %s", path.name, exc)
            return {}

    def _persist(self, org_id: str, records: dict[str, PolicyMonitoringRecord]) -> None:
        import json

        payload = {pid: rec.model_dump(mode="json") for pid, rec in records.items()}
        path = self._org_file(org_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)

    def save(self, record: PolicyMonitoringRecord) -> None:
        records = self._load_all(record.org_id)
        records[record.policy_id] = record
        self._persist(record.org_id, records)

    def get(self, policy_id: str, org_id: str = "default") -> PolicyMonitoringRecord | None:
        return self._load_all(org_id).get(policy_id)

    def get_by_bundle(self, bundle_id: str, org_id: str = "default") -> PolicyMonitoringRecord | None:
        for rec in self.list(org_id):
            if rec.bundle_id == bundle_id:
                return rec
        return None

    def list(self, org_id: str = "default") -> list[PolicyMonitoringRecord]:
        records = self._load_all(org_id)
        return sorted(records.values(), key=lambda r: r.created_at, reverse=True)

    def delete(self, policy_id: str, org_id: str = "default") -> bool:
        records = self._load_all(org_id)
        if policy_id not in records:
            return False
        del records[policy_id]
        self._persist(org_id, records)
        return True
