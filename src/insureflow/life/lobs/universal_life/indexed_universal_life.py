"""Indexed Universal Life (IUL) — dedicated logic path (LOB 3).

Coverages: Indexed Account, Fixed Account, Blend. Cash value credits track a
stock index with an explicit floor / cap / participation structure — the
policyholder takes index-linked upside, never negative crediting, in exchange
for caps and higher policy charges than GUL.
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

PRODUCT_ID = "indexed_universal_life"
LOGIC_PATH = "insureflow.life.lobs.universal_life.indexed_universal_life"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.30,
    "illustration_disclosure_required": True,
    "disclosures": [
        "IUL illustration disclosure: cap and participation rates are NOT guaranteed and may change",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "NY": {"free_look_days": 20, "paramed_face_threshold": 500_000.0},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 80
MIN_FACE = 100_000.0
INDEX_FLOOR = 0.00  # credited rate never below zero on indexed account
INDEX_CAP = 0.095  # annual cap on indexed crediting
PARTICIPATION_RATE = 1.00  # share of index gain that participates
FIXED_ACCOUNT_RATE = 0.025
CHARGE_LOAD = 1.12  # higher monthly charges vs GUL on same lifetime basis
PAY_TO_AGE = 100


def _credited(index_gain: float) -> float:
    return min(max(index_gain * PARTICIPATION_RATE, INDEX_FLOOR), INDEX_CAP)


def underwrite_iul(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Indexed Universal Life")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"IUL issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.face < MIN_FACE:
        outcome.eligible = False
        outcome.add_reason(f"IUL minimum face ${MIN_FACE:,.0f} — selected face ${ctx.face:,.0f}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    blend = ctx.coverage_id == "blend"
    fixed_only = ctx.coverage_id == "fixed_account"
    if blend:
        outcome.product_label = "Indexed Universal Life — Blended Accounts"
    elif fixed_only:
        outcome.product_label = "Indexed Universal Life — Fixed Account"

    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    if state_rules["illustration_disclosure_required"]:
        outcome.add_condition("Signed IUL illustration disclosure required at delivery")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    interest = float(state_rules["interest_rate"])
    loading = float(state_rules["expense_loading_pct"])
    pay_years = max(min(PAY_TO_AGE - ctx.age, 30), 1)
    formula = compute_full_whole_life_quote(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=ctx.face,
        interest_rate=interest,
        expense_loading_pct=loading,
        policy_fee=0.0,
        premium_term=pay_years,
    )

    class_f = medical_class_factor(ctx)
    band_f = band_factor(ctx)
    state_rel = state_relativity(ctx)
    loaded = formula.gross_premium * CHARGE_LOAD * class_f * band_f * state_rel
    annual = add_common_loads(ctx, loaded)

    # Illustrative crediting ladder for the indexed account.
    scenarios = {f"index_gain_{int(g * 100)}pct": round(_credited(g), 6) for g in (-0.10, 0.04, 0.08, 0.15)}

    outcome.base_premium = round(formula.gross_premium * CHARGE_LOAD, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="lifetime_basis_gross", amount=round(formula.gross_premium, 2), basis=f"A_x/ä_x pay-to-{PAY_TO_AGE} @ {interest:.0%}"),
        RateComponent(name="policy_charge_load", amount=round(CHARGE_LOAD - 1.0, 4), basis="higher IUL monthly charges"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                **formula.to_metadata(),
                "interest_rate": interest,
                "expense_loading_pct": loading,
                "premium_term": pay_years,
            },
            "index_floor": INDEX_FLOOR,
            "index_cap": INDEX_CAP,
            "participation_rate": PARTICIPATION_RATE,
            "fixed_account_rate": FIXED_ACCOUNT_RATE,
            "allocation": "fixed" if fixed_only else ("blend" if blend else "indexed"),
            "credited_rate_scenarios": scenarios,
            "state_rules_applied": state_rules,
            "exam_required": bool(state_rules["paramed_exam_required"]),
        }
    )

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason(f"indexed universal life priced on actuarial equivalence — illustrative only, no {filing}-filed IUL rates")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_iul(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="universal_life")
