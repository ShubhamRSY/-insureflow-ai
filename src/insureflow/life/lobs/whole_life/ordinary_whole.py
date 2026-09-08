"""Traditional / Ordinary Whole Life — dedicated logic path (LOB 2).

Coverages: Guaranteed Whole Life, Ordinary Whole Life. Priced on actuarial
equivalence (net level premium P_x = A_x / ä_x) with expense loading —
explicitly NOT a flat multiplier on term mortality.

Pilot filing: traditional_whole_life is issueable on the IL permanent exhibit
(same honesty class as the term exhibit). Other permanent products stay
illustrative until their filings land.
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
    state_relativity,
)
from insureflow.life.whole_life_formulas import compute_full_whole_life_quote
from insureflow.rating.models import RateComponent
from insureflow.underwriting.life_product import is_filed_permanent_product

PRODUCT_ID = "traditional_whole_life"
LOGIC_PATH = "insureflow.life.lobs.whole_life.ordinary_whole"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.30,
    "disclosures": [
        "Illustration acknowledgment (signed) — cash value projections are guaranteed for basic WL",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "NY": {"free_look_days": 20},
}

MIN_ISSUE_AGE = 0
MAX_ISSUE_AGE = 80


def underwrite_ordinary_whole_life(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Guaranteed Whole Life")

    if ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Whole life issue age {ctx.age} above maximum {MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    # Prefer filed-manual permanent rates when present; else carrier defaults.
    manual = ctx.manual or {}
    interest = float(manual.get("whole_life_interest_rate") or state_rules["interest_rate"])
    loading = float(manual.get("whole_life_expense_loading") or state_rules["expense_loading_pct"])
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
    loaded = formula.gross_premium * class_f * band_f * state_rel
    annual = add_common_loads(ctx, loaded)

    outcome.base_premium = round(formula.gross_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="whole_life_net_premium", amount=round(formula.level_net_premium, 2), basis=f"A_x/ä_x @ {interest:.0%} age={ctx.age}/{ctx.sex_key}"),
        RateComponent(name="expense_loading", amount=round(formula.gross_premium - formula.level_net_premium, 2), basis=f"{loading:.0%} of net"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["actuarial"] = {
        **formula.to_metadata(),
        "interest_rate": interest,
        "expense_loading_pct": loading,
    }
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = bool(state_rules["paramed_exam_required"])

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False

    filed = is_filed_permanent_product(PRODUCT_ID)
    apply_state_filing_gate(ctx, outcome, filed_for_state=filed, product_family="traditional_whole_life")
    if filed:
        permanent = manual.get("permanent_filing") if isinstance(manual.get("permanent_filing"), dict) else {}
        outcome.metadata["filed_permanent"] = True
        if permanent.get("filing_id"):
            outcome.metadata["filing_id"] = permanent["filing_id"]
        if permanent.get("serff_tracking"):
            outcome.metadata["serff_tracking"] = permanent["serff_tracking"]
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_ordinary_whole_life(ctx)
    filed = is_filed_permanent_product(PRODUCT_ID)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="whole_life",
        rating_engine="life_filing" if filed else "life_whole_life_actuarial",
    )
