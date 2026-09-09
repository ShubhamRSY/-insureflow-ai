from __future__ import annotations

import fcntl
from datetime import datetime, timezone
from pathlib import Path

from insureflow.storage.job_store import JobStore, LockBusyError, distributed_lock, get_job_store
from insureflow.workflow.models import WorkflowRecord, WorkflowState

WORKFLOW_NS = "workflows"


class WorkflowConflictError(RuntimeError):
    """Raised by ``WorkflowStore.save`` when the record on disk has moved on
    since it was read — i.e. a second underwriter (or a second browser tab)
    saved a change to this same bundle in between. The caller should reload
    the current record and either re-apply its change or tell the user
    someone else already acted on this case."""


class WorkflowStoreBusyError(RuntimeError):
    """Raised (job-store-backed mode only) when the distributed lock on a
    workflow record can't be acquired within its timeout."""


def _read_locked(path: Path) -> WorkflowRecord | None:
    """Read a workflow record under a shared lock, so a reader never sees a
    write that's only half-flushed to disk. File mode only."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_SH)
        try:
            raw = fh.read()
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    return WorkflowRecord.model_validate_json(raw) if raw.strip() else None


class WorkflowStore:
    """Persist UW workflow and sign-off records.

    Two backends, chosen by how you construct it:

    - ``WorkflowStore(base_path=...)`` — one JSON file per bundle, guarded by
      an OS file lock (``fcntl.flock``). Real multi-*process* safety on one
      machine (or a shared filesystem); no protection across separate
      machines with independent local disks. Kept for explicit test
      isolation (existing tests construct it this way against a tmp dir) —
      unchanged from before.
    - ``WorkflowStore()`` (the default, used by the real app) — backed by
      the shared ``JobStore`` (Redis in production, see
      ``insureflow.storage.job_store.get_job_store``), locked via the same
      ``distributed_lock`` helper ``DraftBundleStore`` uses. This is the one
      that actually solves multi-app-server-instance safety: BANK_MODE
      forces a real Redis job store, so the lock is a genuine cross-process,
      cross-machine Redis lock, not just a local file lock.

    Either way, every write goes through an optimistic concurrency check
    (``WorkflowRecord.version``) taken atomically with the lock, so two
    underwriters (or two tabs) racing to sign off / assign / escalate the
    same bundle can no longer silently overwrite each other — the second
    save raises ``WorkflowConflictError`` instead.
    """

    def __init__(self, base_path: Path | None = None, job_store: JobStore | None = None) -> None:
        if base_path is not None:
            self._mode = "file"
            self.base_path = base_path
            self.base_path.mkdir(parents=True, exist_ok=True)
        else:
            self._mode = "job_store"
            self._job_store = job_store or get_job_store()

    # ── file mode ────────────────────────────────────────────────
    def _path(self, bundle_id: str, org_id: str) -> Path:
        org_dir = self.base_path / org_id
        org_dir.mkdir(parents=True, exist_ok=True)
        return org_dir / f"{bundle_id}.json"

    def _save_file(self, record: WorkflowRecord) -> None:
        """Atomically checks that nobody else saved a newer version of this
        bundle since ``record`` was read, holding an exclusive lock across
        the whole read-compare-write sequence (not just the write)."""
        path = self._path(record.bundle_id, record.org_id)
        path.touch(exist_ok=True)
        with open(path, "r+", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                raw = fh.read()
                on_disk = WorkflowRecord.model_validate_json(raw) if raw.strip() else None
                if on_disk is not None and on_disk.version != record.version:
                    raise WorkflowConflictError(
                        f"Workflow for bundle {record.bundle_id} was updated by someone else (you read version {record.version}, current is {on_disk.version}) — reload and retry"
                    )
                record.version += 1
                record.updated_at = datetime.now(tz=timezone.utc)
                fh.seek(0)
                fh.write(record.model_dump_json(indent=2))
                fh.truncate()
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    # ── job-store mode ───────────────────────────────────────────
    def _save_job_store(self, record: WorkflowRecord) -> None:
        key = f"insureflow:lock:{record.org_id}:{WORKFLOW_NS}:{record.bundle_id}"
        try:
            with distributed_lock(self._job_store, key):
                data = self._job_store.get(WORKFLOW_NS, record.bundle_id, org_id=record.org_id)
                on_disk = WorkflowRecord.model_validate(data) if data else None
                if on_disk is not None and on_disk.version != record.version:
                    raise WorkflowConflictError(
                        f"Workflow for bundle {record.bundle_id} was updated by someone else (you read version {record.version}, current is {on_disk.version}) — reload and retry"
                    )
                record.version += 1
                record.updated_at = datetime.now(tz=timezone.utc)
                self._job_store.set(WORKFLOW_NS, record.bundle_id, record.model_dump(mode="json"), org_id=record.org_id)
        except LockBusyError as exc:
            raise WorkflowStoreBusyError(f"Workflow for bundle {record.bundle_id} is being updated by someone else right now — try again in a moment") from exc

    # ── public API (dispatches on mode) ─────────────────────────
    def get(self, bundle_id: str, org_id: str = "default") -> WorkflowRecord | None:
        if self._mode == "file":
            return _read_locked(self._path(bundle_id, org_id))
        data = self._job_store.get(WORKFLOW_NS, bundle_id, org_id=org_id)
        return WorkflowRecord.model_validate(data) if data else None

    def save(self, record: WorkflowRecord) -> None:
        if self._mode == "file":
            self._save_file(record)
        else:
            self._save_job_store(record)

    def list_pending(self, org_id: str = "default") -> list[str]:
        if self._mode == "file":
            org_dir = self.base_path / org_id
            if not org_dir.exists():
                return []
            pending: list[str] = []
            for path in org_dir.glob("*.json"):
                rec = _read_locked(path)
                if rec is not None and rec.state in (WorkflowState.PENDING_REVIEW, WorkflowState.PENDING_CO_SIGN):
                    pending.append(rec.bundle_id)
            return sorted(pending)

        pending = []
        for bid in self._job_store.list_ids(WORKFLOW_NS, org_id=org_id):
            rec = self.get(bid, org_id=org_id)
            if rec is not None and rec.state in (WorkflowState.PENDING_REVIEW, WorkflowState.PENDING_CO_SIGN):
                pending.append(rec.bundle_id)
        return sorted(pending)

    def list_records(self, org_id: str = "default") -> list[WorkflowRecord]:
        """Return every workflow record for an org, newest first (workbench inbox)."""
        if self._mode == "file":
            org_dir = self.base_path / org_id
            if not org_dir.exists():
                return []
            records: list[WorkflowRecord] = []
            for path in org_dir.glob("*.json"):
                try:
                    rec = _read_locked(path)
                except Exception:
                    continue
                if rec is not None:
                    records.append(rec)
            return sorted(records, key=lambda r: r.updated_at, reverse=True)

        records = []
        for bid in self._job_store.list_ids(WORKFLOW_NS, org_id=org_id):
            try:
                rec = self.get(bid, org_id=org_id)
            except Exception:
                continue
            if rec is not None:
                records.append(rec)
        return sorted(records, key=lambda r: r.updated_at, reverse=True)
