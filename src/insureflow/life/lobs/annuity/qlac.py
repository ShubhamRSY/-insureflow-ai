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
    finish_quote,
    merge_state_rules,
    purchase_price,
)

PRODUCT_ID = "qlac"
LOGIC_PATH = "insureflow.life.lobs.annuity.qlac"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "min_issue_age": 50,
    "max_issue_age": 80,
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


def underwrite_qlac(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="QLAC — Deferred Lifetime Income")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.age < int(state_rules["min_issue_age"]) or ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"QLAC issue age {ctx.age} outside {state_rules['min_issue_age']}-{state_rules['max_issue_age']}")

    principal_raw = purchase_price(ctx)
    cap = float(state_rules["irs_premium_cap"])
    capped = principal_raw > cap
    principal = min(principal_raw, cap)
    if capped:
        outcome.add_reason(f"Purchase price ${principal_raw:,.0f} exceeds the IRS QLAC cap ${cap:,.0f} — priced at cap, excess needs separate treatment")
        outcome.add_condition("EXCESS OVER IRS CAP must be reclassified or returned — QLAC status lost otherwise")

    start_age = int(state_rules["max_income_start_age"]) - 10
    outcome.add_condition(f"Income must start by age {int(state_rules['max_income_start_age'])}")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    interest = 0.04
    factor = whole_life_annuity_due_factor(start_age, ctx.sex_key, ctx.smoker, interest)
    annual_payout = round(principal / factor, 2) if factor > 0 else 0.0

    lifetime_form = ctx.coverage_id == "qlac_lifetime"

    # Single-consideration product — the premium IS the purchase price (capped).
    outcome.annual_premium = round(principal, 2)
    outcome.base_premium = round(principal, 2)

    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "QLAC deferred to income-start age",
                "interest_rate": interest,
                "annuity_factor_at_start": round(factor, 4),
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
            "years_of_deferral": max(start_age - ctx.age, 1),
            "annual_payout_at_start": annual_payout,
            "monthly_payout_at_start": round(annual_payout / 12.0, 2),
            "payout_form": "lifetime" if lifetime_form else "deferred period certain",
            "rmd_excluded_until_income_starts": True,
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
    outcome = underwrite_qlac(ctx)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="annuity_illustration",
        apply_minimum_premium=False,
    )
