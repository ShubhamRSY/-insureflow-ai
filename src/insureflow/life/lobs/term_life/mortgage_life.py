"""Mortgage Life Insurance — dedicated logic path (LOB 1 · Term Life).

Coverages: Mortgage Balance Protection (amortization-matched), Lender-Assigned
Benefit (assignable to the lender, small admin load). Distinct from generic
Decreasing Term: the lender relationship is underwritten explicitly.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    add_common_loads,
    apply_state_filing_gate,
    band_factor,
    finish_quote,
    medical_class_factor,
    merge_state_rules,
    stack_shape_ratio,
    state_relativity,
)
from insureflow.life.product_variants import compute_decreasing_term
from insureflow.rating.models import RateComponent

PRODUCT_ID = "mortgage_life"
LOGIC_PATH = "insureflow.life.lobs.term_life.mortgage_life"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "lender_assignment_admin_load": 0.03,
    "disclosures": ["Lender assignment must be acknowledged in writing by the lender"],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 70


def _mortgage_term_years(ctx: LifeProductContext) -> int:
    blob = f"{ctx.coverage_id or ''} {ctx.coverage_name or ''}".lower()
    match = re.search(r"(?:^|[_\s-])(10|15|20|25|30)(?:$|[_\s-]|\s*-?\s*year|_year)", blob)
    return int(match.group(1)) if match else 30


def underwrite_mortgage_life(ctx: LifeProductContext, *, lender_assigned: bool) -> LobOutcome:
    label = "Lender-Assigned Benefit" if lender_assigned else "Mortgage Balance Protection"
    outcome = LobOutcome(product_label=label)

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Mortgage life issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    if lender_assigned:
        outcome.add_condition("Loss payee / assignment endorsement naming the lender")

    years = _mortgage_term_years(ctx)
    variant = compute_decreasing_term(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        initial_face=ctx.face,
        term_years=years,
        amortize=True,
    )

    manual = ctx.manual or {}
    q_table = (manual.get("mortality_per_1000") or {}).get(ctx.sex_key) or {}
    from insureflow.rating.personal.manuals import nearest_key

    q = float(q_table.get(nearest_key(q_table, ctx.age), 1.5))
    base_premium = (ctx.face / 1000.0) * q
    class_f = medical_class_factor(ctx)
    sex_f = 1.0 if ctx.unisex_forced else float((manual.get("sex_factors") or {}).get(ctx.sex_key, 1.0))
    tobacco_f = float(manual.get("tobacco_factor", 1.85)) if ctx.smoker else 1.0
    band_f = band_factor(ctx)
    term_f = float((manual.get("term_duration_factors") or {}).get(str(years), 1.0))
    state_rel = state_relativity(ctx)
    shape = stack_shape_ratio(ctx, variant.level_premium, years)

    loaded = base_premium * class_f * sex_f * tobacco_f * band_f * term_f * shape * state_rel
    if lender_assigned:
        admin = float(state_rules.get("lender_assignment_admin_load", 0.03))
        loaded *= 1.0 + admin
    annual = add_common_loads(ctx, loaded)

    outcome.base_premium = round(base_premium * shape, 2)
    outcome.annual_premium = annual
    components = [
        RateComponent(name="manual_level_base", amount=round(base_premium * class_f * sex_f * tobacco_f * band_f * term_f, 2), basis=f"amortized {years}yr per filed exhibit"),
        RateComponent(name="mortgage_shape_ratio", amount=round(shape, 4), basis="amortization vs level"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    if lender_assigned:
        components.append(RateComponent(name="lender_assignment_admin", amount=float(state_rules.get("lender_assignment_admin_load", 0.03)), basis="assignment servicing"))
    outcome.components = components
    outcome.metadata["term_years"] = years
    outcome.metadata["variant"] = variant.to_metadata()
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = bool(state_rules["paramed_exam_required"])
    outcome.metadata["lender_assigned"] = lender_assigned

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="mortgage_life")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    lender_assigned = (ctx.coverage_id or "").lower() in {"lender_assign"} or "lender" in (ctx.coverage_name or "").lower()
    outcome = underwrite_mortgage_life(ctx, lender_assigned=lender_assigned)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="term")
