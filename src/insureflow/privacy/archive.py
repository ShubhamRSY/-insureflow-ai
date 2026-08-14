"""Durable decision archive — audit disk, not Redis.

Redis jobs expire in a week. The encrypted audit bundle and decision memory
live on the customer's landing-zone disk for the retention window. This module
rehydrates a job payload from that archive so an old memo can be opened after
the live job is gone. Source documents are not restored — the PAS still has
those.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from insureflow.audit.store import AuditStore
from insureflow.privacy.data_plane import retain_source_documents
from insureflow.privacy.decision_memory import get_decision_memory

logger = logging.getLogger(__name__)

_SKIP_DIRS = {
    "workflows",
    "outcomes",
    "metrics",
    "worm",
    "packages",
    "document_analytics",
    "token_usage.jsonl",
}


def hydrate_job_from_archive(
    bundle_id: str,
    org_id: str = "default",
    *,
    store: AuditStore | None = None,
) -> dict[str, Any] | None:
    """Rebuild a job-shaped payload from encrypted audit artifacts."""
    if not bundle_id:
        return None
    store = store or AuditStore()
    summary = store.load_json(bundle_id, "pipeline_summary.json", org_id=org_id) or {}
    memo = store.load_json(bundle_id, "underwriting_memo.json", org_id=org_id)
    trail = store.load_json(bundle_id, "audit_trail.json", org_id=org_id)
    if not summary and not memo and not trail:
        return None
    results = dict(summary or {})
    results.setdefault("bundle_id", bundle_id)
    results.setdefault("org_id", org_id)
    if memo:
        results["memo"] = memo
        results.setdefault("ai_decision", memo.get("decision") if isinstance(memo, dict) else None)
        results.setdefault("insured_name", memo.get("insured_name") if isinstance(memo, dict) else None)
        results.setdefault("human_review_required", memo.get("human_review_required") if isinstance(memo, dict) else None)
        results.setdefault("human_review_reasons", memo.get("human_review_reasons") if isinstance(memo, dict) else None)
        results.setdefault("conditions", memo.get("conditions") if isinstance(memo, dict) else None)
    quote = store.load_json(bundle_id, "quote.json", org_id=org_id)
    if quote:
        results.setdefault("quote", quote)
    return {
        "job_id": bundle_id,
        "status": "completed",
        "archived": True,
        "source": "audit",
        "source_docs_retained": retain_source_documents(),
        "updated_at": results.get("generated_at") or datetime.now(tz=timezone.utc).isoformat(),
        "results": results,
    }


def list_archive(
    org_id: str = "default",
    *,
    limit: int = 200,
    store: AuditStore | None = None,
    memory: Any | None = None,
) -> list[dict[str, Any]]:
    """List durable cases from audit folders + decision memory (newest first)."""
    store = store or AuditStore()
    mem = memory or get_decision_memory()
    root = store.base_path / org_id
    seen: dict[str, dict[str, Any]] = {}

    if root.exists():
        for path in root.iterdir():
            if not path.is_dir() or path.name in _SKIP_DIRS or path.name.startswith("."):
                continue
            bundle_id = path.name
            has_memo = (path / "underwriting_memo.json").exists()
            has_summary = (path / "pipeline_summary.json").exists()
            if not has_memo and not has_summary:
                continue
            summary = store.load_json(bundle_id, "pipeline_summary.json", org_id=org_id) or {}
            memo = store.load_json(bundle_id, "underwriting_memo.json", org_id=org_id) or {}
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            seen[bundle_id] = {
                "bundle_id": bundle_id,
                "org_id": org_id,
                "has_memo": has_memo,
                "archived": True,
                "source_docs_retained": retain_source_documents(),
                "ai_decision": summary.get("ai_decision") or memo.get("decision") or "",
                "insurance_line": summary.get("insurance_line") or summary.get("product_line") or "",
                "primary_state": summary.get("primary_state") or "",
                "tiv": summary.get("tiv"),
                "updated_at": summary.get("generated_at") or mtime.isoformat(),
            }

    for rec in mem.list_records(org_id, limit=limit):
        card = seen.get(rec.bundle_id) or {
            "bundle_id": rec.bundle_id,
            "org_id": org_id,
            "has_memo": False,
            "archived": True,
            "source_docs_retained": retain_source_documents(),
        }
        card.setdefault("ai_decision", rec.decision)
        card.setdefault("insurance_line", rec.line)
        card.setdefault("primary_state", rec.state)
        card["tiv_band"] = rec.tiv_band
        card["naics"] = rec.naics
        card["remembered_at"] = rec.remembered_at.isoformat()
        card.setdefault("updated_at", rec.remembered_at.isoformat())
        seen[rec.bundle_id] = card

    rows = list(seen.values())
    rows.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    return rows[: max(1, min(limit, 500))]


def similar_payload(org_id: str, bundle_id: str, *, limit: int = 8) -> dict[str, Any]:
    hits = get_decision_memory().similar_to_bundle(org_id, bundle_id, limit=limit)
    return {
        "bundle_id": bundle_id,
        "org_id": org_id,
        "similar": [
            {
                "bundle_id": rec.bundle_id,
                "score": round(score, 3),
                "line": rec.line,
                "state": rec.state,
                "tiv_band": rec.tiv_band,
                "decision": rec.decision,
                "naics": rec.naics,
                "construction": rec.construction,
                "occupancy": rec.occupancy,
                "loss_count_band": rec.loss_count_band,
                "remembered_at": rec.remembered_at.isoformat(),
            }
            for rec, score in hits
        ],
    }
