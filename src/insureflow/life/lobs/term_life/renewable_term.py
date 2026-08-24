"""Renewable Term Life — dedicated logic path (LOB 1 · Term Life).

Coverages: Renewable Term (10-year renewable periods), Annual Renewable Term
(ART — 1-year periods). Renewal right without new evidence; each renewal
re-prices at attained age.
"""

from __future__ import annotations

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
from insureflow.life.product_variants import compute_renewable_term
from insureflow.rating.models import RateComponent

PRODUCT_ID = "renewable_term"
LOGIC_PATH = "insureflow.life.lobs.term_life.renewable_term"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "max_renewal_age": 75,
    "disclosures": ["Renewal premium schedule at attained ages must be disclosed at issue"],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20, "max_renewal_age": 70},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 65


def underwrite_renewable_term(ctx: LifeProductContext, *, annual: bool) -> LobOutcome:
    label = "Annual Renewable Style" if annual else "Renewable Term"
    outcome = LobOutcome(product_label=label)

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Renewable term issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition("Signed renewal form at each renewal — no new medical evidence")

    variant = compute_renewable_term(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=ctx.face,
        initial_term_years=1 if annual else 10,
        max_renewal_age=int(state_rules["max_renewal_age"]),
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
    state_rel = state_relativity(ctx)
    first_premium = float(variant.renewal_periods[0]["annual_premium"]) if variant.renewal_periods else 0.0
    shape = stack_shape_ratio(ctx, first_premium, 1 if annual else 10)

    loaded = base_premium * class_f * sex_f * tobacco_f * band_f * shape * state_rel
    annual_premium = add_common_loads(ctx, loaded)

    outcome.base_premium = round(base_premium * shape, 2)
    outcome.annual_premium = annual_premium
    outcome.components = [
        RateComponent(name="manual_level_base", amount=round(base_premium * class_f * sex_f * tobacco_f * band_f, 2), basis="filed exhibit"),
        RateComponent(name="renewal_period_shape_ratio", amount=round(shape, 4), basis=f"{1 if annual else 10}yr period @ attained age"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["term_years"] = 1 if annual else 10
    outcome.metadata["renewal_schedule"] = variant.renewal_periods
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = bool(state_rules["paramed_exam_required"])
    outcome.metadata["annual_renewable"] = annual

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="renewable_term")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    annual = (ctx.coverage_id or "").lower() in {"art_style"} or "annual" in (ctx.coverage_name or "").lower()
    outcome = underwrite_renewable_term(ctx, annual=annual)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="term")
