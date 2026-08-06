"""Moral-hazard agent — the doctrine of the underwriter as a judge of people.

The underwriter must judge the applicant for insurance in every instance. If
the applicant's morals are open to question the underwriter will decline the
policy, no matter how sound the property or how healthy the life. This agent
runs the deterministic character screen from
``insureflow.underwriting.moral_hazard`` against the submission: intentional
misrepresentation, non-disclosed losses, prior carrier cancellation, financial
distress, claims filed suspiciously soon after inception, suspicious claim
causes, and entity churn. A ``critical`` character finding forces declination
in the pipeline regardless of every other signal.
"""

from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.moral_hazard import (
    MoralHazardAssessment,
    MoralHazardConfig,
    assess_moral_hazard,
)


class MoralHazardAgent(BaseAgent):
    """Flags applicants whose morals are open to question."""

    agent_type = AgentType.MORAL_HAZARD
    agent_name = "MoralHazardAgent"

    def __init__(self, config: MoralHazardConfig | None = None) -> None:
        super().__init__()
        self._config = config or MoralHazardConfig()
        self._last_assessment: MoralHazardAssessment | None = None

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        if bundle.structured is None:
            self._last_assessment = MoralHazardAssessment()
            return
        assessment = assess_moral_hazard(bundle, config=self._config)
        self._last_assessment = assessment
        self._record_findings(assessment)

    @property
    def last_assessment(self) -> MoralHazardAssessment | None:
        return self._last_assessment

    def _record_findings(self, assessment: MoralHazardAssessment) -> None:
        if not assessment.signals:
            self._add_finding(
                Finding(
                    title="Moral hazard: no character red flags detected",
                    description=(
                        "The applicant shows no intentional misrepresentation, no hidden losses, "
                        "no prior cancellation, no financial distress, no suspicious claim timing "
                        "or cause, and no entity churn — nothing suggests the applicant's morals "
                        "are open to question."
                    ),
                    severity=RiskSeverity.LOW,
                    category="moral_hazard",
                )
            )
            return

        evidence = [f"{s.signal_type.value}: {s.detail}" for s in assessment.signals]
        evidence += [f" - {e}" for s in assessment.signals for e in s.evidence]
        if assessment.status == "critical":
            severity, title = (
                RiskSeverity.CRITICAL,
                "Moral hazard: applicant's character is open to question — declination indicated",
            )
        elif assessment.status == "high":
            severity, title = (
                RiskSeverity.HIGH,
                "Moral hazard: significant character concerns require referral",
            )
        else:
            severity, title = (
                RiskSeverity.MODERATE,
                "Moral hazard: character concerns warrant careful review",
            )

        self._add_finding(
            Finding(
                title=title,
                description=(
                    f"Moral-hazard score {assessment.moral_hazard_score:.0%} for "
                    f"{assessment.applicant_name or 'the applicant'}: the underwriter must be a "
                    "skillful judge of people, and if the applicant's morals are open to question "
                    "the policy is declined no matter how sound the property or how healthy the life."
                ),
                severity=severity,
                category="moral_hazard",
                source_value=assessment.moral_hazard_score,
                evidence=evidence,
            )
        )
