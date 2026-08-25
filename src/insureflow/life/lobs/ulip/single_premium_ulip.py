"""Single Premium ULIP — dedicated logic path (LOB 5).

Coverage: Lump-Sum Unit Account. One contribution buys unit-linked exposure;
sum assured is a statutory multiple of the premium, not chosen freely. The
unit account carries market risk — only the death benefit multiple is
contractual.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.actuarial import term_insurance_nsp
from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    disclosures_acknowledged,
    finish_quote,
    merge_state_rules,
)
from insureflow.life.mortality import q_x
from insureflow.rating.models import RateComponent

PRODUCT_ID = "single_premium_ulip"
LOGIC_PATH = "insureflow.life.lobs.ulip.single_premium_ulip"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 15,
    "lock_in_years": 5,
    "min_premium": 10_000.0,
    "sa_multiple_lt45": 1.25,
    "sa_multiple_ge45": 1.10,
    "assumed_net_return": 0.08,
    "fmc_pct": 0.0135,
    "allocation_charge_pct": 0.02,
    "disclosures": [
        "Unit-linked: fund value fluctuates with markets — only the death benefit is contractual",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 65
MORTALITY_LOADING = 1.25
HORIZON_YEARS = 10


def underwrite_sp_ulip(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Single Premium ULIP")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"SP ULIP issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    # Single-premium "face" is treated as the CONTRIBUTION; sum assured follows
    # the statutory multiple for the attained age band.
    premium = max(ctx.face, float(state_rules["min_premium"]))
    multiple = float(state_rules["sa_multiple_lt45"] if ctx.age < 45 else state_rules["sa_multiple_ge45"])
    sum_assured = round(premium * multiple, 2)

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    outcome.add_condition(f"Units locked during the {state_rules['lock_in_years']}-year lock-in — discontinuance charge applies")
    outcome.add_condition(f"Sum assured fixed at {multiple:.2f}× single premium = ${sum_assured:,.0f}")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    alloc = float(state_rules["allocation_charge_pct"])
    fmc = float(state_rules["fmc_pct"])
    r = float(state_rules["assumed_net_return"])
    n = HORIZON_YEARS
    invested = premium * (1.0 - alloc)
    fund_value = round(invested * ((1.0 + r - fmc) ** n), 2)

    # Protection charge is deducted from units, not added to premium — show the
    # year-1 mortality charge and its lifetime PV as transparency items.
    mort_y1 = round(sum_assured * q_x(ctx.age, ctx.sex_key, ctx.smoker) * MORTALITY_LOADING, 2)
    prot_pv = round(sum_assured * term_insurance_nsp(ctx.age, n, ctx.sex_key, ctx.smoker, 0.04), 2)

    # Single-consideration product — the "premium" IS the lump sum, not a
    # recurring annual amount. Leaving both fields at the LobOutcome
    # default of 0.0 (as before) makes QuoteResult.adjusted_premium/
    # base_premium report $0.00 for a real lump-sum contribution.
    outcome.annual_premium = round(premium, 2)
    outcome.base_premium = round(premium, 2)

    # Suitability screening: disclosure evidence is a real, submission-
    # grounded check (premium-to-income doesn't apply — there's no
    # recurring premium to compare against income); risk-appetite/fund-
    # allocation has no data source here, so it's disclosed as unverified.
    if not disclosures_acknowledged(ctx):
        outcome.add_condition("Investor-profile disclosure not confirmed on file — signed suitability questionnaire required before bind")
    outcome.add_condition("Risk-appetite / fund-allocation suitability not screened — no investor questionnaire on file; confirm before relying on this illustration")

    outcome.components = [
        RateComponent(name="single_premium", amount=round(premium, 2), basis="lump-sum contribution"),
        RateComponent(name="allocation_charge", amount=alloc, basis=f"{alloc:.1%} deducted at entry"),
        RateComponent(name="fund_mgmt_charge", amount=fmc, basis="annual % of fund"),
        RateComponent(name="mortality_charge_y1", amount=mort_y1, basis=f"{ctx.age}/{ctx.sex_key} q-based, {MORTALITY_LOADING:.2f}× loading"),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "SP ULIP unit account",
                "assumed_net_return": r,
                "horizon_years": n,
                "protection_pv": prot_pv,
            },
            "single_premium": round(premium, 2),
            "sum_assured": sum_assured,
            "fund_value_projection": fund_value,
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
    outcome = underwrite_sp_ulip(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="ulip", apply_minimum_premium=False)
