"""Producer experience agent — the financial function's underwriter/agent balance.

The doctrine notes that the underwriter is judged on quality while the producing
agent is compensated on volume, and that the insurer may terminate a producer
whose submissions consistently produce above-average claims. This agent measures
each producing broker/agent's realized loss experience (credibility-blended
against the expectation of the classes they submitted) and flags those running
worse than expected, coaching pre-screening against carrier appetite.
"""

from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.portfolio.store import PolicySource, get_portfolio_store
from insureflow.underwriting.selection import ProducerExperience, SelectionStandardsConfig, compute_producer_experience


class ProducerExperienceAgent(BaseAgent):
    """Rates the producing broker's book against the carrier's expectations."""

    agent_type = AgentType.PRODUCER_EXPERIENCE
    agent_name = "ProducerExperienceAgent"

    def __init__(
        self,
        portfolio: PolicySource | None = None,
        config: SelectionStandardsConfig | None = None,
    ) -> None:
        super().__init__()
        self._portfolio = portfolio or get_portfolio_store()
        self._config = config or SelectionStandardsConfig()
        self._last_experiences: dict[str, ProducerExperience] = {}

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        org_id = kwargs.get("org_id", "default")
        producer = self._producer_from_bundle(bundle)

        policies = self._portfolio.list_policies(org_id)
        observed = [p for p in policies if getattr(p, "loss_data_available", False) or getattr(p, "incurred_loss", 0.0) > 0]
        experiences = compute_producer_experience(
            producers=[getattr(p, "producer_name", "") for p in observed],
            premiums=[p.premium for p in observed],
            incurred_losses=[getattr(p, "incurred_loss", 0.0) for p in observed],
            risk_scores=[getattr(p, "risk_score", 0.5) for p in observed],
            config=self._config,
        )
        self._last_experiences = experiences
        self._record_findings(experiences, producer)

    @property
    def last_experiences(self) -> dict[str, ProducerExperience]:
        return self._last_experiences

    @staticmethod
    def _producer_from_bundle(bundle: SubmissionBundle) -> str:
        if bundle.structured and bundle.structured.broker:
            return bundle.structured.broker.broker_name or ""
        return ""

    def _record_findings(self, experiences: dict[str, ProducerExperience], producer: str) -> None:
        if not experiences:
            return

        if producer and producer in experiences:
            exp = experiences[producer]
            if exp.status == "worse":
                self._add_finding(
                    Finding(
                        title=f"Producer {producer}: submissions running above-average claims",
                        description=(
                            f"{producer}'s book is losing {exp.loss_ratio:.0%} against an expected "
                            f"{exp.expected_loss_ratio:.0%} (penalty {exp.penalty_factor:.2f}, credibility "
                            f"{exp.credibility:.0%}, {exp.policy_count} reported policies). If submissions "
                            "consistently produce above-average claims the company may terminate the "
                            "relationship — coach the producer to pre-screen against carrier appetite "
                            "before submitting."
                        ),
                        severity=RiskSeverity.HIGH,
                        category="producer_experience",
                        source_value=exp.penalty_factor,
                        evidence=[
                            f"Realized loss ratio: {exp.loss_ratio:.1%} vs expected {exp.expected_loss_ratio:.1%}",
                            f"Earned premium: ${exp.earned_premium:,.0f}, incurred loss: ${exp.incurred_loss:,.0f}",
                            f"Credibility: {exp.credibility:.0%}",
                        ],
                    )
                )
            elif exp.status == "better":
                self._add_finding(
                    Finding(
                        title=f"Producer {producer}: book performing better than expected",
                        description=(
                            f"{producer}'s book is losing {exp.loss_ratio:.0%} against an expected "
                            f"{exp.expected_loss_ratio:.0%} (penalty {exp.penalty_factor:.2f}) — quality "
                            "production; continue monitoring."
                        ),
                        severity=RiskSeverity.LOW,
                        category="producer_experience",
                        source_value=exp.penalty_factor,
                    )
                )
            elif exp.policy_count < self._config.min_observed_policies_for_feedback:
                self._add_finding(
                    Finding(
                        title=f"Producer {producer}: too little loss experience to rate",
                        description=(
                            f"Only {exp.policy_count} reported policies from {producer} — below the "
                            f"{self._config.min_observed_policies_for_feedback} minimum for the loss "
                            "experience loop to trust the producer's loss ratio."
                        ),
                        severity=RiskSeverity.LOW,
                        category="producer_experience",
                    )
                )

        at_risk = [e for e in experiences.values() if e.status == "worse"]
        if at_risk:
            names = ", ".join(f"{e.producer_name} ({e.policy_count} policies)" for e in sorted(at_risk, key=lambda e: e.penalty_factor, reverse=True))
            self._add_finding(
                Finding(
                    title="Producer book quality: relationship risk in the book",
                    description=(
                        f"{len(at_risk)} producer(s) with credible above-average claims experience: {names}. "
                        "Consistently poor submissions invite termination and dilute the financial function — "
                        "review appointments and enforce pre-screening."
                    ),
                    severity=RiskSeverity.MODERATE,
                    category="producer_experience",
                    source_value=len(at_risk),
                )
            )
