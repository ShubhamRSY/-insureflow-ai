from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

DRAFT_NS = "draft_bundles"


class DraftBundleStore:
    """Persistent store for in-progress submission bundles.

    Supports multi-source intake: users pull from email, then S3, then
    manual upload, accumulating documents into a single draft bundle
    before running the pipeline.
    """

    def __init__(self, job_store: Any) -> None:
        self._store = job_store

    def create(self, org_id: str = "default", name: str = "") -> dict[str, Any]:
        bundle_id = f"draft-{uuid.uuid4().hex[:12]}"
        now = datetime.now(tz=timezone.utc).isoformat()
        bundle: dict[str, Any] = {
            "bundle_id": bundle_id,
            "name": name or "Untitled submission",
            "status": "assembling",
            "documents": [],
            "created_at": now,
            "updated_at": now,
        }
        self._store.set(DRAFT_NS, bundle_id, bundle, org_id=org_id)
        return bundle

    def get(self, bundle_id: str, org_id: str = "default") -> Optional[dict[str, Any]]:
        return self._store.get(DRAFT_NS, bundle_id, org_id=org_id)

    def list_all(self, org_id: str = "default") -> list[dict[str, Any]]:
        ids = self._store.list_ids(DRAFT_NS, org_id=org_id)
        bundles = []
        for bid in ids:
            data = self._store.get(DRAFT_NS, bid, org_id=org_id)
            if data:
                bundles.append(data)
        return sorted(bundles, key=lambda b: b.get("updated_at", ""), reverse=True)

    def add_documents(
        self,
        bundle_id: str,
        documents: list[dict[str, Any]],
        source_id: str = "",
        connection_label: str = "",
        org_id: str = "default",
    ) -> Optional[dict[str, Any]]:
        bundle = self.get(bundle_id, org_id=org_id)
        if not bundle:
            return None

        existing = bundle.get("documents", [])
        for doc in documents:
            doc_id = f"doc-{uuid.uuid4().hex[:8]}"
            existing.append(
                {
                    "doc_id": doc_id,
                    "filename": doc.get("filename", "unknown"),
                    "content": doc.get("content", ""),
                    "encoding": doc.get("encoding", "utf-8"),
                    "source_id": source_id,
                    "connection_label": connection_label,
                    "added_at": datetime.now(tz=timezone.utc).isoformat(),
                }
            )

        bundle["documents"] = existing
        bundle["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        self._store.set(DRAFT_NS, bundle_id, bundle, org_id=org_id)
        return bundle

    def remove_document(self, bundle_id: str, doc_id: str, org_id: str = "default") -> Optional[dict[str, Any]]:
        bundle = self.get(bundle_id, org_id=org_id)
        if not bundle:
            return None

        bundle["documents"] = [d for d in bundle.get("documents", []) if d.get("doc_id") != doc_id]
        bundle["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        self._store.set(DRAFT_NS, bundle_id, bundle, org_id=org_id)
        return bundle

    def delete(self, bundle_id: str, org_id: str = "default") -> bool:
        return self._store.delete(DRAFT_NS, bundle_id, org_id=org_id)

    def to_pipeline_documents(self, bundle_id: str, org_id: str = "default") -> list[dict[str, str]]:
        """Convert accumulated documents to the format expected by pipeline.run()."""
        bundle = self.get(bundle_id, org_id=org_id)
        if not bundle:
            return []
        return [{"filename": d["filename"], "content": d["content"], "encoding": d.get("encoding", "utf-8")} for d in bundle.get("documents", [])]


def get_draft_bundle_store() -> DraftBundleStore:
    from insureflow.storage.job_store import get_job_store

    return DraftBundleStore(get_job_store())
