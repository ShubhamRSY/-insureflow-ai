"""HSA-Qualified High-Deductible Health Plan (HDHP) — dedicated logic path.

Still an ACA-guaranteed-issue plan (same underwriting posture as the base
individual/family products) — the distinguishing feature is entirely on the
plan-design side: the deductible must meet the IRS minimum for the plan to
be HSA-eligible at all. ``ctx.benefit_amount`` carries the applicant's
chosen annual deductible; below the IRS floor the plan can still be issued,
it simply is not HSA-qualified, which is a real, checkable distinction this
product's whole reason for existing turns on.
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
    nearest_banded_key,
    policy_fee,
    reconcile_for_aca_guaranteed_issue,
    tobacco_surcharge,
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "hdhp_hsa_qualified"
LOGIC_PATH = "insureflow.health.lobs.individual.hdhp_hsa_qualified"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["HSA contribution eligibility requires no other disqualifying coverage — confirm with a tax advisor"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 0
MAX_ISSUE_AGE = 64
MIN_HDHP_DEDUCTIBLE_SELF = 1650.0
MAX_HDHP_OUT_OF_POCKET_SELF = 8300.0


def underwrite_hdhp(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="individual_basic")
    reconcile_for_aca_guaranteed_issue(ctx.uw)

    outcome = LobOutcome(product_label="HSA-Qualified HDHP")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"HDHP issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE} (65+ is Medicare-eligible)")

    deductible = ctx.benefit_amount or MIN_HDHP_DEDUCTIBLE_SELF
    hsa_qualified = MIN_HDHP_DEDUCTIBLE_SELF <= deductible <= MAX_HDHP_OUT_OF_POCKET_SELF
    if deductible < MIN_HDHP_DEDUCTIBLE_SELF:
        outcome.add_condition(f"Chosen deductible ${deductible:,.0f} is below the IRS HSA-qualifying minimum of ${MIN_HDHP_DEDUCTIBLE_SELF:,.0f} — plan can issue but will NOT be HSA-eligible")
    elif deductible > MAX_HDHP_OUT_OF_POCKET_SELF:
        outcome.add_condition(f"Chosen deductible ${deductible:,.0f} exceeds the IRS maximum out-of-pocket of ${MAX_HDHP_OUT_OF_POCKET_SELF:,.0f} — plan can issue but will NOT be HSA-eligible")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    for mandate in state_rules.get("mandated_benefits") or []:
        outcome.add_condition(f"State-mandated benefit: {mandate}")

    manual = (ctx.manual or {}).get("individual") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    bronze_f = float((manual.get("metal_tier_av_factors") or {}).get("bronze", 0.82))
    age_f = age_band_factor(ctx)
    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)
    credit_table = manual.get("hdhp_deductible_credit_factors") or {}
    credit_f = float(credit_table.get(nearest_banded_key(credit_table, deductible), 1.0)) if credit_table else 1.0

    monthly = silver_base * bronze_f * age_f * tobacco_f * area_f * credit_f
    annual = round(monthly * 12.0 + policy_fee(ctx), 2)

    outcome.base_premium = round(silver_base * bronze_f * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="deductible_credit", amount=credit_f, basis=f"deductible=${deductible:,.0f}"),
    ]
    outcome.metadata.update(
        {
            "chosen_deductible": deductible,
            "hsa_qualified": hsa_qualified,
            "monthly_premium": round(monthly, 2),
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="hdhp_hsa_qualified")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_hdhp(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="individual")
