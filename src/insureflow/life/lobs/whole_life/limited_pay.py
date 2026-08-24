"""Limited-Pay Whole Life — dedicated logic path (LOB 2).

Coverages: 10-Pay, 20-Pay, Paid-Up-at-65. Premiums cease after the pay
period while coverage continues for life — priced with limited-pay annuity
ä_{x:n} in the equivalence principle.
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

PRODUCT_ID = "limited_pay_whole_life"
LOGIC_PATH = "insureflow.life.lobs.whole_life.limited_pay"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.30,
    "max_income_multiple_of_premium": 0.20,  # annual premium should not exceed 20% of documented income
    "disclosures": [
        "Illustration acknowledgment showing the premium payment schedule",
        "After the pay period no further premiums are due — policy remains in force for life",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}


def _pay_period(ctx: LifeProductContext) -> int:
    coverage = f"{ctx.coverage_id or ''} {ctx.coverage_name or ''}".lower()
    if re.search(r"ten[_\s-]?pay|10[_\s-]?pay", coverage):
        return 10
    if re.search(r"twenty[_\s-]?pay|20[_\s-]?pay", coverage):
        return 20
    match = re.search(r"paid.?up.{0,6}(65|70)", coverage)
    if match:
        return max(1, int(match.group(1)) - ctx.age)
    return 20


def underwrite_limited_pay(ctx: LifeProductContext) -> LobOutcome:
    pay_years = _pay_period(ctx)
    outcome = LobOutcome(product_label=f"{pay_years}-Pay Whole Life")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    interest = float(state_rules["interest_rate"])
    loading = float(state_rules["expense_loading_pct"])
    formula = compute_full_whole_life_quote(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=ctx.face,
        interest_rate=interest,
        expense_loading_pct=loading,
        premium_term=pay_years,
        policy_fee=0.0,
    )

    class_f = medical_class_factor(ctx)
    band_f = band_factor(ctx)
    state_rel = state_relativity(ctx)
    loaded = formula.gross_premium * class_f * band_f * state_rel
    annual = add_common_loads(ctx, loaded)

    income = float(getattr(ctx.factors, "income", 0.0) or 0.0)
    if income and annual > income * float(state_rules["max_income_multiple_of_premium"]):
        outcome.add_condition(f"Affordability review — annual premium exceeds {float(state_rules['max_income_multiple_of_premium']):.0%} of documented income during the {pay_years}-pay period")

    outcome.base_premium = round(formula.gross_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="limited_pay_net_premium", amount=round(formula.level_net_premium, 2), basis=f"P_{{x:{pay_years}}} = A_x / ä_{{x:{pay_years}}} @ {interest:.0%}"),
        RateComponent(name="expense_loading", amount=round(formula.gross_premium - formula.level_net_premium, 2), basis=f"{loading:.0%} of net"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["pay_period_years"] = pay_years
    outcome.metadata["actuarial"] = {
        **formula.to_metadata(),
        "interest_rate": interest,
        "expense_loading_pct": loading,
        "premium_term": pay_years,
    }
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = bool(state_rules["paramed_exam_required"])

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    outcome.eligible = False
    outcome.add_reason(f"limited-pay whole life priced on actuarial equivalence (A_x / ä_x) — illustrative only, no {ctx.filing_state}-filed permanent rates")
    if ctx.issue_state and ctx.issue_state != ctx.filing_state:
        outcome.add_reason(f"{ctx.filing_state} pilot exhibit applied — not a {ctx.issue_state} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_limited_pay(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="whole_life")
