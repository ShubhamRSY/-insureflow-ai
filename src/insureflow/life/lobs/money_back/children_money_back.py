"""Children's Money-Back — dedicated logic path (LOB 6).

Coverage: Children's Money-Back Plan. Taken out by a proposer (parent/guardian)
on the child's life; survival payouts land at EDUCATION MILESTONE ages, and
premiums are waived if the proposer dies — the plan must survive the parent.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.actuarial import endowment_insurance_nsp, temporary_annuity_due
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
from insureflow.life.mortality import discount_factor, k_p_x
from insureflow.rating.models import RateComponent

PRODUCT_ID = "children_money_back"
LOGIC_PATH = "insureflow.life.lobs.money_back.children_money_back"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 15,
    "paramed_exam_required": False,  # child life — minimal evidence below threshold
    "paramed_face_threshold": 100_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.25,
    "milestone_ages": [18, 20, 22],
    "maturity_age": 25,
    "milestone_benefit_pct": 0.25,
    "wp_rider_load": 1.03,
    "disclosures": [
        "Premiums are waived on the PROPOSER's death — benefits continue unchanged",
        "Policy vests in the child at majority",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "CT": {"free_look_days": 30},
}

MIN_PROPOSER_AGE = 21
MAX_PROPOSER_AGE = 55


def underwrite_children_money_back(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Children's Money-Back Plan")

    # ctx.age is the PROPOSER's age in this path.
    if ctx.age < MIN_PROPOSER_AGE or ctx.age > MAX_PROPOSER_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Proposer age {ctx.age} outside {MIN_PROPOSER_AGE}-{MAX_PROPOSER_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    interest = float(state_rules["interest_rate"])
    loading = float(state_rules["expense_loading_pct"])
    milestones = list(state_rules["milestone_ages"])
    maturity_age = int(state_rules["maturity_age"])
    ms_pct = float(state_rules["milestone_benefit_pct"])
    wp_load = float(state_rules["wp_rider_load"])

    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")

    v = discount_factor(interest)
    # Child's issue age is not carried separately in ctx — milestone PVs use
    # an explicit assumption: child is 5 at proposal (documented, auditable).
    child_age_at_issue = 5
    coupon_pv_per_1 = 0.0
    schedule: list[dict[str, Any]] = []
    for age in [*milestones, maturity_age]:
        year = age - child_age_at_issue
        pct = ms_pct if age < maturity_age else 1.0 - ms_pct * len(milestones)
        amount_per_1 = pct
        pv = amount_per_1 * (v**year) * k_p_x(child_age_at_issue, year, ctx.sex_key, ctx.smoker)
        coupon_pv_per_1 += pv
        schedule.append({"child_age": age, "year": year, "pct_of_sa": round(pct, 2)})

    term = maturity_age - child_age_at_issue
    nsp_death = endowment_insurance_nsp(child_age_at_issue, term, ctx.sex_key, ctx.smoker, interest)
    a_due = temporary_annuity_due(child_age_at_issue, term, ctx.sex_key, ctx.smoker, interest)
    class_f = medical_class_factor(ctx, cap=1.0)  # child rates never load up
    level_net = ctx.face * (nsp_death + coupon_pv_per_1) / max(a_due, 1e-9)

    band_f = band_factor(ctx)
    state_rel = state_relativity(ctx)
    gross = level_net * (1.0 + loading) * class_f * wp_load
    loaded = gross * band_f * state_rel
    annual = add_common_loads(ctx, loaded)

    outcome.base_premium = round(gross, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="child_benefit_net", amount=round(level_net / wp_load, 2), basis=f"milestones {milestones} + maturity at {maturity_age}"),
        RateComponent(name="waiver_of_premium_rider", amount=round(wp_load - 1.0, 4), basis="premiums waived on proposer death"),
        RateComponent(name="expense_loading", amount=loading, basis=f"{loading:.0%} of net"),
        RateComponent(name="underwriting_class", amount=class_f, basis=f"{ctx.medical.underwriting_class} (capped at standard for child life)"),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": f"children's money-back milestones @ {interest:.0%}",
                "interest_rate": interest,
                "expense_loading_pct": loading,
                "child_age_assumption": child_age_at_issue,
            },
            "term_years": term,
            "payout_schedule": schedule,
            "proposer_age": ctx.age,
            "death_benefit": round(ctx.face, 2),
            "waiver_of_premium_included": True,
            "state_rules_applied": state_rules,
            "exam_required": bool(state_rules["paramed_exam_required"]),
        }
    )

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason(f"children's money-back priced on actuarial equivalence — illustrative only, no {filing}-filed money-back rates")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_children_money_back(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="money_back")
