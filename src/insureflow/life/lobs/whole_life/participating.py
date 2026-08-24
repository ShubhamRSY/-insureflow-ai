"""Participating (Par) Whole Life — dedicated logic path (LOB 2).

Coverages: Dividend Cash Option, Dividend Paid-Up Additions. Base guaranteed
pricing plus an explicit dividend loading; the dividend option election is a
required condition and dividends are flagged non-guaranteed.
"""

from __future__ import annotations

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

PRODUCT_ID = "participating_whole_life"
LOGIC_PATH = "insureflow.life.lobs.whole_life.participating"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.30,
    "dividend_loading_pct": 0.12,  # par gross premium uplift funding the dividend scale
    "disclosures": [
        "Dividends are NOT guaranteed — based on current dividend scale",
        "Dividend option election form required (cash / PUA / premium reduction / accumulation)",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20, "disclosures_extra": ["NY standard nonforfeiture & dividend disclosure"]},
}


def _coverage_label(ctx: LifeProductContext) -> str:
    coverage = (ctx.coverage_id or "").lower()
    if coverage in {"div_cash"} or "cash" in (ctx.coverage_name or "").lower():
        return "Participating Whole Life — Dividend Cash Option"
    if coverage in {"div_pua"} or "paid-up additions" in (ctx.coverage_name or "").lower() or "pua" in coverage:
        return "Participating Whole Life — Paid-Up Additions"
    return "Participating Whole Life"


def underwrite_participating(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label=_coverage_label(ctx))

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    interest = float(state_rules["interest_rate"])
    loading = float(state_rules["expense_loading_pct"])
    div_loading = float(state_rules["dividend_loading_pct"])
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
    loaded = formula.gross_premium * class_f * band_f * state_rel * (1.0 + div_loading)
    annual = add_common_loads(ctx, loaded)

    outcome.base_premium = round(formula.gross_premium * (1.0 + div_loading), 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="whole_life_net_premium", amount=round(formula.level_net_premium, 2), basis=f"A_x/ä_x @ {interest:.0%} age={ctx.age}/{ctx.sex_key}"),
        RateComponent(name="expense_loading", amount=round(formula.gross_premium - formula.level_net_premium, 2), basis=f"{loading:.0%} of net"),
        RateComponent(name="dividend_loading", amount=div_loading, basis="par dividend scale funding"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["actuarial"] = {
        **formula.to_metadata(),
        "interest_rate": interest,
        "expense_loading_pct": loading,
        "participating": True,
    }
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = bool(state_rules["paramed_exam_required"])
    outcome.metadata["dividend_loading_pct"] = div_loading

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    outcome.eligible = False
    outcome.add_reason(f"participating whole life priced on actuarial equivalence with dividend loading — illustrative only, no {ctx.filing_state}-filed permanent rates")
    if ctx.issue_state and ctx.issue_state != ctx.filing_state:
        outcome.add_reason(f"{ctx.filing_state} pilot exhibit applied — not a {ctx.issue_state} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_participating(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="whole_life")
