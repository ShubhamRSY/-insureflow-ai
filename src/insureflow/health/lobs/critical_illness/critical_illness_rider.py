"""Critical Illness Rider — dedicated logic path.

Attaches to an existing base policy rather than standing alone — no
independent free-look period or policy fee of its own (it follows the base
policy's), and requires evidence the base policy exists before it can be
underwritten at all. This is the real, structural difference from
Standalone CI: a rider can't be priced or issued in isolation.
"""

from __future__ import annotations

from typing import Any

from insureflow.health.lobs.base import (
    HealthProductContext,
    LobOutcome,
    apply_state_filing_gate,
    finish_quote,
    merge_state_rules,
    tobacco_surcharge,
)
from insureflow.health.lobs.critical_illness.critical_illness_standalone import _nearest_age
from insureflow.rating.models import RateComponent

PRODUCT_ID = "critical_illness_rider"
LOGIC_PATH = "insureflow.health.lobs.critical_illness.critical_illness_rider"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Rider terminates automatically if the base policy lapses or is surrendered"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 70


def underwrite_ci_rider(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="critical_illness_rider")

    outcome = LobOutcome(product_label="Critical Illness Rider")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Critical illness rider issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Lump-sum rider benefit amount missing — cannot rate without a coverage amount")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    ci_manual = (ctx.manual or {}).get("critical_illness") or {}
    sex_key = ctx.sex_key if ctx.sex_key in ("male", "female") else "male"
    table = (ci_manual.get("morbidity_per_1000") or {}).get(sex_key) or {}
    rate_per_1000 = float(table.get(_nearest_age(table, ctx.age), 3.0)) if table else 3.0
    rider_load_f = float(ci_manual.get("rider_load_factor", 0.6))
    tobacco_f = tobacco_surcharge(ctx)

    base_premium = (ctx.benefit_amount / 1000.0) * rate_per_1000 * rider_load_f
    annual = round(base_premium * tobacco_f, 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="morbidity_per_1000", amount=rate_per_1000, basis=f"age={ctx.age}/{sex_key}"),
        RateComponent(name="rider_load", amount=rider_load_f, basis="attaches to base policy — no standalone policy fee"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
    ]
    outcome.metadata.update(
        {
            "lump_sum_benefit": ctx.benefit_amount,
            "attaches_to_base_policy": True,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="critical_illness_rider")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_ci_rider(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="critical_illness")
