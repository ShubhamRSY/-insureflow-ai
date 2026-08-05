"""Selection standards agent — balances written volume against risk homogeneity.

Applies the book-balance model from ``insureflow.underwriting.selection`` to the
carrier's current portfolio and a new submission. A thin or heterogeneous book
keeps selection standards strict (substandard risks referred or declined); a
large homogeneous book can relax the gate and admit substandard risks on a
loaded rate. Selection expense is also surfaced so evidence-gathering cost does
not quietly erode margin.
"""

from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, Recommendation, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.portfolio.store import PortfolioStore, get_portfolio_store
from insureflow.underwriting.selection import (
    RiskClass,
    SelectionAssessment,
    SelectionCandidate,
    SelectionStandardsConfig,
    assess_selection,
    build_book_snapshot,
)

_HAZARD_NAICS_PREFIXES = (
    "1133",  # logging
    "2131",  # mining support
    "3241",  # petroleum & coal products
    "3251",  # basic chemicals
    "4821",  # rail transportation
    "4911",  # postal service
    "7211",  # travel accommodation (fire)
    "9211",  # public administration (wildland)
)


class SelectionStandardsAgent(BaseAgent):
    """Evaluates a new submission against the carrier's book posture.

    The agent reads the written book from the portfolio store, derives the
    candidate risk from the bundle, and reports whether current selection
    standards admit the candidate plus any book-level imbalance warnings.
    """

    agent_type = AgentType.SELECTION_STANDARDS
    agent_name = "SelectionStandardsAgent"

    def __init__(
        self,
        portfolio: PortfolioStore | None = None,
        config: SelectionStandardsConfig | None = None,
    ) -> None:
        super().__init__()
        self._portfolio = portfolio or get_portfolio_store()
        self._config = config or SelectionStandardsConfig()
        self._last_assessment: SelectionAssessment | None = None

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        org_id = kwargs.get("org_id", "default")
        candidate = self._candidate_from_bundle(bundle, kwargs.get("candidate_risk_score"))

        policies = self._portfolio.list_policies(org_id)
        book = build_book_snapshot(
            policy_count=len(policies),
            total_tiv=sum(p.tiv for p in policies),
            total_premium=sum(p.premium for p in policies),
            premiums=[p.premium for p in policies],
            tivs=[p.tiv for p in policies],
            config=self._config,
            risk_scores=[getattr(p, "risk_score", 0.5) for p in policies],
        )

        assessment = assess_selection(candidate, book, self._config)
        self._last_assessment = assessment
        self._record_findings(assessment)

    @property
    def last_assessment(self) -> SelectionAssessment | None:
        return self._last_assessment

    def _build_recommendation(self) -> Recommendation | None:
        """Carry the substandard loading into pricing when the risk is admitted."""
        assessment = self._last_assessment
        if not assessment or assessment.substandard_loading_pct <= 0 or assessment.action not in (UWDecision.ACCEPT, UWDecision.CONDITIONAL_ACCEPT):
            return None
        return Recommendation(
            action=assessment.action.value,
            rationale=(f"Substandard class admitted under current selection standards; {assessment.substandard_loading_pct:.0f}% loading applied."),
            conditions=["Require evidence (APS / loss-run) and confirm substandard rate before binding."],
            suggested_premium_modification=assessment.substandard_loading_pct,
        )

    def _candidate_from_bundle(self, bundle: SubmissionBundle, override_score: Any = None) -> SelectionCandidate:
        tiv = 0.0
        premium = 0.0
        occupancy = ""
        naics = ""
        if bundle.structured:
            for loc in bundle.structured.locations or []:
                tiv += (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)
            premium = sum(c.premium or 0 for c in (bundle.structured.coverages or []))
            if bundle.structured.risk_profile:
                occupancy = bundle.structured.risk_profile.occupancy_type or ""
                naics = bundle.structured.risk_profile.naics_code or ""

        if override_score is not None:
            try:
                risk_score = float(override_score)
            except (TypeError, ValueError):
                risk_score = self._derive_risk_score(bundle, premium, tiv, naics)
        else:
            risk_score = self._derive_risk_score(bundle, premium, tiv, naics)

        if risk_score < 0.4:
            risk_class = RiskClass.PREFERRED
        elif risk_score < 0.65:
            risk_class = RiskClass.STANDARD
        else:
            risk_class = RiskClass.SUBSTANDARD

        return SelectionCandidate(
            tiv=tiv,
            premium=premium,
            risk_class=risk_class,
            risk_score=round(min(1.0, max(0.0, risk_score)), 4),
            occupancy_type=occupancy,
        )

    @staticmethod
    def _derive_risk_score(bundle: SubmissionBundle, premium: float, tiv: float, naics: str) -> float:
        """Heuristic candidate risk score (0..1) used when no memo score is available."""
        score = 0.5
        if bundle.structured:
            if bundle.structured.risk_profile:
                score += 0.1 * min(len(bundle.structured.risk_profile.prior_claims), 3)
            fin = bundle.structured.financial
            if fin is not None and fin.loss_run is not None and premium > 0:
                if fin.loss_run.total_incurred / premium > 0.7:
                    score += 0.15
            if naics and naics[:4] in _HAZARD_NAICS_PREFIXES:
                score += 0.1
        if tiv > 0 and premium > 0 and premium / tiv < 0.003:
            score += 0.05
        return score

    def _record_findings(self, assessment: SelectionAssessment) -> None:
        book = assessment.book
        tier = book.tier

        self._add_finding(
            Finding(
                title=f"Selection standards: {tier.value} posture",
                description=(
                    f"Book has {book.policy_count} policies, ${book.total_tiv:,.0f} TIV, "
                    f"${book.total_premium:,.0f} premium; predictability {book.predictability:.0%} "
                    f"(size {book.size_score:.0%}, homogeneity {book.homogeneity:.0%}) dictates "
                    f"{tier.value} selection standards."
                ),
                severity=RiskSeverity.LOW,
                category="selection_standards",
                evidence=[
                    f"Premium coefficient of variation: {book.cv_premium:.2f}",
                    f"TIV coefficient of variation: {book.cv_tiv:.2f}",
                    f"Selection expense: ${assessment.selection_expense_usd:,.0f} ({assessment.selection_expense_ratio:.1%} of book premium)",
                ],
            )
        )

        if book.policy_count < self._config.min_volume_for_law_of_averages:
            self._add_finding(
                Finding(
                    title="Law of averages: book too small for predictable losses",
                    description=(
                        f"{book.policy_count} policies is below the "
                        f"{self._config.min_volume_for_law_of_averages}-policy minimum for loss "
                        "predictability — keep standards strict and grow volume within "
                        "homogeneous classes before relaxing selection."
                    ),
                    severity=RiskSeverity.MODERATE,
                    category="selection_standards",
                )
            )

        if assessment.selection_expense_ratio > self._config.max_selection_expense_ratio:
            self._add_finding(
                Finding(
                    title="Selection expense burden on the book",
                    description=(
                        f"Selection expense is {assessment.selection_expense_ratio:.1%} of book "
                        "premium, above the "
                        f"{self._config.max_selection_expense_ratio:.0%} guideline — relax "
                        "evidence requirements or grow premium volume."
                    ),
                    severity=RiskSeverity.MODERATE,
                    category="selection_standards",
                )
            )

        if book.intra_class_cv > self._config.max_intra_class_cv:
            per_class = ", ".join(f"{k}={v:.2f}" for k, v in book.class_dispersion.items())
            self._add_finding(
                Finding(
                    title="Class purity eroded: poor risks pooling with good",
                    description=(
                        f"Intra-class risk-score dispersion is {book.intra_class_cv:.2f} "
                        f"(per class: {per_class}) — within a class there are good and poor "
                        "risks, and the weaker ones are being carried at the class average rate."
                    ),
                    severity=RiskSeverity.MODERATE,
                    category="selection_standards",
                    source_value=book.intra_class_cv,
                )
            )

        action = assessment.action
        if action == UWDecision.DECLINE:
            severity, title = RiskSeverity.CRITICAL, "Selection gate: decline recommended"
        elif action == UWDecision.REFER:
            severity, title = RiskSeverity.HIGH, "Selection gate: refer to licensed UW"
        elif action == UWDecision.CONDITIONAL_ACCEPT:
            severity, title = RiskSeverity.MODERATE, "Selection gate: conditional acceptance"
        else:
            severity, title = RiskSeverity.LOW, "Selection gate: candidate admissible"

        self._add_finding(
            Finding(
                title=title,
                description=f"{'; '.join(assessment.rationale)}",
                severity=severity,
                category="selection_standards",
                source_value=action.value,
                evidence=[
                    f"Candidate class: {assessment.candidate.risk_class.value}, risk score {assessment.candidate.risk_score:.2f}",
                    f"Candidate premium ${assessment.candidate.premium:,.0f}, TIV ${assessment.candidate.tiv:,.0f}",
                ]
                + list(assessment.warnings),
            )
        )
