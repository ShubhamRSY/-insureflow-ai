"""Hospital Indemnity — dedicated logic path.

Fixed dollar-per-day-of-hospitalization payout — a genuinely different
structure from Standard/Super Gap's deductible-based reimbursement. This is
a real, common standalone US supplemental category (Aflac-style hospital
cash): the cash pays out regardless of the base plan's deductible or
coinsurance, and the amount owed has nothing to do with actual billed
charges — it is a fixed multiple of the elected daily benefit times nights
in hospital.
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
    nearest_banded_key,
    policy_fee,
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "hospital_indemnity"
LOGIC_PATH = "insureflow.health.lobs.topup.hospital_indemnity"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Pays a fixed daily cash benefit for each night of covered hospitalization — not a reimbursement of actual billed charges"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 0
MAX_ISSUE_AGE = 75


def underwrite_hospital_indemnity(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="hospital_cash")

    outcome = LobOutcome(product_label="Hospital Indemnity")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Hospital indemnity issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Daily benefit amount missing — cannot rate without an elected daily cash benefit")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    hi_manual = (ctx.manual or {}).get("hospital_indemnity") or {}
    base_rate_per_100 = float(hi_manual.get("base_annual_rate_per_100_daily_benefit", 180.0))
    age_table = hi_manual.get("age_factor_by_band") or {}
    age_f = float(age_table.get(nearest_banded_key(age_table, ctx.age), 1.0)) if age_table else 1.0
    area_f = area_relativity(ctx)

    annual_before_area = (ctx.benefit_amount / 100.0) * base_rate_per_100 * age_f
    annual = round(annual_before_area * area_f + policy_fee(ctx), 2)

    outcome.base_premium = round(annual_before_area, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="daily_benefit_rate_per_100", amount=base_rate_per_100, basis="annual"),
        RateComponent(name="age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "daily_benefit_amount": ctx.benefit_amount,
            "payout_structure": "fixed_daily_cash",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="hospital_indemnity")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_hospital_indemnity(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="topup")
