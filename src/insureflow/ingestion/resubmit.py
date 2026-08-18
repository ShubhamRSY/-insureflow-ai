from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insureflow.ingestion.doc_quality import DocumentQualityScorer

logger = logging.getLogger(__name__)

_RESUBMIT_DIR = Path(__file__).parent.parent / "data" / "resubmit_queue"


class ResubmitRequest:
    """A request for a broker to resubmit a document."""

    def __init__(self, bundle_id: str, filename: str, reason: str, required: bool, document_type: str = "") -> None:
        self.bundle_id = bundle_id
        self.filename = filename
        self.reason = reason
        self.required = required
        self.document_type = document_type
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.status = "pending"
        self.replaced_by = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "filename": self.filename,
            "reason": self.reason,
            "required": self.required,
            "document_type": self.document_type,
            "created_at": self.created_at,
            "status": self.status,
            "replaced_by": self.replaced_by,
        }


class ResubmitManager:
    """Manages document resubmission workflow."""

    def __init__(self) -> None:
        _RESUBMIT_DIR.mkdir(parents=True, exist_ok=True)

    def create_resubmit_request(
        self,
        bundle_id: str,
        filename: str,
        reason: str,
        document_type: str = "",
        required: bool = True,
    ) -> ResubmitRequest:
        """Create a resubmit request for a failed document."""
        req = ResubmitRequest(bundle_id, filename, reason, required, document_type)
        self._save_request(req)
        logger.info("Created resubmit request for bundle=%s file=%s reason=%s", bundle_id, filename, reason)
        return req

    def evaluate_and_request_resubmit(
        self,
        bundle_id: str,
        documents: list[dict[str, Any]],
    ) -> list[ResubmitRequest]:
        """Score all documents and create resubmit requests for rejects.

        Returns list of ResubmitRequest for documents that failed quality check.
        """
        scorer = DocumentQualityScorer()
        results = scorer.score_batch(documents)
        requests: list[ResubmitRequest] = []
        for doc, quality in zip(documents, results):
            if quality.status == "reject":
                reason = f"Document failed quality check (score: {quality.score:.2f}). Issues: {'; '.join(quality.issues)}"
                req = self.create_resubmit_request(
                    bundle_id=bundle_id,
                    filename=doc.get("filename", "unknown"),
                    reason=reason,
                    document_type=doc.get("document_type", ""),
                    required=True,
                )
                requests.append(req)
            elif quality.status == "warn":
                reason = f"Document quality is marginal (score: {quality.score:.2f}). Issues: {'; '.join(quality.issues)}"
                req = self.create_resubmit_request(
                    bundle_id=bundle_id,
                    filename=doc.get("filename", "unknown"),
                    reason=reason,
                    document_type=doc.get("document_type", ""),
                    required=False,
                )
                requests.append(req)
        return requests

    def get_pending(self, bundle_id: str = "") -> list[dict[str, Any]]:
        """Get pending resubmit requests, optionally filtered by bundle."""
        results: list[dict[str, Any]] = []
        for path in _RESUBMIT_DIR.glob("*.jsonl"):
            if bundle_id and path.stem != bundle_id:
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                        except json.JSONDecodeError:
                            logger.warning("Skipping malformed JSONL line in %s", path)
                            continue
                        if record.get("status") == "pending":
                            results.append(record)
            except OSError as exc:
                logger.warning("Could not read %s: %s", path, exc)
        return results

    def mark_resubmitted(self, bundle_id: str, filename: str, new_filename: str) -> bool:
        """Mark a request as resubmitted with the new filename."""
        return self._update_request_status(bundle_id, filename, "resubmitted", replaced_by=new_filename)

    def mark_waived(self, bundle_id: str, filename: str, reason: str = "") -> bool:
        """Waive a resubmit request (UW decides to proceed without the doc)."""
        return self._update_request_status(bundle_id, filename, "waived", replaced_by="")

    def get_resubmit_summary(self, bundle_id: str) -> dict[str, Any]:
        """Get summary of resubmit status for a bundle."""
        all_records = self._read_bundle_records(bundle_id)
        summary: dict[str, Any] = {
            "bundle_id": bundle_id,
            "total": len(all_records),
            "pending": 0,
            "resubmitted": 0,
            "waived": 0,
            "required_pending": 0,
            "optional_pending": 0,
            "documents": [],
        }
        for record in all_records:
            status = str(record.get("status", "pending"))
            if status == "pending":
                summary["pending"] += 1
            elif status == "resubmitted":
                summary["resubmitted"] += 1
            elif status == "waived":
                summary["waived"] += 1
            if status == "pending" and record.get("required"):
                summary["required_pending"] += 1
            elif status == "pending":
                summary["optional_pending"] += 1
            summary["documents"].append(
                {
                    "filename": record.get("filename", ""),
                    "status": status,
                    "required": record.get("required", True),
                    "document_type": record.get("document_type", ""),
                    "reason": record.get("reason", ""),
                    "replaced_by": record.get("replaced_by", ""),
                    "created_at": record.get("created_at", ""),
                }
            )
        return summary

    def _save_request(self, req: ResubmitRequest) -> None:
        """Persist request to JSONL file."""
        bundle_file = _RESUBMIT_DIR / f"{req.bundle_id}.jsonl"
        try:
            with open(bundle_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(req.to_dict(), default=str) + "\n")
        except OSError as exc:
            logger.error("Failed to save resubmit request for bundle=%s: %s", req.bundle_id, exc)

    def _read_bundle_records(self, bundle_id: str) -> list[dict[str, Any]]:
        """Read all records for a bundle from its JSONL file."""
        bundle_file = _RESUBMIT_DIR / f"{bundle_id}.jsonl"
        records: list[dict[str, Any]] = []
        if not bundle_file.exists():
            return records
        try:
            with open(bundle_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed JSONL line in %s", bundle_file)
        except OSError as exc:
            logger.warning("Could not read bundle file %s: %s", bundle_file, exc)
        return records

    def _update_request_status(
        self,
        bundle_id: str,
        filename: str,
        new_status: str,
        replaced_by: str = "",
    ) -> bool:
        """Update the status of the latest matching request in a bundle file.

        Rewrites the JSONL file keeping the original line for the matched record
        but with updated fields so there is an audit trail.
        """
        bundle_file = _RESUBMIT_DIR / f"{bundle_id}.jsonl"
        if not bundle_file.exists():
            logger.warning("Bundle file %s does not exist", bundle_file)
            return False

        lines: list[str] = []
        updated = False
        try:
            with open(bundle_file, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        record = json.loads(stripped)
                    except json.JSONDecodeError:
                        lines.append(stripped)
                        continue
                    if record.get("filename") == filename and not updated:
                        record["status"] = new_status
                        if replaced_by:
                            record["replaced_by"] = replaced_by
                        updated = True
                    lines.append(json.dumps(record, default=str))
        except OSError as exc:
            logger.error("Failed to read bundle file %s: %s", bundle_file, exc)
            return False

        if not updated:
            logger.warning("No matching request found for bundle=%s file=%s", bundle_id, filename)
            return False

        try:
            with open(bundle_file, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")
        except OSError as exc:
            logger.error("Failed to write bundle file %s: %s", bundle_file, exc)
            return False

        logger.info("Marked %s as %s for bundle=%s", filename, new_status, bundle_id)
        return True
