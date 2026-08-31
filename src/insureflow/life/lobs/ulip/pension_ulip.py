"""Pension / Retirement ULIP — dedicated logic path (LOB 5).

Coverage: Retirement Unit Account. Accumulation toward a vesting age with a
MANDATORY minimum annuitization share — this is a retirement vehicle, not a
lump-sum savings wrapper. Death benefit during accumulation = fund value or
SA multiple, whichever is higher.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    disclosures_acknowledged,
    finish_quote,
    merge_state_rules,
    ulip_suitability_conditions,
)
from insureflow.life.mortality import q_x
from insureflow.rating.models import RateComponent

PRODUCT_ID = "pension_ulip"
LOGIC_PATH = "insureflow.life.lobs.ulip.pension_ulip"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 15,
    "lock_in_years": 5,
    "min_annuitization_pct": 66.7,
    "default_vesting_age": 60,
    "assumed_net_return": 0.075,
    "fmc_pct": 0.0125,
    "allocation_charge_pct": 0.04,
    "sa_multiple_lt45": 10.0,
    "sa_multiple_ge45": 7.0,
    "disclosures": [
        "At least 2/3 of the corpus MUST be annuitized at vesting — lump withdrawal is capped",
        "Tax treatment of pension annuity income applies at vesting — consult a tax adviser",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
}

MIN_ISSUE_AGE = 18
MAX_ENTRY_AGE = 55
MAX_VESTING_AGE = 75
MORTALITY_LOADING = 1.25


def underwrite_pension_ulip(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Pension / Retirement ULIP")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ENTRY_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Pension ULIP entry age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ENTRY_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    # MAX_VESTING_AGE is a hard cap on top of the state rule's default —
    # a longer accumulation than the platform allows for a pension vehicle.
    vesting_age = min(int(state_rules["default_vesting_age"]), MAX_VESTING_AGE)
    if int(state_rules["default_vesting_age"]) > MAX_VESTING_AGE:
        outcome.add_condition(f"Vesting age capped at platform maximum {MAX_VESTING_AGE} (state default was {state_rules['default_vesting_age']})")
    years_to_vesting = max(vesting_age - ctx.age, 5)
    annual_premium = max(round(ctx.face / 10.0, 2), 600.0) if ctx.face else 2400.0

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    outcome.add_condition(f"Corpus vests at age {vesting_age} ({years_to_vesting} years)")
    outcome.add_condition(f"Minimum {state_rules['min_annuitization_pct']}% of corpus must be annuitized at vesting")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    alloc = float(state_rules["allocation_charge_pct"])
    fmc = float(state_rules["fmc_pct"])
    r = float(state_rules["assumed_net_return"])
    net_r = 1.0 + r - fmc
    n = years_to_vesting
    fund_at_vesting = round(annual_premium * (1.0 - alloc) * ((net_r**n - 1) / (net_r - 1)), 2)
    annuitizable = round(fund_at_vesting * float(state_rules["min_annuitization_pct"]) / 100.0, 2)

    # Death-during-accumulation benefit — the disclosed "higher of SA
    # multiple or fund value" needs an actual sum assured and mortality
    # charge, same pattern as ulip_type_i.py, not just a description string.
    sa_multiple = float(state_rules["sa_multiple_lt45"] if ctx.age < 45 else state_rules["sa_multiple_ge45"])
    sum_assured = round(annual_premium * sa_multiple, 2)
    mort_y1 = round(sum_assured * q_x(ctx.age, ctx.sex_key, ctx.smoker) * MORTALITY_LOADING, 2)

    # Suitability screening: premium-to-income and disclosure evidence are
    # real, submission-grounded checks; risk-appetite/fund-allocation has
    # no data source here (no investor questionnaire on the extraction
    # pipeline), so it's disclosed as unverified.
    income = getattr(ctx.factors, "income", 0.0)
    if income and annual_premium / income > 0.15:
        outcome.add_condition(f"CRITICAL: Premium-to-income {annual_premium / income:.1%} exceeds 15% — ULIP unsuitable, client cannot absorb investment losses")
    elif income and annual_premium / income > 0.12:
        outcome.add_condition(f"Premium-to-income {annual_premium / income:.1%} exceeds 12% guideline for ULIPs")
    if not disclosures_acknowledged(ctx):
        outcome.add_condition("Investor-profile disclosure not confirmed on file — signed suitability questionnaire required before bind")
    for _c in ulip_suitability_conditions(ctx):
        outcome.add_condition(_c)

    outcome.base_premium = annual_premium
    outcome.annual_premium = annual_premium
    outcome.components = [
        RateComponent(name="annual_contribution", amount=annual_premium, basis=f"to vesting age {vesting_age}"),
        RateComponent(name="allocation_charge", amount=alloc, basis="per-contribution entry charge"),
        RateComponent(name="fund_mgmt_charge", amount=fmc, basis="annual % of pension fund"),
        RateComponent(name="mortality_charge_y1", amount=mort_y1, basis=f"{ctx.age}/{ctx.sex_key} q-based on SA, {MORTALITY_LOADING:.2f}× loading"),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "pension ULIP accumulation to vesting",
                "assumed_net_return": r,
                "years_to_vesting": n,
            },
            "annual_premium": annual_premium,
            "vesting_age": vesting_age,
            "fund_value_at_vesting": fund_at_vesting,
            "minimum_annuitization_amount": annuitizable,
            "sum_assured": sum_assured,
            "mortality_charge_year1": mort_y1,
            "death_benefit_during_accumulation": "higher of SA or fund value",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason(f"ULIP unit account is market-linked — illustrative projection only, no {filing}-filed ULIP rates")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_pension_ulip(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="ulip", apply_minimum_premium=False)
