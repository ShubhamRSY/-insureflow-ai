"""With-Profit Money-Back — dedicated logic path (LOB 6).

Coverage: With-Profit Money-Back Plan. Identical payout skeleton to the
traditional plan, but every survival payout and the maturity share carry a
reversionary bonus that is ILLUSTRATED only — never guaranteed.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.actuarial import temporary_annuity_due, term_insurance_nsp
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
from insureflow.life.lobs.money_back.traditional_money_back import (
    DEFAULT_STATE_RULES as _TRADITIONAL_STATE_RULES,
)
from insureflow.life.lobs.money_back.traditional_money_back import (
    MAX_ISSUE_AGE,
    TERM_YEARS,
    _coupon_pv,
)
from insureflow.life.lobs.money_back.traditional_money_back import (
    STATE_RULES as _TRADITIONAL_STATE_TABLE,
)
from insureflow.life.money_back_uw import run_money_back_uw
from insureflow.life.mortality import discount_factor, k_p_x
from insureflow.rating.models import RateComponent

PRODUCT_ID = "with_profit_money_back"
LOGIC_PATH = "insureflow.life.lobs.money_back.with_profit_money_back"

# Same state skeleton as the traditional plan; bonus disclosures differ.
DEFAULT_STATE_RULES: dict[str, Any] = {
    **_TRADITIONAL_STATE_RULES,
    "simple_bonus_rate": 0.045,
    "disclosures": [
        "Bonuses on survival payouts depend on participating-fund performance and are NOT guaranteed",
    ],
}

MIN_ISSUE_AGE = 18
SIMPLE_BONUS_RATE = float(DEFAULT_STATE_RULES["simple_bonus_rate"])


def underwrite_with_profit_money_back(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="With-Profit Money-Back Plan")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"With-profit money-back issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, _TRADITIONAL_STATE_TABLE)
    interest = float(state_rules["interest_rate"])
    loading = float(state_rules["expense_loading_pct"])
    sb_pct = float(state_rules["survival_benefit_pct"])
    interval = int(state_rules["payout_interval_years"])
    term = TERM_YEARS
    bonus_rate = SIMPLE_BONUS_RATE

    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")

    # Guaranteed basis identical to traditional; bonuses illustrated on top of
    # each payout (accruing at `bonus_rate` per year from issue to payout).
    coupon_pv_per_1, schedule = _coupon_pv(1.0, sb_pct, term, interval, ctx.age, ctx.sex_key, ctx.smoker, interest)
    # Death cover priced on a DEATH-ONLY basis — the coupon schedule already
    # sums to 100% of face by maturity, so endowment_insurance_nsp (term +
    # pure endowment) would price a second, undisclosed maturity payment.
    nsp_death = term_insurance_nsp(ctx.age, term, ctx.sex_key, ctx.smoker, interest)
    a_due = temporary_annuity_due(ctx.age, term, ctx.sex_key, ctx.smoker, interest)
    class_f = medical_class_factor(ctx)
    level_net = ctx.face * (nsp_death + coupon_pv_per_1) / max(a_due, 1e-9)

    band_f = band_factor(ctx)
    state_rel = state_relativity(ctx)
    gross = level_net * (1.0 + loading) * class_f
    loaded = gross * band_f * state_rel
    annual = add_common_loads(ctx, loaded)

    v = discount_factor(interest)
    bonus_pv = 0.0
    for entry in schedule:
        year = int(entry["year"])
        accrued = bonus_rate * year  # total bonus pct of SA by that payout
        bonus_pv += ctx.face * accrued * (v**year) * k_p_x(ctx.age, year, ctx.sex_key, ctx.smoker)

    # Non-guaranteed bonuses make persistency risk here at least as
    # relevant as on the traditional plan (arguably more so — the client's
    # expectations are pinned to an illustrated, not guaranteed, number).
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
        for finding in uw.findings:
            outcome.add_reason(f"Money-back UW: {finding}")
    for finding in uw.findings:
        outcome.add_condition(f"Money-back UW: {finding}")

    outcome.base_premium = round(gross, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="guaranteed_basis_net", amount=round(level_net, 2), basis=f"traditional money-back skeleton @ {interest:.0%}"),
        RateComponent(name="expense_loading", amount=loading, basis=f"{loading:.0%} of net"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": f"money-back + illustrated bonus PVs @ {interest:.0%}",
                "interest_rate": interest,
                "expense_loading_pct": loading,
            },
            "term_years": term,
            "survival_benefit_schedule": schedule,
            "simple_bonus_rate": bonus_rate,
            "illustrated_bonus_pv": round(bonus_pv, 2),
            "death_benefit": round(ctx.face, 2),
            "money_back_uw": uw.to_metadata(),
            "state_rules_applied": state_rules,
            "exam_required": bool(state_rules["paramed_exam_required"]),
        }
    )

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason(f"with-profit money-back priced on actuarial equivalence — illustrative only, no {filing}-filed money-back rates")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_with_profit_money_back(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="money_back")
