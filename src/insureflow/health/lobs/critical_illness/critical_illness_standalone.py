"""Critical Illness (Standalone) — dedicated logic path.

A lump-sum indemnity payment on first diagnosis of a covered condition
(cancer, heart attack, stroke, kidney failure, etc.) — sold as a real,
distinct supplemental product in the US market (Aflac/Cigna-style), not
major medical. Priced per $1,000 of lump-sum benefit off a sex-specific
morbidity incidence table, the same shape as life's mortality_per_1000 —
sex is read from the submission, never hardcoded, unlike the flat health
rating engine this replaces.
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
    tobacco_surcharge,
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "critical_illness_standalone"
LOGIC_PATH = "insureflow.health.lobs.critical_illness.critical_illness_standalone"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["This is a lump-sum indemnity benefit, not major medical coverage — it does not replace a health plan"],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "NY": {"free_look_days": 30},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 70


def _nearest_age(table: dict[str, float], age: int) -> str:
    keys = sorted((int(k) for k in table))
    best = keys[0]
    for k in keys:
        if k <= age:
            best = k
    return str(best)


def underwrite_ci_standalone(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="critical_illness_standalone")

    outcome = LobOutcome(product_label="Critical Illness (Standalone)")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Critical illness issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Lump-sum benefit amount missing — cannot rate a critical illness plan without a coverage amount")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    ci_manual = (ctx.manual or {}).get("critical_illness") or {}
    sex_key = ctx.sex_key if ctx.sex_key in ("male", "female") else "male"
    table = (ci_manual.get("morbidity_per_1000") or {}).get(sex_key) or {}
    rate_per_1000 = float(table.get(_nearest_age(table, ctx.age), 3.0)) if table else 3.0

    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)

    base_premium = (ctx.benefit_amount / 1000.0) * rate_per_1000
    annual = round(base_premium * tobacco_f * area_f + policy_fee(ctx), 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="morbidity_per_1000", amount=rate_per_1000, basis=f"age={ctx.age}/{sex_key}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "lump_sum_benefit": ctx.benefit_amount,
            "morbidity_sex_source": "submission" if ctx.sex_key in ("male", "female") else "assumed_default",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="critical_illness_standalone")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_ci_standalone(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="critical_illness")
