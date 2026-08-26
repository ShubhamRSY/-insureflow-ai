"""Beneficiary review agent — structured review of beneficiary designations.

Validates beneficiary allocations, insurable interest, ownership structures,
and trust/estate considerations beyond simple flagging.
"""

from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.beneficiary_review import (
    BeneficiaryReviewResult,
    review_beneficiaries,
    persist_beneficiary_review,
)
from insureflow.underwriting.personal_lines import extract_life_factors


class BeneficiaryReviewAgent(BaseAgent):
    agent_type = AgentType.BENEFICIARY_REVIEW
    agent_name = "beneficiary_review_agent"

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        result: BeneficiaryReviewResult = review_beneficiaries(bundle)
        persist_beneficiary_review(result.record)

        for f in result.findings:
            self._add_finding(f)

        if result.allocation_valid:
            self._add_finding(
                Finding(
                    title=f"Beneficiary allocation valid ({result.primary_total_pct:.0f}% primary)",
                    description=f"Primary {result.primary_total_pct:.0f}%, contingent {result.contingent_total_pct:.0f}%.",
                    severity=RiskSeverity.LOW,
                    category="beneficiary_review",
                )
            )

        if result.insurable_interest_flags:
            self._add_finding(
                Finding(
                    title=f"{len(result.insurable_interest_flags)} insurable interest flag(s)",
                    description="; ".join(result.insurable_interest_flags[:3]),
                    severity=RiskSeverity.HIGH,
                    category="beneficiary_review",
                )
            )

        if result.action_items:
            for item in result.action_items:
                self._add_finding(
                    Finding(
                        title=f"Beneficiary action: {item}",
                        description="",
                        severity=RiskSeverity.MODERATE,
                        category="beneficiary_review",
                    )
                )

        self._review_result = result

    def _build_summary(self) -> str:
        if hasattr(self, "_review_result"):
            r = self._review_result
            return (
                f"Beneficiary review: {r.record.status.value}, "
                f"primary={r.primary_total_pct:.0f}%, "
                f"contingent={r.contingent_total_pct:.0f}%, "
                f"flags={len(r.insurable_interest_flags)}, "
                f"actions={len(r.action_items)}"
            )
        return super()._build_summary()
