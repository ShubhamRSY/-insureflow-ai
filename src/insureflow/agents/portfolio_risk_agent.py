from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.portfolio.store import PortfolioConcentrationSummary, get_portfolio_store


class PortfolioRiskAgent(BaseAgent):
    """Evaluates how a new policy submission shifts the carrier's overall
    geographic and industry concentration. Prevents portfolio-level risk
    from accumulating unnoticed."""

    agent_type = AgentType.PORTFOLIO_RISK
    agent_name = "PortfolioRiskAgent"

    def __init__(self) -> None:
        super().__init__()
        self._portfolio = get_portfolio_store()

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        org_id = kwargs.get("org_id", "default")

        state = ""
        naics_code = ""
        tiv = 0.0

        if bundle.structured:
            if bundle.structured.locations:
                state = bundle.structured.locations[0].state or ""
            if bundle.structured.risk_profile:
                naics_code = bundle.structured.risk_profile.naics_code or ""
            for loc in bundle.structured.locations:
                tiv += (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)

        if not state and not naics_code:
            self._add_finding(
                Finding(
                    title="Insufficient data for portfolio concentration analysis",
                    description="No location state or NAICS code available to evaluate portfolio impact",
                    severity=RiskSeverity.LOW,
                    category="portfolio_risk",
                )
            )
            return

        result = self._portfolio.analyze_concentration(state, naics_code, tiv, org_id)
        self._record_findings(result, bundle.bundle_id, org_id)

    def _record_findings(
        self,
        result: PortfolioConcentrationSummary,
        bundle_id: str,
        org_id: str,
    ) -> None:
        result.bundle_id = bundle_id
        result.org_id = org_id

        self._add_finding(
            Finding(
                title="Portfolio concentration analysis",
                description=f"Current portfolio: {result.existing_policy_count} policies, ${result.existing_tiv_total:,.0f} total TIV",
                severity=RiskSeverity.LOW,
                category="portfolio_risk",
                evidence=[
                    f"Same state ({result.same_state_policy_count} policies, ${result.same_state_tiv_total:,.0f} TIV, {result.same_state_pct_of_portfolio:.1f}% of portfolio)",
                    f"Same NAICS2 ({result.same_naics2_policy_count} policies, ${result.same_naics2_tiv_total:,.0f} TIV, {result.same_naics2_pct_of_portfolio:.1f}% of portfolio)",
                ],
            )
        )

        for warning in result.concentration_warnings:
            sev = RiskSeverity.CRITICAL if "exceeds" in warning and "40" in warning else (RiskSeverity.HIGH if "exceeds" in warning or "Double concentration" in warning else (RiskSeverity.MODERATE))
            self._add_finding(
                Finding(
                    title=f"Portfolio concentration: {warning.split(':')[0].strip()}",
                    description=warning,
                    severity=sev,
                    category="portfolio_risk",
                )
            )

        score = result.concentration_score
        if score >= 0.7:
            self._add_finding(
                Finding(
                    title="HIGH portfolio concentration risk",
                    description=f"Portfolio concentration score: {score:.0%} — new submission would significantly increase exposure concentration",
                    severity=RiskSeverity.CRITICAL,
                    category="portfolio_risk",
                    source_value=score,
                )
            )
        elif score >= 0.4:
            self._add_finding(
                Finding(
                    title="Moderate portfolio concentration risk",
                    description=f"Portfolio concentration score: {score:.0%} — review geographic/industry diversification before binding",
                    severity=RiskSeverity.HIGH,
                    category="portfolio_risk",
                    source_value=score,
                )
            )
        elif score > 0:
            self._add_finding(
                Finding(
                    title="Low portfolio concentration risk",
                    description=f"Portfolio concentration score: {score:.0%} — acceptable diversification",
                    severity=RiskSeverity.LOW if score < 0.2 else RiskSeverity.MODERATE,
                    category="portfolio_risk",
                    source_value=score,
                )
            )
