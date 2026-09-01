"""Off-Exchange Individual Major Medical — dedicated logic path.

Sold directly by a carrier outside the Marketplace, not eligible for premium
subsidies, but still ACA-compliant (guaranteed issue, community rating, same
essential-health-benefits floor) since it's still individual-market major
medical. The only real difference from a Marketplace plan is distribution
and subsidy eligibility, not underwriting or rating — both are reflected
directly, not invented as separate mechanics.
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

PRODUCT_ID = "off_exchange_major_medical"
LOGIC_PATH = "insureflow.health.lobs.individual.off_exchange_major_medical"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": [
        "Not eligible for premium tax credits or cost-sharing reductions — Marketplace enrollment required for subsidy eligibility",
        "Summary of Benefits and Coverage (SBC) must be delivered before enrollment",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "NY": {"free_look_days": 30},
    "CA": {"free_look_days": 30},
}

MIN_ISSUE_AGE = 0
MAX_ISSUE_AGE = 64


def underwrite_off_exchange(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="individual_basic")

    outcome = LobOutcome(product_label="Off-Exchange Major Medical")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Off-exchange individual plan issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE} (65+ is Medicare-eligible)")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    if state_rules.get("guaranteed_issue") or state_rules.get("community_rating"):
        outcome.add_condition("Guaranteed issue / community rating applies in this state even off-exchange")

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
        RateComponent(name="metal_tier_equivalent", amount=tier_f, basis="silver-equivalent actuarial value"),
        RateComponent(name="age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="household_tier", amount=tier_size_f, basis=f"members={ctx.household_members}"),
    ]
    outcome.metadata.update(
        {
            "monthly_premium": round(monthly, 2),
            "subsidy_eligible": False,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="off_exchange_major_medical")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_off_exchange(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="individual")
