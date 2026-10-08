"""Qualified Longevity Annuity Contract (QLAC) — dedicated logic path (LOB 7).

Coverages: QLAC Deferred, QLAC Lifetime. A deferred-income annuity bought
inside a qualified plan with an IRS premium cap; the premium is EXCLUDED from
required minimum distribution (RMD) calculations until income starts.
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
)
from insureflow.life.mortality import discount_factor, k_p_x
from insureflow.underwriting.life_product import is_filed_annuity_product

PRODUCT_ID = "qlac"
LOGIC_PATH = "insureflow.life.lobs.annuity.qlac"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "min_issue_age": 50,
    # Same ceiling as the filed manual (eligibility.max_age). 76–80 never
    # cleared the shared medical gate, so a higher number here was a dead range.
    "max_issue_age": 75,
    "irs_premium_cap": 210_000.0,  # 2025 IRS limit per person — carrier/pilot configurable
    "max_income_start_age": 85,
    "disclosures": [
        "QLAC premiums are excluded from RMD calculations until income begins",
        "Exceeding the IRS cap disqualifies the excess from QLAC treatment",
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


def _stated_consideration(ctx: LifeProductContext) -> float | None:
    """Purchase price the submission actually states. No $500,000 stand-in."""
    import re

    from insureflow.underwriting.personal_lines import _blob

    if ctx.face > 0:
        return float(ctx.face)
    match = re.search(
        r"(?:principal|consideration|purchase price|premium)\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d+)?)",
        _blob(ctx.bundle),
        re.I,
    )
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def underwrite_qlac(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="QLAC — Deferred Lifetime Income")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.age < int(state_rules["min_issue_age"]) or ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"QLAC issue age {ctx.age} outside {state_rules['min_issue_age']}-{state_rules['max_issue_age']}")

    stated = _stated_consideration(ctx)
    if stated is None:
        principal_raw = 0.0
        outcome.eligible = False
        outcome.add_reason("QLAC consideration is not on the submission")
    else:
        principal_raw = stated
    enforce_minimum_consideration(outcome, principal_raw, MIN_PURCHASE_PRICE)
    cap = float(state_rules["irs_premium_cap"])
    capped = principal_raw > cap
    principal = min(principal_raw, cap)
    if capped:
        outcome.eligible = False
        outcome.add_reason(f"Purchase price ${principal_raw:,.0f} exceeds the IRS QLAC cap ${cap:,.0f} — priced at cap, excess needs separate treatment")
        outcome.add_condition("EXCESS OVER IRS CAP must be reclassified or returned — QLAC status lost otherwise")

    # Income starts at 75, or at the attained age when the buyer is already older.
    start_age = int(state_rules["max_income_start_age"]) - 10
    if ctx.age > start_age:
        start_age = ctx.age
    outcome.add_condition(f"Income must start by age {int(state_rules['max_income_start_age'])}")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    interest = 0.04
    years = max(start_age - ctx.age, 0)
    a_due = whole_life_annuity_due_factor(start_age, ctx.sex_key, ctx.smoker, interest)
    # Premium is paid now. Income is principal ÷ (v^n · npx · ä at the start age).
    survive = k_p_x(ctx.age, years, ctx.sex_key, ctx.smoker) if years else 1.0
    factor = (discount_factor(interest) ** years) * survive * a_due
    annual_payout = round(principal / factor, 2) if factor > 0 else 0.0

    # Single-consideration product — the premium IS the purchase price (capped).
    outcome.annual_premium = round(principal, 2)
    outcome.base_premium = round(principal, 2)

    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "QLAC deferred to income-start age",
                "interest_rate": interest,
                "annuity_factor_at_start": round(a_due, 4),
                "deferred_annuity_factor": round(factor, 6),
            },
            # QLACs are, by IRS definition, funded with qualified (IRA/plan)
            # money — this must be True so the platform-level premium-tax
            # disclosure (base.py::apply_platform_state_law) uses each
            # state's qualified_money_rate instead of the higher retail rate.
            "qualified_money": True,
            "purchase_price": round(principal, 2),
            "purchase_price_uncapped": round(principal_raw, 2),
            "irs_cap": cap,
            "capped_at_irs_limit": capped or None,
            "income_start_age": start_age,
            "years_of_deferral": years,
            "annual_payout_at_start": annual_payout,
            "monthly_payout_at_start": round(annual_payout / 12.0, 2),
            "payout_form": "lifetime",
            "rmd_excluded_until_income_starts": True,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    filed = is_filed_annuity_product(PRODUCT_ID)
    apply_state_filing_gate(ctx, outcome, filed_for_state=filed, product_family="qlac")
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
    outcome = underwrite_qlac(ctx)
    filed = is_filed_annuity_product(PRODUCT_ID)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="life_filing" if filed else "annuity_illustration",
        apply_minimum_premium=False,
    )
