"""Family Health Plan — dedicated logic path.

A single policy covering the whole household under one aggregate family
deductible — this is simply how a standard US family major-medical plan
works (no separate "floater" mechanic to invent). Rated the same way as
Individual, with the family composite-tier factor replacing the self-only
factor, per ACA composite-tier rating rules.
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
    policy_fee,
    tobacco_surcharge,
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "family_health_plan"
LOGIC_PATH = "insureflow.health.lobs.family.family_health_plan"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": [
        "Summary of Benefits and Coverage (SBC) must be delivered before enrollment",
        "Aggregate family deductible — one shared deductible for all covered members, not per-member",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "NY": {"free_look_days": 30},
    "CA": {"free_look_days": 30},
}

MIN_ISSUE_AGE = 0
MAX_ISSUE_AGE = 64
MIN_HOUSEHOLD_MEMBERS = 2


def underwrite_family_plan(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.health.lobs.base import reconcile_for_aca_guaranteed_issue
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="family_floater_standard")
    reconcile_for_aca_guaranteed_issue(ctx.uw)

    outcome = LobOutcome(product_label="Family Health Plan")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Primary applicant age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE} (65+ is Medicare-eligible)")
    if ctx.household_members < MIN_HOUSEHOLD_MEMBERS:
        outcome.add_condition(f"Only {ctx.household_members} covered member(s) documented — confirm this is a family enrollment, not individual")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    for mandate in state_rules.get("mandated_benefits") or []:
        outcome.add_condition(f"State-mandated benefit: {mandate}")
    if state_rules.get("ivf_mandate"):
        outcome.add_condition(f"{state_rules['issue_state']} IVF mandate applies to this family plan")
    if state_rules.get("autism_mandate"):
        outcome.add_condition(f"{state_rules['issue_state']} autism-spectrum-disorder treatment mandate applies")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    tier_f = float((manual.get("metal_tier_av_factors") or {}).get("silver", 1.0))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    tier_size_f = household_tier_factor(ctx)

    monthly = silver_base * tier_f * age_f * tobacco_f * area_f * tier_size_f
    annual = round(monthly * 12.0 + policy_fee(ctx), 2)

    outcome.base_premium = round(silver_base * tier_f * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="primary_applicant_age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="household_composite_tier", amount=tier_size_f, basis=f"members={ctx.household_members}"),
    ]
    outcome.metadata.update(
        {
            "household_members": ctx.household_members,
            "monthly_premium": round(monthly, 2),
            "deductible_basis": "aggregate_family",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="family_health_plan")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_family_plan(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="family")
