from __future__ import annotations

from typing import Any, Optional

from insureflow.models.agents import Finding, RiskSeverity
from insureflow.models.submissions import (
    ClaimRecord,
    CoverageDetail,
    LocationData,
    LossRunData,
    RiskProfile,
    ScheduleOfValues,
    SubmissionBundle,
)


class UnderwritingTools:
    @staticmethod
    def loss_ratio(incurred: float, premium: float) -> float:
        if premium == 0:
            return 0.0
        return round(incurred / premium, 4)

    @staticmethod
    def claim_frequency(claims: list[ClaimRecord], years: float = 5.0) -> float:
        if years == 0 or not claims:
            return 0.0
        return round(len(claims) / years, 2)

    @staticmethod
    def average_severity(claims: list[ClaimRecord]) -> float:
        if not claims:
            return 0.0
        total = sum(c.incurred_amount for c in claims)
        return round(total / len(claims), 2)

    @staticmethod
    def large_loss_ratio(claims: list[ClaimRecord], threshold: float = 100_000) -> float:
        if not claims:
            return 0.0
        large = [c for c in claims if c.incurred_amount >= threshold]
        return round(len(large) / len(claims), 4)

    @staticmethod
    def litigation_ratio(claims: list[ClaimRecord]) -> float:
        if not claims:
            return 0.0
        lit = [c for c in claims if c.claim_status.value in ("pending_litigation",)]
        return round(len(lit) / len(claims), 4)

    @staticmethod
    def open_claim_ratio(claims: list[ClaimRecord]) -> float:
        if not claims:
            return 0.0
        open_c = [c for c in claims if c.claim_status.value == "open"]
        return round(len(open_c) / len(claims), 4)

    @staticmethod
    def total_insurable_value(locations: list[LocationData]) -> float:
        return sum((loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0) for loc in locations)

    @staticmethod
    def coverage_adequacy(coverage: CoverageDetail, total_insurable_value: float) -> tuple[float, str]:
        if total_insurable_value == 0:
            return 1.0, "unknown"
        ratio = coverage.limit_amount / total_insurable_value
        if ratio >= 1.0:
            return ratio, "adequate"
        if ratio >= 0.8:
            return ratio, "marginal"
        return ratio, "inadequate"

    @staticmethod
    def protection_class_risk(pclass: Optional[int]) -> RiskSeverity:
        if pclass is None:
            return RiskSeverity.MODERATE
        if pclass <= 4:
            return RiskSeverity.LOW
        if pclass <= 6:
            return RiskSeverity.MODERATE
        if pclass <= 8:
            return RiskSeverity.HIGH
        return RiskSeverity.CRITICAL

    @staticmethod
    def sprinkler_risk(sprinklered: Optional[bool]) -> RiskSeverity:
        if sprinklered is None:
            return RiskSeverity.MODERATE
        if sprinklered:
            return RiskSeverity.LOW
        return RiskSeverity.HIGH

    @staticmethod
    def year_built_risk(year: Optional[int]) -> RiskSeverity:
        if year is None:
            return RiskSeverity.MODERATE
        current = 2026
        age = current - year
        if age <= 15:
            return RiskSeverity.LOW
        if age <= 30:
            return RiskSeverity.MODERATE
        if age <= 50:
            return RiskSeverity.HIGH
        return RiskSeverity.CRITICAL

    @staticmethod
    def find_non_disclosed_losses(
        loss_run_claims: list[ClaimRecord],
        structured_claims: list[dict[str, Any]],
    ) -> list[ClaimRecord]:
        structured_ids = {c.get("claim_id", "") for c in structured_claims}
        return [c for c in loss_run_claims if c.claim_id not in structured_ids]

    @staticmethod
    def assess_overall_severity(findings: list[Finding]) -> RiskSeverity:
        if not findings:
            return RiskSeverity.LOW
        severities = [f.severity for f in findings]
        if RiskSeverity.CRITICAL in severities:
            return RiskSeverity.CRITICAL
        if RiskSeverity.HIGH in severities:
            return RiskSeverity.HIGH
        if RiskSeverity.MODERATE in severities:
            return RiskSeverity.MODERATE
        return RiskSeverity.LOW

    @staticmethod
    def get_loss_run(bundle: SubmissionBundle) -> Optional[LossRunData]:
        if bundle.structured and bundle.structured.financial:
            return bundle.structured.financial.loss_run
        return None

    @staticmethod
    def get_coverages(bundle: SubmissionBundle) -> list[CoverageDetail]:
        if bundle.structured:
            return bundle.structured.coverages
        return []

    @staticmethod
    def get_locations(bundle: SubmissionBundle) -> list[LocationData]:
        if bundle.structured:
            return bundle.structured.locations
        return []

    @staticmethod
    def get_risk_profile(bundle: SubmissionBundle) -> Optional[RiskProfile]:
        if bundle.structured:
            return bundle.structured.risk_profile
        return None

    @staticmethod
    def get_sovs(bundle: SubmissionBundle) -> list[ScheduleOfValues]:
        if bundle.structured:
            return bundle.structured.schedule_of_values
        return []

    @staticmethod
    def get_named_insured(bundle: SubmissionBundle) -> str:
        if bundle.structured and bundle.structured.named_insured:
            return bundle.structured.named_insured.legal_name
        return bundle.bundle_id
