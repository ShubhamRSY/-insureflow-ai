from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)

_PREVIEW_LIMIT = 80_000

DRAFT_NS = "draft_bundles"

# Same per-file ceiling as the SFTP connector (sftp_connector.MAX_BYTES) —
# one sanity limit for "how big a single document can be" everywhere a file
# enters the system. Base64 inflates ~33%, so this is the decoded-size cap;
# oversized files are skipped (not silently truncated) and reported back to
# the caller via bundle["last_skipped_oversized"].
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024

# Per-file caps (MAX_DOCUMENT_BYTES, object_storage.MAX_UPLOAD_BYTES) don't
# stop someone confirming many large uploads into one bundle — this bounds
# the sum. 20GB is generous (room for several genuinely huge attachments)
# while still being a real ceiling, not "unbounded."
MAX_BUNDLE_TOTAL_BYTES = 20 * 1024 * 1024 * 1024


class BundleTooLargeError(RuntimeError):
    """Raised when adding a document would push a draft bundle's total size over MAX_BUNDLE_TOTAL_BYTES."""


def _bundle_total_bytes(bundle: dict[str, Any]) -> int:
    return sum(int(d.get("size_bytes") or 0) for d in bundle.get("documents") or [])


class DraftBundleBusyError(RuntimeError):
    """Raised when the lock on a draft bundle can't be acquired in time."""


@contextmanager
def _bundle_lock(job_store: Any, bundle_id: str, org_id: str) -> Iterator[None]:
    """Serialize concurrent accumulate/remove calls on one draft bundle.

    Without this, two nearly-simultaneous calls (two underwriters editing the
    same draft, or a "pull from email" and a "pull from S3" landing at once)
    each read the bundle, each append to their own in-memory copy of the
    document list, and whichever writes last wins — the other's documents
    silently vanish. This closes that window.

    Delegates to ``job_store.distributed_lock`` — see its docstring for the
    Redis-vs-in-process distinction; the ``DraftBundleBusyError`` wrapper
    here just keeps this store's public exception type stable.
    """
    from insureflow.storage.job_store import LockBusyError, distributed_lock

    key = f"insureflow:lock:{org_id}:{DRAFT_NS}:{bundle_id}"
    try:
        with distributed_lock(job_store, key):
            yield
    except LockBusyError as exc:
        raise DraftBundleBusyError(f"Draft bundle {bundle_id} is being edited by someone else right now — try again in a moment") from exc


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
        result: Optional[dict[str, Any]] = self._store.get(DRAFT_NS, bundle_id, org_id=org_id)
        return result

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
        with _bundle_lock(self._store, bundle_id, org_id):
            bundle = self.get(bundle_id, org_id=org_id)
            if not bundle:
                return None

            existing = bundle.get("documents", [])
            running_total = _bundle_total_bytes(bundle)
            skipped: list[dict[str, Any]] = []
            for doc in documents:
                filename = str(doc.get("filename") or "unknown")
                content = doc.get("content", "") or ""
                encoding = doc.get("encoding", "utf-8") or "utf-8"
                size = _size_bytes(content, encoding)
                if size > MAX_DOCUMENT_BYTES:
                    skipped.append(
                        {
                            "filename": filename,
                            "size_bytes": size,
                            "reason": f"exceeds {MAX_DOCUMENT_BYTES // (1024 * 1024)}MB per-document limit",
                        }
                    )
                    logger.warning("Dropping oversized document %s (%d bytes) from bundle %s", filename, size, bundle_id)
                    continue
                if running_total + size > MAX_BUNDLE_TOTAL_BYTES:
                    skipped.append(
                        {
                            "filename": filename,
                            "size_bytes": size,
                            "reason": f"would exceed the {MAX_BUNDLE_TOTAL_BYTES // (1024**3)}GB total bundle size limit",
                        }
                    )
                    logger.warning("Dropping %s (%d bytes) — bundle %s already at %d bytes, would exceed total cap", filename, size, bundle_id, running_total)
                    continue

                doc_id = f"doc-{uuid.uuid4().hex[:8]}"
                rel_path = str(doc.get("path") or filename).replace("\\", "/").lstrip("/")
                directory = str(doc.get("directory") or "").replace("\\", "/").strip("/")
                if not directory and "/" in rel_path:
                    directory = str(Path(rel_path).parent)
                    if directory in {".", ""}:
                        directory = ""
                existing.append(
                    {
                        "doc_id": doc_id,
                        "filename": Path(filename).name or filename,
                        "path": rel_path,
                        "directory": directory,
                        "content": content,
                        "encoding": encoding,
                        "size_bytes": size,
                        "source_id": source_id,
                        "connection_label": connection_label,
                        "added_at": datetime.now(tz=timezone.utc).isoformat(),
                    }
                )
                running_total += size

            bundle["documents"] = existing
            bundle["last_skipped_oversized"] = skipped
            bundle["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
            self._store.set(DRAFT_NS, bundle_id, bundle, org_id=org_id)
            return bundle

    def add_object_reference(
        self,
        bundle_id: str,
        *,
        storage_key: str,
        filename: str,
        size_bytes: int,
        content_type: str = "",
        source_id: str = "",
        connection_label: str = "",
        org_id: str = "default",
    ) -> Optional[dict[str, Any]]:
        """Register a file that was uploaded directly to object storage
        rather than inline (see ``object_storage.presign_upload`` — the path
        for files too large for ``add_documents``'s per-document cap).

        The bundle stores only the reference; ``content`` holds the storage
        key (not the bytes) with ``encoding="s3_ref"`` so the ingestion
        loader knows to fetch it from storage at pipeline-run time.
        """
        with _bundle_lock(self._store, bundle_id, org_id):
            bundle = self.get(bundle_id, org_id=org_id)
            if not bundle:
                return None

            running_total = _bundle_total_bytes(bundle)
            if running_total + size_bytes > MAX_BUNDLE_TOTAL_BYTES:
                raise BundleTooLargeError(
                    f"Adding {filename} ({size_bytes:,} bytes) would push bundle {bundle_id} over the "
                    f"{MAX_BUNDLE_TOTAL_BYTES // (1024**3)}GB total size limit (currently {running_total:,} bytes)"
                )

            existing = bundle.get("documents", [])
            doc_id = f"doc-{uuid.uuid4().hex[:8]}"
            existing.append(
                {
                    "doc_id": doc_id,
                    "filename": Path(filename).name or filename,
                    "path": filename,
                    "directory": "",
                    "content": storage_key,
                    "encoding": "s3_ref",
                    "content_type": content_type,
                    "size_bytes": size_bytes,
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
        with _bundle_lock(self._store, bundle_id, org_id):
            bundle = self.get(bundle_id, org_id=org_id)
            if not bundle:
                return None

            removed = [d for d in bundle.get("documents", []) if d.get("doc_id") == doc_id]
            bundle["documents"] = [d for d in bundle.get("documents", []) if d.get("doc_id") != doc_id]
            bundle["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
            self._store.set(DRAFT_NS, bundle_id, bundle, org_id=org_id)

        for doc in removed:
            if str(doc.get("encoding") or "") == "s3_ref" and doc.get("content"):
                from insureflow.storage.object_storage import delete_object

                delete_object(str(doc["content"]))
        return bundle

    def delete(self, bundle_id: str, org_id: str = "default") -> bool:
        bundle = self.get(bundle_id, org_id=org_id)
        result: bool = self._store.delete(DRAFT_NS, bundle_id, org_id=org_id)
        if bundle:
            from insureflow.storage.object_storage import delete_object

            for doc in bundle.get("documents") or []:
                if str(doc.get("encoding") or "") == "s3_ref" and doc.get("content"):
                    delete_object(str(doc["content"]))
        return result

    def to_pipeline_documents(self, bundle_id: str, org_id: str = "default") -> list[dict[str, str]]:
        """Convert accumulated documents to the format expected by pipeline.run()."""
        bundle = self.get(bundle_id, org_id=org_id)
        if not bundle:
            return []
        return [{"filename": d["filename"], "content": d["content"], "encoding": d.get("encoding", "utf-8")} for d in bundle.get("documents", [])]

    def get_document(self, bundle_id: str, doc_id: str, org_id: str = "default") -> dict[str, Any] | None:
        bundle = self.get(bundle_id, org_id=org_id)
        if not bundle:
            return None
        for doc in bundle.get("documents") or []:
            if isinstance(doc, dict) and doc.get("doc_id") == doc_id:
                typed: dict[str, Any] = {str(k): v for k, v in doc.items()}
                return typed
        return None

    def file_tree(self, bundle_id: str, org_id: str = "default") -> dict[str, Any] | None:
        bundle = self.get(bundle_id, org_id=org_id)
        if not bundle:
            return None
        return {
            "bundle_id": bundle["bundle_id"],
            "name": bundle.get("name", ""),
            "status": bundle.get("status", ""),
            "document_count": len(bundle.get("documents") or []),
            "sources": build_file_tree(bundle.get("documents") or []),
        }


def _size_bytes(content: str, encoding: str) -> int:
    if not content:
        return 0
    if (encoding or "").lower() == "base64":
        return max(0, (len(content) * 3) // 4)
    return len(content.encode("utf-8", errors="replace"))


def build_file_tree(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group accumulated docs by source → directory for the Connect & pull viewer."""
    sources: dict[str, dict[str, Any]] = {}
    for doc in documents:
        sid = str(doc.get("source_id") or "unknown")
        label = str(doc.get("connection_label") or sid)
        if sid not in sources:
            sources[sid] = {"source_id": sid, "label": label, "directories": {}}
        directory = str(doc.get("directory") or "").strip("/")
        dirs: dict[str, list[dict[str, Any]]] = sources[sid]["directories"]
        dirs.setdefault(directory, []).append(_public_file_meta(doc))

    out: list[dict[str, Any]] = []
    for sid, src in sources.items():
        directories = []
        for dpath, files in sorted(src["directories"].items(), key=lambda item: (item[0] != "", item[0])):
            directories.append(
                {
                    "path": dpath,
                    "name": dpath.rsplit("/", 1)[-1] if dpath else "/",
                    "file_count": len(files),
                    "files": files,
                }
            )
        out.append(
            {
                "source_id": sid,
                "label": src["label"],
                "file_count": sum(d["file_count"] for d in directories),
                "directories": directories,
            }
        )
    return out


def _public_file_meta(doc: dict[str, Any]) -> dict[str, Any]:
    filename = str(doc.get("filename") or "unknown")
    rel = str(doc.get("path") or filename)
    encoding = str(doc.get("encoding") or "utf-8")
    content = doc.get("content") or ""
    return {
        "doc_id": doc.get("doc_id", ""),
        "filename": filename,
        "path": rel,
        "directory": str(doc.get("directory") or ""),
        "source_id": doc.get("source_id", ""),
        "connection_label": doc.get("connection_label", ""),
        "encoding": encoding,
        "size_bytes": int(doc.get("size_bytes") or (0 if encoding.lower() == "s3_ref" else _size_bytes(str(content), encoding))),
        "added_at": doc.get("added_at", ""),
        "previewable": encoding.lower() not in {"base64", "s3_ref"},
    }


def preview_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Return a safe preview payload (no huge binary dumps)."""
    meta = _public_file_meta(doc)
    encoding = str(doc.get("encoding") or "utf-8")
    content = str(doc.get("content") or "")
    if encoding.lower() == "s3_ref":
        return {
            **meta,
            "previewable": False,
            "truncated": False,
            "content": "",
            "message": "Large file stored in object storage — run the pipeline to extract text (OCR), or download the original from the source.",
        }
    if encoding.lower() == "base64":
        return {
            **meta,
            "previewable": False,
            "truncated": False,
            "content": "",
            "message": "Binary file — run the pipeline to extract text (OCR) or download from the source.",
        }
    truncated = len(content) > _PREVIEW_LIMIT
    return {
        **meta,
        "previewable": True,
        "truncated": truncated,
        "content": content[:_PREVIEW_LIMIT],
        "message": "Preview truncated." if truncated else "",
    }


def get_draft_bundle_store() -> DraftBundleStore:
    from insureflow.storage.job_store import get_job_store

    return DraftBundleStore(get_job_store())
