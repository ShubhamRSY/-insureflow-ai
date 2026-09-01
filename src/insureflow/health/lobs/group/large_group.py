"""Large Group Health (ERISA) — dedicated logic path.

51+ employees (ACA large-group threshold). Unlike Small Group, large-group
plans are NOT community-rated — real experience rating (the group's own
claims history) and self-funded/level-funded arrangements are standard,
and ERISA preempts most state-mandated-benefit laws for self-funded plans
— a genuinely different regulatory posture from every other product in
this file, not just a bigger small-group plan.
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
from insureflow.health.lobs.state_law import small_group_size_threshold
from insureflow.rating.models import RateComponent

PRODUCT_ID = "large_group_health"
LOGIC_PATH = "insureflow.health.lobs.group.large_group"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Summary Plan Description (SPD) required under ERISA §102"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}


def underwrite_large_group(ctx: HealthProductContext, *, self_funded: bool) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="group_employer_mediclaim")

    outcome = LobOutcome(product_label="Large Group Health Plan" + (" (Self-Funded)" if self_funded else " (Fully Insured)"))

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    group_manual = (ctx.manual or {}).get("group") or {}
    small_group_max = small_group_size_threshold(ctx.issue_state)

    employee_count = ctx.household_members  # reused field: covered-lives count, not household
    if employee_count <= small_group_max:
        outcome.add_condition(f"{employee_count} employees is within the small-group threshold of {small_group_max} — confirm Large Group is the correct market, not Small Group")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    if self_funded:
        outcome.add_condition("ERISA preemption: state-mandated benefit laws generally do NOT apply to a self-funded plan — federal law (ACA, ERISA, HIPAA) governs instead")
    else:
        for mandate in state_rules.get("mandated_benefits") or []:
            outcome.add_condition(f"Fully insured — state-mandated benefit applies: {mandate}")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    admin_fee = float(group_manual.get("large_group_admin_fee_pepm", 22.0))
    # Real large-group experience rating: a simple size-based credibility
    # discount stands in for the group's own claims experience — larger
    # groups are more credible (predictable) and get a bigger discount than
    # a still-community-rated small group ever would.
    experience_credibility_discount = min(0.15, employee_count / 10_000.0)

    per_employee_monthly = (silver_base * age_f * tobacco_f * area_f) * (1.0 - experience_credibility_discount) + admin_fee
    annual = round(per_employee_monthly * employee_count * 12.0, 2)

    outcome.base_premium = round(silver_base * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="employee_age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="experience_credibility_discount", amount=round(1.0 - experience_credibility_discount, 4), basis=f"{employee_count} covered lives"),
        RateComponent(name="admin_fee_pepm", amount=admin_fee, basis="per-employee-per-month"),
    ]
    outcome.metadata.update(
        {
            "employee_count": employee_count,
            "self_funded": self_funded,
            "per_employee_monthly": round(per_employee_monthly, 2),
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="large_group_health")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    self_funded = "self_funded" in (ctx.coverage_id or "").lower() or "self-funded" in (ctx.coverage_name or "").lower()
    outcome = underwrite_large_group(ctx, self_funded=self_funded)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="group")
