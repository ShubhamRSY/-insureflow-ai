"""Regular Premium ULIP — dedicated logic path (LOB 5).

Coverage: Recurring-Premium Unit Account. Premium follows a statutory minimum
multiple rule (sum assured ≥ 10× annual premium under age 45, 7× from 45) and
suitability is underwritten on BOTH tracks — medical (mortality charge) and
investor profile (run_ulip_uw).
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
from insureflow.life.ulip_uw import run_ulip_uw
from insureflow.rating.models import RateComponent

PRODUCT_ID = "regular_premium_ulip"
LOGIC_PATH = "insureflow.life.lobs.ulip.regular_premium_ulip"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 15,
    "lock_in_years": 5,
    "sa_multiple_lt45": 10.0,
    "sa_multiple_ge45": 7.0,
    "assumed_net_return": 0.08,
    "fmc_pct": 0.0135,
    "allocation_charges": {"year_1": 0.08, "years_2_5": 0.04, "thereafter": 0.015},
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
TERM_YEARS = 15


def _avg_allocation(charges: dict[str, float]) -> float:
    return (charges["year_1"] + 4 * charges["years_2_5"] + (TERM_YEARS - 5) * charges["thereafter"]) / TERM_YEARS


def underwrite_rp_ulip(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Regular Premium ULIP")

    if ctx.age < MIN_ISSUE_AGE or ctx.age > MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"ULIP issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    multiple = float(state_rules["sa_multiple_lt45"] if ctx.age < 45 else state_rules["sa_multiple_ge45"])
    annual_premium = max(round(ctx.face / multiple, 2), 600.0)

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    outcome.add_condition(f"Units locked during the {state_rules['lock_in_years']}-year lock-in — discontinuance charge applies")
    outcome.add_condition(f"Sum assured {multiple:.0f}× annual premium (${annual_premium:,.0f}/yr → ${annual_premium * multiple:,.0f} cover)")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    charges = state_rules["allocation_charges"]
    avg_alloc = _avg_allocation({k: float(v) for k, v in charges.items()})
    fmc = float(state_rules["fmc_pct"])
    r = float(state_rules["assumed_net_return"])
    n = TERM_YEARS
    net_r = 1.0 + r - fmc
    fund_value = round(annual_premium * (1.0 - avg_alloc) * ((net_r**n - 1) / (net_r - 1)), 2)

    mort_y1 = round(annual_premium * multiple * q_x(ctx.age, ctx.sex_key, ctx.smoker) * MORTALITY_LOADING, 2)
    prot_pv = round(annual_premium * multiple * term_insurance_nsp(ctx.age, n, ctx.sex_key, ctx.smoker, 0.04), 2)

    # risk_appetite and the equity/debt/balanced fund split both come from
    # the submission's documented investor profile when present — real
    # investor-profile answers, not defaults — so the mismatch/allocation
    # checks below are genuine whenever that data exists. run_ulip_uw falls
    # back to its own moderate-fund defaults (60/30/10) only for whichever
    # piece isn't actually on file.
    disclosures_ok = disclosures_acknowledged(ctx)
    risk_tolerance = (getattr(ctx.factors, "risk_tolerance", "") or "").strip().lower()
    risk_tolerance_known = risk_tolerance in ("conservative", "moderate", "aggressive", "very_aggressive")
    equity_from_submission = getattr(ctx.factors, "equity_allocation_pct", None)
    debt_from_submission = getattr(ctx.factors, "debt_allocation_pct", None)
    balanced_from_submission = getattr(ctx.factors, "balanced_allocation_pct", None)
    if equity_from_submission is not None and debt_from_submission is not None and balanced_from_submission is not None:
        fund_split_documented = True
        equity_pct: float = float(equity_from_submission)
        debt_pct: float = float(debt_from_submission)
        balanced_pct: float = float(balanced_from_submission)
    else:
        fund_split_documented = False
        equity_pct, debt_pct, balanced_pct = 60.0, 30.0, 10.0
    uw = run_ulip_uw(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        face_amount=round(annual_premium * multiple, 2),
        annual_premium=annual_premium,
        income=getattr(ctx.factors, "income", 0.0),
        equity_pct=equity_pct,
        debt_pct=debt_pct,
        balanced_pct=balanced_pct,
        risk_appetite=risk_tolerance if risk_tolerance_known else "moderate",
        disclosures_complete=disclosures_ok,
    )
    if uw.decision == "DECLINE":
        outcome.eligible = False
        for finding in uw.findings:
            outcome.add_reason(f"ULIP suitability: {finding}")
    for finding in uw.findings:
        outcome.add_condition(f"ULIP suitability: {finding}")
    if not disclosures_ok:
        outcome.add_condition("Investor-profile disclosure not confirmed on file — signed suitability questionnaire required before bind")
    if risk_tolerance_known and fund_split_documented:
        outcome.add_condition(
            f"Risk-appetite and fund allocation screened against documented investor data (tolerance: {risk_tolerance}, equity {equity_pct:.0f}% / debt {debt_pct:.0f}% / balanced {balanced_pct:.0f}%)"
        )
    elif risk_tolerance_known:
        outcome.add_condition(f"Risk-appetite screened against documented investor risk tolerance ({risk_tolerance}); fund allocation still assumed at the product default — confirm actual fund split")
    elif fund_split_documented:
        outcome.add_condition(f"Fund allocation screened against documented split (equity {equity_pct:.0f}% / debt {debt_pct:.0f}% / balanced {balanced_pct:.0f}%); risk tolerance not on file")
    else:
        outcome.add_condition("Risk-appetite / fund-allocation screened against DEFAULT assumptions, not a verified questionnaire — confirm before relying on the suitability result above")

    income = getattr(ctx.factors, "income", 0.0)
    if income and annual_premium / income > 0.15:
        outcome.add_condition("Premium-to-income above 15% — affordability review required")

    outcome.base_premium = annual_premium
    outcome.annual_premium = annual_premium
    outcome.components = [
        RateComponent(name="annual_premium", amount=annual_premium, basis=f"sum assured ${ctx.face:,.0f} ÷ {multiple:.0f}× multiple"),
        RateComponent(
            name="avg_allocation_charge", amount=round(avg_alloc, 4), basis=f"yr1 {float(charges['year_1']):.0%}, yr2-5 {float(charges['years_2_5']):.0%}, then {float(charges['thereafter']):.1%}"
        ),
        RateComponent(name="fund_mgmt_charge", amount=fmc, basis="annual % of fund"),
        RateComponent(name="mortality_charge_y1", amount=mort_y1, basis=f"{ctx.age}/{ctx.sex_key} q-based, {MORTALITY_LOADING:.2f}× loading"),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "RP ULIP unit account",
                "assumed_net_return": r,
                "term_years": n,
                "protection_pv": prot_pv,
            },
            "annual_premium": annual_premium,
            "sum_assured": round(annual_premium * multiple, 2),
            "fund_value_projection": fund_value,
            "mortality_charge_year1": mort_y1,
            "suitability_uw": uw.to_metadata(),
            "risk_tolerance_source": "submission" if risk_tolerance_known else "assumed_default",
            "fund_allocation_source": "submission" if fund_split_documented else "assumed_default",
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
    outcome = underwrite_rp_ulip(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="ulip", apply_minimum_premium=False)
