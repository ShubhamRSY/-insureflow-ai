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
    apply_state_filing_gate,
    band_factor,
    finish_quote,
    medical_class_factor,
    merge_state_rules,
    state_relativity,
)
from insureflow.life.whole_life_formulas import compute_full_whole_life_quote
from insureflow.rating.models import RateComponent
from insureflow.underwriting.life_product import is_filed_gul_product

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
GUARANTEED_CREDIT = 0.02


def _first_negative_year(face: float, age: int, sex: str, smoker: bool, annual: float, horizon: int) -> int | None:
    from insureflow.life.mortality import q_x

    av = 0.0
    for year in range(1, horizon + 1):
        coi = face * q_x(age + year, sex, smoker) * COI_LOADING
        raw = (av + annual - coi - ADMIN_FEE_ANNUAL) * (1.0 + GUARANTEED_CREDIT)
        if raw < 0:
            return year
        av = raw
    return None


def _cents_that_hold(face: float, age: int, sex: str, smoker: bool, premium: float, horizon: int) -> tuple[float, bool]:
    """Round to cents and step up until the shadow account holds.

    The binary-search result can round down through the boundary and go
    negative in the last guarantee year.
    """
    premium = round(max(premium, 0.0), 2)
    for _ in range(500):
        if _first_negative_year(face, age, sex, smoker, premium, horizon) is None:
            return premium, True
        premium = round(premium + 0.01, 2)
    return premium, False


def _solve_no_lapse_premium(face: float, age: int, sex: str, smoker: bool, seed: float, horizon: int) -> tuple[float, bool]:
    """Level premium that keeps the guaranteed-credit shadow account non-negative.

    # ponytail: binary search, closed form if this path is hot.
    """
    if _first_negative_year(face, age, sex, smoker, seed, horizon) is None:
        return _cents_that_hold(face, age, sex, smoker, seed, horizon)
    hi = max(seed, 1.0)
    ceiling = max(face, hi)
    while _first_negative_year(face, age, sex, smoker, hi, horizon) is not None and hi < ceiling:
        hi = min(hi * 2.0, ceiling)
    if _first_negative_year(face, age, sex, smoker, hi, horizon) is not None:
        return round(hi, 2), False
    lo = 0.0
    for _ in range(48):
        mid = (lo + hi) / 2.0
        if _first_negative_year(face, age, sex, smoker, mid, horizon) is None:
            hi = mid
        else:
            lo = mid
    return _cents_that_hold(face, age, sex, smoker, hi, horizon)


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
    seed = add_common_loads(ctx, loaded)
    horizon_years = max(to_age - ctx.age, 1)
    annual, funded = _solve_no_lapse_premium(ctx.face, ctx.age, ctx.sex_key, ctx.smoker, seed, horizon_years)
    first_negative_year = _first_negative_year(ctx.face, ctx.age, ctx.sex_key, ctx.smoker, annual, horizon_years)
    funded = funded and first_negative_year is None

    av = 0.0
    projection: dict[str, float] = {}
    checkpoint_years = {5, 10, 20, horizon_years}
    for year in range(1, horizon_years + 1):
        coi = ctx.face * q_x(ctx.age + year, ctx.sex_key, ctx.smoker) * COI_LOADING
        credited = (av + annual - coi - ADMIN_FEE_ANNUAL) * (1.0 + GUARANTEED_CREDIT)
        av = max(credited, 0.0)
        if year in checkpoint_years:
            projection[f"av_year_{year}"] = round(av, 2)

    if not funded:
        outcome.eligible = False
        outcome.add_reason(f"No premium at or below the face amount keeps the no-lapse guarantee funded to age {to_age} at the {GUARANTEED_CREDIT:.0%} credit")

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
            "shadow_account_funding_adequate": funded and first_negative_year is None,
            "shadow_account_first_negative_year": first_negative_year,
            "no_lapse_premium_solved": funded and annual > seed + 0.01,
            "formula_premium_before_solve": round(seed, 2),
            "state_rules_applied": state_rules,
            "exam_required": bool(state_rules["paramed_exam_required"]),
        }
    )

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    income = getattr(ctx.financial, "income", 0.0) or 0.0
    if income > 0 and annual > income * 0.35:
        outcome.eligible = False
        outcome.add_reason(f"No-lapse premium ${annual:,.0f} exceeds 35% of documented income ${income:,.0f}")

    filed = is_filed_gul_product(PRODUCT_ID)
    apply_state_filing_gate(ctx, outcome, filed_for_state=filed, product_family="guaranteed_universal_life")
    if filed and outcome.eligible:
        raw = (ctx.manual or {}).get("gul_filing")
        filing = raw if isinstance(raw, dict) else {}
        outcome.metadata["filed_gul"] = True
        if filing.get("filing_id"):
            outcome.metadata["filing_id"] = filing["filing_id"]
        if filing.get("serff_tracking"):
            outcome.metadata["serff_tracking"] = filing["serff_tracking"]
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_gul(ctx)
    filed = is_filed_gul_product(PRODUCT_ID)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="universal_life",
        rating_engine="life_filing" if filed else "life_whole_life_actuarial",
    )
