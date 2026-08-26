"""File-backed job store — durable across restarts without Redis."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insureflow.storage.job_store import JobStore

logger = logging.getLogger(__name__)


class FileJobStore(JobStore):
    """JSON-on-disk job store. Survives process restart; not multi-writer safe."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root or Path.cwd() / "data" / "job_store")
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @staticmethod
    def _safe_id(value: str) -> str:
        # Prevent path traversal via job_id / org_id / namespace
        cleaned = value.replace("..", "").replace("/", "_").replace("\\", "_").strip()
        if not cleaned or cleaned in {".", ".."}:
            raise ValueError(f"Invalid path segment: {value!r}")
        return cleaned

    def _path(self, namespace: str, job_id: str, org_id: str) -> Path:
        safe_ns = self._safe_id(namespace)
        safe_org = self._safe_id(org_id)
        safe_job = self._safe_id(job_id)
        d = self.root / safe_org / safe_ns
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{safe_job}.json"

    def _index_path(self, namespace: str, org_id: str) -> Path:
        safe_ns = self._safe_id(namespace)
        safe_org = self._safe_id(org_id)
        d = self.root / safe_org / safe_ns
        d.mkdir(parents=True, exist_ok=True)
        return d / "_index.json"

    def _read_index(self, namespace: str, org_id: str) -> list[str]:
        path = self._index_path(namespace, org_id)
        if not path.exists():
            return []
        try:
            return list(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            return []

    def _write_index(self, namespace: str, org_id: str, ids: list[str]) -> None:
        self._index_path(namespace, org_id).write_text(json.dumps(sorted(set(ids))), encoding="utf-8")

    def set(self, namespace: str, job_id: str, data: dict[str, Any], org_id: str = "default") -> None:
        with self._lock:
            existing = self.get(namespace, job_id, org_id)
            created_at = (existing or {}).get("created_at") or datetime.now(tz=timezone.utc).isoformat()
            payload = {**data, "org_id": org_id, "created_at": created_at, "updated_at": datetime.now(tz=timezone.utc).isoformat()}
            self._path(namespace, job_id, org_id).write_text(json.dumps(payload, default=str), encoding="utf-8")
            ids = self._read_index(namespace, org_id)
            if job_id not in ids:
                ids.append(job_id)
            self._write_index(namespace, org_id, ids)

    def get(self, namespace: str, job_id: str, org_id: str = "default") -> dict[str, Any] | None:
        path = self._path(namespace, job_id, org_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        return raw if isinstance(raw, dict) else None

    def delete(self, namespace: str, job_id: str, org_id: str = "default") -> bool:
        with self._lock:
            path = self._path(namespace, job_id, org_id)
            ids = self._read_index(namespace, org_id)
            was_listed = job_id in ids
            existed = path.exists()
            if existed:
                path.unlink()
            self._write_index(namespace, org_id, [i for i in ids if i != job_id])
            return existed or was_listed

    def list_ids(self, namespace: str, org_id: str = "default") -> list[str]:
        return sorted(self._read_index(namespace, org_id))
