from __future__ import annotations

from insureflow.models.audit import ReconciliationResult
from insureflow.models.provenance import ProvenanceRecord, TrustLevel


class TrustScorer:
    def score(self, record: ProvenanceRecord) -> dict[str, float]:
        if record.record_count() == 0:
            return {"overall": 0.0}

        verified = record.verified_count()
        total = record.record_count()
        discrepancies = record.discrepancy_count()

        verified_rate = verified / total
        discrepancy_penalty = discrepancies / max(total, 1)

        base_score = verified_rate * 100
        penalty = discrepancy_penalty * 50

        overall = max(0.0, min(100.0, base_score - penalty))

        return {
            "overall": round(overall, 2),
            "verified_rate": round(verified_rate, 4),
            "discrepancy_rate": round(discrepancy_penalty, 4),
            "verified_fields": verified,
            "total_fields": total,
            "discrepancies": discrepancies,
        }

    def overall_trust_level(self, score: float) -> TrustLevel:
        if score >= 90:
            return TrustLevel.AUTHORITATIVE
        if score >= 75:
            return TrustLevel.HIGH
        if score >= 55:
            return TrustLevel.MEDIUM
        if score >= 35:
            return TrustLevel.LOW
        return TrustLevel.UNVERIFIED

    def needs_human_review(self, result: ReconciliationResult) -> bool:
        if result.match_rate < 0.7:
            return True
        critical_discrepancies = [d for d in result.discrepancies if d.severity.value == "critical"]
        return len(critical_discrepancies) > 0
