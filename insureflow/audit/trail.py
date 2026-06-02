from __future__ import annotations

from typing import Any

from insureflow.models.audit import AuditEntry, AuditTrail
from insureflow.models.provenance import ProvenanceNode, ProvenanceRecord


class ProvenanceTrailBuilder:
    @staticmethod
    def build_field_trail(
        record: ProvenanceRecord, field_path: str
    ) -> list[dict[str, Any]]:
        if field_path not in record.nodes:
            return []

        trail: list[dict[str, Any]] = []
        nodes = sorted(
            record.nodes[field_path],
            key=lambda n: n.source.hierarchy_rank,
            reverse=True,
        )

        for node in nodes:
            trail.append(
                {
                    "field_path": node.field_path,
                    "value": node.value,
                    "source": node.source.source_name,
                    "source_type": node.source.source_type.value,
                    "trust_level": node.source.trust_level.value,
                    "hierarchy_rank": node.source.hierarchy_rank,
                    "confidence": node.confidence,
                    "verification_status": node.verification_status.value,
                    "verified_against": node.verified_against,
                    "extracted_at": node.extracted_at.isoformat(),
                }
            )

        return trail

    @staticmethod
    def build_source_lineage(
        record: ProvenanceRecord,
    ) -> dict[str, list[str]]:
        lineage: dict[str, list[str]] = {}
        for field_path, nodes in record.nodes.items():
            for node in nodes:
                src = node.source.source_name
                if src not in lineage:
                    lineage[src] = []
                if field_path not in lineage[src]:
                    lineage[src].append(field_path)
        return lineage

    @staticmethod
    def build_audit_summary(
        trail: AuditTrail, record: ProvenanceRecord
    ) -> dict[str, Any]:
        node_counts = record.record_count()
        verified = record.verified_count()
        discrepancies = record.discrepancy_count()

        entry_summary: dict[str, int] = {}
        for entry in trail.entries:
            key = entry.event.value
            entry_summary[key] = entry_summary.get(key, 0) + 1

        return {
            "bundle_id": trail.bundle_id,
            "total_audit_entries": len(trail.entries),
            "total_provenance_nodes": node_counts,
            "verified_nodes": verified,
            "discrepancy_nodes": discrepancies,
            "verification_rate": round(verified / max(node_counts, 1), 4),
            "event_summary": entry_summary,
            "started_at": trail.started_at.isoformat(),
            "completed_at": trail.completed_at.isoformat() if trail.completed_at else None,
        }
