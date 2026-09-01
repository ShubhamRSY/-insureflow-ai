"""ACA Marketplace Individual/Family Plans — dedicated logic path.

Coverages: Bronze / Silver / Gold / Platinum metal tiers. Guaranteed issue —
no medical underwriting on the individual market (ACA §2702): the reused
health_uw handler here only gates on paperwork (income proof for subsidy
eligibility, self-declared health questionnaire on file), never on health
status. Rated on the federal 3:1 age curve + tobacco (up to 1.5x) + area,
per ACA community-rating rules — sex, health status, and claims history are
NOT rating factors on this market, unlike every other product in this file.
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

PRODUCT_ID = "aca_marketplace_plan"
LOGIC_PATH = "insureflow.health.lobs.individual.bronze_silver_plans"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Summary of Benefits and Coverage (SBC) must be delivered before enrollment"],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "NY": {"free_look_days": 30},
    "CA": {"free_look_days": 30},
}

MIN_ISSUE_AGE = 0
MAX_ISSUE_AGE = 64  # 65+ moves to Medicare — see health/lobs/senior/


def underwrite_marketplace_plan(ctx: HealthProductContext, tier: str) -> LobOutcome:
    # underwrite_health() is product-id-aware (its own dispatch table), so each
    # LOB path resolves its OWN reused handler here rather than the generic
    # dispatcher pre-populating ctx.uw. Deliberately NOT "individual_comprehensive":
    # that handler requires evidence of a "pre-policy medical check-up" above
    # age 45 / high SI — a real health-status-adjacent gate that directly
    # contradicts ACA guaranteed issue (§2702), even though it only produces a
    # REFER, not a decline. "individual_basic" is administrative/KYC-only
    # (a self-declared questionnaire on file, never a medical exam requirement).
    from insureflow.health.lobs.base import reconcile_for_aca_guaranteed_issue
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="individual_basic")
    reconcile_for_aca_guaranteed_issue(ctx.uw)

    outcome = LobOutcome(product_label=f"ACA Marketplace {tier.title()} Plan")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Marketplace individual plan issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE} (65+ is Medicare-eligible)")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    if state_rules.get("guaranteed_issue") or state_rules.get("community_rating"):
        outcome.add_condition("Guaranteed issue / community rating applies in this state — enrollment cannot be refused or rated on health status")
    if state_rules.get("state_individual_mandate"):
        outcome.add_condition(f"{state_rules['issue_state']} state individual mandate applies — penalty for lapse in coverage")
    for mandate in state_rules.get("mandated_benefits") or []:
        outcome.add_condition(f"State-mandated benefit: {mandate}")
    if state_rules.get("minimum_metal_level") and tier == "bronze":
        outcome.add_condition(f"{state_rules['issue_state']} requires a minimum metal level of {state_rules['minimum_metal_level']} — confirm Bronze satisfies it")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    tier_f = float((manual.get("metal_tier_av_factors") or {}).get(tier, 1.0))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    tier_size_f = household_tier_factor(ctx)

    monthly = silver_base * tier_f * age_f * tobacco_f * area_f * tier_size_f
    annual = round(monthly * 12.0 + policy_fee(ctx), 2)

    outcome.base_premium = round(silver_base * tier_f * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="metal_tier", amount=tier_f, basis=tier),
        RateComponent(name="age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="household_tier", amount=tier_size_f, basis=f"members={ctx.household_members}"),
    ]
    outcome.metadata.update(
        {
            "metal_tier": tier,
            "monthly_premium": round(monthly, 2),
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="aca_marketplace_plan")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    tier = "silver"
    cov = (ctx.coverage_id or "").lower()
    for candidate in ("bronze", "silver", "gold", "platinum"):
        if candidate in cov or candidate in (ctx.coverage_name or "").lower():
            tier = candidate
            break
    outcome = underwrite_marketplace_plan(ctx, tier)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="individual")
