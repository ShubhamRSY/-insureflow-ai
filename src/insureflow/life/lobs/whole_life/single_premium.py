"""Single-Premium Whole Life — dedicated logic path (LOB 2).

Coverages: Lump-Sum Single Premium, Immediate Cash Value. The single premium
is the net single premium A_x (premium_term=1 collapses the annuity to one
payment) plus loading; source-of-funds and AML checks are explicit gates.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    band_factor,
    finish_quote,
    medical_class_factor,
    merge_state_rules,
    state_relativity,
)
from insureflow.life.whole_life_formulas import compute_full_whole_life_quote
from insureflow.rating.models import RateComponent

PRODUCT_ID = "single_premium_whole_life"
LOGIC_PATH = "insureflow.life.lobs.whole_life.single_premium"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.30,
    "aml_review_threshold": 10_000.0,  # federal AML / CSI trigger for lump-sum funding
    "disclosures": [
        "Modified Endowment Contract (MEC) tax notice — single-funding a WL policy typically creates a MEC under IRC §7702A",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}


def underwrite_single_premium(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Single-Premium Whole Life")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition("Source-of-funds documentation required (bank statement / sale proceeds)")
    outcome.add_condition("AML declaration and OFAC screening before premium acceptance")

    interest = float(state_rules["interest_rate"])
    loading = float(state_rules["expense_loading_pct"])
    formula = compute_full_whole_life_quote(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=ctx.face,
        interest_rate=interest,
        expense_loading_pct=loading,
        premium_term=1,  # single payment → P_x:n=1 = A_x
        policy_fee=0.0,
    )

    class_f = medical_class_factor(ctx)
    band_f = band_factor(ctx)
    state_rel = state_relativity(ctx)
    loaded = formula.gross_premium * class_f * band_f * state_rel
    annual = loaded + float((ctx.manual or {}).get("policy_fee", 60.0))

    if annual > float(state_rules["aml_review_threshold"]):
        outcome.add_condition(f"Large lump-sum (${annual:,.0f}) — enhanced AML review per ${float(state_rules['aml_review_threshold']):,.0f} threshold")

    outcome.base_premium = round(formula.gross_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="net_single_premium", amount=round(formula.level_net_premium, 2), basis=f"A_x @ {interest:.0%} age={ctx.age}/{ctx.sex_key}"),
        RateComponent(name="expense_loading", amount=round(formula.gross_premium - formula.level_net_premium, 2), basis=f"{loading:.0%} of NSP"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["actuarial"] = {
        **formula.to_metadata(),
        "interest_rate": interest,
        "expense_loading_pct": loading,
        "premium_term": 1,
    }
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = bool(state_rules["paramed_exam_required"])
    outcome.metadata["mec_notice_required"] = True

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    outcome.eligible = False
    outcome.add_reason(f"single-premium whole life priced on net single premium A_x — illustrative only, no {ctx.filing_state}-filed permanent rates")
    if ctx.issue_state and ctx.issue_state != ctx.filing_state:
        outcome.add_reason(f"{ctx.filing_state} pilot exhibit applied — not a {ctx.issue_state} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_single_premium(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="whole_life")
