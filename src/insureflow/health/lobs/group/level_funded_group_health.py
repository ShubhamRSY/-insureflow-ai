"""Level-Funded Group Health — dedicated logic path.

Structurally self-funded — like Large Group — but sized for small
employers below the ACA large-group threshold, with a stop-loss policy
capping the employer's claims exposure. The real, distinct underwriting
step this creates: unlike a standard ACA-community-rated small-group plan,
a level-funded arrangement requires a per-employee health questionnaire so
the stop-loss carrier can price the attachment point — genuine medical
information collection a small-group ACA plan is legally barred from using.
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

PRODUCT_ID = "level_funded_group_health"
LOGIC_PATH = "insureflow.health.lobs.group.level_funded_group_health"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": [
        "Stop-loss policy caps the employer's own claims exposure — this is not fully insured community-rated coverage",
        "Per-employee health questionnaire is used only for stop-loss attachment-point pricing, not for enrollment eligibility",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

# Level-funding is a small/mid-size-employer alternative-funding mechanism —
# above this size, an employer is just Large Group self-funded outright, not
# "level-funded" in the sense this product actually prices (a flat monthly
# payment reconciled annually against a stop-loss-capped claims fund).
MAX_LEVEL_FUNDED_EMPLOYEES = 200


def _has_stop_loss_questionnaire(blob: str) -> bool:
    return any(k in blob for k in ("stop-loss questionnaire", "stop loss questionnaire", "stop-loss health questionnaire"))


def underwrite_level_funded_group(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="group_employer_mediclaim")

    outcome = LobOutcome(product_label="Level-Funded Group Health Plan")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    employee_count = max(1, ctx.household_members)
    if employee_count > MAX_LEVEL_FUNDED_EMPLOYEES:
        outcome.add_condition(
            f"{employee_count} employees exceeds the typical level-funded range (up to {MAX_LEVEL_FUNDED_EMPLOYEES}) — confirm this should not be priced as traditional Large Group self-funded"
        )

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    if not _has_stop_loss_questionnaire(ctx.blob):
        outcome.add_condition("Per-employee stop-loss health questionnaire required for every covered employee before stop-loss attachment can be priced")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    group_manual = (ctx.manual or {}).get("group") or {}
    admin_fee = float(group_manual.get("level_funded_admin_fee_pepm", 28.0))
    stop_loss_fee = float(group_manual.get("level_funded_stop_loss_fee_pepm", 18.0))

    per_employee_monthly = silver_base * age_f * tobacco_f * area_f + admin_fee + stop_loss_fee
    annual = round(per_employee_monthly * employee_count * 12.0, 2)

    outcome.base_premium = round(silver_base * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="employee_age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="admin_fee_pepm", amount=admin_fee, basis="per-employee-per-month"),
        RateComponent(name="stop_loss_fee_pepm", amount=stop_loss_fee, basis="per-employee-per-month"),
    ]
    outcome.metadata.update(
        {
            "employee_count": employee_count,
            "per_employee_monthly": round(per_employee_monthly, 2),
            "funding_type": "level_funded",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="level_funded_group_health")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_level_funded_group(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="group")
