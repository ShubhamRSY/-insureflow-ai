"""Subjectivity tracker + bind-readiness checklist for licensed UW desks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from insureflow.storage.job_store import get_job_store

_NS = "insurance"


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _get_job(bundle_id: str, org_id: str) -> dict[str, Any]:
    store = get_job_store()
    job = store.get(_NS, bundle_id, org_id=org_id)
    if not job:
        # Some jobs use job_id != bundle_id; try scan by results.bundle_id
        for jid in store.list_ids(_NS, org_id=org_id) or []:
            cand = store.get(_NS, jid, org_id=org_id) or {}
            if (cand.get("results") or {}).get("bundle_id") == bundle_id:
                return cand
        raise KeyError(bundle_id)
    return job


def _save_job(bundle_id: str, job: dict[str, Any], org_id: str) -> None:
    store = get_job_store()
    # Prefer the job's own id key if present
    job_id = job.get("job_id") or bundle_id
    for jid in store.list_ids(_NS, org_id=org_id) or []:
        cand = store.get(_NS, jid, org_id=org_id) or {}
        if jid == bundle_id or (cand.get("results") or {}).get("bundle_id") == bundle_id:
            job_id = jid
            break
    store.set(_NS, job_id, job, org_id=org_id)


def list_subjectivities(bundle_id: str, org_id: str) -> list[dict[str, Any]]:
    job = _get_job(bundle_id, org_id)
    results = job.get("results") or {}
    return list(results.get("subjectivities") or [])


def add_subjectivity(
    bundle_id: str,
    org_id: str,
    *,
    text: str,
    category: str = "other",
    created_by: str = "",
) -> dict[str, Any]:
    job = _get_job(bundle_id, org_id)
    results = dict(job.get("results") or {})
    items = list(results.get("subjectivities") or [])
    item = {
        "id": f"subj-{uuid4().hex[:10]}",
        "text": text.strip(),
        "category": category or "other",
        "status": "open",
        "created_by": created_by,
        "created_at": _now(),
        "cleared_by": "",
        "cleared_at": "",
        "notes": "",
    }
    items.append(item)
    results["subjectivities"] = items
    results["bind_readiness"] = compute_bind_readiness(results)
    job["results"] = results
    _save_job(bundle_id, job, org_id)
    return item


def clear_subjectivity(
    bundle_id: str,
    org_id: str,
    subjectivity_id: str,
    *,
    cleared_by: str = "",
    notes: str = "",
) -> dict[str, Any]:
    job = _get_job(bundle_id, org_id)
    results = dict(job.get("results") or {})
    items = list(results.get("subjectivities") or [])
    found: dict[str, Any] | None = None
    for item in items:
        if item.get("id") == subjectivity_id:
            item["status"] = "cleared"
            item["cleared_by"] = cleared_by
            item["cleared_at"] = _now()
            item["notes"] = notes
            found = item
            break
    if found is None:
        raise KeyError(subjectivity_id)
    results["subjectivities"] = items
    results["bind_readiness"] = compute_bind_readiness(results)
    job["results"] = results
    _save_job(bundle_id, job, org_id)
    return found


def seed_subjectivities_from_conditions(results: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert open memo conditions into subjectivities if none exist yet."""
    existing = list(results.get("subjectivities") or [])
    if existing:
        return existing
    seeded: list[dict[str, Any]] = []
    for cond in (results.get("open_conditions") or [])[:12]:
        text = cond if isinstance(cond, str) else str(cond)
        if not text.strip():
            continue
        seeded.append(
            {
                "id": f"subj-{uuid4().hex[:10]}",
                "text": text.strip(),
                "category": "condition",
                "status": "open",
                "created_by": "system",
                "created_at": _now(),
                "cleared_by": "",
                "cleared_at": "",
                "notes": "",
            }
        )
    return seeded


def compute_bind_readiness(results: dict[str, Any]) -> dict[str, Any]:
    """Desk checklist: checkpoints, subjectivities, terms validation, eligibility."""
    checks: list[dict[str, Any]] = []

    quote = results.get("quote") or {}
    eligible = bool(quote.get("eligible", True))
    checks.append(
        {
            "id": "quote_eligible",
            "label": "Quote eligible",
            "status": "pass" if eligible else "fail",
            "detail": "" if eligible else "; ".join(quote.get("ineligibility_reasons") or ["Ineligible"]),
        }
    )

    validated = results.get("validated_terms")
    checks.append(
        {
            "id": "terms_validated",
            "label": "UW validated terms",
            "status": "pass" if validated else "pending",
            "detail": "Premium/limit/deductible confirmed" if validated else "Open UW validator and confirm terms",
        }
    )

    open_cps = [c for c in (results.get("human_checkpoints") or []) if (c.get("status") or "") == "pending"]
    checks.append(
        {
            "id": "checkpoints",
            "label": "Human checkpoints cleared",
            "status": "pass" if not open_cps else "pending",
            "detail": f"{len(open_cps)} open" if open_cps else "All cleared",
        }
    )

    subj = list(results.get("subjectivities") or [])
    open_subj = [s for s in subj if s.get("status") == "open"]
    checks.append(
        {
            "id": "subjectivities",
            "label": "Subjectivities cleared",
            "status": "pass" if not open_subj else "pending",
            "detail": f"{len(open_subj)} open" if open_subj else ("None" if not subj else "All cleared"),
        }
    )

    wf = (results.get("workflow_state") or "").lower()
    checks.append(
        {
            "id": "workflow",
            "label": "Workflow approved",
            "status": "pass" if wf in ("approved", "bound") else "pending",
            "detail": wf or "pending_review",
        }
    )

    failed = [c for c in checks if c["status"] == "fail"]
    pending = [c for c in checks if c["status"] == "pending"]
    ready = not failed and not pending
    return {
        "ready_to_bind": ready,
        "checks": checks,
        "open_subjectivities": len(open_subj),
        "open_checkpoints": len(open_cps),
        "summary": "Ready to bind" if ready else (f"{len(failed)} blocking · {len(pending)} pending"),
    }


def ensure_bind_readiness(bundle_id: str, org_id: str) -> dict[str, Any]:
    job = _get_job(bundle_id, org_id)
    results = dict(job.get("results") or {})
    if not results.get("subjectivities"):
        results["subjectivities"] = seed_subjectivities_from_conditions(results)
    bind = compute_bind_readiness(results)
    results["bind_readiness"] = bind
    job["results"] = results
    _save_job(bundle_id, job, org_id)
    return bind
