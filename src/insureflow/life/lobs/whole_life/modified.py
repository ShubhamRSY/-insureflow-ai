"""Modified Whole Life — dedicated logic path (LOB 2).

Coverages: Modified (Step-Up), Modified 5/10. Lower premiums in the first
five years stepping to a higher level premium — year-1 affordability is
underwritten explicitly against the step-up schedule.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    add_common_loads,
    band_factor,
    finish_quote,
    medical_class_factor,
    merge_state_rules,
    state_relativity,
)
from insureflow.life.whole_life_formulas import compute_full_whole_life_quote
from insureflow.rating.models import RateComponent

PRODUCT_ID = "modified_whole_life"
LOGIC_PATH = "insureflow.life.lobs.whole_life.modified"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.30,
    "initial_premium_ratio": 0.60,  # years 1–5 priced at 60% of the level premium
    "step_up_year": 6,
    "max_income_multiple_of_final": 0.25,  # FINAL stepped premium vs income
    "disclosures": [
        "Illustration acknowledgment showing the premium step-up schedule",
        "Premium increases at year 6 — affordability of the higher premium must be confirmed",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}


def _is_5_10_variant(ctx: LifeProductContext) -> bool:
    coverage = f"{ctx.coverage_id or ''} {ctx.coverage_name or ''}".lower()
    return bool(re.search(r"5.?10|five.{0,3}ten", coverage))


def underwrite_modified(ctx: LifeProductContext) -> LobOutcome:
    variant_5_10 = _is_5_10_variant(ctx)
    outcome = LobOutcome(product_label="Modified 5/10 Whole Life" if variant_5_10 else "Modified Whole Life (Step-Up)")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    interest = float(state_rules["interest_rate"])
    loading = float(state_rules["expense_loading_pct"])
    initial_ratio = float(state_rules["initial_premium_ratio"])
    step_year = int(state_rules["step_up_year"])
    formula = compute_full_whole_life_quote(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=ctx.face,
        interest_rate=interest,
        expense_loading_pct=loading,
        policy_fee=0.0,
    )

    class_f = medical_class_factor(ctx)
    band_f = band_factor(ctx)
    state_rel = state_relativity(ctx)
    level_gross = formula.gross_premium * class_f * band_f * state_rel
    year1_premium = level_gross * initial_ratio
    annual = add_common_loads(ctx, year1_premium)

    income = float(getattr(ctx.factors, "income", 0.0) or 0.0)
    final_premium = add_common_loads(ctx, level_gross)
    if income and final_premium > income * float(state_rules["max_income_multiple_of_final"]):
        outcome.eligible = False
        outcome.add_reason(f"Post-step-up premium exceeds {float(state_rules['max_income_multiple_of_final']):.0%} of documented income — modified structure unsuitable")

    outcome.base_premium = round(year1_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="whole_life_net_premium", amount=round(formula.level_net_premium, 2), basis=f"A_x/ä_x @ {interest:.0%} age={ctx.age}/{ctx.sex_key}"),
        RateComponent(name="expense_loading", amount=round(formula.gross_premium - formula.level_net_premium, 2), basis=f"{loading:.0%} of net"),
        RateComponent(name="modified_initial_discount", amount=1 - initial_ratio, basis=f"years 1-{step_year - 1}"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["actuarial"] = {
        **formula.to_metadata(),
        "interest_rate": interest,
        "expense_loading_pct": loading,
        "structure": "modified",
    }
    outcome.metadata["premium_schedule"] = {
        "years_1_to_step": {"ratio": initial_ratio, "annual": round(add_common_loads(ctx, year1_premium), 2)},
        "year_step_onward": {"ratio": 1.0, "annual": round(final_premium, 2)},
        "step_up_year": step_year,
        "variant_5_10": variant_5_10,
    }
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = bool(state_rules["paramed_exam_required"])

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    outcome.eligible = False
    outcome.add_reason(f"modified whole life priced on actuarial equivalence with step-up schedule — illustrative only, no {ctx.filing_state}-filed permanent rates")
    if ctx.issue_state and ctx.issue_state != ctx.filing_state:
        outcome.add_reason(f"{ctx.filing_state} pilot exhibit applied — not a {ctx.issue_state} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_modified(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="whole_life")
