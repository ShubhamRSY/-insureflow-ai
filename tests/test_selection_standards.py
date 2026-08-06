"""Tests for the selection-standards / book-balance underwriting model."""

from __future__ import annotations

import math
from typing import Any

import pytest

from insureflow.agents.selection_standards_agent import SelectionStandardsAgent
from insureflow.models.agents import UWDecision
from insureflow.models.submissions import (
    BrokerInfo,
    CoverageDetail,
    LocationData,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
)
from insureflow.underwriting.selection import (
    RiskClass,
    SelectionCandidate,
    SelectionStandardsConfig,
    SelectionTier,
    apply_experience_to_config,
    assess_selection,
    build_book_snapshot,
    coefficient_of_variation,
    compute_book_experience,
    compute_producer_experience,
)


def _book(policy_count: int, premium_cv: float = 0.3, mean_premium: float = 40_000) -> tuple[int, list[float], list[float]]:
    """Build a synthetic book with N policies and a controlled premium CV."""
    import math

    premiums = [mean_premium * (1 + premium_cv * math.sin(i)) for i in range(policy_count)]
    tivs = [p * 20 for p in premiums]
    return policy_count, premiums, tivs


class TestSelectionEngine:
    def test_coefficient_of_variation(self) -> None:
        assert coefficient_of_variation([]) == 0.0
        assert coefficient_of_variation([100]) == 0.0
        assert abs(coefficient_of_variation([100, 100, 100]) - 0.0) < 1e-9
        assert abs(coefficient_of_variation([0, 100]) - 0.0) < 1e-9

    def test_predictability_grows_with_volume(self) -> None:
        small = build_book_snapshot(5, 0, 0, [100, 200, 300, 400, 500], [1000] * 5)
        large = build_book_snapshot(100, 0, 0, [100] * 100, [1000] * 100)
        assert large.predictability > small.predictability

    def test_tier_transitions(self) -> None:
        thin = build_book_snapshot(3, 0, 0, [100, 200, 300], [1000, 2000, 3000])
        grown = build_book_snapshot(80, 0, 0, [100] * 80, [1000] * 80)
        assert thin.tier == SelectionTier.STRICT
        assert grown.tier == SelectionTier.BROAD

    def test_homogeneity_boosts_predictability(self) -> None:
        homogeneous = build_book_snapshot(30, 0, 0, [100] * 30, [1000] * 30)
        heterogeneous = build_book_snapshot(30, 0, 0, [100, 200, 400, 800, 1600, 3200] * 5, [1000] * 30)
        assert homogeneous.predictability > heterogeneous.predictability

    def test_strict_book_declines_substandard(self) -> None:
        _, premiums, tivs = _book(4)
        book = build_book_snapshot(4, sum(tivs), sum(premiums), premiums, tivs)
        assert book.tier == SelectionTier.STRICT
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.75)
        result = assess_selection(candidate, book)
        assert result.action == UWDecision.DECLINE

    def test_strict_book_refers_standard(self) -> None:
        _, premiums, tivs = _book(4)
        book = build_book_snapshot(4, sum(tivs), sum(premiums), premiums, tivs)
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.STANDARD, risk_score=0.5)
        assert assess_selection(candidate, book).action == UWDecision.ACCEPT

    def test_balanced_book_conditions_substandard(self) -> None:
        _, premiums, tivs = _book(30, premium_cv=0.2)
        book = build_book_snapshot(30, sum(tivs), sum(premiums), premiums, tivs)
        assert book.tier == SelectionTier.BALANCED
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.7)
        assert assess_selection(candidate, book).action == UWDecision.CONDITIONAL_ACCEPT

    def test_broad_book_admits_substandard(self) -> None:
        _, premiums, tivs = _book(80)
        book = build_book_snapshot(80, sum(tivs), sum(premiums), premiums, tivs)
        assert book.tier == SelectionTier.BROAD
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.7)
        assert assess_selection(candidate, book).action == UWDecision.ACCEPT

    def test_selection_expense_flagged_when_high(self) -> None:
        # Tiny premium book: selection cost swamps written premium.
        premiums = [500] * 10
        book = build_book_snapshot(10, sum(premiums) * 10, sum(premiums), premiums, [5000] * 10)
        candidate = SelectionCandidate(tiv=100_000, premium=500, risk_class=RiskClass.STANDARD, risk_score=0.5)
        result = assess_selection(candidate, book)
        assert result.selection_expense_ratio > 0.05
        assert any("Selection expense" in w for w in result.warnings)

    def test_candidate_expense_ratio_flagged(self) -> None:
        premiums = [1000] * 60
        book = build_book_snapshot(60, sum(premiums) * 10, sum(premiums), premiums, [10000] * 60)
        candidate = SelectionCandidate(tiv=200_000, premium=200, risk_class=RiskClass.STANDARD, risk_score=0.5)
        result = assess_selection(candidate, book)
        assert any("candidate premium" in w for w in result.warnings)

    def test_substandard_loading_applied_when_admitted(self) -> None:
        _, premiums, tivs = _book(30, premium_cv=0.2)
        book = build_book_snapshot(30, sum(tivs), sum(premiums), premiums, tivs)
        assert book.tier == SelectionTier.BALANCED
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.7)
        result = assess_selection(candidate, book)
        assert result.action == UWDecision.CONDITIONAL_ACCEPT
        assert result.substandard_loading_pct == 20.0

    def test_substandard_loading_clamped(self) -> None:
        _, premiums, tivs = _book(80)
        book = build_book_snapshot(80, sum(tivs), sum(premiums), premiums, tivs)
        assert book.tier == SelectionTier.BROAD
        low = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.65)
        assert assess_selection(low, book).substandard_loading_pct == 15.0
        mid = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.8)
        assert assess_selection(mid, book).substandard_loading_pct == 30.0

    def test_no_loading_when_declined(self) -> None:
        _, premiums, tivs = _book(4)
        book = build_book_snapshot(4, sum(tivs), sum(premiums), premiums, tivs)
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.75)
        result = assess_selection(candidate, book)
        assert result.action == UWDecision.DECLINE
        assert result.substandard_loading_pct == 0.0

    def test_intra_class_dispersion(self) -> None:
        uniform = build_book_snapshot(30, 0, 0, [100] * 30, [1000] * 30, risk_scores=[0.5] * 30)
        assert uniform.intra_class_cv == 0.0
        assert uniform.class_dispersion == {"standard": 0.0}

        mixed = build_book_snapshot(30, 0, 0, [100] * 30, [1000] * 30, risk_scores=[0.41, 0.64] * 15)
        assert mixed.intra_class_cv > 0.15

        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.STANDARD, risk_score=0.5)
        result = assess_selection(candidate, mixed)
        assert any("Intra-class" in w for w in result.warnings)


class TestBookExperience:
    def test_experience_unknown_without_data(self) -> None:
        exp = compute_book_experience([], [], [])
        assert exp.status == "unknown"
        assert exp.credibility == 0.0
        assert exp.penalty_factor == 1.0

    def test_experience_better_when_clean(self) -> None:
        exp = compute_book_experience([10_000] * 30, [4_000] * 30, [0.5] * 30)
        assert exp.credibility == 1.0
        assert exp.status == "better"
        assert exp.penalty_factor < 1.0
        assert exp.loss_ratio == pytest.approx(0.4)
        assert exp.expected_loss_ratio == pytest.approx(0.6)
        assert exp.classes["standard"].loss_ratio == pytest.approx(0.4)

    def test_experience_worse_when_lossy(self) -> None:
        exp = compute_book_experience([10_000] * 30, [9_000] * 30, [0.5] * 30)
        assert exp.status == "worse"
        assert exp.penalty_factor > 1.0
        # 1 + credibility * (0.9 / 0.6 - 1) = 1.5
        assert exp.penalty_factor == pytest.approx(1.5)

    def test_experience_credibility_scales_thin_book(self) -> None:
        exp = compute_book_experience([10_000] * 6, [10_000] * 6, [0.5] * 6)
        assert exp.credibility == pytest.approx(math.sqrt(6 / 30), abs=1e-3)
        assert exp.penalty_factor > 1.0
        assert exp.penalty_factor < 1.5

    def test_experience_ignores_subthreshold_classes(self) -> None:
        exp = compute_book_experience([10_000] * 3, [10_000] * 3, [0.5] * 3)
        assert exp.classes["standard"].credibility == 0.0
        assert exp.classes["standard"].penalty_factor == 1.0
        assert exp.penalty_factor == 1.0
        assert exp.status == "unknown"

    def test_experience_groups_by_class(self) -> None:
        premiums = [10_000] * 40
        losses = [8_000] * 40
        scores = ([0.35] * 20) + ([0.75] * 20)  # preferred + substandard, no standard
        exp = compute_book_experience(premiums, losses, scores)
        assert set(exp.classes) == {"preferred", "substandard"}
        assert exp.classes["preferred"].expected_loss_ratio == pytest.approx(0.45)
        assert exp.classes["substandard"].expected_loss_ratio == pytest.approx(0.70)

    def test_apply_experience_tightens_on_worse(self) -> None:
        cfg = SelectionStandardsConfig()
        exp = compute_book_experience([10_000] * 30, [9_000] * 30, [0.5] * 30)
        adjusted = apply_experience_to_config(cfg, exp)
        assert adjusted.strict_threshold > cfg.strict_threshold
        assert adjusted.balanced_threshold > cfg.balanced_threshold
        assert adjusted.strict_threshold < adjusted.balanced_threshold

    def test_apply_experience_relaxes_on_better(self) -> None:
        cfg = SelectionStandardsConfig()
        exp = compute_book_experience([10_000] * 30, [3_000] * 30, [0.5] * 30)
        adjusted = apply_experience_to_config(cfg, exp)
        assert adjusted.strict_threshold < cfg.strict_threshold
        assert adjusted.balanced_threshold < cfg.balanced_threshold

    def test_apply_experience_noop_without_data(self) -> None:
        cfg = SelectionStandardsConfig()
        exp = compute_book_experience([], [], [])
        assert apply_experience_to_config(cfg, exp) is cfg

    def test_substandard_loading_scaled_by_class_experience(self) -> None:
        _, premiums, tivs = _book(80)
        book = build_book_snapshot(80, sum(tivs), sum(premiums), premiums, tivs)
        assert book.tier == SelectionTier.BROAD
        exp = compute_book_experience([10_000] * 80, [9_000] * 80, [0.75] * 80)
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.7)
        result = assess_selection(candidate, book, experience=exp)
        # base loading 20% scaled up by the lossy substandard class penalty
        assert result.substandard_loading_pct > 20.0
        assert result.experience is exp

    def test_worse_class_experience_warns(self) -> None:
        _, premiums, tivs = _book(80)
        book = build_book_snapshot(80, sum(tivs), sum(premiums), premiums, tivs)
        exp = compute_book_experience([10_000] * 80, [9_000] * 80, [0.75] * 80)
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.7)
        result = assess_selection(candidate, book, experience=exp)
        assert any("worse than rating assumed" in w for w in result.warnings)


class TestProducerExperience:
    def test_producer_experience_groups_by_producer(self) -> None:
        exp = compute_producer_experience(
            ["Acme Brokerage"] * 30,
            [10_000] * 30,
            [4_000] * 30,
            [0.5] * 30,
        )
        assert set(exp) == {"Acme Brokerage"}
        pe = exp["Acme Brokerage"]
        assert pe.status == "better"
        assert pe.policy_count == 30
        assert pe.loss_ratio == pytest.approx(0.4)
        assert pe.expected_loss_ratio == pytest.approx(0.6)

    def test_producer_experience_worse(self) -> None:
        exp = compute_producer_experience(
            ["Acme Brokerage"] * 30,
            [10_000] * 30,
            [9_000] * 30,
            [0.5] * 30,
        )
        pe = exp["Acme Brokerage"]
        assert pe.status == "worse"
        assert pe.penalty_factor == pytest.approx(1.5)

    def test_producer_experience_expectation_blends_classes(self) -> None:
        # Half preferred (expected 0.45) + half substandard (expected 0.70).
        exp = compute_producer_experience(
            ["Acme Brokerage"] * 40,
            [10_000] * 40,
            [5_750] * 40,
            ([0.35] * 20) + ([0.75] * 20),
        )
        pe = exp["Acme Brokerage"]
        assert pe.expected_loss_ratio == pytest.approx(0.575)
        assert pe.status == "expected"

    def test_producer_experience_ignores_unknown_producer(self) -> None:
        exp = compute_producer_experience(["", ""], [10_000, 10_000], [5_000, 5_000], [0.5, 0.5])
        assert exp == {}

    def test_producer_experience_too_little_data(self) -> None:
        exp = compute_producer_experience(["Acme Brokerage"] * 3, [10_000] * 3, [10_000] * 3, [0.5] * 3)
        pe = exp["Acme Brokerage"]
        assert pe.credibility == 0.0
        assert pe.penalty_factor == 1.0
        assert pe.status == "unknown"


def _better_producer() -> Any:
    return compute_producer_experience(["Acme Brokerage"] * 30, [10_000] * 30, [4_000] * 30, [0.5] * 30)["Acme Brokerage"]


def _worse_producer() -> Any:
    return compute_producer_experience(["Acme Brokerage"] * 30, [10_000] * 30, [9_000] * 30, [0.5] * 30)["Acme Brokerage"]


class TestProducerSelectionTip:
    """The doctrine: an agent's past performance may determine acceptance of a marginal exposure."""

    def test_better_producer_tips_strict_refer_to_admission(self) -> None:
        _, premiums, tivs = _book(4)
        book = build_book_snapshot(4, sum(tivs), sum(premiums), premiums, tivs)
        assert book.tier == SelectionTier.STRICT
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.6)
        result = assess_selection(candidate, book, producer_experience=_better_producer())
        assert result.action == UWDecision.CONDITIONAL_ACCEPT
        assert result.producer_tipped
        assert result.producer_experience is not None
        assert result.substandard_loading_pct == 15.0
        assert any("tips this marginally acceptable exposure" in r for r in result.rationale)

    def test_worse_producer_tips_admission_to_refer(self) -> None:
        _, premiums, tivs = _book(30, premium_cv=0.2)
        book = build_book_snapshot(30, sum(tivs), sum(premiums), premiums, tivs)
        assert book.tier == SelectionTier.BALANCED
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.7)
        result = assess_selection(candidate, book, producer_experience=_worse_producer())
        assert result.action == UWDecision.REFER
        assert result.producer_tipped
        assert result.substandard_loading_pct == 0.0

    def test_worse_producer_tips_broad_accept_to_refer(self) -> None:
        _, premiums, tivs = _book(80)
        book = build_book_snapshot(80, sum(tivs), sum(premiums), premiums, tivs)
        assert book.tier == SelectionTier.BROAD
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.7)
        assert assess_selection(candidate, book).action == UWDecision.ACCEPT
        result = assess_selection(candidate, book, producer_experience=_worse_producer())
        assert result.action == UWDecision.REFER
        assert result.producer_tipped

    def test_better_producer_credits_loading_when_already_admitted(self) -> None:
        _, premiums, tivs = _book(80)
        book = build_book_snapshot(80, sum(tivs), sum(premiums), premiums, tivs)
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.8)
        base = assess_selection(candidate, book)
        assert base.action == UWDecision.ACCEPT
        result = assess_selection(candidate, book, producer_experience=_better_producer())
        assert result.action == UWDecision.ACCEPT
        assert result.producer_tipped
        # base loading 30% scaled by the 0.67 better-producer penalty factor
        assert result.substandard_loading_pct < base.substandard_loading_pct

    def test_no_tip_without_producer_credibility(self) -> None:
        _, premiums, tivs = _book(4)
        book = build_book_snapshot(4, sum(tivs), sum(premiums), premiums, tivs)
        pe = compute_producer_experience(["Acme Brokerage"] * 5, [10_000] * 5, [4_000] * 5, [0.5] * 5)["Acme Brokerage"]
        assert pe.status == "better"
        assert pe.credibility < 0.5
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.6)
        result = assess_selection(candidate, book, producer_experience=pe)
        assert result.action == UWDecision.REFER
        assert not result.producer_tipped

    def test_no_tip_for_standard_risk(self) -> None:
        _, premiums, tivs = _book(4)
        book = build_book_snapshot(4, sum(tivs), sum(premiums), premiums, tivs)
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.STANDARD, risk_score=0.5)
        result = assess_selection(candidate, book, producer_experience=_worse_producer())
        assert result.action == UWDecision.ACCEPT
        assert not result.producer_tipped

    def test_no_tip_above_accept_upgrade_cap(self) -> None:
        _, premiums, tivs = _book(80)
        book = build_book_snapshot(80, sum(tivs), sum(premiums), premiums, tivs)
        assert book.tier == SelectionTier.BROAD
        candidate = SelectionCandidate(tiv=1_000_000, premium=40_000, risk_class=RiskClass.SUBSTANDARD, risk_score=0.9)
        assert assess_selection(candidate, book).action == UWDecision.REFER
        result = assess_selection(candidate, book, producer_experience=_better_producer())
        # score 0.9 is beyond even a good producer's admission band
        assert result.action == UWDecision.REFER
        assert not result.producer_tipped


class TestSelectionStandardsAgent:
    def test_agent_accepts_clean_standard_candidate(self) -> None:
        agent = SelectionStandardsAgent(portfolio=_FakePortfolio(), config=SelectionStandardsConfig())
        bundle = _make_bundle(
            premium=50_000,
            tiv=1_500_000,
            naics="452210",
            claims=1,
            candidate_risk_score=0.4,
        )
        result = agent.run(bundle, org_id="default", candidate_risk_score=0.4)
        assert result.success
        assert any(f.category == "selection_standards" for f in result.findings)
        gate = [f for f in result.findings if f.title.startswith("Selection gate")]
        assert gate and gate[0].source_value == UWDecision.ACCEPT.value

    def test_agent_gate_reflects_strict_book(self) -> None:
        agent = SelectionStandardsAgent(
            portfolio=_FakePortfolio(),
            config=SelectionStandardsConfig(strict_threshold=0.8, balanced_threshold=0.9),
        )
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210", claims=4, candidate_risk_score=0.8)
        result = agent.run(bundle, org_id="default", candidate_risk_score=0.8)
        gate = [f for f in result.findings if f.title.startswith("Selection gate")]
        assert gate and gate[0].source_value == UWDecision.DECLINE.value

    def test_agent_law_of_averages_finding(self) -> None:
        agent = SelectionStandardsAgent(portfolio=_FakePortfolio(), config=SelectionStandardsConfig())
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210")
        result = agent.run(bundle, org_id="default")
        assert any("Law of averages" in f.title for f in result.findings)

    def test_agent_recommendation_carries_loading(self) -> None:
        agent = SelectionStandardsAgent(portfolio=_FakePortfolio(count=30), config=SelectionStandardsConfig())
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210")
        result = agent.run(bundle, org_id="default", candidate_risk_score=0.7)
        assert result.recommendation is not None
        assert result.recommendation.suggested_premium_modification == 20.0

    def test_agent_no_loading_when_declined(self) -> None:
        agent = SelectionStandardsAgent(portfolio=_FakePortfolio(count=4), config=SelectionStandardsConfig())
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210")
        result = agent.run(bundle, org_id="default", candidate_risk_score=0.8)
        assert result.recommendation is None
        gate = [f for f in result.findings if f.title.startswith("Selection gate")]
        assert gate and gate[0].source_value == UWDecision.DECLINE.value

    def test_agent_loop_inactive_without_loss_data(self) -> None:
        agent = SelectionStandardsAgent(portfolio=_FakePortfolio(count=30), config=SelectionStandardsConfig())
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210")
        result = agent.run(bundle, org_id="default", candidate_risk_score=0.7)
        exp = agent.last_experience
        assert exp is not None and exp.status == "unknown" and exp.policy_count == 0
        assert result.recommendation is not None
        assert result.recommendation.suggested_premium_modification == 20.0

    def test_agent_tightens_tier_on_worse_experience(self) -> None:
        agent = SelectionStandardsAgent(
            portfolio=_FakePortfolio(count=80, observed_count=80, loss_ratio=1.0, risk_score=0.75),
            config=SelectionStandardsConfig(),
        )
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210")
        result = agent.run(bundle, org_id="default", candidate_risk_score=0.8)
        exp = agent.last_experience
        assert exp is not None and exp.status == "worse"
        assert agent.last_assessment is not None
        # 80-policy homogeneous book would be BROAD; worse experience demotes it.
        assert agent.last_assessment.book.tier == SelectionTier.BALANCED
        gate = [f for f in result.findings if f.title.startswith("Selection gate")]
        assert gate and gate[0].source_value == UWDecision.CONDITIONAL_ACCEPT.value
        assert any(f.title.startswith("Experience feedback: book losing more") for f in result.findings)

    def test_agent_loading_scaled_by_worse_class_experience(self) -> None:
        agent = SelectionStandardsAgent(
            portfolio=_FakePortfolio(count=80, observed_count=80, loss_ratio=1.0, risk_score=0.75),
            config=SelectionStandardsConfig(),
        )
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210")
        result = agent.run(bundle, org_id="default", candidate_risk_score=0.7)
        assert result.recommendation is not None
        mod = result.recommendation.suggested_premium_modification
        assert mod is not None
        # base 20% scaled by the substandard class penalty (>1) → above the base
        assert mod > 20.0

    def test_agent_records_better_experience(self) -> None:
        agent = SelectionStandardsAgent(
            portfolio=_FakePortfolio(count=40, observed_count=40, loss_ratio=0.2),
            config=SelectionStandardsConfig(),
        )
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210")
        result = agent.run(bundle, org_id="default", candidate_risk_score=0.7)
        exp = agent.last_experience
        assert exp is not None and exp.status == "better"
        assert any(f.title.startswith("Experience feedback: book performing better") for f in result.findings)

    def test_agent_better_producer_tips_refer_to_admission(self) -> None:
        agent = SelectionStandardsAgent(portfolio=_FakePortfolio(), config=SelectionStandardsConfig())
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210", broker="Acme Brokerage")
        result = agent.run(
            bundle,
            org_id="default",
            candidate_risk_score=0.68,
            producer_experiences={"Acme Brokerage": _better_producer()},
        )
        assert agent.last_producer_tip is not None and agent.last_producer_tip.status == "better"
        gate = [f for f in result.findings if f.title.startswith("Selection gate")]
        assert gate and gate[0].source_value == UWDecision.CONDITIONAL_ACCEPT.value
        assert any(f.title.startswith("Producer track record:") for f in result.findings)
        assert result.recommendation is not None
        assert result.recommendation.suggested_premium_modification == 15.0

    def test_agent_worse_producer_tips_admission_to_refer(self) -> None:
        agent = SelectionStandardsAgent(portfolio=_FakePortfolio(count=30), config=SelectionStandardsConfig())
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210", broker="Acme Brokerage")
        result = agent.run(
            bundle,
            org_id="default",
            candidate_risk_score=0.7,
            producer_experiences={"Acme Brokerage": _worse_producer()},
        )
        gate = [f for f in result.findings if f.title.startswith("Selection gate")]
        assert gate and gate[0].source_value == UWDecision.REFER.value
        assert result.recommendation is None

    def test_agent_no_producer_tip_without_experiences(self) -> None:
        agent = SelectionStandardsAgent(portfolio=_FakePortfolio(count=30), config=SelectionStandardsConfig())
        bundle = _make_bundle(premium=50_000, tiv=1_500_000, naics="452210", broker="Acme Brokerage")
        result = agent.run(bundle, org_id="default", candidate_risk_score=0.7)
        assert agent.last_producer_tip is None
        assert not any(f.title.startswith("Producer track record:") for f in result.findings)


class _FakePortfolio:
    """Read-only stub matching PolicySource.list_policies, avoiding disk I/O."""

    def __init__(
        self,
        count: int = 4,
        observed_count: int = 0,
        loss_ratio: float = 0.0,
        risk_score: float = 0.5,
    ) -> None:
        self._count = count
        self._observed_count = observed_count
        self._loss_ratio = loss_ratio
        self._risk_score = risk_score

    def list_policies(self, org_id: str = "default") -> list[Any]:
        from insureflow.portfolio.store import PortfolioPolicy

        policies = []
        for i in range(self._count):
            observed = i < self._observed_count
            premium = 10_000 * (i + 1)
            policies.append(
                PortfolioPolicy(
                    policy_id=f"pol-{i}",
                    bundle_id="book",
                    org_id=org_id,
                    naics_code="452210",
                    state="FL",
                    tiv=2_000_000 * (i + 1),
                    premium=premium,
                    risk_score=self._risk_score,
                    incurred_loss=premium * self._loss_ratio if observed else 0.0,
                    loss_data_available=observed,
                    is_active=True,
                )
            )
        return policies


def _make_bundle(
    premium: float,
    tiv: float,
    naics: str,
    claims: int = 0,
    candidate_risk_score: float | None = None,
    broker: str | None = None,
) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="sel-test-bundle",
        structured=StructuredSubmission(
            submission_id="sel-test-sub",
            broker=BrokerInfo(broker_name=broker) if broker else None,
            coverages=[CoverageDetail(coverage_type="general_liability", limit_amount=tiv, premium=premium, deductible=0.0)],
            locations=[LocationData(address="1 Main St", city="Anywhere", state="FL", zip_code="33101", building_value=tiv)],
            risk_profile=RiskProfile(naics_code=naics, occupancy_type="retail"),
        ),
    )
