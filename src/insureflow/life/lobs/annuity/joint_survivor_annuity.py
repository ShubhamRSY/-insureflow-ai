"""Joint Life / Survivor Annuity — dedicated logic path (LOB 7).

Coverages: 100% Continuation, 50% Continuation. Income continues to the
surviving spouse at the elected share; the richer the continuation, the lower
the starting payout (priced on joint survival, not a flat discount).
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.actuarial import joint_and_survivor_annuity_factor, whole_life_annuity_due_factor
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

PRODUCT_ID = "joint_survivor_annuity"
LOGIC_PATH = "insureflow.life.lobs.annuity.joint_survivor_annuity"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "min_issue_age": 50,
    "max_issue_age": 85,
    "spouse_age_offset": -3,  # explicit assumption when spouse age unstated
    "spouse_sex_assumption": "female",
    "spousal_consent_required": False,
    "disclosures": [
        "Spouse age/sex defaults are used when not documented — verified at issue",
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
    "CA": {"spousal_consent_required": True},
    "TX": {"spousal_consent_required": True},
}

MIN_PURCHASE_PRICE = 10_000.0


def underwrite_joint_annuity(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Joint & Survivor Annuity")
    principal = purchase_price(ctx)
    enforce_minimum_consideration(outcome, principal, MIN_PURCHASE_PRICE)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.age < int(state_rules["min_issue_age"]) or ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"Joint annuity issue age {ctx.age} outside {state_rules['min_issue_age']}-{state_rules['max_issue_age']}")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    if state_rules["spousal_consent_required"]:
        outcome.add_condition("SPOUSAL CONSENT required for survivor-election changes (community-property state)")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    survivor_pct = 1.0 if ctx.coverage_id == "joint_100" else 0.5
    spouse_age_from_submission = getattr(ctx.factors, "spouse_age", None)
    if spouse_age_from_submission is not None:
        spouse_age: int = int(spouse_age_from_submission)
    else:
        spouse_age = ctx.age + int(state_rules["spouse_age_offset"])
    spouse_age_known = spouse_age_from_submission is not None
    spouse_sex_from_submission = getattr(ctx.factors, "spouse_sex", "") or ""
    spouse_sex_known = spouse_sex_from_submission in ("male", "female")
    spouse_sex = spouse_sex_from_submission if spouse_sex_known else str(state_rules["spouse_sex_assumption"])
    if spouse_age_known:
        outcome.add_condition(f"Spouse's age ({spouse_age}) taken from submission — confirm before bind")
    if spouse_sex_known:
        outcome.add_condition(f"Spouse's sex ({spouse_sex}) taken from submission — confirm before bind")
    interest = 0.04
    factor = joint_and_survivor_annuity_factor(
        ctx.age,
        max(spouse_age, 30),
        survivor_pct,
        sex_primary=ctx.sex_key,
        sex_spouse=spouse_sex,
        smoker=ctx.smoker,
        interest_rate=interest,
    )
    single_factor = whole_life_annuity_due_factor(ctx.age, ctx.sex_key, ctx.smoker, interest)
    annual_payout = round(principal / factor, 2) if factor > 0 else 0.0
    single_payout = round(principal / single_factor, 2) if single_factor > 0 else 0.0

    # Single-consideration product — the premium IS the purchase price.
    outcome.annual_premium = round(principal, 2)
    outcome.base_premium = round(principal, 2)

    outcome.product_label = f"J&S {int(survivor_pct * 100)}% Continuation Annuity"
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": f"joint & survivor ({int(survivor_pct * 100)}% continuation) on joint survival",
                "interest_rate": interest,
                "joint_factor": round(factor, 4),
                "single_life_factor": round(single_factor, 4),
            },
            "purchase_price": round(principal, 2),
            "annual_payout": annual_payout,
            "monthly_payout": round(annual_payout / 12.0, 2),
            "single_life_payout_comparison": single_payout,
            "continuation_pct": survivor_pct,
            "assumed_spouse_age": max(spouse_age, 30),
            "assumed_spouse_sex": spouse_sex,
            "spouse_age_source": "submission" if spouse_age_known else "assumed_default",
            "spouse_sex_source": "submission" if spouse_sex_known else "assumed_default",
            "payout_reduction_vs_single_pct": round(1.0 - annual_payout / single_payout, 4) if single_payout else None,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    if outcome.metadata.get("spouse_age_source") != "submission" or outcome.metadata.get("spouse_sex_source") != "submission":
        outcome.eligible = False
        outcome.add_reason("Joint annuitant age and sex are not on the submission — payout is not issueable on an assumed spouse")

    filed = is_filed_annuity_product(PRODUCT_ID)
    apply_state_filing_gate(ctx, outcome, filed_for_state=filed, product_family="joint_survivor_annuity")
    if filed and outcome.eligible:
        annuity_raw = (ctx.manual or {}).get("annuity_filing")
        annuity = annuity_raw if isinstance(annuity_raw, dict) else {}
        outcome.metadata["filed_annuity"] = True
        if annuity.get("filing_id"):
            outcome.metadata["filing_id"] = annuity["filing_id"]
        if annuity.get("serff_tracking"):
            outcome.metadata["serff_tracking"] = annuity["serff_tracking"]
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_joint_annuity(ctx)
    filed = is_filed_annuity_product(PRODUCT_ID)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="life_filing" if filed else "annuity_illustration",
        apply_minimum_premium=False,
    )
