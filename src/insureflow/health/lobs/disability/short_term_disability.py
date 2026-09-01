"""Short-Term Disability Income — dedicated logic path.

Weekly benefit, short elimination period, benefit period typically capped
at 2 years. In CA/NY/NJ/RI/HI (+PR) a mandatory state disability insurance
(SDI) program already exists — a private STD policy issued there has to
coordinate with (usually offset by) the state benefit, a real compliance
fact this path surfaces, not a generic disclosure.
"""

from __future__ import annotations

from typing import Any

from insureflow.health.lobs.base import (
    HealthProductContext,
    LobOutcome,
    apply_state_filing_gate,
    area_relativity,
    finish_quote,
    merge_state_rules,
    policy_fee,
)
from insureflow.health.lobs.state_law import is_sdi_state
from insureflow.rating.models import RateComponent

# Internal reuse — same occupation-class classifier used across PA/disability.
from insureflow.underwriting.health_uw import _occupation_class

PRODUCT_ID = "short_term_disability"
LOGIC_PATH = "insureflow.health.lobs.disability.short_term_disability"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Benefit is income replacement, not a lump sum — verify the weekly benefit amount against actual earnings"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 64
DEFAULT_ELIMINATION_DAYS = 14
DEFAULT_BENEFIT_PERIOD = "2_year"


def underwrite_std(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="disability_ttd")

    outcome = LobOutcome(product_label="Short-Term Disability Income")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Short-term disability issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Weekly benefit amount missing — cannot rate short-term disability without a coverage amount")
    if ctx.income and ctx.benefit_amount and (ctx.benefit_amount * 52.0) > ctx.income * 0.7:
        outcome.add_condition("Weekly benefit annualized exceeds 70% of documented income — most STD filings cap replacement at 60-70% of pre-disability earnings")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    if is_sdi_state(ctx.issue_state):
        outcome.add_condition(f"{ctx.issue_state} runs a mandatory state disability insurance (SDI) program — this policy's benefit must be coordinated with (typically offset by) the state benefit")

    occ_class = _occupation_class(ctx.blob) or "II"

    disability_manual = (ctx.manual or {}).get("disability") or {}
    rate_per_10 = float(disability_manual.get("std_base_rate_per_10_weekly_benefit", 0.11))
    occ_f = float((disability_manual.get("occupation_class_factors") or {}).get(occ_class, 1.0))
    area_f = area_relativity(ctx)

    base_premium = (ctx.benefit_amount / 10.0) * rate_per_10 * 52.0
    annual = round(base_premium * occ_f * area_f + policy_fee(ctx), 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="std_rate_per_10_weekly", amount=rate_per_10, basis="weekly benefit"),
        RateComponent(name="occupation_class", amount=occ_f, basis=f"Class {occ_class}"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "weekly_benefit": ctx.benefit_amount,
            "occupation_class": occ_class,
            "sdi_coordination_required": is_sdi_state(ctx.issue_state),
            "elimination_period_days": DEFAULT_ELIMINATION_DAYS,
            "benefit_period": DEFAULT_BENEFIT_PERIOD,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="short_term_disability")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_std(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="disability")
