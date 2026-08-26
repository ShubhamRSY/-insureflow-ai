"""Renewal tracker agent — monitors policy renewal dates and conversion windows.

Proactively identifies upcoming renewals, conversion deadlines, and lapse
risks to ensure timely action on expiring coverage.
"""

from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.renewal_tracking import (
    PolicyRenewalRecord,
    RenewalCheckResult,
    RenewalType,
    check_renewal,
    persist_renewal,
)
from insureflow.underwriting.personal_lines import extract_life_factors


class RenewalTrackerAgent(BaseAgent):
    agent_type = AgentType.RENEWAL_TRACKER
    agent_name = "renewal_tracker_agent"

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        factors = extract_life_factors(bundle)
        face = float(factors.face_amount or 0)
        age = factors.age or 40

        from datetime import date, timedelta

        today = date.today()
        renewal_type = RenewalType.ANNUAL_RENEWAL
        if age < 65:
            renewal_type = RenewalType.CONVERTIBLE_TERM

        record = PolicyRenewalRecord(
            bundle_id=bundle.bundle_id or "",
            insured_name="",
            product_type="term_life",
            face_amount=face,
            current_annual_premium=kwargs.get("annual_premium", 0),
            renewal_type=renewal_type,
            effective_date=today,
            expiration_date=today + timedelta(days=365),
            renewal_date=today + timedelta(days=335),
            conversion_window_end=today + timedelta(days=730) if renewal_type == RenewalType.CONVERTIBLE_TERM else None,
            premium_guarantee_end=today + timedelta(days=365),
            conversion_eligible=renewal_type == RenewalType.CONVERTIBLE_TERM,
            conversion_face_amount=face,
            conversion_product_options=["whole_life", "universal_life", "level_term_20"] if renewal_type == RenewalType.CONVERTIBLE_TERM else [],
        )

        result: RenewalCheckResult = check_renewal(record)
        persist_renewal(record)

        for f in result.findings:
            self._add_finding(f)

        if result.action_items:
            for item in result.action_items:
                self._add_finding(
                    Finding(
                        title=f"Renewal action: {item}",
                        description=f"Days until renewal: {result.days_until_renewal}",
                        severity=RiskSeverity.MODERATE,
                        category="renewal",
                    )
                )

        self._renewal_result = result

    def _build_summary(self) -> str:
        if hasattr(self, "_renewal_result"):
            r = self._renewal_result
            return (
                f"Renewal: {r.record.renewal_type.value}, "
                f"days_to_renewal={r.days_until_renewal}, "
                f"conversion={r.record.conversion_eligible}, "
                f"actions={len(r.action_items)}"
            )
        return super()._build_summary()
