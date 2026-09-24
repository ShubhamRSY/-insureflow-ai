"""Long-Term Disability Income — dedicated logic path.

Monthly benefit, longer elimination period, benefit period runs to a fixed
term or to age 65. Real individual LTD underwriting requires income proof
to size the benefit (issue-and-participation limits are set as a percentage
of income, same principle life's own financial-underwriting income-multiple
check uses) — reused here via the existing disability_income handler, which
already gates on income proof.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.health.lobs.base import (
    HealthProductContext,
    LobOutcome,
    age_band_factor,
    apply_state_filing_gate,
    area_relativity,
    finish_quote,
    merge_state_rules,
    policy_fee,
)
from insureflow.rating.models import RateComponent

# Internal reuse — same occupation-class classifier used across PA/disability.
from insureflow.underwriting.health_uw import _occupation_class

PRODUCT_ID = "long_term_disability"
LOGIC_PATH = "insureflow.health.lobs.disability.long_term_disability"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Benefit is capped as a percentage of pre-disability income, not the full amount requested"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 60  # most LTD filings stop new issue near/at the benefit-to-65 ceiling
MAX_INCOME_REPLACEMENT_PCT = 0.60
MAX_MONTHLY_BENEFIT = 20_000.0  # ponytail: assumed typical carrier issue limit, not from the filed manual; move to manual when filed


def _elimination_days(blob: str) -> int | None:
    """Stated elimination period in days, or None when the submission states none."""
    match = re.search(r"elimination period\s*[:=]?\s*(\d+)\s*-?\s*day|(?<![\d-])(\d+)\s*-?\s*day\s+elimination", blob, re.I)
    return int(match.group(1) or match.group(2)) if match else None


def _priced_elimination_days(days: int, listed: list[int]) -> int:
    """Nearest LISTED period at or below the stated one (shorter elimination = higher premium, so never cheaper than asked)."""
    at_or_below = [d for d in listed if d <= days]
    return max(at_or_below) if at_or_below else min(listed)


def _benefit_period(blob: str) -> str:
    if re.search(r"to age (?:6\d|7\d)|to[_\s-]?(?:6\d|7\d)\b|lifetime|life[_\s-]?long|for life", blob, re.I):
        return "to_65"
    # Only a stated benefit period counts — never an unrelated "45-year-old".
    m = re.search(r"benefit period\s*[:=]?\s*(?:of\s*)?(\d+)\s*-?\s*years?|(?<![\d-])(\d+)\s*-?\s*years?\s+benefit period", blob, re.I)
    if m:
        years = int(m.group(1) or m.group(2))
        return "to_65" if years >= 10 else ("5_year" if years > 2 else "2_year")
    return "2_year"


def underwrite_ltd(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="disability_income")

    outcome = LobOutcome(product_label="Long-Term Disability Income")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Long-term disability issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Monthly benefit amount missing — cannot rate long-term disability without a coverage amount")
    if ctx.benefit_amount > MAX_MONTHLY_BENEFIT:
        outcome.add_condition(f"Monthly benefit ${ctx.benefit_amount:,.0f} exceeds the ${MAX_MONTHLY_BENEFIT:,.0f} maximum issue limit — refer for underwriter approval")
        outcome.metadata.setdefault("_outcome", "refer")
    if ctx.income and ctx.benefit_amount and (ctx.benefit_amount * 12.0) > ctx.income * MAX_INCOME_REPLACEMENT_PCT:
        outcome.add_condition(f"Monthly benefit annualized exceeds the {MAX_INCOME_REPLACEMENT_PCT:.0%} income-replacement ceiling most LTD filings enforce")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    occ_class = _occupation_class(ctx.blob) or "II"
    stated_days = _elimination_days(ctx.blob)
    elimination_days = 90 if stated_days is None else stated_days
    benefit_period = _benefit_period(ctx.blob)
    if stated_days is None:
        outcome.add_condition("Elimination period not stated — priced at the 90-day default; confirm before bind")
    if not re.search(r"benefit period|to age (?:6\d|7\d)|to[_\s-]?(?:6\d|7\d)\b|lifetime|life[_\s-]?long|for life", ctx.blob, re.I):
        outcome.add_condition("Benefit period not stated — priced at the 2-year default; confirm before bind")

    disability_manual = (ctx.manual or {}).get("disability") or {}
    rate_per_100 = float(disability_manual.get("ltd_base_rate_per_100_monthly_benefit", 2.35))
    occ_f = float((disability_manual.get("occupation_class_factors") or {}).get(occ_class, 1.0))
    elim_table = disability_manual.get("elimination_period_factors") or {}
    priced_days = _priced_elimination_days(elimination_days, sorted(int(k) for k in elim_table)) if elim_table else elimination_days
    elim_f = float(elim_table.get(str(priced_days), 1.0))
    if priced_days != elimination_days:
        outcome.add_condition(f"{elimination_days}-day elimination period is not a filed option — priced at the {priced_days}-day factor")
    period_f = float((disability_manual.get("benefit_period_factors") or {}).get(benefit_period, 1.0))
    area_f = area_relativity(ctx)
    age_f = age_band_factor(ctx, "age_factors", section="disability")

    base_premium = (ctx.benefit_amount / 100.0) * rate_per_100 * 12.0
    annual = round(base_premium * occ_f * elim_f * period_f * area_f * age_f + policy_fee(ctx), 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="ltd_rate_per_100_monthly", amount=rate_per_100, basis="monthly benefit"),
        RateComponent(name="occupation_class", amount=occ_f, basis=f"Class {occ_class}"),
        RateComponent(name="elimination_period", amount=elim_f, basis=f"{elimination_days} days"),
        RateComponent(name="benefit_period", amount=period_f, basis=benefit_period),
        RateComponent(name="attained_age", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "monthly_benefit": ctx.benefit_amount,
            "occupation_class": occ_class,
            "elimination_period_days": elimination_days,
            "benefit_period": benefit_period,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="long_term_disability")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_ltd(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="disability")
