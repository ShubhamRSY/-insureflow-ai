from __future__ import annotations

import threading
import time

import pytest

from insureflow.storage.job_store import MemoryJobStore
from insureflow.workflow.models import WorkflowRecord, WorkflowState
from insureflow.workflow.store import WorkflowConflictError, WorkflowStore


def _make_store() -> WorkflowStore:
    """job_store-backed mode — the one the real app uses by default
    (WorkflowStore() with no base_path). See test_cosign_workflow.py /
    test_adversarial*.py for the file-backed (base_path=) mode, used there
    for explicit tmp_path test isolation."""
    return WorkflowStore(job_store=MemoryJobStore())


def test_job_store_mode_is_the_default() -> None:
    assert WorkflowStore()._mode == "job_store"


def test_save_and_get_round_trip() -> None:
    store = _make_store()
    record = WorkflowRecord(bundle_id="b1", org_id="org1", state=WorkflowState.PENDING_REVIEW)
    store.save(record)
    assert record.version == 1

    fetched = store.get("b1", org_id="org1")
    assert fetched is not None
    assert fetched.state == WorkflowState.PENDING_REVIEW
    assert fetched.version == 1


def test_concurrent_save_raises_conflict_not_silent_overwrite() -> None:
    """Reproduces the exact race this store used to have: two underwriters
    (or two tabs) load the same record, both mutate it, both save — the
    second save must fail loudly instead of clobbering the first."""
    store = _make_store()
    record = WorkflowRecord(bundle_id="b1", org_id="org1", state=WorkflowState.PENDING_REVIEW)
    store.save(record)

    uw_a = store.get("b1", org_id="org1")
    uw_b = store.get("b1", org_id="org1")
    assert uw_a is not None and uw_b is not None

    uw_a.assigned_to = "alice"
    store.save(uw_a)

    uw_b.assigned_to = "bob"
    with pytest.raises(WorkflowConflictError):
        store.save(uw_b)

    final = store.get("b1", org_id="org1")
    assert final is not None
    assert final.assigned_to == "alice"


def test_concurrent_saves_under_load_never_lose_the_conflict_check() -> None:
    """Five threads race to save the same record; only the version-checked
    winners should succeed, and the final state must be internally
    consistent (not a interleaved/corrupted write)."""
    store = _make_store()
    record = WorkflowRecord(bundle_id="b1", org_id="org1", state=WorkflowState.PENDING_REVIEW)
    store.save(record)

    orig_get = store.get

    def slow_get(bundle_id: str, org_id: str = "default") -> WorkflowRecord | None:
        result = orig_get(bundle_id, org_id=org_id)
        time.sleep(0.02)
        return result

    store.get = slow_get  # type: ignore[method-assign]

    results: list[str] = []

    def worker(name: str) -> None:
        # Read through the slow_get patch so every thread's read overlaps
        # with the others — reproducing "all five read the same stale
        # version before anyone writes," the actual race this test targets.
        rec = store.get("b1", org_id="org1")
        assert rec is not None
        rec.assigned_to = name
        try:
            store.save(rec)
            results.append(f"{name}:saved")
        except WorkflowConflictError:
            results.append(f"{name}:conflict")

    threads = [threading.Thread(target=worker, args=(f"uw{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    saved = [r for r in results if r.endswith(":saved")]
    assert len(saved) == 1, f"exactly one save should win the race, got: {results}"

    final = orig_get("b1", org_id="org1")
    assert final is not None
    assert final.version == 2  # initial save (1) + exactly one winning save (2)


def test_list_pending_and_list_records() -> None:
    store = _make_store()
    pending = WorkflowRecord(bundle_id="b1", org_id="org1", state=WorkflowState.PENDING_REVIEW)
    approved = WorkflowRecord(bundle_id="b2", org_id="org1", state=WorkflowState.APPROVED)
    store.save(pending)
    store.save(approved)

    assert store.list_pending("org1") == ["b1"]
    all_records = store.list_records("org1")
    assert {r.bundle_id for r in all_records} == {"b1", "b2"}


def test_org_isolation() -> None:
    store = _make_store()
    store.save(WorkflowRecord(bundle_id="b1", org_id="org-a", state=WorkflowState.PENDING_REVIEW))
    assert store.get("b1", org_id="org-a") is not None
    assert store.get("b1", org_id="org-b") is None
