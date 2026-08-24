"""Indexed Annuity — dedicated logic path (LOB 7).

Coverages: Indexed Crediting, Fixed-Indexed Blend. Crediting tracks an index
through participation/cap/floor mechanics; principal is protected by the
floor (index-linked upside, never negative crediting).
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

PRODUCT_ID = "indexed_annuity"
LOGIC_PATH = "insureflow.life.lobs.annuity.indexed_annuity"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "min_issue_age": 45,
    "max_issue_age": 80,
    "participation_rate": 0.55,
    "index_cap": 0.09,
    "index_floor": 0.00,
    "fixed_rate_leg": 0.025,
    "payout_basis_interest": 0.04,
    "surrender_charge_schedule": {1: 0.10, 2: 0.09, 3: 0.08, 4: 0.07, 5: 0.06, 6: 0.05, 7: 0.04, 8: 0.03},
    "disclosures": [
        "Index crediting is capped and may change at renewal — not a direct index investment",
        "Dividends on the underlying index are NOT included in crediting",
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

MIN_PURCHASE_PRICE = 10_000.0


def _credited(gain: float, part: float, cap: float, floor: float) -> float:
    return min(max(gain * part, floor), cap)


def underwrite_indexed_annuity(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Fixed Index Annuity")
    principal = purchase_price(ctx)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.age < int(state_rules["min_issue_age"]) or ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"Indexed annuity issue age {ctx.age} outside {state_rules['min_issue_age']}-{state_rules['max_issue_age']}")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    part = float(state_rules["participation_rate"])
    cap = float(state_rules["index_cap"])
    floor = float(state_rules["index_floor"])
    scenarios = {f"index_gain_{int(g * 100)}pct": round(_credited(g, part, cap, floor), 6) for g in (-0.15, 0.05, 0.10, 0.20)}

    # Illustrative accumulation at the midpoint scenario (5% gain → credited).
    mid_credited = _credited(0.05, part, cap, floor)
    vesting_age = max(ctx.age + 10, 65)
    years = max(vesting_age - ctx.age, 5)
    fund_at_vesting = round(principal * ((1.0 + mid_credited) ** years), 2)
    income_factor = whole_life_annuity_due_factor(vesting_age, ctx.sex_key, ctx.smoker, float(state_rules["payout_basis_interest"]))
    annual_payout = round(fund_at_vesting / income_factor, 2) if income_factor > 0 else 0.0

    schedule = {f"surrender_charge_year_{y}": f"{int(pct * 100)}%" for y, pct in state_rules["surrender_charge_schedule"].items()}

    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "indexed annuity with participation/cap/floor crediting",
                "illustrative_crediting_scenario": mid_credited,
                "payout_basis_interest": float(state_rules["payout_basis_interest"]),
            },
            "purchase_price": round(principal, 2),
            "vesting_age": vesting_age,
            "fund_value_projection_midpoint": fund_at_vesting,
            "annual_payout_at_vesting": annual_payout,
            "monthly_payout_at_vesting": round(annual_payout / 12.0, 2),
            "participation_rate": part,
            "index_cap": cap,
            "index_floor": floor,
            "fixed_rate_leg": float(state_rules["fixed_rate_leg"]),
            "allocation": "fixed_indexed" if ctx.coverage_id == "fixed_indexed" else "indexed_crediting",
            "credited_rate_scenarios": scenarios,
            "surrender_charge_schedule": schedule,
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
    outcome = underwrite_indexed_annuity(ctx)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="annuity_illustration",
        apply_minimum_premium=False,
    )
