"""Fixed Annuity — dedicated logic path (LOB 7).

Coverages: Fixed Income, Fixed Accumulation. The carrier declares the
crediting rate and bears ALL investment risk; a back-end surrender charge
schedule protects against arbitrage.
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

PRODUCT_ID = "fixed_annuity"
LOGIC_PATH = "insureflow.life.lobs.annuity.fixed_annuity"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "min_issue_age": 40,
    "max_issue_age": 85,
    "accumulation_rate": 0.045,  # declared first-year rate
    "renewal_rate_floor": 0.030,  # contractual minimum after initial period
    "payout_basis_interest": 0.04,
    "surrender_charge_schedule": {1: 0.09, 2: 0.08, 3: 0.07, 4: 0.06, 5: 0.05, 6: 0.04, 7: 0.03},
    "disclosures": [
        "Carrier may renew the credited rate at or above the contractual floor with notice",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "AZ": {"free_look_days": 30, "spousal_consent_required": True},
    "ID": {"free_look_days": 30, "spousal_consent_required": True},
    "LA": {"free_look_days": 30, "spousal_consent_required": True},
    "NV": {"free_look_days": 30, "spousal_consent_required": True},
    "NM": {"free_look_days": 30, "spousal_consent_required": True},
    "WA": {"free_look_days": 30, "spousal_consent_required": True},
    "WI": {"free_look_days": 30, "spousal_consent_required": True},
    "FL": {"free_look_days": 14},
    "CT": {"free_look_days": 30},
}

MIN_PURCHASE_PRICE = 5_000.0


def underwrite_fixed_annuity(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Fixed Annuity")
    principal = purchase_price(ctx)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.age < int(state_rules["min_issue_age"]) or ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"Fixed annuity issue age {ctx.age} outside {state_rules['min_issue_age']}-{state_rules['max_issue_age']}")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    r = float(state_rules["accumulation_rate"])
    vesting_age = max(ctx.age + 10, 65)
    years = max(vesting_age - ctx.age, 5)
    fund_at_vesting = round(principal * ((1.0 + r) ** years), 2)
    income_factor = whole_life_annuity_due_factor(vesting_age, ctx.sex_key, ctx.smoker, float(state_rules["payout_basis_interest"]))
    annual_payout = round(fund_at_vesting / income_factor, 2) if income_factor > 0 else 0.0

    show_income = ctx.coverage_id == "fixed_income"
    schedule = {f"surrender_charge_year_{y}": f"{int(pct * 100)}%" for y, pct in state_rules["surrender_charge_schedule"].items()}

    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "fixed declared-rate annuity",
                "accumulation_rate": r,
                "renewal_rate_floor": float(state_rules["renewal_rate_floor"]),
                "payout_basis_interest": float(state_rules["payout_basis_interest"]),
            },
            "purchase_price": round(principal, 2),
            "vesting_age": vesting_age,
            "fund_value_at_vesting": fund_at_vesting,
            "annual_payout_at_vesting": annual_payout,
            "monthly_payout_at_vesting": round(annual_payout / 12.0, 2),
            "surrender_charge_schedule": schedule,
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
    outcome = underwrite_fixed_annuity(ctx)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="annuity_illustration",
        apply_minimum_premium=False,
    )
