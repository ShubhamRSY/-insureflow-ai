"""Public Sector Group Health — dedicated logic path.

Municipal, county, or state-government employer groups. Real, distinct
treatment from a private-sector Small/Large Group plan: public employers
are frequently self-funded and can carry different ACA employer-mandate
and reporting exemptions, and enrollment verification runs through a
government service record rather than a private employer's payroll.
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

PRODUCT_ID = "public_sector_group_health"
LOGIC_PATH = "insureflow.health.lobs.group.public_sector_group_health"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Summary Plan Description required for enrolling government employees"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}


def underwrite_public_sector_group(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="group_government_psu")

    outcome = LobOutcome(product_label="Public Sector Group Health Plan")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    employee_count = max(1, ctx.household_members)

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition("Government/PSU employer status verified via service record, not private payroll")
    for mandate in state_rules.get("mandated_benefits") or []:
        outcome.add_condition(f"State-mandated benefit: {mandate}")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    admin_fee = float((ctx.manual or {}).get("group", {}).get("public_sector_admin_fee_pepm", 20.0))

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
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="public_sector_group_health")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_public_sector_group(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="group")
