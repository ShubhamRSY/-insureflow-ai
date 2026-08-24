"""Immediate Annuity — dedicated logic path (LOB 7).

Coverages: Life Income, Period-Certain & Life. A single consideration buys a
payout starting within 12 months; income = principal ÷ annuity factor from
the mortality table. Longevity risk sits with the carrier.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.actuarial import certain_and_life_annuity_due, whole_life_annuity_due_factor
from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    finish_quote,
    merge_state_rules,
    purchase_price,
)

PRODUCT_ID = "immediate_annuity"
LOGIC_PATH = "insureflow.life.lobs.annuity.immediate_annuity"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "min_issue_age": 45,
    "max_issue_age": 85,
    "spousal_consent_required": False,
    "disclosures": [
        "Irrevocable once the free-look period ends — payments cannot be commuted",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
    "CA": {"free_look_days": 30, "spousal_consent_required": True},
    "TX": {"spousal_consent_required": True},
}

MIN_PURCHASE_PRICE = 10_000.0


def underwrite_immediate_annuity(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Immediate Annuity")
    principal = purchase_price(ctx)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.age < int(state_rules["min_issue_age"]) or ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"Immediate annuity issue age {ctx.age} outside {state_rules['min_issue_age']}-{state_rules['max_issue_age']}")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    if state_rules["spousal_consent_required"]:
        outcome.add_condition("SPOUSAL CONSENT required on beneficiary elections (community-property state)")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    interest = 0.04  # payout basis rate (carrier-configurable)
    period_certain = ctx.coverage_id == "period_certain"
    if period_certain:
        outcome.product_label = "10-Year Certain & Life Annuity"
        factor = certain_and_life_annuity_due(ctx.age, 10, ctx.sex_key, ctx.smoker, interest)
    else:
        factor = whole_life_annuity_due_factor(ctx.age, ctx.sex_key, ctx.smoker, interest)

    annual_payout = round(principal / factor, 2) if factor > 0 else 0.0

    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "immediate life annuity due",
                "interest_rate": interest,
                "annuity_factor": round(factor, 4),
            },
            "purchase_price": round(principal, 2),
            "annual_payout": annual_payout,
            "monthly_payout": round(annual_payout / 12.0, 2),
            "payout_form": "10-year certain & life" if period_certain else "single life",
            "longevity_risk": "on carrier",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason("annuity illustration only — requires a payout / consideration filing to issue")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_immediate_annuity(ctx)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="annuity_illustration",
        apply_minimum_premium=False,
    )
