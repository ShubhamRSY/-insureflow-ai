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
    apply_state_filing_gate,
    enforce_minimum_consideration,
    finish_quote,
    merge_state_rules,
    purchase_price,
)
from insureflow.underwriting.life_product import is_filed_annuity_product

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
    "AZ": {"spousal_consent_required": True},
    "ID": {"spousal_consent_required": True},
    "LA": {"spousal_consent_required": True},
    "NV": {"spousal_consent_required": True},
    "NM": {"spousal_consent_required": True},
    "WA": {"spousal_consent_required": True},
    "WI": {"spousal_consent_required": True},
    "CA": {"free_look_days": 30, "spousal_consent_required": True},
}

MIN_PURCHASE_PRICE = 10_000.0


def underwrite_life_annuity(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Single-Life Income Annuity")
    principal = purchase_price(ctx)
    enforce_minimum_consideration(outcome, principal, MIN_PURCHASE_PRICE)

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

    # Single-consideration product — the premium IS the purchase price.
    outcome.annual_premium = round(principal, 2)
    outcome.base_premium = round(principal, 2)

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

    filed = is_filed_annuity_product(PRODUCT_ID)
    apply_state_filing_gate(ctx, outcome, filed_for_state=filed, product_family="life_annuity")
    if filed:
        annuity_raw = (ctx.manual or {}).get("annuity_filing")
        annuity = annuity_raw if isinstance(annuity_raw, dict) else {}
        outcome.metadata["filed_annuity"] = True
        if annuity.get("filing_id"):
            outcome.metadata["filing_id"] = annuity["filing_id"]
        if annuity.get("serff_tracking"):
            outcome.metadata["serff_tracking"] = annuity["serff_tracking"]
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_life_annuity(ctx)
    filed = is_filed_annuity_product(PRODUCT_ID)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="life_filing" if filed else "annuity_illustration",
        apply_minimum_premium=False,
    )
