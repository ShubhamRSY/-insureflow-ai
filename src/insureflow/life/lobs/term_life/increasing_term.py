"""Increasing Term Life — dedicated logic path (LOB 1 · Term Life).

Coverages: CPI-Linked Increasing Term (COLI rate), Step-Up Increasing Term
(fixed annual % increase). Benefit rises on schedule; premium is level.
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
from insureflow.life.product_variants import compute_increasing_term
from insureflow.rating.models import RateComponent

PRODUCT_ID = "increasing_term"
LOGIC_PATH = "insureflow.life.lobs.term_life.increasing_term"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "max_projected_face_multiple": 3.0,  # projected face may not exceed 3x initial without re-review
    "disclosures": ["Projected benefit schedule must be illustrated and acknowledged"],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 70


def _term_years(ctx: LifeProductContext) -> int:
    blob = f"{ctx.coverage_id or ''} {ctx.coverage_name or ''}".lower()
    match = re.search(r"(?:^|[_\s-])(10|15|20|25|30)(?:$|[_\s-]|\s*-?\s*year|_year)", blob)
    return int(match.group(1)) if match else 20


def underwrite_increasing_term(ctx: LifeProductContext, *, cpi_linked: bool) -> LobOutcome:
    label = "CPI-Linked Increasing Term" if cpi_linked else "Step-Up Increasing Term"
    outcome = LobOutcome(product_label=label)

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Increasing term issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    years = _term_years(ctx)
    variant = compute_increasing_term(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        initial_face=ctx.face,
        term_years=years,
        use_coli=cpi_linked,
        coli_rate=2.5,
        annual_increase_pct=5.0,
    )
    projected_final_face = float(variant.yearly_detail[-1]["face_amount"])
    max_allowed = ctx.face * float(state_rules["max_projected_face_multiple"])
    if projected_final_face > max_allowed:
        outcome.eligible = False
        outcome.add_reason(f"Projected final face ${projected_final_face:,.0f} exceeds {state_rules['max_projected_face_multiple']:.0f}x initial — financial re-review required")

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

    # Increasing benefit costs more than level: shape ratio > 1.
    loaded = base_premium * class_f * sex_f * tobacco_f * band_f * term_f * shape * state_rel
    annual = add_common_loads(ctx, loaded)

    outcome.base_premium = round(base_premium * shape, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="manual_level_base", amount=round(base_premium * class_f * sex_f * tobacco_f * band_f * term_f, 2), basis=f"{years}yr level per filed exhibit"),
        RateComponent(name="increasing_shape_ratio", amount=round(shape, 4), basis="COLI 2.5%/yr" if cpi_linked else "step-up 5%/yr"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["term_years"] = years
    outcome.metadata["variant"] = variant.to_metadata()
    outcome.metadata["projected_final_face"] = round(projected_final_face, 2)
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = bool(state_rules["paramed_exam_required"])

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="increasing_term")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    cpi_linked = (ctx.coverage_id or "").lower() in {"cpi_term"} or "cpi" in (ctx.coverage_name or "").lower()
    outcome = underwrite_increasing_term(ctx, cpi_linked=cpi_linked)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="term")
