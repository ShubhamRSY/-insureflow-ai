"""Tests for the selection-standards / book-balance underwriting model."""

from __future__ import annotations

from typing import Any

from insureflow.agents.selection_standards_agent import SelectionStandardsAgent
from insureflow.models.agents import UWDecision
from insureflow.models.submissions import (
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
    assess_selection,
    build_book_snapshot,
    coefficient_of_variation,
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


class _FakePortfolio:
    """Read-only stub matching PortfolioStore.list_policies, avoiding disk I/O."""

    def __init__(self, count: int = 4) -> None:
        self._count = count

    def list_policies(self, org_id: str = "default") -> list[Any]:
        from insureflow.portfolio.store import PortfolioPolicy

        return [
            PortfolioPolicy(
                policy_id=f"pol-{i}",
                bundle_id="book",
                org_id=org_id,
                naics_code="452210",
                state="FL",
                tiv=2_000_000 * (i + 1),
                premium=10_000 * (i + 1),
                is_active=True,
            )
            for i in range(self._count)
        ]


def _make_bundle(
    premium: float,
    tiv: float,
    naics: str,
    claims: int = 0,
    candidate_risk_score: float | None = None,
) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="sel-test-bundle",
        structured=StructuredSubmission(
            submission_id="sel-test-sub",
            coverages=[CoverageDetail(coverage_type="general_liability", limit_amount=tiv, premium=premium, deductible=0.0)],
            locations=[LocationData(address="1 Main St", city="Anywhere", state="FL", zip_code="33101", building_value=tiv)],
            risk_profile=RiskProfile(naics_code=naics, occupancy_type="retail"),
        ),
    )
