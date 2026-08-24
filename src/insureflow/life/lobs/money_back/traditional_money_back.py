"""Traditional Money-Back — dedicated logic path (LOB 6).

Coverage: Traditional Money-Back Plan. Survival benefits are paid at fixed
intervals DURING the term (the policy keeps paying while the insured lives)
plus a maturity share; full sum assured is payable on death at any time.
Priced as PV(survival coupons) + PV(death cover) amortized over the term.
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
from insureflow.life.money_back_uw import run_money_back_uw
from insureflow.life.mortality import discount_factor, k_p_x
from insureflow.rating.models import RateComponent

PRODUCT_ID = "traditional_money_back"
LOGIC_PATH = "insureflow.life.lobs.money_back.traditional_money_back"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 15,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.25,
    "survival_benefit_pct": 0.20,  # at each payout date
    "maturity_benefit_pct": 0.20,  # plus remaining 20% at maturity
    "payout_interval_years": 5,
    "disclosures": [
        "Death benefit is FULL sum assured throughout — survival payouts do not reduce it",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 55
TERM_YEARS = 20


def _coupon_pv(face: float, sb_pct: float, term: int, interval: int, age: int, sex: str, smoker: bool, interest: float) -> tuple[float, list[dict[str, Any]]]:
    v = discount_factor(interest)
    total = 0.0
    schedule: list[dict[str, Any]] = []
    for year in range(interval, term + 1, interval):
        p_alive = k_p_x(age, year, sex, smoker)
        amount = face * (sb_pct if year < term else sb_pct + 0.20)  # maturity adds its share
        pv = amount * (v**year) * p_alive
        total += pv
        schedule.append({"year": year, "pct_of_sa": round(sb_pct if year < term else sb_pct + 0.20, 2), "amount": round(amount, 2)})
    return total, schedule


def underwrite_traditional_money_back(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Traditional Money-Back Plan")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Money-back issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    interest = float(state_rules["interest_rate"])
    loading = float(state_rules["expense_loading_pct"])
    sb_pct = float(state_rules["survival_benefit_pct"])
    interval = int(state_rules["payout_interval_years"])
    term = TERM_YEARS

    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")

    coupon_pv_per_1, schedule = _coupon_pv(1.0, sb_pct, term, interval, ctx.age, ctx.sex_key, ctx.smoker, interest)

    # Premium basis: death cover (full SA endowment-style) + survival coupons.
    nsp_death = endowment_insurance_nsp(ctx.age, term, ctx.sex_key, ctx.smoker, interest)
    a_due = temporary_annuity_due(ctx.age, term, ctx.sex_key, ctx.smoker, interest)
    class_f = medical_class_factor(ctx)
    level_net = ctx.face * (nsp_death + coupon_pv_per_1) / max(a_due, 1e-9)

    band_f = band_factor(ctx)
    state_rel = state_relativity(ctx)
    gross = level_net * (1.0 + loading) * class_f
    loaded = gross * band_f * state_rel
    annual = add_common_loads(ctx, loaded)

    uw = run_money_back_uw(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=ctx.face,
        annual_premium=round(annual, 2),
        term_years=term,
        income=getattr(ctx.factors, "income", 0.0),
        payout_schedule="every_5_years",
        survival_benefit_pct=sb_pct * 100,
    )
    if uw.decision == "DECLINE":
        outcome.eligible = False
    for finding in uw.findings[:5]:
        outcome.add_condition(f"Money-back UW: {finding}")

    outcome.base_premium = round(gross, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="death_cover_net", amount=round(level_net - coupon_pv_per_1 * ctx.face / max(a_due, 1e-9), 2), basis=f"A_x:{term} full SA on death"),
        RateComponent(name="survival_coupon_net", amount=round(coupon_pv_per_1 * ctx.face / max(a_due, 1e-9), 2), basis=f"{sb_pct:.0%} every {interval}y + maturity share"),
        RateComponent(name="expense_loading", amount=loading, basis=f"{loading:.0%} of net"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": f"money-back A_x:{term} + coupon PVs @ {interest:.0%}",
                "interest_rate": interest,
                "expense_loading_pct": loading,
            },
            "term_years": term,
            "survival_benefit_schedule": schedule,
            "death_benefit": round(ctx.face, 2),
            "total_survival_payouts_pct": round(sb_pct * (term // interval) + 0.20, 2),
            "money_back_uw": uw.to_metadata(),
            "state_rules_applied": state_rules,
            "exam_required": bool(state_rules["paramed_exam_required"]),
        }
    )

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason(f"traditional money-back priced on actuarial equivalence — illustrative only, no {filing}-filed money-back rates")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_traditional_money_back(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="money_back")
