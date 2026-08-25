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
from insureflow.life.whole_life_formulas import compute_full_whole_life_quote
from insureflow.rating.models import RateComponent

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
    "FL": {"free_look_days": 14},
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
        # A condition, not a reason: the quote stays eligible after capping,
        # and finish_quote only surfaces `reasons` when eligible=False.
        outcome.add_condition(f"Requested face ${ctx.face:,.0f} capped to GI maximum ${max_face:,.0f}")
        ctx.face = effective_face

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    manual = ctx.manual or {}
    # Priced on real actuarial equivalence (A_x/ä_x), same engine as every
    # other whole-life path — a flat current-year mortality charge (the
    # previous approach) is an annual-renewable-term rate, not a level
    # premium that pre-funds the whole increasing future mortality curve,
    # and would systematically underprice at the older ages this product
    # is issued to (min_issue_age defaults to 50). The no-exam
    # anti-selection risk is priced as an explicit load on top of the net
    # premium, same pattern as every other simplified-issue path.
    wl_interest = float(manual.get("whole_life_interest_rate", 0.04))
    wl_loading = float(manual.get("whole_life_expense_loading", 0.30))
    anti_selection_load = 1.60
    wl_quote = compute_full_whole_life_quote(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=effective_face,
        interest_rate=wl_interest,
        expense_loading_pct=wl_loading,
        policy_fee=0.0,
    )
    net_premium = float(wl_quote.level_net_premium)
    state_rel_manual = float(((manual or {}).get("state_relativities") or {}).get(ctx.issue_state) or 1.0)
    loaded = net_premium * (1.0 + wl_loading) * anti_selection_load * state_rel_manual
    annual = add_common_loads(ctx, loaded)

    # Graded death benefit — real payout math, not a label. Non-accidental
    # death in years 1-2 pays the graded percentage of face (or premiums
    # paid with interest if greater, per the disclosure); year 3+ pays 100%.
    graded_pct = {int(k): float(v) for k, v in state_rules["graded_schedule"].items()}
    refund_interest_rate = 0.03

    def _graded_death_benefit(policy_year: int) -> dict[str, Any]:
        if policy_year not in graded_pct:
            return {"policy_year": policy_year, "pct_of_face": 1.0, "amount": round(effective_face, 2), "basis": "full face"}
        pct = graded_pct[policy_year]
        premiums_paid = annual * policy_year
        refund_with_interest = premiums_paid * ((1.0 + refund_interest_rate) ** policy_year)
        graded_amount = effective_face * pct
        amount = max(graded_amount, refund_with_interest)
        basis = "refund + interest (exceeds graded %)" if refund_with_interest > graded_amount else f"{pct:.0%} of face"
        return {"policy_year": policy_year, "pct_of_face": round(amount / effective_face, 4) if effective_face else 0.0, "amount": round(amount, 2), "basis": basis}

    graded_benefit_schedule = [_graded_death_benefit(y) for y in (1, 2, 3)]

    outcome.base_premium = round(net_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="whole_life_net_premium", amount=round(net_premium, 2), basis=f"A_x/ä_x @ {wl_interest:.0%} age={ctx.age}/{ctx.sex_key}"),
        RateComponent(name="expense_loading", amount=wl_loading, basis=f"{wl_loading:.0%} of net"),
        RateComponent(name="no_exam_anti_selection_load", amount=anti_selection_load, basis="guaranteed issue"),
        RateComponent(name="state_relativity", amount=state_rel_manual, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["capped_face"] = effective_face
    outcome.metadata["graded_schedule"] = dict(state_rules["graded_schedule"])
    outcome.metadata["graded_death_benefit_schedule"] = graded_benefit_schedule
    outcome.metadata["immediate_full_benefit"] = guaranteed_issue is False
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = False
    outcome.metadata["simplified_underwriting"] = True
    outcome.metadata["_outcome"] = "accept"
    # Guaranteed issue: medical declines/APS/paramedical evidence gates do
    # NOT apply — that is the product's purpose. Eligibility rests on the
    # age window + face cap only (both enforced above).
    outcome.metadata["_skip_medical_gate"] = True

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
