"""Deferred Annuity — dedicated logic path (LOB 7).

Coverages: Deferred Accumulation, Deferred Income. Contributions accumulate at
a credited rate to a vesting age, then the corpus converts into lifetime
income priced at the OLDER attained age.
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
from insureflow.life.mortality import discount_factor, k_p_x
from insureflow.underwriting.life_product import is_filed_annuity_product

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
    stated = _stated_consideration(ctx)
    if stated is None:
        principal = 0.0
        outcome.eligible = False
        outcome.add_reason("Deferred annuity consideration is not on the submission")
    else:
        principal = stated
    enforce_minimum_consideration(outcome, principal, MIN_PURCHASE_PRICE)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.age < int(state_rules["min_issue_age"]) or ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"Deferred annuity issue age {ctx.age} outside {state_rules['min_issue_age']}-{state_rules['max_issue_age']}")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    r = float(state_rules["credited_rate"])
    vesting_age = int(state_rules["default_vesting_age"])
    if ctx.age > vesting_age:
        vesting_age = ctx.age
    years = max(vesting_age - ctx.age, 0)
    fund_at_vesting = round(principal * ((1.0 + r) ** years), 2)
    interest = 0.04
    income_factor = whole_life_annuity_due_factor(vesting_age, ctx.sex_key, ctx.smoker, interest)
    survive = k_p_x(ctx.age, years, ctx.sex_key, ctx.smoker) if years else 1.0
    deferred_factor = (discount_factor(interest) ** years) * survive * income_factor
    guaranteed_payout = round(principal / deferred_factor, 2) if deferred_factor > 0 else 0.0
    illustrated_payout = round(fund_at_vesting / income_factor, 2) if income_factor > 0 else 0.0

    show_income = ctx.coverage_id == "deferred_income"
    annual_payout = guaranteed_payout if show_income else illustrated_payout
    if not show_income:
        outcome.product_label = "Deferred Annuity — Accumulation Phase"

    schedule = {f"year_{y}": round(principal * ((1.0 + r) ** y), 2) for y in (5, 10, years)}

    # Single-consideration product — the premium IS the purchase price.
    outcome.annual_premium = round(principal, 2)
    outcome.base_premium = round(principal, 2)

    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "deferred annuity — accumulate then annuitize",
                "credited_rate": r,
                "payout_basis_interest": interest,
                "deferred_annuity_factor": round(deferred_factor, 6),
            },
            "purchase_price": round(principal, 2),
            "vesting_age": vesting_age,
            "years_to_vesting": years,
            "fund_value_at_vesting": fund_at_vesting,
            "accumulation_schedule": schedule,
            "annual_payout_at_vesting": annual_payout,
            "illustrated_payout_at_vesting": illustrated_payout,
            "monthly_payout_at_vesting": round(annual_payout / 12.0, 2),
            "annuitization_factor_at_vesting": round(income_factor, 4),
            "phase": "income" if show_income else "accumulation",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    if not show_income:
        outcome.eligible = False
        outcome.add_reason("Deferred annuity accumulation uses an assumed credited rate — the fund value is illustrated, not a guaranteed payout")

    filed = is_filed_annuity_product(PRODUCT_ID)
    apply_state_filing_gate(ctx, outcome, filed_for_state=filed, product_family="deferred_annuity")
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
    outcome = underwrite_deferred_annuity(ctx)
    filed = is_filed_annuity_product(PRODUCT_ID)
    income = outcome.metadata.get("phase") == "income"
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="life_filing" if filed and income else "annuity_illustration",
        apply_minimum_premium=False,
    )
