"""Convertible Term Life — dedicated logic path (LOB 1 · Term Life).

Coverages: Convertible Term (Conversion window), Convert-to-Permanent.
Priced like level term for the chosen duration; the conversion privilege
(guaranteed issue to permanent, no new evidence) is underwritten explicitly.
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
from insureflow.life.product_variants import compute_convertible_term
from insureflow.rating.models import RateComponent

PRODUCT_ID = "convertible_term"
LOGIC_PATH = "insureflow.life.lobs.term_life.convertible_term"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "conversion_deadline_age": 65,
    "disclosures": ["Conversion privilege disclosure (no new evidence at conversion)"],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 70


def _term_years(ctx: LifeProductContext) -> int:
    blob = f"{ctx.coverage_id or ''} {ctx.coverage_name or ''}".lower()
    match = re.search(r"(?:^|[_\s-])(10|15|20|25|30)(?:$|[_\s-]|\s*-?\s*year|_year)", blob)
    return int(match.group(1)) if match else 20


def underwrite_convertible_term(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Convertible Term")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Convertible term issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    deadline_age = int(state_rules["conversion_deadline_age"])
    if ctx.age >= deadline_age:
        outcome.eligible = False
        outcome.add_reason(f"Issue age {ctx.age} at/after conversion deadline age {deadline_age}")

    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    years = _term_years(ctx)
    variant = compute_convertible_term(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=ctx.face,
        term_years=years,
        convert_by_age=deadline_age,
    )

    # Filed-manual level economics, reshaped to the convertible structure,
    # plus an explicit conversion-privilege load.
    q_table = ((ctx.manual or {}).get("mortality_per_1000") or {}).get(ctx.sex_key) or {}
    from insureflow.rating.personal.manuals import nearest_key

    q = float(q_table.get(nearest_key(q_table, ctx.age), 1.5))
    base_premium = (ctx.face / 1000.0) * q
    class_f = medical_class_factor(ctx)
    sex_f = 1.0 if ctx.unisex_forced else float(((ctx.manual or {}).get("sex_factors") or {}).get(ctx.sex_key, 1.0))
    tobacco_f = float((ctx.manual or {}).get("tobacco_factor", 1.85)) if ctx.smoker else 1.0
    band_f = band_factor(ctx)
    state_rel = state_relativity(ctx)
    term_f = float(((ctx.manual or {}).get("term_duration_factors") or {}).get(str(years), 1.0))
    shape = stack_shape_ratio(ctx, variant.level_premium, years)

    loaded = base_premium * class_f * sex_f * tobacco_f * band_f * term_f * shape * state_rel * 1.05
    annual = add_common_loads(ctx, loaded)

    outcome.base_premium = round(base_premium * shape, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="manual_level_base", amount=round(base_premium * class_f * sex_f * tobacco_f * band_f * term_f, 2), basis=f"{years}yr level per filed exhibit"),
        RateComponent(name="conversion_privilege_load", amount=0.05, basis=f"guaranteed issue to {deadline_age}"),
        RateComponent(name="convertible_shape_ratio", amount=round(shape, 4), basis="formula-stack level vs filed exhibit"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["term_years"] = years
    outcome.metadata["variant"] = variant.to_metadata()
    outcome.metadata["conversion_deadline_age"] = deadline_age
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = bool(state_rules["paramed_exam_required"])

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="convertible_term")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_convertible_term(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="term")
