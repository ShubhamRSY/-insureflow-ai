"""Accidental Death & Dismemberment (AD&D) / Accident Indemnity — dedicated logic path.

Coverages: Individual, Family, Group. Priced per $1,000 of principal sum
off occupation class — the real, dominant rating factor for accident
insurance (a Class IV hazardous occupation is several times the cost of a
desk job), reusing the existing occupation-classification keyword logic
rather than re-deriving it.
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
    policy_fee,
)
from insureflow.rating.models import RateComponent

# Internal reuse: the same occupation-class keyword classifier the existing
# PA/disability handlers already use — not re-derived here.
from insureflow.underwriting.health_uw import _occupation_class

PRODUCT_ID = "add_accident_indemnity"
LOGIC_PATH = "insureflow.health.lobs.personal_accident.add_accident_indemnity"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Pays only for accidental injury or death — illness is not a covered cause of loss"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 75

_COVERAGE_TO_HANDLER = {"individual": "pa_individual", "family": "pa_family", "group": "pa_group"}


def underwrite_add(ctx: HealthProductContext, unit: str) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id=_COVERAGE_TO_HANDLER.get(unit, "pa_individual"))

    outcome = LobOutcome(product_label=f"AD&D — {unit.title()}")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"AD&D issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Principal sum missing — cannot rate AD&D without a coverage amount")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    occ_class = _occupation_class(ctx.blob) or "II"
    if occ_class == "IV":
        outcome.add_condition("Class IV hazardous occupation — refer for underwriter review before bind")

    pa_manual = (ctx.manual or {}).get("personal_accident") or {}
    rate_per_1000 = float(pa_manual.get("add_rate_per_1000_annual", 0.55))
    occ_f = float((pa_manual.get("occupation_class_factors") or {}).get(occ_class, 1.0))
    area_f = area_relativity(ctx)

    base_premium = (ctx.benefit_amount / 1000.0) * rate_per_1000
    annual = round(base_premium * occ_f * area_f + policy_fee(ctx), 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="add_rate_per_1000", amount=rate_per_1000, basis="annual"),
        RateComponent(name="occupation_class", amount=occ_f, basis=f"Class {occ_class}"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "principal_sum": ctx.benefit_amount,
            "occupation_class": occ_class,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="add_accident_indemnity")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    unit = "individual"
    cov = f"{ctx.coverage_id or ''} {ctx.coverage_name or ''}".lower()
    for candidate in ("family", "group", "individual"):
        if candidate in cov:
            unit = candidate
            break
    outcome = underwrite_add(ctx, unit)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="personal_accident")
