"""Current Assumption / Adjustable Universal Life — dedicated logic path (LOB 3).

Coverages: Adjustable Benefit, Current-Rate Crediting. Crediting follows the
carrier's CURRENT declared rate (reviewed periodically) subject to a
contractual guaranteed minimum; death benefit and premium are adjustable
within contractual bands with notice.
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

PRODUCT_ID = "current_assumption_universal_life"
LOGIC_PATH = "insureflow.life.lobs.universal_life.current_assumption_universal_life"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.30,
    "rate_change_notice_days": 31,
    "disclosures": [
        "Carrier may change the current credited rate (never below the guaranteed minimum) with advance notice",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "NY": {"free_look_days": 20, "paramed_face_threshold": 500_000.0},
}

MIN_ISSUE_AGE = 18
# Capped at the filed manual's eligibility.max_age (life_medical.underwrite_life
# declines anyone older than that regardless of this product's own gate), not
# 80 — a higher local ceiling here was dead: ages 76-80 always got declined by
# the shared medical gate anyway, while this product's own message claimed
# they were in range.
MAX_ISSUE_AGE = 75
MIN_FACE = 100_000.0
CURRENT_CREDIT_RATE = 0.050  # carrier's current declared rate (illustrative)
GUARANTEED_MIN_RATE = 0.040  # contractual floor — matches the manual's basis
ADJUSTABLE_LOAD = 1.05  # flexibility pricing on the lifetime basis
PAY_TO_AGE = 100


def underwrite_caul(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Current Assumption Universal Life")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"CAUL issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.face < MIN_FACE:
        outcome.eligible = False
        outcome.add_reason(f"CAUL minimum face ${MIN_FACE:,.0f} — selected face ${ctx.face:,.0f}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    adjustable_db = ctx.coverage_id == "adjustable"
    if adjustable_db:
        outcome.product_label = "Adjustable Death Benefit Universal Life"
        outcome.add_condition("Death benefit Option A/B may be adjusted subject to evidence and corridor rules")

    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    outcome.add_condition(f"Credited-rate changes require {state_rules['rate_change_notice_days']}-day advance notice ({state_rules['issue_state'] or 'default'})")
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
    loaded = formula.gross_premium * ADJUSTABLE_LOAD * class_f * band_f * state_rel
    annual = add_common_loads(ctx, loaded)

    # Two crediting columns: current declared rate vs contractual guarantee.
    # Annual COI ≈ face × q(age+t) × loading (attained age rises each year).
    # `annual` is already the annual premium — modal_f converts annual->modal
    # payment size (e.g. 0.087 for monthly); dividing by it here would
    # inflate the account-value input ~11.5x for monthly payers instead of
    # leaving the annual funding amount unchanged.
    premium_net = annual
    from insureflow.life.mortality import q_x

    projections: dict[str, dict[str, float]] = {"current_rate": {}, "guaranteed_min": {}}
    for label, rate in (("current_rate", CURRENT_CREDIT_RATE), ("guaranteed_min", GUARANTEED_MIN_RATE)):
        av = 0.0
        for year in range(1, 21):
            coi = ctx.face * q_x(min(ctx.age + year, 95), ctx.sex_key, ctx.smoker) * 1.25
            av = max((av + premium_net - coi - 96.0) * (1.0 + rate), 0.0)
            if year in (5, 10, 20):
                projections[label][f"av_year_{year}"] = round(av, 2)

    outcome.base_premium = round(formula.gross_premium * ADJUSTABLE_LOAD, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="lifetime_basis_gross", amount=round(formula.gross_premium, 2), basis=f"A_x/ä_x pay-to-{PAY_TO_AGE} @ {interest:.0%}"),
        RateComponent(name="adjustability_load", amount=round(ADJUSTABLE_LOAD - 1.0, 4), basis="flexible premium / benefit option"),
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
            "current_credit_rate": CURRENT_CREDIT_RATE,
            "guaranteed_minimum_rate": GUARANTEED_MIN_RATE,
            "av_projection_columns": projections,
            "adjustable_death_benefit": adjustable_db,
            "state_rules_applied": state_rules,
            "exam_required": bool(state_rules["paramed_exam_required"]),
        }
    )

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason(f"current assumption universal life priced on actuarial equivalence — illustrative only, no {filing}-filed UL rates")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_caul(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="universal_life")
