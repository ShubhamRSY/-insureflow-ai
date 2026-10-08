"""Pure Endowment — dedicated logic path (LOB 4).

Coverage: Pure Maturity Benefit. Pays the sum assured ONLY if the insured is
alive at maturity — there is NO death benefit during the term. Priced on
v^n · _n p_x amortized over the term; explicitly NOT a flat multiplier.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.endowment_uw import run_endowment_uw
from insureflow.life.lobs.actuarial import pure_endowment_nsp, temporary_annuity_due
from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    add_common_loads,
    apply_state_filing_gate,
    band_factor,
    finish_quote,
    merge_state_rules,
    state_relativity,
    stated_term_years,
)
from insureflow.rating.models import RateComponent
from insureflow.underwriting.life_product import is_filed_endowment_product

PRODUCT_ID = "pure_endowment"
LOGIC_PATH = "insureflow.life.lobs.endowment.pure_endowment"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": False,  # no death benefit — mortality evidence minimal
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.25,
    "min_term_years": 5,
    "max_term_years": 30,
    "disclosures": [
        "PURE ENDOWMENT: nothing is payable if the insured dies before maturity",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "NY": {"free_look_days": 20},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 70


def underwrite_pure_endowment(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Pure Endowment (Maturity Only)")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Pure endowment issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    term_years = min(max(stated_term_years(ctx, 20), int(state_rules["min_term_years"])), int(state_rules["max_term_years"]))

    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")

    interest = float(state_rules["interest_rate"])
    loading = float(state_rules["expense_loading_pct"])

    # Net single premium for $1 of maturity benefit, amortized over the term.
    nsp_rate = pure_endowment_nsp(ctx.age, term_years, ctx.sex_key, ctx.smoker, interest)
    a_due = temporary_annuity_due(ctx.age, term_years, ctx.sex_key, ctx.smoker, interest)
    level_net = ctx.face * nsp_rate / max(a_due, 1e-9)

    band_f = band_factor(ctx)
    state_rel = state_relativity(ctx)
    gross = level_net * (1.0 + loading)
    loaded = gross * band_f * state_rel
    annual = add_common_loads(ctx, loaded)

    # Financial underwriting owns suitability here (no medical gate to fail).
    uw = run_endowment_uw(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=ctx.face,
        annual_premium=round(annual, 2),
        term_years=term_years,
        income=ctx.financial.income if hasattr(ctx.financial, "income") else getattr(ctx.factors, "income", 0.0),
        expected_maturity_value=ctx.face,
    )
    if uw.decision == "DECLINE":
        outcome.eligible = False
        for finding in uw.findings:
            outcome.add_reason(f"Endowment UW: {finding}")
    for finding in uw.findings[:6]:
        outcome.add_condition(f"Endowment UW: {finding}")

    outcome.base_premium = round(gross, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="pure_endowment_net", amount=round(level_net, 2), basis=f"v^{term_years}·_n p_x @ {interest:.0%} age={ctx.age}"),
        RateComponent(name="expense_loading", amount=loading, basis=f"{loading:.0%} of net"),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": f"pure endowment v^{term_years} * npx",
                "interest_rate": interest,
                "expense_loading_pct": loading,
                "nsp_per_1": round(nsp_rate, 6),
                "annuity_due_factor": round(a_due, 4),
            },
            "term_years": term_years,
            "maturity_value": round(ctx.face, 2),
            "death_benefit": 0.0,
            "endowment_uw": uw.to_metadata(),
            "state_rules_applied": state_rules,
            "exam_required": bool(state_rules["paramed_exam_required"]),
        }
    )

    filed = is_filed_endowment_product(PRODUCT_ID)
    apply_state_filing_gate(ctx, outcome, filed_for_state=filed, product_family="pure_endowment")
    if filed and outcome.eligible:
        raw = (ctx.manual or {}).get("endowment_filing")
        filing = raw if isinstance(raw, dict) else {}
        outcome.metadata["filed_endowment"] = True
        if filing.get("filing_id"):
            outcome.metadata["filing_id"] = filing["filing_id"]
        if filing.get("serff_tracking"):
            outcome.metadata["serff_tracking"] = filing["serff_tracking"]
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_pure_endowment(ctx)
    filed = is_filed_endowment_product(PRODUCT_ID)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="endowment", rating_engine="life_filing" if filed else "life_whole_life_actuarial")
