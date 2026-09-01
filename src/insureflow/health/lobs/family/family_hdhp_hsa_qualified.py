"""Family HSA-Qualified HDHP — dedicated logic path.

Same guaranteed-issue posture as the base Family Health Plan; the
distinguishing feature is the same one HDHP has over the base Individual
plan — a family-tier IRS minimum deductible for HSA eligibility, roughly
double the self-only floor, since it is a shared family deductible rather
than a per-member one.
"""

from __future__ import annotations

from typing import Any

from insureflow.health.lobs.base import (
    HealthProductContext,
    LobOutcome,
    age_band_factor,
    apply_state_filing_gate,
    area_relativity,
    finish_quote,
    household_tier_factor,
    merge_state_rules,
    nearest_banded_key,
    policy_fee,
    reconcile_for_aca_guaranteed_issue,
    tobacco_surcharge,
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "family_hdhp_hsa_qualified"
LOGIC_PATH = "insureflow.health.lobs.family.family_hdhp_hsa_qualified"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": [
        "Aggregate family deductible — one shared deductible for all covered members, not per-member",
        "HSA contribution eligibility requires no other disqualifying coverage — confirm with a tax advisor",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "NY": {"free_look_days": 30},
    "CA": {"free_look_days": 30},
}

MIN_ISSUE_AGE = 0
MAX_ISSUE_AGE = 64
MIN_HOUSEHOLD_MEMBERS = 2
MIN_HDHP_DEDUCTIBLE_FAMILY = 3300.0
MAX_HDHP_OUT_OF_POCKET_FAMILY = 16600.0


def underwrite_family_hdhp(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="family_floater_standard")
    reconcile_for_aca_guaranteed_issue(ctx.uw)

    outcome = LobOutcome(product_label="Family HSA-Qualified HDHP")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Primary applicant age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE} (65+ is Medicare-eligible)")
    if ctx.household_members < MIN_HOUSEHOLD_MEMBERS:
        outcome.add_condition(f"Only {ctx.household_members} covered member(s) documented — confirm this is a family enrollment, not individual")

    deductible = ctx.benefit_amount or MIN_HDHP_DEDUCTIBLE_FAMILY
    hsa_qualified = MIN_HDHP_DEDUCTIBLE_FAMILY <= deductible <= MAX_HDHP_OUT_OF_POCKET_FAMILY
    if deductible < MIN_HDHP_DEDUCTIBLE_FAMILY:
        outcome.add_condition(
            f"Chosen family deductible ${deductible:,.0f} is below the IRS HSA-qualifying minimum of ${MIN_HDHP_DEDUCTIBLE_FAMILY:,.0f} — plan can issue but will NOT be HSA-eligible"
        )

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    for mandate in state_rules.get("mandated_benefits") or []:
        outcome.add_condition(f"State-mandated benefit: {mandate}")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    bronze_f = float((manual.get("metal_tier_av_factors") or {}).get("bronze", 0.82))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    tier_size_f = household_tier_factor(ctx)
    credit_table = manual.get("hdhp_deductible_credit_factors") or {}
    credit_f = float(credit_table.get(nearest_banded_key(credit_table, deductible / 2.0), 1.0)) if credit_table else 1.0

    monthly = silver_base * bronze_f * age_f * tobacco_f * area_f * tier_size_f * credit_f
    annual = round(monthly * 12.0 + policy_fee(ctx), 2)

    outcome.base_premium = round(silver_base * bronze_f * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="primary_applicant_age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="household_composite_tier", amount=tier_size_f, basis=f"members={ctx.household_members}"),
        RateComponent(name="deductible_credit", amount=credit_f, basis=f"family deductible=${deductible:,.0f}"),
    ]
    outcome.metadata.update(
        {
            "household_members": ctx.household_members,
            "chosen_deductible": deductible,
            "hsa_qualified": hsa_qualified,
            "monthly_premium": round(monthly, 2),
            "deductible_basis": "aggregate_family",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="family_hdhp_hsa_qualified")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_family_hdhp(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="family")
