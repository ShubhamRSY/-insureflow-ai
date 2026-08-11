from __future__ import annotations

from insureflow.models.agents import RiskSeverity
from insureflow.rating.investment_income import LossTail, assess_investment_income, investment_income_across_lines, investment_income_severity, states_requiring_explicit_investment_income
from insureflow.rating.models import InsuranceLine


def test_liability_lines_offset_more_than_property() -> None:
    gl = assess_investment_income(InsuranceLine.GENERAL_LIABILITY)
    prop = assess_investment_income(InsuranceLine.COMMERCIAL_PROPERTY)
    assert gl.rate_offset_pct > prop.rate_offset_pct
    assert gl.tail == LossTail.LONG
    assert prop.tail == LossTail.SHORT
    assert gl.investment_income_pct_of_premium > prop.investment_income_pct_of_premium


def test_investment_income_math() -> None:
    a = assess_investment_income(InsuranceLine.GENERAL_LIABILITY, yield_rate=0.04)
    total = a.loss_reserve_funding + a.unearned_premium_reserve_funding
    assert a.investment_income_pct_of_premium == round(total * 0.04 * 100, 2)
    assert a.rate_offset_pct == a.investment_income_pct_of_premium


def test_yield_scales_income() -> None:
    low = assess_investment_income(InsuranceLine.GENERAL_LIABILITY, yield_rate=0.02)
    high = assess_investment_income(InsuranceLine.GENERAL_LIABILITY, yield_rate=0.06)
    assert high.rate_offset_pct > low.rate_offset_pct
    assert high.investment_income_pct_of_premium == round(low.investment_income_pct_of_premium * 3, 2)


def test_state_requirement() -> None:
    assert assess_investment_income(InsuranceLine.GENERAL_LIABILITY, state="NY").state_requires_explicit is True
    assert assess_investment_income(InsuranceLine.GENERAL_LIABILITY, state="CA").state_requires_explicit is False
    assert assess_investment_income(InsuranceLine.GENERAL_LIABILITY).state_requires_explicit is False
    assert "NY" in states_requiring_explicit_investment_income()
    assert len(states_requiring_explicit_investment_income()) >= 3


def test_across_lines_covers_all() -> None:
    rows = investment_income_across_lines()
    assert {r.line for r in rows} == {line.value for line in InsuranceLine}


def test_life_line_has_no_offset() -> None:
    life = assess_investment_income(InsuranceLine.LIFE)
    assert life.tail == LossTail.NOT_APPLICABLE
    assert life.rate_offset_pct == 0.0
    assert life.investment_income_pct_of_premium == 0.0


def test_severity_escalation() -> None:
    gl_ny = assess_investment_income(InsuranceLine.GENERAL_LIABILITY, state="NY")
    assert investment_income_severity(gl_ny, state="NY") == RiskSeverity.HIGH
    gl = assess_investment_income(InsuranceLine.GENERAL_LIABILITY)
    assert investment_income_severity(gl) == RiskSeverity.MODERATE
    prop = assess_investment_income(InsuranceLine.COMMERCIAL_PROPERTY)
    assert investment_income_severity(prop) == RiskSeverity.LOW


def test_umbrella_is_longest_tail() -> None:
    umbrella = assess_investment_income(InsuranceLine.UMBRELLA)
    assert umbrella.tail == LossTail.LONG
    assert umbrella.rate_offset_pct > assess_investment_income(InsuranceLine.GENERAL_LIABILITY).rate_offset_pct
