from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from insureflow.models.audit import ReconciliationResult
from insureflow.models.provenance import ProvenanceRecord
from insureflow.provenance.rules import VerificationRuleSet
from insureflow.reconciliation.discrepancies import DiscrepancyDetector
from insureflow.reconciliation.matcher import FieldMatcher


class ReconciliationEngine:
    def __init__(self) -> None:
        self.matcher = FieldMatcher()
        self.detector = DiscrepancyDetector()
        self.rule_set = VerificationRuleSet.default_rules()

    def reconcile(self, provenance_record: ProvenanceRecord) -> ReconciliationResult:
        result = ReconciliationResult(
            bundle_id=provenance_record.bundle_id,
        )

        discrepancies = self.detector.batch_detect(provenance_record.nodes)

        matched = 0
        total = 0
        field_reconciliation: dict[str, dict[str, Any]] = {}

        for field_path, nodes in provenance_record.nodes.items():
            total += 1

            node_dicts = [
                {
                    "value": n.value,
                    "confidence": n.confidence,
                    "source": {
                        "source_name": n.source.source_name,
                        "hierarchy_rank": n.source.hierarchy_rank,
                        "trust_level": n.source.trust_level.value,
                    },
                }
                for n in nodes
            ]

            match_result = self.matcher.match(field_path, node_dicts)
            rule = self.rule_set.get_rule(field_path)

            if match_result:
                is_match = True
                match_method = "hierarchy_resolved"

                if rule:
                    values = [n.value for n in nodes]
                    rule_ok, rule_detail = rule.verify(values)
                    if not rule_ok:
                        is_match = False
                        match_method = f"rule_failed: {rule_detail}"

                if is_match:
                    matched += 1
                    match_method = "hierarchy_match"

                field_reconciliation[field_path] = {
                    "resolved_value": match_result["resolved_value"],
                    "authoritative_source": match_result["authoritative_source"],
                    "confidence": match_result["confidence"],
                    "sources_checked": match_result["sources_checked"],
                    "consensus_rate": match_result["consensus_rate"],
                    "match_method": match_method,
                }
            else:
                field_reconciliation[field_path] = {
                    "resolved_value": None,
                    "authoritative_source": None,
                    "confidence": 0.0,
                    "sources_checked": len(nodes),
                    "consensus_rate": 0.0,
                    "match_method": "no_match",
                }

        result.field_reconciliation = field_reconciliation
        result.discrepancies = discrepancies
        result.matched_fields = matched
        result.total_fields = total
        result.match_rate = matched / max(total, 1)
        result.reconciled_at = datetime.now(timezone.utc)

        critical_discrepancies = sum(1 for d in discrepancies if d.severity.value == "critical")
        result.overall_status = "flagged" if critical_discrepancies > 0 else "reconciled" if result.match_rate >= 0.8 else "partial"

        return result
