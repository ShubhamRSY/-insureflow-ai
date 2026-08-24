"""Graded / Guaranteed Issue Whole Life — dedicated logic path (LOB 2).

Coverages: Graded Benefit Whole Life, Guaranteed Issue Whole Life.
No paramedical exam and no medical decline — anti-selection is controlled
by a graded death-benefit schedule (30% yr 1 / 65% yr 2 / 100% yr 3+),
tight face caps, and issue-age windows.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    add_common_loads,
    finish_quote,
    merge_state_rules,
)
from insureflow.rating.models import RateComponent
from insureflow.rating.personal.manuals import nearest_key

PRODUCT_ID = "graded_guaranteed_issue_whole_life"
LOGIC_PATH = "insureflow.life.lobs.whole_life.graded"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": False,
    "min_issue_age": 50,
    "max_issue_age": 85,
    "max_face": 50_000.0,
    "graded_schedule": {"1": 0.30, "2": 0.65},  # % of face by policy year; year 3+ = 100%
    "disclosures": [
        "Graded benefit disclosure — death benefit is limited (refund-plus-interest) in the first 2 years for non-accidental death",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}


def underwrite_graded(ctx: LifeProductContext, *, guaranteed_issue: bool) -> LobOutcome:
    label = "Guaranteed Issue Whole Life" if guaranteed_issue else "Graded Benefit Whole Life"
    outcome = LobOutcome(product_label=label)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    min_age = int(state_rules["min_issue_age"])
    max_age = int(state_rules["max_issue_age"])
    if not min_age <= ctx.age <= max_age:
        outcome.eligible = False
        outcome.add_reason(f"{label} issue age {ctx.age} outside {min_age}–{max_age}")

    max_face = float(state_rules["max_face"])
    effective_face = min(ctx.face, max_face)
    if ctx.face > max_face:
        outcome.add_reason(f"Requested face ${ctx.face:,.0f} capped to GI maximum ${max_face:,.0f}")
        ctx.face = effective_face

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    manual = ctx.manual or {}
    q_table = (manual.get("mortality_per_1000") or {}).get(ctx.sex_key) or {}
    q = float(q_table.get(nearest_key(q_table, ctx.age), 1.5))

    # Simplified/GI pricing on the graded face with an explicit no-exam load;
    # the graded schedule itself limits early claims rather than the premium.
    base_premium = (effective_face / 1000.0) * q * 1.60
    state_rel_manual = float(((manual or {}).get("state_relativities") or {}).get(ctx.issue_state) or 1.0)
    annual = add_common_loads(ctx, base_premium * state_rel_manual)

    outcome.base_premium = round((effective_face / 1000.0) * q, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="gi_mortality_per_1000", amount=q, basis=f"age={ctx.age}/{ctx.sex_key}"),
        RateComponent(name="no_exam_anti_selection_load", amount=1.60, basis="guaranteed issue"),
        RateComponent(name="state_relativity", amount=state_rel_manual, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["capped_face"] = effective_face
    outcome.metadata["graded_schedule"] = dict(state_rules["graded_schedule"])
    outcome.metadata["immediate_full_benefit"] = guaranteed_issue is False
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = False
    outcome.metadata["simplified_underwriting"] = True
    outcome.metadata["_outcome"] = "accept"

    # Guaranteed issue: medical declines do NOT apply — that is the product's
    # purpose. Eligibility rests on age window + face cap only.
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    guaranteed_issue = (ctx.coverage_id or "").lower() in {"guaranteed_issue"} or "guaranteed issue" in (ctx.coverage_name or "").lower()
    outcome = underwrite_graded(ctx, guaranteed_issue=guaranteed_issue)
    variant = "guaranteed issue" if guaranteed_issue else "graded"
    outcome.eligible = False
    outcome.add_reason(f"{variant} whole life priced on GI exhibit — illustrative only, no {ctx.filing_state}-filed permanent rates")
    if ctx.issue_state and ctx.issue_state != ctx.filing_state:
        outcome.add_reason(f"{ctx.filing_state} pilot exhibit applied — not a {ctx.issue_state} state-of-issue filing")
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="whole_life")
