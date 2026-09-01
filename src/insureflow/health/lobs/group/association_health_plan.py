"""Association Health Plan (AHP) — dedicated logic path.

A DOL-regulated ERISA multi-employer arrangement: a bona fide trade,
professional, or industry association sponsors one plan covering multiple
otherwise-unrelated small employers. Distinct from Small Group in filing
treatment — it can sometimes be treated as a single large-group risk pool
for underwriting purposes even though every participating employer is
individually small, which is the whole regulatory point of an AHP.
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
    merge_state_rules,
    tobacco_surcharge,
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "association_health_plan"
LOGIC_PATH = "insureflow.health.lobs.group.association_health_plan"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Summary of Benefits and Coverage (SBC) must be delivered to every enrolling member"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}


def underwrite_association_health_plan(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="group_association")

    outcome = LobOutcome(product_label="Association Health Plan")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    member_employers = max(1, ctx.household_members)  # reused field: participating covered lives across member employers

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition("Bona fide association status (common trade/professional/industry purpose beyond offering insurance) required under DOL rules")
    for mandate in state_rules.get("mandated_benefits") or []:
        outcome.add_condition(f"State-mandated benefit: {mandate}")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    admin_fee = float((ctx.manual or {}).get("group", {}).get("association_admin_fee_pepm", 30.0))

    per_member_monthly = silver_base * age_f * tobacco_f * area_f + admin_fee
    annual = round(per_member_monthly * member_employers * 12.0, 2)

    outcome.base_premium = round(silver_base * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="member_age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="admin_fee_pepm", amount=admin_fee, basis="per-member-per-month"),
    ]
    outcome.metadata.update(
        {
            "covered_members": member_employers,
            "per_member_monthly": round(per_member_monthly, 2),
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="association_health_plan")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_association_health_plan(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="group")
