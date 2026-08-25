"""Variable Universal Life (VUL) — dedicated logic path (LOB 3).

Coverages: Separate-Account (Vx) Investment, FINRA Suitability Review, GMDB
Rider. Cash value invests in SEC-registered separate-account subaccounts —
investment risk is on the policyholder. Requires FINRA suitability and a
prospectus; GMDB guarantees a floor death benefit for an explicit rider fee.
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

PRODUCT_ID = "variable_universal_life"
LOGIC_PATH = "insureflow.life.lobs.universal_life.variable_universal_life"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.30,
    "prospectus_delivery_required": True,
    "disclosures": [
        "SEC prospectus must be delivered — separate account performance is not guaranteed",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "NY": {"free_look_days": 20, "paramed_face_threshold": 500_000.0},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 75
MIN_FACE = 250_000.0
M_E_RISK_CHARGE_LOAD = 1.15  # mortality & expense risk charge on lifetime basis
GMDB_RIDER_LOAD = 1.06  # guaranteed minimum death benefit rider fee
ASSUMED_AIR = 0.07  # assumed investment return for illustration only
PAY_TO_AGE = 100


def underwrite_vul(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Variable Universal Life")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"VUL issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.face < MIN_FACE:
        outcome.eligible = False
        outcome.add_reason(f"VUL minimum face ${MIN_FACE:,.0f} — selected face ${ctx.face:,.0f}")

    # VUL is a securities-registered product on every coverage option (the
    # base "vx_account" separate-account coverage included) — this must not
    # be gated to one specific coverage_id, since that leaves the two real
    # catalog coverages (vx_account, gmdb) with no suitability requirement.
    outcome.add_condition("FINRA suitability review REQUIRED before issue — investor profile documented by a registered representative")
    if ctx.coverage_id == "finra_suitability":
        outcome.product_label = "Variable Universal Life — FINRA Suitability Track"
    if ctx.coverage_id == "gmdb":
        outcome.product_label = "Variable Universal Life with GMDB Rider"
        outcome.add_condition("GMDB: death benefit floored at greater of premiums paid or account value")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    if state_rules["prospectus_delivery_required"]:
        outcome.add_condition("Prospectus delivery receipt required — subaccount value fluctuates and may lose value")
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
    loaded = formula.gross_premium * M_E_RISK_CHARGE_LOAD * class_f * band_f * state_rel
    if ctx.coverage_id == "gmdb":
        loaded *= GMDB_RIDER_LOAD
    annual = add_common_loads(ctx, loaded)

    # Illustrative separate-account growth at the ASSUMED AIR — not guaranteed.
    # `annual` is already the annual premium — dividing by modal_f would
    # inflate the account-value input ~11.5x for monthly payers.
    premium_net = annual
    from insureflow.life.mortality import q_x

    av = 0.0
    projection: dict[str, float] = {}
    for year in range(1, 21):
        coi = ctx.face * q_x(min(ctx.age + year, 95), ctx.sex_key, ctx.smoker) * 1.25
        av = max((av + premium_net) * (1.0 + ASSUMED_AIR) - coi, 0.0)
        if year in (5, 10, 20):
            projection[f"av_year_{year}_at_air"] = round(av, 2)

    outcome.base_premium = round(formula.gross_premium * M_E_RISK_CHARGE_LOAD * (GMDB_RIDER_LOAD if ctx.coverage_id == "gmdb" else 1.0), 2)
    outcome.annual_premium = annual
    components = [
        RateComponent(name="lifetime_basis_gross", amount=round(formula.gross_premium, 2), basis=f"A_x/ä_x pay-to-{PAY_TO_AGE} @ {interest:.0%}"),
        RateComponent(name="m_e_risk_charge", amount=round(M_E_RISK_CHARGE_LOAD - 1.0, 4), basis="separate-account M&E charge"),
    ]
    if ctx.coverage_id == "gmdb":
        components.append(RateComponent(name="gmdb_rider_load", amount=round(GMDB_RIDER_LOAD - 1.0, 4), basis="guaranteed minimum death benefit"))
    components += [
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.components = components
    outcome.metadata.update(
        {
            "actuarial": {
                **formula.to_metadata(),
                "interest_rate": interest,
                "expense_loading_pct": loading,
                "premium_term": pay_years,
            },
            "assumed_air": ASSUMED_AIR,
            "gmdb_rider": ctx.coverage_id == "gmdb",
            "separate_account_projection_air_basis": projection,
            "state_rules_applied": state_rules,
            "exam_required": bool(state_rules["paramed_exam_required"]),
        }
    )

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason(f"variable universal life priced on actuarial equivalence — illustrative only, no {filing}-filed VUL rates")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_vul(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="universal_life")
