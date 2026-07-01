from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: f"dr-{uuid4().hex[:10]}")
    bundle_id: str
    vertical: str = ""
    document_count: int = 0
    structured_count: int = 0
    unstructured_count: int = 0
    human_review_required: bool = False
    decision: str = ""
    org_id: str = "default"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class DocumentAnalyticsStore:
    """Persist document counts per pipeline run for aggregate analysis."""

    def __init__(self, base_path: Path | None = None) -> None:
        from insureflow.config import settings
        self.base_path = (base_path or settings.audit_log_path / "document_analytics")
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, record: DocumentRecord) -> None:
        path = self.base_path / f"{record.bundle_id}.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def get(self, bundle_id: str) -> DocumentRecord | None:
        path = self.base_path / f"{bundle_id}.json"
        if not path.exists():
            return None
        return DocumentRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def list_all(self, vertical: str = "") -> list[DocumentRecord]:
        records: list[DocumentRecord] = []
        for path in sorted(
            self.base_path.glob("*.json"),
            key=lambda p: p.stat().st_mtime, reverse=True,
        ):
            try:
                rec = DocumentRecord.model_validate_json(path.read_text(encoding="utf-8"))
                if not vertical or rec.vertical == vertical:
                    records.append(rec)
            except Exception:
                continue
        return records


class DocumentAnalyticsEngine:
    """Compute aggregate document statistics across pipeline runs."""

    def __init__(self, store: DocumentAnalyticsStore | None = None) -> None:
        self.store = store or DocumentAnalyticsStore()

    def record(
        self,
        bundle_id: str,
        document_count: int,
        vertical: str = "",
        structured_count: int = 0,
        unstructured_count: int = 0,
        human_review_required: bool = False,
        decision: str = "",
        org_id: str = "default",
    ) -> DocumentRecord:
        rec = DocumentRecord(
            bundle_id=bundle_id,
            vertical=vertical,
            document_count=document_count,
            structured_count=structured_count,
            unstructured_count=unstructured_count,
            human_review_required=human_review_required,
            decision=decision,
            org_id=org_id,
        )
        self.store.save(rec)
        return rec

    def summary(self, vertical: str = "") -> dict[str, Any]:
        records = self.store.list_all(vertical=vertical)
        if not records:
            return {
                "total_applications": 0,
                "avg_documents_per_application": 0.0,
                "min_documents": 0,
                "max_documents": 0,
                "total_documents_processed": 0,
                "vertical": vertical or "all",
            }

        counts = [r.document_count for r in records]
        total_docs = sum(counts)
        n = len(counts)
        sorted_counts = sorted(counts)

        return {
            "total_applications": n,
            "avg_documents_per_application": round(total_docs / n, 2),
            "min_documents": sorted_counts[0],
            "max_documents": sorted_counts[-1],
            "median_documents": self._median(sorted_counts),
            "p95_documents": sorted_counts[int(n * 0.95)],
            "total_documents_processed": total_docs,
            "vertical": vertical or "all",
            "applications_with_review": sum(1 for r in records if r.human_review_required),
            "applications_without_review": sum(1 for r in records if not r.human_review_required),
            "by_decision": self._by_decision(records),
            "by_vertical": self._by_vertical(records),
            "sample_records": [
                {
                    "bundle_id": r.bundle_id,
                    "count": r.document_count,
                    "vertical": r.vertical,
                    "decision": r.decision,
                }
                for r in records[:10]
            ],
        }

    def distribution(self, vertical: str = "") -> dict[str, int]:
        records = self.store.list_all(vertical=vertical)
        dist: dict[str, int] = {}
        for r in records:
            bucket = self._bucket(r.document_count)
            dist[bucket] = dist.get(bucket, 0) + 1
        def sort_key(item: tuple[str, int]) -> int:
            bucket = item[0]
            if bucket == "21+":
                return 21
            try:
                return int(bucket.split("-")[0])
            except ValueError:
                return 999
        return dict(sorted(dist.items(), key=sort_key))

    @staticmethod
    def _median(sorted_counts: list[int]) -> float:
        n = len(sorted_counts)
        if n == 0:
            return 0.0
        mid = n // 2
        if n % 2 == 1:
            return float(sorted_counts[mid])
        return (sorted_counts[mid - 1] + sorted_counts[mid]) / 2.0

    @staticmethod
    def _bucket(count: int) -> str:
        if count <= 1:
            return "1"
        if count <= 3:
            return "2-3"
        if count <= 5:
            return "4-5"
        if count <= 10:
            return "6-10"
        if count <= 20:
            return "11-20"
        return "21+"

    @staticmethod
    def _by_decision(records: list[DocumentRecord]) -> dict[str, int]:
        result: dict[str, int] = {}
        for r in records:
            d = r.decision or "unknown"
            result[d] = result.get(d, 0) + 1
        return result

    @staticmethod
    def _by_vertical(records: list[DocumentRecord]) -> dict[str, dict[str, Any]]:
        from collections import defaultdict
        by_v: dict[str, list[int]] = defaultdict(list)
        for r in records:
            by_v[r.vertical or "unknown"].append(r.document_count)
        result = {}
        for v, counts in by_v.items():
            result[v] = {
                "count": len(counts),
                "avg": round(sum(counts) / len(counts), 2),
                "min": min(counts),
                "max": max(counts),
            }
        return result
