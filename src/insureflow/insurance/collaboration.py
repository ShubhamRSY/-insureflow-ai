"""Insurance collaboration: broker info-requests + relationship notes on a submission."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from insureflow.audit.store import AuditStore


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class CollaborationStore:
    """Persist lightweight UW↔broker collaboration artifacts on the audit bundle."""

    INFO_FILE = "info_requests.json"
    NOTES_FILE = "relationship_notes.json"

    def __init__(self, audit_store: AuditStore | None = None) -> None:
        self.audit = audit_store or AuditStore()

    def _load_list(self, bundle_id: str, org_id: str, filename: str) -> list[dict[str, Any]]:
        raw = self.audit.load_json(bundle_id, filename, org_id=org_id)
        if isinstance(raw, dict):
            items = raw.get("items")
            return list(items) if isinstance(items, list) else []
        if isinstance(raw, list):
            return list(raw)
        return []

    def _save_list(self, bundle_id: str, org_id: str, filename: str, items: list[dict[str, Any]]) -> None:
        self.audit.save_json(bundle_id, filename, {"items": items}, org_id=org_id)

    def add_info_request(
        self,
        bundle_id: str,
        org_id: str,
        documents: list[str],
        *,
        notes: str = "",
        requested_by: str = "",
        source: str = "uw",
    ) -> dict[str, Any]:
        items = self._load_list(bundle_id, org_id, self.INFO_FILE)
        req = {
            "request_id": f"ir-{uuid4().hex[:10]}",
            "bundle_id": bundle_id,
            "org_id": org_id,
            "documents": [str(d) for d in documents if str(d).strip()],
            "notes": notes,
            "requested_by": requested_by or "underwriter",
            "source": source,
            "status": "pending",
            "created_at": _now(),
            "response_note": "",
            "responded_at": "",
            "responded_by": "",
        }
        items.append(req)
        self._save_list(bundle_id, org_id, self.INFO_FILE, items)
        return req

    def list_info_requests(self, bundle_id: str, org_id: str) -> list[dict[str, Any]]:
        return self._load_list(bundle_id, org_id, self.INFO_FILE)

    def pending_info_requests(self, bundle_id: str, org_id: str) -> list[dict[str, Any]]:
        return [r for r in self.list_info_requests(bundle_id, org_id) if r.get("status") == "pending"]

    def respond_info_request(
        self,
        bundle_id: str,
        org_id: str,
        request_id: str,
        *,
        response_note: str = "",
        responded_by: str = "broker",
        mark_all_pending: bool = False,
    ) -> dict[str, Any]:
        items = self._load_list(bundle_id, org_id, self.INFO_FILE)
        updated: dict[str, Any] | None = None
        for item in items:
            if item.get("status") != "pending":
                continue
            if mark_all_pending or item.get("request_id") == request_id:
                item["status"] = "fulfilled"
                item["response_note"] = response_note
                item["responded_at"] = _now()
                item["responded_by"] = responded_by or "broker"
                updated = item
                if not mark_all_pending:
                    break
        if not updated:
            raise ValueError(f"No pending info request matching {request_id or 'all'}")
        self._save_list(bundle_id, org_id, self.INFO_FILE, items)
        return updated

    def add_note(
        self,
        bundle_id: str,
        org_id: str,
        text: str,
        *,
        author: str = "",
        role: str = "uw",
    ) -> dict[str, Any]:
        clean = text.strip()
        if not clean:
            raise ValueError("Note text is required")
        items = self._load_list(bundle_id, org_id, self.NOTES_FILE)
        note = {
            "note_id": f"rn-{uuid4().hex[:10]}",
            "bundle_id": bundle_id,
            "author": author or "underwriter",
            "role": role if role in ("uw", "broker", "carrier", "ops") else "uw",
            "text": clean[:4000],
            "created_at": _now(),
        }
        items.append(note)
        self._save_list(bundle_id, org_id, self.NOTES_FILE, items)
        return note

    def list_notes(self, bundle_id: str, org_id: str) -> list[dict[str, Any]]:
        return self._load_list(bundle_id, org_id, self.NOTES_FILE)


def get_collaboration_store() -> CollaborationStore:
    return CollaborationStore()
