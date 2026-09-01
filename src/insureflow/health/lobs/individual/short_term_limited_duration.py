"""Short-Term Limited Duration Insurance (STLDI) — dedicated logic path.

The one genuinely medically-underwritten individual health product left in
the US market: not ACA-compliant (no Essential Health Benefits mandate, no
guaranteed issue, pre-existing conditions can be permanently excluded),
federal maximum initial certificate term of 364 days. Several states ban or
effectively bar it outright — a real, material state split unlike every
ACA-guaranteed-issue product in this package, where state variation is only
ever a matter of degree (free-look days, mandated benefits), never
availability itself.
"""

from __future__ import annotations

from typing import Any

from insureflow.health.lobs.base import (
    HealthProductContext,
    LobOutcome,
    age_band_factor,
    apply_state_filing_gate,
    area_relativity,
    finish_quote,
    merge_state_rules,
    policy_fee,
    tobacco_surcharge,
)
from insureflow.health.lobs.state_law import stldi_available
from insureflow.rating.models import RateComponent

PRODUCT_ID = "short_term_limited_duration"
LOGIC_PATH = "insureflow.health.lobs.individual.short_term_limited_duration"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": [
        "Not ACA-compliant — no Essential Health Benefits guarantee, no ban on pre-existing-condition exclusions",
        "Federal maximum initial certificate term is 364 days",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "NY": {"free_look_days": 30},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 64


def underwrite_stldi(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="individual_comprehensive")

    outcome = LobOutcome(product_label="Short-Term Limited Duration Insurance")

    if not stldi_available(ctx.issue_state):
        outcome.eligible = False
        outcome.add_reason(f"{ctx.issue_state} bans or does not permit short-term limited duration plans")
    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"STLDI issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE} (65+ is Medicare-eligible)")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition("Any condition disclosed on the medical questionnaire may be permanently excluded from coverage, not merely waited out")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    discount_f = float(manual.get("stldi_medical_underwriting_discount", 0.75))

    monthly = silver_base * age_f * tobacco_f * area_f * discount_f
    annual = round(monthly * 12.0 + policy_fee(ctx), 2)

    outcome.base_premium = round(silver_base * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="medical_underwriting_discount", amount=discount_f, basis="non-ACA medically underwritten pool"),
    ]
    outcome.metadata.update(
        {
            "monthly_premium": round(monthly, 2),
            "aca_compliant": False,
            "guaranteed_issue": False,
            "state_rules_applied": state_rules,
            "exam_required": True,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="short_term_limited_duration")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_stldi(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="individual")
