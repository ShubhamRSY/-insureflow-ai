"""Standalone AD&D — dedicated logic path.

Pure accidental-death-and-dismemberment: death/dismemberment schedule only,
no broader accident-medical-expense or weekly-indemnity benefit the way
add_accident_indemnity's individual/family/group coverages carry. Cheaper
and narrower — sold as a standalone voluntary benefit, payout is always to
the nominee, never a reimbursement.
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
from insureflow.underwriting.health_uw import _occupation_class

PRODUCT_ID = "standalone_add"
LOGIC_PATH = "insureflow.health.lobs.personal_accident.standalone_add"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Pays only for accidental death or dismemberment per the benefit schedule — no accident-medical-expense or weekly-indemnity benefit"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 75


def underwrite_standalone_add(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="pa_add")

    outcome = LobOutcome(product_label="Standalone AD&D")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Standalone AD&D issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
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
    rate_per_1000 = float(pa_manual.get("standalone_add_rate_per_1000_annual", 0.35))
    occ_f = float((pa_manual.get("occupation_class_factors") or {}).get(occ_class, 1.0))
    area_f = area_relativity(ctx)

    base_premium = (ctx.benefit_amount / 1000.0) * rate_per_1000
    annual = round(base_premium * occ_f * area_f + policy_fee(ctx), 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="standalone_add_rate_per_1000", amount=rate_per_1000, basis="annual"),
        RateComponent(name="occupation_class", amount=occ_f, basis=f"Class {occ_class}"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "principal_sum": ctx.benefit_amount,
            "occupation_class": occ_class,
            "benefit_scope": "death_dismemberment_only",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="standalone_add")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_standalone_add(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="personal_accident")
