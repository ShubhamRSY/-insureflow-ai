"""Child ULIP — dedicated logic path (LOB 5).

Coverage: Child Education/Marriage Unit Account. The PROPOSER (parent/legal
guardian) owns the policy and pays premiums; benefits vest in the child at
milestone ages. Waiver-of-premium on proposer death is built in — the plan
must survive the proposer.
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
from insureflow.rating.models import RateComponent

PRODUCT_ID = "child_ulip"
LOGIC_PATH = "insureflow.life.lobs.ulip.child_ulip"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 15,
    "lock_in_years": 5,
    "max_child_entry_age": 10,
    "max_proposer_age": 55,
    "milestone_ages": [18, 20, 22, 25],
    "assumed_net_return": 0.08,
    "fmc_pct": 0.0135,
    "allocation_charge_pct": 0.05,
    "wp_rider_load": 1.03,
    "disclosures": [
        "Waiver of premium on proposer death is included — contributions cease, plan continues",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
}

MIN_PROPOSER_AGE = 21


def underwrite_child_ulip(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Child ULIP")

    # ctx.age here is the PROPOSER's age; benefits vest in the child.
    if ctx.age < MIN_PROPOSER_AGE or ctx.age > int(DEFAULT_STATE_RULES["max_proposer_age"]):
        max_proposer = int(DEFAULT_STATE_RULES["max_proposer_age"])
        outcome.eligible = False
        outcome.add_reason(f"Child ULIP proposer age {ctx.age} outside {MIN_PROPOSER_AGE}-{max_proposer}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    wp_load = float(state_rules["wp_rider_load"])
    milestones = list(state_rules["milestone_ages"])
    annual_premium = max(round(ctx.face / 10.0, 2), 600.0) if ctx.face else 1800.0

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    outcome.add_condition(f"Benefits vest to the child at milestone ages {milestones}")
    outcome.add_condition("Proposer must be parent or LEGAL GUARDIAN — proof of guardianship required")
    max_child_age = int(state_rules["max_child_entry_age"])
    child_age = getattr(ctx.factors, "child_age", None)
    if child_age is not None:
        outcome.add_condition(f"Insured child's age ({child_age}) taken from submission — confirm against birth certificate before bind")
        if child_age > max_child_age:
            outcome.eligible = False
            outcome.add_reason(f"Insured child's age {child_age} exceeds the {max_child_age}-year entry maximum")
    else:
        outcome.add_condition(f"Insured child's age not captured on this submission — verify child's age is at or below the {max_child_age}-year entry maximum before bind")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    alloc = float(state_rules["allocation_charge_pct"])
    fmc = float(state_rules["fmc_pct"])
    r = float(state_rules["assumed_net_return"])
    net_r = 1.0 + r - fmc
    if child_age is not None:
        horizon = max(int(milestones[-1]) - child_age, 1)  # years until final milestone, from the real child age
    else:
        horizon = max(int(milestones[-1]), 15) - min(max(ctx.age - 30, 0), 5)  # years until final milestone (proposer assumed ~30 at child's birth)
    fund_at_maturity = round(annual_premium * (1.0 - alloc) * wp_load * ((net_r**horizon - 1) / (net_r - 1)), 2)

    # Suitability screening: premium-to-proposer-income and disclosure
    # evidence are real, submission-grounded checks; risk-appetite/fund
    # allocation has no data source here (no investor questionnaire on the
    # extraction pipeline), so it's disclosed as unverified.
    income = getattr(ctx.factors, "income", 0.0)
    if income and annual_premium / income > 0.15:
        outcome.add_condition(f"CRITICAL: Premium-to-income {annual_premium / income:.1%} exceeds 15% — ULIP unsuitable, proposer cannot absorb investment losses")
    elif income and annual_premium / income > 0.12:
        outcome.add_condition(f"Premium-to-income {annual_premium / income:.1%} exceeds 12% guideline for ULIPs")
    if not disclosures_acknowledged(ctx):
        outcome.add_condition("Investor-profile disclosure not confirmed on file — signed suitability questionnaire required before bind")
    for _c in ulip_suitability_conditions(ctx):
        outcome.add_condition(_c)

    outcome.base_premium = round(annual_premium * wp_load, 2)
    outcome.annual_premium = round(annual_premium * wp_load, 2)
    outcome.components = [
        RateComponent(name="annual_contribution", amount=annual_premium, basis="proposer-paid unit account"),
        RateComponent(name="waiver_of_premium_rider", amount=round(wp_load - 1.0, 4), basis="premiums waived on proposer death"),
        RateComponent(name="allocation_charge", amount=alloc, basis="per-contribution entry charge"),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "child ULIP accumulation to final milestone",
                "assumed_net_return": r,
                "horizon_years": horizon,
            },
            "annual_premium": round(annual_premium * wp_load, 2),
            "proposer_age": ctx.age,
            "child_age": child_age,
            "child_age_source": "submission" if child_age is not None else "not_captured",
            "milestone_ages": milestones,
            "fund_value_projection": fund_at_maturity,
            "waiver_of_premium_included": True,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason(f"ULIP unit account is market-linked — illustrative projection only, no {filing}-filed ULIP rates")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_child_ulip(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="ulip", apply_minimum_premium=False)
