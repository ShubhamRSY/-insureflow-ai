"""Guaranteed / Fixed Endowment — dedicated logic path (LOB 4).

Coverage: Fixed Maturity Value. Every maturity and death benefit is fully
guaranteed at issue — no bonuses, no participation. Priced on the mixed
endowment basis with a conservative loading because the carrier bears all
investment risk.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.endowment_uw import run_endowment_uw
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
from insureflow.rating.models import RateComponent

PRODUCT_ID = "guaranteed_fixed_endowment"
LOGIC_PATH = "insureflow.life.lobs.endowment.guaranteed_fixed_endowment"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.25,
    "guarantee_loading_pct": 0.10,
    "min_term_years": 5,
    "max_term_years": 25,
    "disclosures": [
        "All values guaranteed at issue — the carrier bears full investment risk",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 65


def underwrite_fixed_endowment(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Guaranteed Fixed Endowment")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Fixed endowment issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    term_years = min(max(int(getattr(ctx.factors, "term_years", 0) or 15), int(state_rules["min_term_years"])), int(state_rules["max_term_years"]))

    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")

    interest = float(state_rules["interest_rate"])
    loading = float(state_rules["expense_loading_pct"])

    nsp_rate = endowment_insurance_nsp(ctx.age, term_years, ctx.sex_key, ctx.smoker, interest)
    a_due = temporary_annuity_due(ctx.age, term_years, ctx.sex_key, ctx.smoker, interest)
    class_f = medical_class_factor(ctx)
    level_net = ctx.face * nsp_rate / max(a_due, 1e-9)

    band_f = band_factor(ctx)
    state_rel = state_relativity(ctx)
    gross = level_net * (1.0 + loading) * class_f * float(state_rules["guarantee_loading_pct"] + 1.0)
    loaded = gross * band_f * state_rel
    annual = add_common_loads(ctx, loaded)

    uw = run_endowment_uw(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=ctx.face,
        annual_premium=round(annual, 2),
        term_years=term_years,
        income=getattr(ctx.factors, "income", 0.0),
        expected_maturity_value=round(ctx.face, 2),
    )
    if uw.decision == "DECLINE":
        outcome.eligible = False
    for finding in uw.findings[:6]:
        outcome.add_condition(f"Endowment UW: {finding}")

    outcome.base_premium = round(gross, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="endowment_insurance_net", amount=round(level_net, 2), basis=f"A_x:n̄ @ {interest:.0%}"),
        RateComponent(name="expense_loading", amount=loading, basis=f"{loading:.0%} of net"),
        RateComponent(name="guarantee_load", amount=float(state_rules["guarantee_loading_pct"]), basis="all values guaranteed — investment risk on carrier"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": f"mixed endowment A_x:{term_years} fully guaranteed",
                "interest_rate": interest,
                "expense_loading_pct": loading,
                "nsp_per_1": round(nsp_rate, 6),
                "annuity_due_factor": round(a_due, 4),
            },
            "term_years": term_years,
            "guaranteed_maturity_value": round(ctx.face, 2),
            "death_benefit": round(ctx.face, 2),
            "endowment_uw": uw.to_metadata(),
            "state_rules_applied": state_rules,
            "exam_required": bool(state_rules["paramed_exam_required"]),
        }
    )

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason(f"fixed endowment priced on actuarial equivalence — illustrative only, no {filing}-filed endowment rates")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_fixed_endowment(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="endowment")
