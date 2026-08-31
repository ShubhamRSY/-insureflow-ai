"""ULIP Type I — dedicated logic path (LOB 5).

Coverage: Type I death benefit = HIGHER of sum assured or fund value. Because
the insurer never pays more than the larger of the two, the mortality charge
basis stays at the nominal sum assured — cheaper than Type II.
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

PRODUCT_ID = "ulip_type_i"
LOGIC_PATH = "insureflow.life.lobs.ulip.ulip_type_i"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 15,
    "lock_in_years": 5,
    "sa_multiple_lt45": 10.0,
    "sa_multiple_ge45": 7.0,
    "assumed_net_return": 0.08,
    "fmc_pct": 0.0135,
    "allocation_charge_pct": 0.05,
    "disclosures": [
        "Type I: beneficiaries receive the HIGHER of sum assured or fund value — the two are never added",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 65
MORTALITY_LOADING = 1.25
TERM_YEARS = 15


def underwrite_ulip_type_i(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Type I ULIP (Higher of SA or Fund Value)")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Type I ULIP issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    multiple = float(state_rules["sa_multiple_lt45"] if ctx.age < 45 else state_rules["sa_multiple_ge45"])
    annual_premium = max(round(ctx.face / multiple, 2), 600.0)

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    outcome.add_condition(f"Units locked during the {state_rules['lock_in_years']}-year lock-in")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    alloc = float(state_rules["allocation_charge_pct"])
    fmc = float(state_rules["fmc_pct"])
    r = float(state_rules["assumed_net_return"])
    net_r = 1.0 + r - fmc
    n = TERM_YEARS
    fund_value = round(annual_premium * (1.0 - alloc) * ((net_r**n - 1) / (net_r - 1)), 2)

    # Type I COI basis = sum assured (the higher-of formula caps the exposure).
    mort_y1 = round(annual_premium * multiple * q_x(ctx.age, ctx.sex_key, ctx.smoker) * MORTALITY_LOADING, 2)
    crossover_year: int | None = None
    fv = annual_premium * (1.0 - alloc)
    sa = annual_premium * multiple
    for year in range(2, n + 1):
        fv *= net_r
        if fv > sa and crossover_year is None:
            crossover_year = year
            break

    # Suitability screening: premium-to-income and disclosure evidence are
    # real, submission-grounded checks; risk-appetite/fund-allocation
    # screening has no data source here (no investor questionnaire on the
    # extraction pipeline), so it's disclosed as unverified rather than
    # silently skipped or faked with unfalsifiable defaults.
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
        RateComponent(name="annual_premium", amount=annual_premium, basis=f"sum assured ${ctx.face:,.0f} ÷ {multiple:.0f}×"),
        RateComponent(name="allocation_charge", amount=alloc, basis="year-1 entry charge"),
        RateComponent(name="mortality_basis_sa_only", amount=mort_y1, basis="higher-of formula keeps COI on nominal SA"),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "Type I ULIP — DB = max(SA, FV)",
                "assumed_net_return": r,
                "term_years": n,
            },
            "annual_premium": annual_premium,
            "sum_assured": round(sa, 2),
            "fund_value_projection": fund_value,
            "db_formula": "max(SA, FV)",
            "crossover_year_fv_exceeds_sa": crossover_year,
            "mortality_charge_year1": mort_y1,
            "lock_in_years": int(state_rules["lock_in_years"]),
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
    outcome = underwrite_ulip_type_i(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="ulip", apply_minimum_premium=False)
