"""Small Group Health (ACA Small-Group Market) — dedicated logic path.

Employers with 1-50 full-time-equivalent employees — 1-100 in CA/CO/NY/VT,
which raised their own small-group ceiling under the state-flexibility
option in 45 CFR 144.103. Community-rated like the individual market:
age/tobacco/area/tier only, no group-specific experience rating — that's
the real, distinguishing feature of the ACA small-group reforms versus
large group below.
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

PRODUCT_ID = "small_group_health"
LOGIC_PATH = "insureflow.health.lobs.group.small_group"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Summary of Benefits and Coverage (SBC) must be delivered to every enrolling employee"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}


def underwrite_small_group(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="group_employer_mediclaim")

    outcome = LobOutcome(product_label="Small Group Health Plan")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    group_manual = (ctx.manual or {}).get("group") or {}
    small_group_max = small_group_size_threshold(ctx.issue_state)

    employee_count = ctx.household_members  # reused field: covered-lives count, not household
    if employee_count > small_group_max:
        outcome.eligible = False
        outcome.add_reason(f"{employee_count} employees exceeds the small-group threshold of {small_group_max} — route to Large Group")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    if state_rules.get("small_group_reform"):
        outcome.add_condition(f"{state_rules['issue_state']} small-group reform: guaranteed issue, community rating — no group-level experience rating")
    for mandate in state_rules.get("mandated_benefits") or []:
        outcome.add_condition(f"State-mandated benefit: {mandate}")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    admin_fee = float(group_manual.get("small_group_admin_fee_pepm", 35.0))

    per_employee_monthly = silver_base * age_f * tobacco_f * area_f + admin_fee
    annual = round(per_employee_monthly * employee_count * 12.0, 2)

    outcome.base_premium = round(silver_base * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="employee_age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="admin_fee_pepm", amount=admin_fee, basis="per-employee-per-month"),
    ]
    outcome.metadata.update(
        {
            "employee_count": employee_count,
            "per_employee_monthly": round(per_employee_monthly, 2),
            "small_group_max": small_group_max,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="small_group_health")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_small_group(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="group")
