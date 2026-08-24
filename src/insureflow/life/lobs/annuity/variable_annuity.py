"""Variable Annuity — dedicated logic path (LOB 7).

Coverages: Separate-Account Annuity, GMWB Rider. Units invest in
SEC-registered subaccounts; investment risk is entirely on the owner. The
GMWB rider guarantees a WITHDRAWAL base for an explicit annual fee.
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

PRODUCT_ID = "variable_annuity"
LOGIC_PATH = "insureflow.life.lobs.annuity.variable_annuity"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "min_issue_age": 40,
    "max_issue_age": 80,
    "assumed_air": 0.06,  # assumed investment return — illustration only
    "gmwb_rider_fee_pct": 0.0115,  # of withdrawal benefit base, per year
    "gmwb_withdrawal_pct": 0.05,  # of base per year once activated
    "disclosures": [
        "SEC prospectus required — subaccount value fluctuates and may lose value",
        "Rider fees reduce account value even when the guarantee is unused",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
}

MIN_PURCHASE_PRICE = 25_000.0


def underwrite_variable_annuity(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Variable Annuity")
    principal = purchase_price(ctx)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.age < int(state_rules["min_issue_age"]) or ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"Variable annuity issue age {ctx.age} outside {state_rules['min_issue_age']}-{state_rules['max_issue_age']}")

    gmwb = ctx.coverage_id == "var_gmwb"
    if gmwb:
        outcome.product_label = "Variable Annuity with GMWB Rider"
        outcome.add_condition(f"GMWB: guaranteed withdrawals of {float(state_rules['gmwb_withdrawal_pct']) * 100:.0f}% of benefit base per year, for life once exhausted")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    air = float(state_rules["assumed_air"])
    vesting_age = max(ctx.age + 10, 65)
    years = max(vesting_age - ctx.age, 5)
    fund_at_vesting = round(principal * ((1.0 + air) ** years), 2)
    if gmwb:
        fee_years = min(years, 20)
        fund_at_vesting = round(fund_at_vesting * ((1.0 - float(state_rules["gmwb_rider_fee_pct"])) ** fee_years), 2)
    income_factor = whole_life_annuity_due_factor(vesting_age, ctx.sex_key, ctx.smoker, 0.04)
    annual_payout = round(fund_at_vesting / income_factor, 2) if income_factor > 0 else 0.0

    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "variable annuity at ASSUMED AIR (not guaranteed)",
                "assumed_air": air,
            },
            "purchase_price": round(principal, 2),
            "vesting_age": vesting_age,
            "fund_value_projection_air_basis": fund_at_vesting,
            "annual_payout_at_vesting": annual_payout,
            "monthly_payout_at_vesting": round(annual_payout / 12.0, 2),
            "gmwb_rider": gmwb,
            "gmwb_rider_fee_pct": float(state_rules["gmwb_rider_fee_pct"]) if gmwb else None,
            "withdrawal_base_if_gmwb": round(principal, 2) if gmwb else None,
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
    outcome = underwrite_variable_annuity(ctx)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="annuity_illustration",
        apply_minimum_premium=False,
    )
