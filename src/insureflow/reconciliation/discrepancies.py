from __future__ import annotations

from typing import Optional

from insureflow.models.audit import DiscrepancyRecord, EventSeverity
from insureflow.models.provenance import ProvenanceNode
from insureflow.reconciliation.matcher import FieldMatcher


class DiscrepancyDetector:
    CRITICAL_FIELDS = {
        "named_insured.legal_name",
        "policy_period.effective_date",
        "policy_period.expiration_date",
        "financial.annual_revenue",
    }

    HIGH_FIELDS = {
        "risk_profile.construction_type",
        "risk_profile.occupancy_type",
        "location.0.year_built",
        "location.0.square_footage",
        "risk_profile.number_of_stories",
        "risk_profile.protection_class",
    }

    def __init__(self) -> None:
        self.matcher = FieldMatcher()

    def detect(self, field_path: str, nodes: list[ProvenanceNode]) -> Optional[DiscrepancyRecord]:
        if len(nodes) < 2:
            return None

        values = [node.value for node in nodes]
        unique_str_values = {str(v).strip().lower() for v in values if v is not None}

        if len(unique_str_values) <= 1:
            return None

        sorted_nodes = sorted(
            nodes,
            key=lambda n: n.source.hierarchy_rank,
            reverse=True,
        )
        authoritative = sorted_nodes[0]
        conflicts = [n for n in sorted_nodes[1:] if str(n.value) != str(authoritative.value)]

        if not conflicts:
            return None

        non_null_vals = [v for v in values if v is not None]
        num_unique = len({str(v).strip().lower() for v in non_null_vals})
        severity = self._determine_severity(field_path, num_unique, len(values))

        return DiscrepancyRecord(
            field_path=field_path,
            structured_value=authoritative.value,
            unstructured_value=conflicts[0].value if conflicts else None,
            severity=severity,
            description=f"Field '{field_path}' has {num_unique} conflicting values across {len(values)} sources. "
            f"Authority ({authoritative.source.source_name}): '{authoritative.value}' conflicts with "
            f"'{' vs '.join(str(c.value) for c in conflicts)}'",
            source_a=authoritative.source.source_name,
            source_b=conflicts[0].source.source_name if conflicts else "",
            provenance_node_ids=[n.node_id for n in sorted_nodes],
        )

    def _determine_severity(self, field_path: str, unique_count: int, total_sources: int) -> EventSeverity:
        if field_path in self.CRITICAL_FIELDS:
            return EventSeverity.CRITICAL
        if field_path in self.HIGH_FIELDS:
            return EventSeverity.WARNING
        if unique_count >= 3:
            return EventSeverity.WARNING
        return EventSeverity.INFO

    def batch_detect(self, reconciled_fields: dict[str, list[ProvenanceNode]]) -> list[DiscrepancyRecord]:
        discrepancies: list[DiscrepancyRecord] = []
        for field_path, nodes in reconciled_fields.items():
            result = self.detect(field_path, nodes)
            if result is not None:
                discrepancies.append(result)
        return sorted(
            discrepancies,
            key=lambda d: {"critical": 0, "warning": 1, "error": 2, "info": 3}.get(d.severity.value, 4),
        )
