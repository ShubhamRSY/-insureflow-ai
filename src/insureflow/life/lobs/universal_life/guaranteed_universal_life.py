"""Guaranteed Universal Life (GUL) — dedicated logic path (LOB 3).

Coverages: No-Lapse Guarantee, GUL-to-120. Flexible premium with a SECONDARY
no-lapse guarantee: the carrier guarantees the death benefit persists to age
121 even if account value hits zero, as long as the scheduled premium is paid.
Priced on the lifetime A_x/ä_x basis amortized over a pay-to-100 window with
an explicit no-lapse guarantee load.
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

PRODUCT_ID = "guaranteed_universal_life"
LOGIC_PATH = "insureflow.life.lobs.universal_life.guaranteed_universal_life"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "interest_rate": 0.04,
    "expense_loading_pct": 0.30,
    "no_lapse_notice_required": True,
    "disclosures": [
        "No-lapse guarantee void if policy value goes negative or premium is missed — grace-period rules apply",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "NY": {"free_look_days": 20, "paramed_face_threshold": 500_000.0},
}

MIN_ISSUE_AGE = 18
# Capped at the filed manual's eligibility.max_age (life_medical.underwrite_life
# declines anyone older than that regardless of this product's own gate), not
# 85 — a higher local ceiling here was dead: ages 76-85 always got declined by
# the shared medical gate anyway, while this product's own message claimed
# they were in range.
MAX_ISSUE_AGE = 75
MIN_FACE = 100_000.0
NO_LAPSE_LOAD = 1.08  # secondary-guarantee reserve charge on top of lifetime basis
PAY_TO_AGE = 100
COI_LOADING = 1.25
ADMIN_FEE_ANNUAL = 96.0


def underwrite_gul(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="No-Lapse Guaranteed Universal Life")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"GUL issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.face < MIN_FACE:
        outcome.eligible = False
        outcome.add_reason(f"GUL minimum face ${MIN_FACE:,.0f} — selected face ${ctx.face:,.0f}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    to_age = 121 if ctx.coverage_id == "gul_to_120" else 120
    if ctx.coverage_id == "gul_to_120":
        outcome.product_label = "GUL Guaranteed to Age 120"

    if ctx.face > float(state_rules["paramed_face_threshold"]) and state_rules["paramed_exam_required"]:
        outcome.add_condition("Paramedical exam required above threshold")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    if state_rules["no_lapse_notice_required"]:
        outcome.add_condition("State no-lapse guarantee notice must accompany delivery")
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
    from insureflow.life.mortality import q_x

    coi_annual = round(ctx.face * q_x(ctx.age, ctx.sex_key, ctx.smoker) * COI_LOADING, 2)  # year-1 estimate
    loaded = formula.gross_premium * NO_LAPSE_LOAD * class_f * band_f * state_rel
    annual = add_common_loads(ctx, loaded)

    # Shadow-account projection at the guaranteed credit rate, run over the
    # FULL guarantee horizon (to `to_age`, not a fixed 20 years) — the
    # no-lapse guarantee's shadow-account test runs for as long as the
    # guarantee itself does. Mortality is NOT capped at an arbitrary
    # attained age; q_x() already clamps correctly to each sex table's own
    # terminal age, so letting it run the full horizon doesn't understate
    # COI at the older durations this guarantee actually covers.
    # `annual` is already the annual premium — dividing by modal_f would
    # inflate the account-value input ~11.5x for monthly payers.
    premium_net = annual
    horizon_years = max(to_age - ctx.age, 1)
    av = 0.0
    shadow_account_negative = False
    first_negative_year: int | None = None
    projection: dict[str, float] = {}
    checkpoint_years = {5, 10, 20, horizon_years}
    for year in range(1, horizon_years + 1):
        coi = ctx.face * q_x(ctx.age + year, ctx.sex_key, ctx.smoker) * COI_LOADING
        raw = (av + premium_net - coi - ADMIN_FEE_ANNUAL) * (1.0 + 0.02)
        if raw < 0 and not shadow_account_negative:
            shadow_account_negative = True
            first_negative_year = year
        av = max(raw, 0.0)
        if year in checkpoint_years:
            projection[f"av_year_{year}"] = round(av, 2)

    if shadow_account_negative:
        outcome.add_condition(
            f"Shadow-account funding test fails in policy year {first_negative_year} at the guaranteed credit rate — "
            f"the quoted premium may be insufficient to keep the no-lapse guarantee in force to age {to_age}; "
            "re-illustrate at a higher premium or shorter guarantee period before issue"
        )

    outcome.base_premium = round(formula.gross_premium * NO_LAPSE_LOAD, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="lifetime_basis_gross", amount=round(formula.gross_premium, 2), basis=f"A_x/ä_x pay-to-{PAY_TO_AGE} @ {interest:.0%}"),
        RateComponent(name="no_lapse_guarantee_load", amount=round(NO_LAPSE_LOAD - 1.0, 4), basis=f"secondary guarantee to age {to_age}"),
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
            "guarantee_to_age": to_age,
            "coi_loading": COI_LOADING,
            "annual_coi_estimate": coi_annual,
            "admin_fee_annual": ADMIN_FEE_ANNUAL,
            "account_value_projection_guaranteed_basis": projection,
            "shadow_account_funding_adequate": not shadow_account_negative,
            "shadow_account_first_negative_year": first_negative_year,
            "state_rules_applied": state_rules,
            "exam_required": bool(state_rules["paramed_exam_required"]),
        }
    )

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False

    # Pilot has no filed universal life rates — illustrative only.
    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason(f"universal life priced on actuarial equivalence — illustrative only, no {filing}-filed UL rates")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_gul(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="universal_life")
