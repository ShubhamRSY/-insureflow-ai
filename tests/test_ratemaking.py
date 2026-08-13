"""Tests for the Chapter 5 additions: ratemaking process, methods, and goals."""

from __future__ import annotations

from insureflow.models.agents import RiskSeverity
from insureflow.rating.models import InsuranceLine
from insureflow.rating.ratemaking import (
    AdvisoryOrganization,
    JudgmentAdjustment,
    RateCharacteristic,
    RegulatoryGoal,
    advisory_loss_costs,
    judgment_method,
    line_rate_build_ups,
    loss_ratio_method,
    pure_premium_method,
    rate_characteristics_review,
    ratemaking_factors,
    regulatory_review,
    run_ratemaking_study,
)

# ── 1. Three-step process / pure premium method ────────────────────────────


def test_mas_wholesale_base_rate():
    """Reproduce the textbook example: $100 pure premium + $35 expense loading = $135 base rate."""
    result = pure_premium_method(
        10_000_000,
        100_000,
        lae=1_000_000,
        acquisition=1_500_000,
        general_admin=800_000,
        premium_taxes=200_000,
        loss_adjustment_in_pure_premium=False,
    )
    assert result.pure_premium == 100.0
    assert result.expense_loading == 35.0
    assert result.base_rate == 135.0
    assert result.earned_exposure_units == 100_000.0
    assert len(result.steps) == 3
    assert [s.step for s in result.steps] == [1, 2, 3]


def test_contingency_and_profit_loading():
    result = pure_premium_method(10_000_000, 100_000, contingency_pct=5.0, profit_pct=5.0)
    assert result.base_rate == 100.0
    assert result.contingency_loading == 5.0
    assert result.profit_loading == 5.0
    assert result.gross_rate == 110.0


def test_pure_premium_zero_exposure_raises():
    import pytest

    with pytest.raises(ValueError):
        pure_premium_method(10_000_000, 0)


# ── 2. Loss ratio method ───────────────────────────────────────────────────


def test_loss_ratio_method_no_change():
    result = loss_ratio_method(135.0, 0.65, 0.65)
    assert result.rate_change_pct == 0.0
    assert result.indicated_rate == 135.0


def test_loss_ratio_method_rate_change():
    result = loss_ratio_method(135.0, 0.60, 0.65)
    assert result.projected_loss_ratio == 0.60
    assert result.rate_change_pct == round((0.60 / 0.65 - 1.0) * 100, 2)
    assert result.indicated_rate == round(135.0 * (0.60 / 0.65), 4)


def test_loss_ratio_method_trend_and_development():
    result = loss_ratio_method(
        135.0,
        0.60,
        0.65,
        trend_factor=1.03,
        loss_development_factor=1.05,
    )
    assert result.projected_loss_ratio == round(0.60 * 1.03 * 1.05, 4)
    assert result.detail.startswith("Projected loss ratio")


# ── 3. Judgment method ─────────────────────────────────────────────────────


def test_judgment_method_compounds_adjustments():
    result = judgment_method(
        135.0,
        [
            JudgmentAdjustment(factor="Deductible option", pct=-10.0, rationale="Credit for $10k deductible"),
            JudgmentAdjustment(factor="Loss control", pct=-5.0, rationale="Sprinkler credit"),
        ],
    )
    assert result.judgment_rate == round(135.0 * 0.9 * 0.95, 4)
    assert len(result.adjustments) == 2


# ── 4. Regulatory goals ────────────────────────────────────────────────────


def test_regulatory_review_pass():
    result = pure_premium_method(10_000_000, 100_000, contingency_pct=5.0, profit_pct=5.0)
    assessments = regulatory_review(result)
    by_goal = {a.goal: a.status for a in assessments}
    assert by_goal[RegulatoryGoal.ADEQUATE] == "pass"
    assert by_goal[RegulatoryGoal.NOT_EXCESSIVE] == "pass"
    assert by_goal[RegulatoryGoal.NOT_UNFAIRLY_DISCRIMINATORY] == "pass"


def test_regulatory_review_flags_excessive_markup():
    result = pure_premium_method(10_000_000, 100_000, contingency_pct=100.0, profit_pct=100.0)
    assessments = regulatory_review(result)
    by_goal = {a.goal: a.status for a in assessments}
    assert by_goal[RegulatoryGoal.NOT_EXCESSIVE] == "fail"
    assert by_goal[RegulatoryGoal.ADEQUATE] == "pass"


def test_regulatory_review_flags_discrimination():
    result = pure_premium_method(10_000_000, 100_000)
    assessments = regulatory_review(result, uses_prohibited_basis=True)
    by_goal = {a.goal: a.status for a in assessments}
    assert by_goal[RegulatoryGoal.NOT_UNFAIRLY_DISCRIMINATORY] == "fail"


# ── 5. Rate characteristics ────────────────────────────────────────────────


def test_rate_characteristics_review():
    result = pure_premium_method(10_000_000, 100_000, contingency_pct=5.0, profit_pct=5.0)
    assessments = rate_characteristics_review(result)
    by_name = {a.characteristic: a.status for a in assessments}
    assert by_name[RateCharacteristic.PROVIDES_FOR_CONTINGENCIES] == "pass"
    assert by_name[RateCharacteristic.PROMOTES_LOSS_CONTROL] == "pass"


def test_rate_characteristics_flags_instability():
    result = pure_premium_method(10_000_000, 100_000, contingency_pct=5.0, profit_pct=5.0)
    assessments = rate_characteristics_review(result, rate_change_pct=25.0, data_lag_years=3.0)
    by_name = {a.characteristic: a.status for a in assessments}
    assert by_name[RateCharacteristic.STABLE] == "flag"
    assert by_name[RateCharacteristic.RESPONSIVE] == "flag"


# ── 6. Advisory organizations and factors ──────────────────────────────────


def test_advisory_organizations():
    iso_costs = advisory_loss_costs(AdvisoryOrganization.ISO)
    assert any(c.line == "commercial_property" for c in iso_costs)
    assert any(c.organization is AdvisoryOrganization.NCCI for c in advisory_loss_costs(AdvisoryOrganization.NCCI))
    assert any(c.organization is AdvisoryOrganization.SURETY for c in advisory_loss_costs(AdvisoryOrganization.SURETY))
    orgs = {org.value for org in AdvisoryOrganization}
    assert {"ISO", "AAIS", "NCCI", "Surety Association of America"}.issubset(orgs)


def test_ratemaking_factors():
    factors = ratemaking_factors()
    assert len(factors) >= 6
    assert any("reserve" in f.factor.lower() for f in factors)
    assert any("delay" in f.factor.lower() for f in factors)
    assert all(isinstance(f.severity, RiskSeverity) for f in factors)


# ── 7. Per-line build-ups and aggregate study ──────────────────────────────


def test_line_rate_build_ups():
    from insureflow.rating.engine import ISO_LOSS_COSTS

    build_ups = line_rate_build_ups()
    assert len(build_ups) == len(ISO_LOSS_COSTS)
    for b in build_ups:
        assert b.gross_rate > b.base_rate >= b.pure_premium


def test_run_ratemaking_study():
    study = run_ratemaking_study(line=InsuranceLine.WORKERS_COMP)
    assert study.pure_premium_result is not None
    assert study.loss_ratio_result is not None
    assert study.judgment_result is not None
    assert len(study.regulatory) == 3
    assert len(study.characteristics) == 5
    assert "ISO" in study.advisory_orgs
    assert "NCCI" in study.advisory_orgs
    assert study.worst_severity in (RiskSeverity.LOW, RiskSeverity.MODERATE, RiskSeverity.HIGH)
    assert "pure premium" in study.summary
