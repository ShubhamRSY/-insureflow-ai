"""Family Plan — Extended Dependent Coverage — dedicated logic path.

Same guaranteed-issue posture and aggregate deductible as the base Family
Health Plan (ACA §2702/§2704 apply identically — an extended dependent
gets ZERO extra health-status underwriting, unlike the reused handler's
own India-market "parent-inclusive floater" concept, which is why this
reuses ``family_floater_standard`` rather than ``family_floater_parent``).
The real, distinct feature is eligibility documentation: ACA §2714 requires
covering dependents to age 26 automatically, and a disabled adult dependent
past 26 only with a disability certification on file — a genuinely
different intake requirement from the base family plan.
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
    reconcile_for_aca_guaranteed_issue,
    tobacco_surcharge,
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "family_extended_dependents"
LOGIC_PATH = "insureflow.health.lobs.family.family_extended_dependents"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": [
        "Aggregate family deductible — one shared deductible for all covered members, not per-member",
        "Dependents covered to age 26 regardless of student, marital, or financial-dependency status (ACA §2714)",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "NY": {"free_look_days": 30},
    "CA": {"free_look_days": 30},
}

MIN_ISSUE_AGE = 0
MAX_ISSUE_AGE = 64
MIN_HOUSEHOLD_MEMBERS = 2
DEPENDENT_AGE_CEILING = 26


def _has_disabled_dependent_certification(blob: str) -> bool:
    return any(k in blob for k in ("disability certification", "disabled dependent certification", "incapacitated dependent"))


def underwrite_extended_dependents(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="family_floater_standard")
    reconcile_for_aca_guaranteed_issue(ctx.uw)

    outcome = LobOutcome(product_label="Family Plan — Extended Dependent Coverage")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Primary applicant age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE} (65+ is Medicare-eligible)")
    if ctx.household_members < MIN_HOUSEHOLD_MEMBERS:
        outcome.add_condition(f"Only {ctx.household_members} covered member(s) documented — confirm this is a family enrollment, not individual")

    certified = _has_disabled_dependent_certification(ctx.blob)
    over_26_declared = any(k in ctx.blob for k in ("over 26", "over-26", "dependent age 27", "disabled adult dependent"))
    if over_26_declared and not certified:
        outcome.add_condition(f"Dependent past age {DEPENDENT_AGE_CEILING} requires a disability certification on file to remain covered")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    for mandate in state_rules.get("mandated_benefits") or []:
        outcome.add_condition(f"State-mandated benefit: {mandate}")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    tier_size_f = household_tier_factor(ctx)
    dependent_load_f = float(manual.get("extended_dependent_load_factor", 1.05))

    monthly = silver_base * age_f * tobacco_f * area_f * tier_size_f * dependent_load_f
    annual = round(monthly * 12.0 + policy_fee(ctx), 2)

    outcome.base_premium = round(silver_base * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="primary_applicant_age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="household_composite_tier", amount=tier_size_f, basis=f"members={ctx.household_members}"),
        RateComponent(name="extended_dependent_load", amount=dependent_load_f, basis="young-adult dependent pool"),
    ]
    outcome.metadata.update(
        {
            "household_members": ctx.household_members,
            "dependent_age_ceiling": DEPENDENT_AGE_CEILING,
            "disabled_dependent_certified": certified,
            "monthly_premium": round(monthly, 2),
            "deductible_basis": "aggregate_family",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="family_extended_dependents")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_extended_dependents(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="family")
