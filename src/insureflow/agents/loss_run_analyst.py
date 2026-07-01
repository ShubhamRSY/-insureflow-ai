from __future__ import annotations

from typing import Any

from insureflow.agents.react_agent import ReActAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import ClaimRecord, SubmissionBundle


class LossRunAnalystAgent(ReActAgent):
    agent_type = AgentType.LOSS_RUN_ANALYST
    agent_name = "LossRunAnalystAgent"
    prompt_key = "loss_run_analyst"

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        loss_run = self.tools.get_loss_run(bundle)
        if not loss_run or not loss_run.claims:
            self._add_finding(
                Finding(
                    title="No loss run data available",
                    description="Cannot analyze claims history — loss run not provided or empty",
                    severity=RiskSeverity.HIGH,
                    category="data_quality",
                )
            )
            return

        claims = loss_run.claims
        self._assess_frequency(claims, loss_run)
        self._assess_severity(claims)
        self._assess_large_losses(claims)
        self._assess_open_exposure(claims)
        self._assess_litigation(claims)
        self._assess_line_distribution(claims)
        self._assess_year_over_year(claims)
        self._check_claim_notes(bundle, claims)

    def _assess_frequency(self, claims: list[ClaimRecord], loss_run: Any) -> None:
        freq = self.tools.claim_frequency(claims)
        if freq > 3:
            self._add_finding(
                Finding(
                    title="High claim frequency",
                    description=f"{freq:.1f} claims/year over {len(claims)} total claims",
                    severity=RiskSeverity.HIGH,
                    category="frequency",
                    field_path="financial.loss_run",
                    source_value=freq,
                    evidence=[f"{c.claim_id} ({c.date_of_loss})" for c in claims[:5]],
                )
            )
        elif freq > 1.5:
            self._add_finding(
                Finding(
                    title="Moderate claim frequency",
                    description=f"{freq:.1f} claims/year — above industry average",
                    severity=RiskSeverity.MODERATE,
                    category="frequency",
                    source_value=freq,
                )
            )

    def _assess_severity(self, claims: list[ClaimRecord]) -> None:
        avg = self.tools.average_severity(claims)
        if avg > 200_000:
            self._add_finding(
                Finding(
                    title="High average claim severity",
                    description=f"Average incurred ${avg:,.0f} per claim",
                    severity=RiskSeverity.HIGH,
                    category="severity",
                    source_value=avg,
                )
            )
        elif avg > 75_000:
            self._add_finding(
                Finding(
                    title="Moderate average claim severity",
                    description=f"Average incurred ${avg:,.0f} per claim",
                    severity=RiskSeverity.MODERATE,
                    category="severity",
                    source_value=avg,
                )
            )

    def _assess_large_losses(self, claims: list[ClaimRecord]) -> None:
        llr = self.tools.large_loss_ratio(claims)
        if llr > 0.3:
            large = [c for c in claims if c.incurred_amount >= 100_000]
            self._add_finding(
                Finding(
                    title="Concentration of large losses",
                    description=f"{len(large)}/{len(claims)} claims exceed $100K ({llr:.0%})",
                    severity=RiskSeverity.HIGH,
                    category="large_loss",
                    evidence=[f"{c.claim_id}: ${c.incurred_amount:,.0f}" for c in large],
                )
            )

    def _assess_open_exposure(self, claims: list[ClaimRecord]) -> None:
        ocr = self.tools.open_claim_ratio(claims)
        if ocr > 0:
            open_claims = [c for c in claims if c.claim_status.value == "open"]
            total_reserves = sum(c.open_reserve for c in open_claims)
            self._add_finding(
                Finding(
                    title=f"Open claims with ${total_reserves:,.0f} in reserves",
                    description=f"{len(open_claims)}/{len(claims)} claims open ({ocr:.0%})",
                    severity=RiskSeverity.MODERATE if ocr < 0.3 else RiskSeverity.HIGH,
                    category="open_exposure",
                    evidence=[f"{c.claim_id}: ${c.open_reserve:,.0f} reserve" for c in open_claims],
                )
            )

    def _assess_litigation(self, claims: list[ClaimRecord]) -> None:
        lr = self.tools.litigation_ratio(claims)
        if lr > 0:
            lit_claims = [c for c in claims if c.claim_status.value == "pending_litigation"]
            for c in lit_claims:
                self._add_finding(
                    Finding(
                        title="Claim with litigation pending",
                        description=f"{c.claim_id}: {c.cause[:100]}",
                        severity=RiskSeverity.HIGH,
                        category="litigation",
                        field_path=f"claim.{c.claim_id}",
                        evidence=[c.cause, c.notes] if c.notes else [c.cause],
                    )
                )

    def _assess_line_distribution(self, claims: list[ClaimRecord]) -> None:
        lines: dict[str, int] = {}
        for c in claims:
            lines[c.line_of_business] = lines.get(c.line_of_business, 0) + 1
        high_freq_lines = [k for k, v in lines.items() if v > 3]
        for line in high_freq_lines:
            self._add_finding(
                Finding(
                    title=f"High claims concentration in {line}",
                    description=f"{lines[line]} claims in this line",
                    severity=RiskSeverity.MODERATE,
                    category="line_concentration",
                    field_path=f"claims_by_line.{line}",
                    source_value=lines[line],
                )
            )

    def _assess_year_over_year(self, claims: list[ClaimRecord]) -> None:
        by_year: dict[int, list[ClaimRecord]] = {}
        for c in claims:
            by_year.setdefault(c.date_of_loss.year, []).append(c)
        years = sorted(by_year.keys())
        if len(years) >= 2:
            recent = years[-1]
            prior = years[-2]
            recent_count = len(by_year[recent])
            prior_count = len(by_year[prior])
            if prior_count > 0 and recent_count > prior_count * 1.5:
                self._add_finding(
                    Finding(
                        title="Increasing claim frequency trend",
                        description=f"{prior_count} claims in {prior} → {recent_count} in {recent}",
                        severity=RiskSeverity.MODERATE,
                        category="trend",
                        evidence=[f"{y}: {len(by_year[y])} claims" for y in years[-3:]],
                    )
                )

    def _check_claim_notes(self, bundle: SubmissionBundle, claims: list[ClaimRecord]) -> None:
        for c in claims:
            text = f"{c.notes} {c.description}".lower()
            if "not disclosed" in text:
                self._add_finding(
                    Finding(
                        title="Previously non-disclosed loss found",
                        description=f"{c.claim_id}: {c.cause[:100]}",
                        severity=RiskSeverity.HIGH,
                        category="non_disclosure",
                        field_path=f"claim.{c.claim_id}",
                        evidence=[c.notes, f"Incurred: ${c.incurred_amount:,.0f}"],
                    )
                )
