"""Adverse-selection agent — the purpose of underwriting doctrine.

Adverse selection is the structural fact that the people and businesses with
the greatest probability of loss are the ones most likely to purchase
insurance: flood-plain owners buy flood cover, and the applicant who has just
had a claim is the one shopping for a new policy. Insurers are not interested in
selling to applicants who expect frequent, severe losses, so the underwriter
minimizes adverse selection by carefully selecting the applicants whose loss
exposures they are willing to insure.

This agent runs the deterministic screen from
``insureflow.underwriting.adverse_selection`` against the submission: it models
the submitted locations through the catastrophe model client and looks for
hazard-zone coverage demand, excluded-zone demand, loss-motivated coverage
seeking, and bare catastrophe-cover buying. Applicants who are
disproportionately motivated to buy are flagged for careful selection before
any coverage is offered.
"""

from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.oracles.cat_model_client import CatastropheModelClient
from insureflow.oracles.factory import build_cat_client
from insureflow.underwriting.adverse_selection import (
    AdverseSelectionAssessment,
    AdverseSelectionConfig,
    assess_adverse_selection,
)


class AdverseSelectionAgent(BaseAgent):
    """Flags applicants who are disproportionately motivated to buy coverage."""

    agent_type = AgentType.ADVERSE_SELECTION
    agent_name = "AdverseSelectionAgent"

    def __init__(
        self,
        cat_model: CatastropheModelClient | None = None,
        config: AdverseSelectionConfig | None = None,
    ) -> None:
        super().__init__()
        self._cat_model = cat_model or build_cat_client()
        self._config = config or AdverseSelectionConfig()
        self._last_assessment: AdverseSelectionAssessment | None = None

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        if bundle.structured is None:
            self._last_assessment = AdverseSelectionAssessment()
            return

        cat_result = None
        loc_dicts = []
        for loc in bundle.structured.locations or []:
            loc_dicts.append(
                {
                    "address": loc.address,
                    "city": loc.city,
                    "state": loc.state,
                    "zip_code": loc.zip_code,
                    "building_value": loc.building_value,
                    "contents_value": loc.contents_value,
                    "bi_value": loc.bi_value,
                }
            )
        if loc_dicts:
            cat_result = self._cat_model.model_submission(loc_dicts)

        assessment = assess_adverse_selection(bundle, cat_result=cat_result, config=self._config)
        self._last_assessment = assessment
        self._record_findings(assessment)

    @property
    def last_assessment(self) -> AdverseSelectionAssessment | None:
        return self._last_assessment

    def _record_findings(self, assessment: AdverseSelectionAssessment) -> None:
        if not assessment.signals:
            self._add_finding(
                Finding(
                    title="Adverse selection: no disproportionate motivation detected",
                    description=(
                        "The applicant shows no hazard-zone coverage demand, no loss-motivated "
                        "coverage seeking, and is not buying bare catastrophe cover — nothing "
                        "suggests they know more about the risk than the carrier does."
                    ),
                    severity=RiskSeverity.LOW,
                    category="adverse_selection",
                )
            )
            return

        evidence = [f"{s.signal_type.value}: {s.detail}" for s in assessment.signals]
        evidence += [f" - {e}" for s in assessment.signals for e in s.evidence]
        if assessment.status == "high":
            severity, title = (
                RiskSeverity.HIGH,
                "Adverse selection: applicant disproportionately motivated to buy coverage",
            )
        else:
            severity, title = (
                RiskSeverity.MODERATE,
                "Adverse selection risk: applicant shows loss-seeking motivation",
            )

        self._add_finding(
            Finding(
                title=title,
                description=(
                    f"Adverse-selection score {assessment.adverse_selection_score:.0%} for "
                    f"{assessment.applicant_name or 'the applicant'}: the individuals and "
                    "businesses with the greatest probability of loss are the ones most likely to "
                    "purchase insurance, so this applicant's profile warrants careful selection "
                    "before any coverage is offered."
                ),
                severity=severity,
                category="adverse_selection",
                source_value=assessment.adverse_selection_score,
                evidence=evidence,
            )
        )
