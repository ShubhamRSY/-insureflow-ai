"""ULIP Type II — dedicated logic path (LOB 5).

Coverage: Type II death benefit = sum assured PLUS fund value. The insurer
pays both on death, so the COI basis grows with the fund and an explicit
additional mortality load applies versus Type I.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    finish_quote,
    merge_state_rules,
)
from insureflow.life.mortality import q_x
from insureflow.rating.models import RateComponent

PRODUCT_ID = "ulip_type_ii"
LOGIC_PATH = "insureflow.life.lobs.ulip.ulip_type_ii"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 15,
    "lock_in_years": 5,
    "sa_multiple_lt45": 10.0,
    "sa_multiple_ge45": 7.0,
    "assumed_net_return": 0.08,
    "fmc_pct": 0.0135,
    "allocation_charge_pct": 0.05,
    "type_ii_extra_mortality_load": 1.15,
    "disclosures": [
        "Type II: beneficiaries receive sum assured PLUS fund value — richer cover, higher mortality charges",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 65
MORTALITY_LOADING = 1.25
TERM_YEARS = 15


def underwrite_ulip_type_ii(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Type II ULIP (SA + Fund Value)")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Type II ULIP issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    extra_load = float(state_rules["type_ii_extra_mortality_load"])
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

    sa = annual_premium * multiple
    # Type II COI basis ≈ SA plus half the expected average fund (explicit
    # conservative proxy because the fund component is paid IN ADDITION).
    avg_fund_proxy = fund_value / 2.0
    mort_y1_type_i_basis = round(sa * q_x(ctx.age, ctx.sex_key, ctx.smoker) * MORTALITY_LOADING, 2)
    mort_y1 = round((sa + avg_fund_proxy) * q_x(ctx.age, ctx.sex_key, ctx.smoker) * MORTALITY_LOADING * extra_load, 2)

    outcome.base_premium = annual_premium
    outcome.annual_premium = annual_premium
    outcome.components = [
        RateComponent(name="annual_premium", amount=annual_premium, basis=f"sum assured ${ctx.face:,.0f} ÷ {multiple:.0f}×"),
        RateComponent(name="allocation_charge", amount=alloc, basis="year-1 entry charge"),
        RateComponent(name="mortality_basis_sa_plus_fund", amount=round(mort_y1 - mort_y1_type_i_basis, 2), basis=f"COI on SA+fund vs SA-only, {extra_load:.2f}× extra load"),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "Type II ULIP — DB = SA + FV",
                "assumed_net_return": r,
                "term_years": n,
            },
            "annual_premium": annual_premium,
            "sum_assured": round(sa, 2),
            "fund_value_projection": fund_value,
            "db_formula": "SA + FV",
            "mortality_charge_year1": mort_y1,
            "mortality_charge_year1_type_i_equivalent": mort_y1_type_i_basis,
            "type_ii_extra_mortality_load": extra_load,
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
    outcome = underwrite_ulip_type_ii(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="ulip", apply_minimum_premium=False)
