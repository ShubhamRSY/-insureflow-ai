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


def _elimination_days(blob: str) -> int:
    match = re.search(r"elimination period\s*[:=]?\s*(\d+)\s*day", blob, re.I)
    return int(match.group(1)) if match else 90


def _benefit_period(blob: str) -> str:
    if re.search(r"to age 65|to[_\s-]?65", blob, re.I):
        return "to_65"
    if re.search(r"5[\s-]?year", blob, re.I):
        return "5_year"
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
    if ctx.income and ctx.benefit_amount and (ctx.benefit_amount * 12.0) > ctx.income * MAX_INCOME_REPLACEMENT_PCT:
        outcome.add_condition(f"Monthly benefit annualized exceeds the {MAX_INCOME_REPLACEMENT_PCT:.0%} income-replacement ceiling most LTD filings enforce")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    occ_class = _occupation_class(ctx.blob) or "II"
    elimination_days = _elimination_days(ctx.blob)
    benefit_period = _benefit_period(ctx.blob)

    disability_manual = (ctx.manual or {}).get("disability") or {}
    rate_per_100 = float(disability_manual.get("ltd_base_rate_per_100_monthly_benefit", 2.35))
    occ_f = float((disability_manual.get("occupation_class_factors") or {}).get(occ_class, 1.0))
    elim_f = float((disability_manual.get("elimination_period_factors") or {}).get(str(elimination_days), 1.0))
    period_f = float((disability_manual.get("benefit_period_factors") or {}).get(benefit_period, 1.0))
    area_f = area_relativity(ctx)

    base_premium = (ctx.benefit_amount / 100.0) * rate_per_100 * 12.0
    annual = round(base_premium * occ_f * elim_f * period_f * area_f + policy_fee(ctx), 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="ltd_rate_per_100_monthly", amount=rate_per_100, basis="monthly benefit"),
        RateComponent(name="occupation_class", amount=occ_f, basis=f"Class {occ_class}"),
        RateComponent(name="elimination_period", amount=elim_f, basis=f"{elimination_days} days"),
        RateComponent(name="benefit_period", amount=period_f, basis=benefit_period),
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
