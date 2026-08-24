"""Life Annuity — dedicated logic path (LOB 7).

Coverages: Single-Life Income, Life with Cash Refund. Plain life income pays
until death (highest payout); the refund form guarantees the principal is
returned to beneficiaries and prices that guarantee as an explicit load.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.actuarial import whole_life_annuity_due_factor
from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    finish_quote,
    merge_state_rules,
    purchase_price,
)

PRODUCT_ID = "life_annuity"
LOGIC_PATH = "insureflow.life.lobs.annuity.life_annuity"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "min_issue_age": 50,
    "max_issue_age": 90,
    "refund_guarantee_load": 1.03,  # refund form costs ≈3% of income
    "spousal_consent_required": False,
    "disclosures": [
        "Single-life payments STOP at death — no value passes to heirs",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "CT": {"free_look_days": 30},
    "CA": {"free_look_days": 30, "spousal_consent_required": True},
}

MIN_PURCHASE_PRICE = 10_000.0


def underwrite_life_annuity(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Single-Life Income Annuity")
    principal = purchase_price(ctx)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.age < int(state_rules["min_issue_age"]) or ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"Life annuity issue age {ctx.age} outside {state_rules['min_issue_age']}-{state_rules['max_issue_age']}")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    if state_rules["spousal_consent_required"]:
        outcome.add_condition("SPOUSAL CONSENT required to waive survivor benefits (community-property state)")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    interest = 0.04
    factor = whole_life_annuity_due_factor(ctx.age, ctx.sex_key, ctx.smoker, interest)
    plain_payout = round(principal / factor, 2) if factor > 0 else 0.0

    refund = ctx.coverage_id == "life_refund"
    if refund:
        outcome.product_label = "Life Annuity with Cash Refund"
        annual_payout = round(plain_payout / float(state_rules["refund_guarantee_load"]), 2)
        outcome.add_condition("Cash refund: if death occurs before payouts equal principal, the shortfall is paid to beneficiaries")
    else:
        annual_payout = plain_payout

    breakeven_years = round(principal / annual_payout, 1) if annual_payout else None

    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "life annuity due" + (" + cash-refund load" if refund else ""),
                "interest_rate": interest,
                "annuity_factor": round(factor, 4),
                "refund_guarantee_load": float(state_rules["refund_guarantee_load"]) if refund else None,
            },
            "purchase_price": round(principal, 2),
            "annual_payout": annual_payout,
            "monthly_payout": round(annual_payout / 12.0, 2),
            "payout_form": "life with cash refund" if refund else "single life",
            "breakeven_years": breakeven_years,
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
    outcome = underwrite_life_annuity(ctx)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="annuity_illustration",
        apply_minimum_premium=False,
    )
