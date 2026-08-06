"""Tests for the producer-experience agent (financial function / distribution quality)."""

from __future__ import annotations

from typing import Any

from insureflow.agents.producer_experience_agent import ProducerExperienceAgent
from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import (
    BrokerInfo,
    CoverageDetail,
    LocationData,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
)
from insureflow.underwriting.selection import SelectionStandardsConfig


class _FakePortfolio:
    """Read-only stub matching PolicySource.list_policies, avoiding disk I/O."""

    def __init__(
        self,
        producers: list[str],
        loss_ratios: list[float] | None = None,
        observed: bool = True,
        risk_score: float = 0.5,
    ) -> None:
        self._producers = producers
        self._loss_ratios = loss_ratios or [0.0] * len(producers)
        self._observed = observed
        self._risk_score = risk_score

    def list_policies(self, org_id: str = "default") -> list[Any]:
        from insureflow.portfolio.store import PortfolioPolicy

        policies = []
        for i, producer in enumerate(self._producers):
            premium = 10_000 * (i + 1)
            policies.append(
                PortfolioPolicy(
                    policy_id=f"pol-{i}",
                    bundle_id=f"b-{i}",
                    org_id=org_id,
                    producer_name=producer,
                    naics_code="452210",
                    state="FL",
                    tiv=2_000_000 * (i + 1),
                    premium=premium,
                    risk_score=self._risk_score,
                    incurred_loss=premium * self._loss_ratios[i] if self._observed else 0.0,
                    loss_data_available=self._observed,
                    is_active=True,
                )
            )
        return policies


def _make_bundle(broker_name: str) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="prod-test-bundle",
        structured=StructuredSubmission(
            submission_id="prod-test-sub",
            coverages=[CoverageDetail(coverage_type="general_liability", limit_amount=1_500_000, premium=50_000, deductible=0.0)],
            locations=[LocationData(address="1 Main St", city="Anywhere", state="FL", zip_code="33101", building_value=1_500_000)],
            risk_profile=RiskProfile(naics_code="452210", occupancy_type="retail"),
            broker=BrokerInfo(broker_name=broker_name),
        ),
    )


def test_agent_loop_inactive_without_loss_data() -> None:
    agent = ProducerExperienceAgent(
        portfolio=_FakePortfolio(producers=["Acme Brokerage"] * 30, observed=False),
        config=SelectionStandardsConfig(),
    )
    result = agent.run(_make_bundle("Acme Brokerage"), org_id="default")
    assert agent.last_experiences == {}
    assert result.findings == []


def test_agent_flags_worse_producer() -> None:
    agent = ProducerExperienceAgent(
        portfolio=_FakePortfolio(producers=["Acme Brokerage"] * 30, loss_ratios=[0.9] * 30),
        config=SelectionStandardsConfig(),
    )
    result = agent.run(_make_bundle("Acme Brokerage"), org_id="default")
    worse = [f for f in result.findings if f.title.startswith("Producer Acme Brokerage: submissions running")]
    assert worse and worse[0].severity == RiskSeverity.HIGH
    assert any("terminate the relationship" in f.description for f in worse)
    assert any("pre-screen against carrier appetite" in f.description for f in worse)
    # Aggregate at-risk finding also fires.
    assert any("Producer book quality" in f.title for f in result.findings)


def test_agent_acknowledges_better_producer() -> None:
    agent = ProducerExperienceAgent(
        portfolio=_FakePortfolio(producers=["Acme Brokerage"] * 30, loss_ratios=[0.3] * 30),
        config=SelectionStandardsConfig(),
    )
    result = agent.run(_make_bundle("Acme Brokerage"), org_id="default")
    better = [f for f in result.findings if f.title.startswith("Producer Acme Brokerage: book performing better")]
    assert better and better[0].severity == RiskSeverity.LOW
    assert not any("Producer book quality" in f.title for f in result.findings)


def test_agent_too_little_data_for_producer() -> None:
    agent = ProducerExperienceAgent(
        portfolio=_FakePortfolio(producers=["Acme Brokerage"] * 3, loss_ratios=[1.0] * 3),
        config=SelectionStandardsConfig(),
    )
    result = agent.run(_make_bundle("Acme Brokerage"), org_id="default")
    thin = [f for f in result.findings if f.title.startswith("Producer Acme Brokerage: too little")]
    assert thin and thin[0].severity == RiskSeverity.LOW
    assert not any("Producer book quality" in f.title for f in result.findings)


def test_agent_lists_multiple_at_risk_producers() -> None:
    producers = ["Acme Brokerage"] * 30 + ["HighRisk Agency"] * 30
    ratios = [0.9] * 30 + [0.95] * 30
    agent = ProducerExperienceAgent(
        portfolio=_FakePortfolio(producers=producers, loss_ratios=ratios),
        config=SelectionStandardsConfig(),
    )
    result = agent.run(_make_bundle("Acme Brokerage"), org_id="default")
    quality = [f for f in result.findings if f.title.startswith("Producer book quality")]
    assert quality
    assert quality[0].source_value == 2
    assert "HighRisk Agency" in quality[0].description


def test_agent_only_rates_submitting_producer_when_others_missing() -> None:
    producers = ["Other Agency"] * 30
    ratios = [0.9] * 30
    agent = ProducerExperienceAgent(
        portfolio=_FakePortfolio(producers=producers, loss_ratios=ratios),
        config=SelectionStandardsConfig(),
    )
    result = agent.run(_make_bundle("Acme Brokerage"), org_id="default")
    # The submitting producer has no recorded experience → only the aggregate fires.
    assert agent.last_experiences.keys() == {"Other Agency"}
    assert not any("Producer Acme Brokerage" in f.title for f in result.findings)
    assert any("Producer book quality" in f.title for f in result.findings)
