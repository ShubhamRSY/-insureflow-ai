"""Variable Annuity — dedicated logic path (LOB 7).

Coverages: Separate-Account Annuity, GMWB Rider. Units invest in
SEC-registered subaccounts; investment risk is entirely on the owner. The
GMWB rider guarantees a WITHDRAWAL base for an explicit annual fee.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.actuarial import whole_life_annuity_due_factor
from insureflow.life.lobs.annuity.qlac import _stated_consideration
from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    apply_state_filing_gate,
    enforce_minimum_consideration,
    finish_quote,
    merge_state_rules,
)
from insureflow.underwriting.life_product import is_filed_annuity_product

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
        "FINRA Reg BI: securities-suitability review by a registered representative REQUIRED — separate from and in addition to insurance Best Interest",
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

MIN_PURCHASE_PRICE = 25_000.0


def underwrite_variable_annuity(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Variable Annuity")
    stated = _stated_consideration(ctx)
    if stated is None:
        principal = 0.0
        outcome.eligible = False
        outcome.add_reason("Variable annuity consideration is not on the submission")
    else:
        principal = stated
    enforce_minimum_consideration(outcome, principal, MIN_PURCHASE_PRICE)

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
    illustrated_payout = round(fund_at_vesting / income_factor, 2) if income_factor > 0 else 0.0
    withdrawal_pct = float(state_rules["gmwb_withdrawal_pct"])
    guaranteed_withdrawal = round(principal * withdrawal_pct, 2) if gmwb else 0.0
    annual_payout = guaranteed_withdrawal if gmwb else illustrated_payout

    # Single-consideration product — the premium IS the purchase price.
    outcome.annual_premium = round(principal, 2)
    outcome.base_premium = round(principal, 2)

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
            "illustrated_payout_at_vesting": illustrated_payout,
            "monthly_payout_at_vesting": round(annual_payout / 12.0, 2),
            "guaranteed_annual_withdrawal": guaranteed_withdrawal,
            "gmwb_rider": gmwb,
            "gmwb_rider_fee_pct": float(state_rules["gmwb_rider_fee_pct"]) if gmwb else None,
            "withdrawal_base_if_gmwb": round(principal, 2) if gmwb else None,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    if not gmwb:
        outcome.eligible = False
        outcome.add_reason("Variable annuity subaccounts can lose value — the account projection is illustrated, not a guaranteed payout")

    filed = is_filed_annuity_product(PRODUCT_ID)
    apply_state_filing_gate(ctx, outcome, filed_for_state=filed, product_family="variable_annuity")
    if filed and outcome.eligible:
        raw = (ctx.manual or {}).get("annuity_filing")
        filing = raw if isinstance(raw, dict) else {}
        outcome.metadata["filed_annuity"] = True
        if filing.get("filing_id"):
            outcome.metadata["filing_id"] = filing["filing_id"]
        if filing.get("serff_tracking"):
            outcome.metadata["serff_tracking"] = filing["serff_tracking"]
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_variable_annuity(ctx)
    filed = is_filed_annuity_product(PRODUCT_ID)
    gmwb = bool(outcome.metadata.get("gmwb_rider"))
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="life_filing" if filed and gmwb else "annuity_illustration",
        apply_minimum_premium=False,
    )
