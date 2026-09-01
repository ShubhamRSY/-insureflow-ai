"""Medicare Advantage (Part C) — dedicated logic path.

A Medicare-replacement plan, not a supplement — always guaranteed issue for
anyone Medicare-eligible during their enrollment window, regardless of
health status or state. Many plans carry a $0 premium (the carrier is paid
by CMS capitation instead); the "premium" priced here is the plan's own
administrative/supplemental-benefit charge, not a medically-underwritten
rate.
"""

from __future__ import annotations

from typing import Any

from insureflow.health.lobs.base import (
    HealthProductContext,
    LobOutcome,
    apply_state_filing_gate,
    area_relativity,
    finish_quote,
    merge_state_rules,
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "medicare_advantage"
LOGIC_PATH = "insureflow.health.lobs.senior.medicare_advantage"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 30,
    "disclosures": ["Replaces Original Medicare — must be used at in-network providers per the plan's network type (HMO/PPO)"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 65


def underwrite_medicare_advantage(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    # Medicare Advantage is ALWAYS guaranteed issue during an enrollment
    # period — never medically underwritten, unlike Medigap outside its
    # federal window. Deliberately NOT reusing "senior_no_medical": that
    # handler is "simplified issue" (no exam, but still knocks out on
    # disclosed cancer/major-condition questions), which is a real and
    # useful distinction for Medigap-style products but wrong for Medicare
    # Advantage, which cannot decline on health status at all. No product
    # hint resolves to the generic KYC-only baseline instead.
    ctx.uw = underwrite_health(ctx.bundle)

    outcome = LobOutcome(product_label="Medicare Advantage (Part C)")

    if ctx.age < MIN_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Medicare Advantage requires Medicare eligibility — applicant age {ctx.age} is below the {MIN_ISSUE_AGE} minimum")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition("Guaranteed issue — Medicare Advantage cannot be declined on health status during an eligible enrollment period")

    manual = (ctx.manual or {}).get("senior") or {}
    base_monthly = float(manual.get("medicare_advantage_base_rate_monthly", 0.0))
    admin_fee = float(manual.get("medicare_advantage_admin_fee_monthly", 25.0))
    area_f = area_relativity(ctx)

    monthly = (base_monthly + admin_fee) * area_f
    annual = round(monthly * 12.0, 2)

    outcome.base_premium = round(base_monthly * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="plan_base_premium", amount=base_monthly, basis="CMS-capitated, often $0"),
        RateComponent(name="administrative_supplemental_fee", amount=admin_fee, basis="monthly"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "guaranteed_issue": True,
            "monthly_premium": round(monthly, 2),
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="medicare_advantage")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_medicare_advantage(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="senior")
