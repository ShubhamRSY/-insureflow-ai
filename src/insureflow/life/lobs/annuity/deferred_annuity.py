"""Deferred Annuity — dedicated logic path (LOB 7).

Coverages: Deferred Accumulation, Deferred Income. Contributions accumulate at
a credited rate to a vesting age, then the corpus converts into lifetime
income priced at the OLDER attained age.
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

PRODUCT_ID = "deferred_annuity"
LOGIC_PATH = "insureflow.life.lobs.annuity.deferred_annuity"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "min_issue_age": 30,
    "max_issue_age": 70,
    "default_vesting_age": 65,
    "credited_rate": 0.042,
    "disclosures": [
        "Earnings tax-deferred until withdrawal — ordinary income treatment applies",
        "Withdrawals before 59½ may incur a 10% penalty tax (pre-59½ disclosure)",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "AZ": {"spousal_consent_required": True},
    "ID": {"spousal_consent_required": True},
    "LA": {"spousal_consent_required": True},
    "NV": {"spousal_consent_required": True},
    "NM": {"spousal_consent_required": True},
    "WA": {"spousal_consent_required": True},
    "WI": {"spousal_consent_required": True},
}

MIN_PURCHASE_PRICE = 5_000.0


def underwrite_deferred_annuity(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Deferred Annuity")
    principal = purchase_price(ctx)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.age < int(state_rules["min_issue_age"]) or ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"Deferred annuity issue age {ctx.age} outside {state_rules['min_issue_age']}-{state_rules['max_issue_age']}")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    r = float(state_rules["credited_rate"])
    vesting_age = int(state_rules["default_vesting_age"])
    years = max(vesting_age - ctx.age, 1)
    fund_at_vesting = round(principal * ((1.0 + r) ** years), 2)
    income_factor = whole_life_annuity_due_factor(vesting_age, ctx.sex_key, ctx.smoker, 0.04)
    annual_payout = round(fund_at_vesting / income_factor, 2) if income_factor > 0 else 0.0

    show_income = ctx.coverage_id == "deferred_income"
    if not show_income:
        outcome.product_label = "Deferred Annuity — Accumulation Phase"

    schedule = {f"year_{y}": round(principal * ((1.0 + r) ** y), 2) for y in (5, 10, years)}

    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "deferred annuity — accumulate then annuitize",
                "credited_rate": r,
                "payout_basis_interest": 0.04,
            },
            "purchase_price": round(principal, 2),
            "vesting_age": vesting_age,
            "years_to_vesting": years,
            "fund_value_at_vesting": fund_at_vesting,
            "accumulation_schedule": schedule,
            "annual_payout_at_vesting": annual_payout,
            "monthly_payout_at_vesting": round(annual_payout / 12.0, 2),
            "annuitization_factor_at_vesting": round(income_factor, 4),
            "phase": "income" if show_income else "accumulation",
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
    outcome = underwrite_deferred_annuity(ctx)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="annuity_illustration",
        apply_minimum_premium=False,
    )
