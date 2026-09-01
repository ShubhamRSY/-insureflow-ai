"""Multi-Stage Critical Illness — dedicated logic path.

Pays a graduated percentage of the benefit at increasing severity stages
(e.g. 25% at early-stage diagnosis, 50% at intermediate, the remaining
balance at advanced/late-stage) instead of one lump sum on first diagnosis
— a real, structurally distinct payout design sold in the US CI market
(vs. Standalone CI's single 100%-on-diagnosis payout). Priced off the same
morbidity table as the other CI products, scaled down since early payouts
happen more often but for less money each time.
"""

from __future__ import annotations

from typing import Any

from insureflow.health.lobs.base import (
    HealthProductContext,
    LobOutcome,
    apply_state_filing_gate,
    finish_quote,
    merge_state_rules,
    policy_fee,
    tobacco_surcharge,
)
from insureflow.health.lobs.critical_illness.critical_illness_standalone import _nearest_age
from insureflow.rating.models import RateComponent

PRODUCT_ID = "critical_illness_multistage"
LOGIC_PATH = "insureflow.health.lobs.critical_illness.critical_illness_multistage"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Pays a graduated percentage of the benefit at each qualifying stage — full benefit is not payable on first (early-stage) diagnosis"],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "NY": {"free_look_days": 30},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 70


def underwrite_ci_multistage(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="critical_illness_multistage")

    outcome = LobOutcome(product_label="Multi-Stage Critical Illness")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Multi-stage CI issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Lump-sum benefit amount missing — cannot rate without a coverage amount")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    ci_manual = (ctx.manual or {}).get("critical_illness") or {}
    sex_key = ctx.sex_key if ctx.sex_key in ("male", "female") else "male"
    table = (ci_manual.get("morbidity_per_1000") or {}).get(sex_key) or {}
    rate_per_1000 = float(table.get(_nearest_age(table, ctx.age), 3.0)) if table else 3.0
    stage_factors = ci_manual.get("multistage_payout_factors") or {}
    blended_stage_f = sum(float(v) for v in stage_factors.values()) / len(stage_factors) if stage_factors else 0.583

    tobacco_f = tobacco_surcharge(ctx)

    base_premium = (ctx.benefit_amount / 1000.0) * rate_per_1000 * blended_stage_f
    annual = round(base_premium * tobacco_f + policy_fee(ctx), 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="morbidity_per_1000", amount=rate_per_1000, basis=f"age={ctx.age}/{sex_key}"),
        RateComponent(name="blended_stage_factor", amount=round(blended_stage_f, 4), basis="graduated payout — cheaper than 100%-on-diagnosis"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
    ]
    outcome.metadata.update(
        {
            "lump_sum_benefit": ctx.benefit_amount,
            "payout_structure": "multistage",
            "stage_factors": stage_factors,
            "state_rules_applied": state_rules,
            "exam_required": True,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="critical_illness_multistage")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_ci_multistage(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="critical_illness")
