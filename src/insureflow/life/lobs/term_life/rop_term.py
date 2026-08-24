"""Return-of-Premium (ROP) Term Life — dedicated logic path (LOB 1 · Term Life).

Coverages: Full Return of Premium, Partial Return. Level term economics plus
an explicit premium load funding the refund feature; the refund schedule is
a required condition.
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
    state_relativity,
)
from insureflow.rating.models import RateComponent
from insureflow.rating.personal.manuals import nearest_key

PRODUCT_ID = "rop_term"
LOGIC_PATH = "insureflow.life.lobs.term_life.rop_term"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "full_rop_load": 1.45,
    "partial_rop_load": 1.28,
    "disclosures": ["Refund schedule illustration must be acknowledged — lapse forfeits return of premium"],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 65


def _term_years(ctx: LifeProductContext) -> int:
    blob = f"{ctx.coverage_id or ''} {ctx.coverage_name or ''}".lower()
    match = re.search(r"(?:^|[_\s-])(10|15|20|25|30)(?:$|[_\s-]|\s*-?\s*year|_year)", blob)
    return int(match.group(1)) if match else 20


def underwrite_rop_term(ctx: LifeProductContext, *, full_refund: bool) -> LobOutcome:
    label = "Full Return-of-Premium Rider" if full_refund else "Partial Return-of-Premium Rider"
    outcome = LobOutcome(product_label=label)

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"ROP term issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    years = _term_years(ctx)
    if years >= 30 and ctx.age > 55:
        outcome.eligible = False
        outcome.add_reason("ROP 30-year requires issue age <= 55 to complete the refund horizon")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    manual = ctx.manual or {}
    q_table = (manual.get("mortality_per_1000") or {}).get(ctx.sex_key) or {}
    q = float(q_table.get(nearest_key(q_table, ctx.age), 1.5))

    base_premium = (ctx.face / 1000.0) * q
    class_f = medical_class_factor(ctx)
    tobacco_f = float(manual.get("tobacco_factor", 1.85)) if ctx.smoker else 1.0
    band_f = band_factor(ctx)
    duration_factors = manual.get("term_duration_factors") or {}
    term_f = float(duration_factors.get(str(years), 1.0))
    rop_load = float(state_rules["full_rop_load"] if full_refund else state_rules["partial_rop_load"])
    state_rel = state_relativity(ctx)

    loaded = base_premium * class_f * tobacco_f * band_f * term_f * state_rel * rop_load
    annual = add_common_loads(ctx, loaded)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="level_mortality_per_1000", amount=q, basis=f"age={ctx.age}/{ctx.sex_key}"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="tobacco_factor", amount=tobacco_f, basis="tobacco" if ctx.smoker else "non_tobacco"),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="term_duration", amount=term_f, basis=f"{years}yr"),
        RateComponent(name="rop_rider_load", amount=rop_load, basis=label),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["term_years"] = years
    outcome.metadata["rop_load"] = rop_load
    outcome.metadata["refund_pct_at_maturity"] = 1.0 if full_refund else 0.65
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = bool(state_rules["paramed_exam_required"])

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="rop_term")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    full_refund = (ctx.coverage_id or "").lower() in {"full_rop"} or "full" in (ctx.coverage_name or "").lower()
    outcome = underwrite_rop_term(ctx, full_refund=full_refund)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="term")
