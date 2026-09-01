"""ACA Catastrophic Plan — dedicated logic path.

Still guaranteed issue and ACA-compliant — the distinguishing feature is
purely eligibility: catastrophic plans are restricted to applicants under
30, or anyone with a documented affordability/hardship exemption. Priced
below Bronze — high deductible, essentially major-medical-only cover for a
population the ACA itself expects to be lower-utilization.
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
    reconcile_for_aca_guaranteed_issue,
    tobacco_surcharge,
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "catastrophic_plan"
LOGIC_PATH = "insureflow.health.lobs.individual.catastrophic_plan"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Catastrophic plans are not premium-tax-credit eligible even on-exchange"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MAX_ISSUE_AGE_WITHOUT_EXEMPTION = 30


def _has_hardship_exemption(blob: str) -> bool:
    return any(k in blob for k in ("hardship exemption", "affordability exemption", "hardship certificate"))


def underwrite_catastrophic(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="individual_basic")
    reconcile_for_aca_guaranteed_issue(ctx.uw)

    outcome = LobOutcome(product_label="ACA Catastrophic Plan")

    exempt = _has_hardship_exemption(ctx.blob)
    if ctx.age >= MAX_ISSUE_AGE_WITHOUT_EXEMPTION and not exempt:
        outcome.eligible = False
        outcome.add_reason(
            f"Catastrophic plans require age under {MAX_ISSUE_AGE_WITHOUT_EXEMPTION} or a documented hardship/affordability exemption — applicant is {ctx.age} with no exemption on file"
        )

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    if exempt:
        outcome.add_condition("Hardship/affordability exemption on file — eligible regardless of age")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    bronze_f = float((manual.get("metal_tier_av_factors") or {}).get("bronze", 0.82))
    catastrophic_f = float(manual.get("catastrophic_discount_factor", 0.85))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)

    monthly = silver_base * bronze_f * catastrophic_f * age_f * tobacco_f * area_f
    annual = round(monthly * 12.0 + policy_fee(ctx), 2)

    outcome.base_premium = round(silver_base * bronze_f * catastrophic_f * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="catastrophic_discount", amount=catastrophic_f, basis="below Bronze"),
    ]
    outcome.metadata.update(
        {
            "monthly_premium": round(monthly, 2),
            "hardship_exemption": exempt,
            "premium_tax_credit_eligible": False,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="catastrophic_plan")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_catastrophic(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="individual")
