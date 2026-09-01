"""Medigap High-Deductible Plan G — dedicated logic path.

CMS-standardized Medigap variant with the SAME guaranteed-issue timing
rules as standard Plan G (this mirrors medicare_supplement.py's own
guaranteed-issue/window handler-selection logic rather than reusing a
"top-up on a base policy" handler — HD Plan G IS the base Medigap policy
itself, not a rider sitting above one, so a base-policy-evidence gate would
be factually wrong here). The real, distinct feature is purely economic:
a much lower premium in exchange for paying the first ~$2,800/year in
Medicare cost-sharing out of pocket before the plan starts paying.
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
from insureflow.health.lobs.state_law import medigap_enrollment_rules
from insureflow.rating.models import RateComponent

PRODUCT_ID = "medigap_high_deductible_plan_g"
LOGIC_PATH = "insureflow.health.lobs.senior.medigap_high_deductible_plan_g"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 30,
    "disclosures": [
        "Medigap does not include prescription drug coverage — a separate Part D plan is required",
        "Coverage does not begin until the annual high deductible is met out of pocket",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 65


def underwrite_hd_plan_g(ctx: HealthProductContext, *, within_open_enrollment: bool) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    enrollment = medigap_enrollment_rules(ctx.issue_state)
    guaranteed_issue = within_open_enrollment or enrollment["continuous_guaranteed_issue"]

    ctx.uw = underwrite_health(ctx.bundle) if guaranteed_issue else underwrite_health(ctx.bundle, product_id="senior_standard")

    outcome = LobOutcome(product_label="Medigap High-Deductible Plan G")

    if ctx.age < MIN_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Medicare Supplement requires Medicare Part B enrollment — applicant age {ctx.age} is below the {MIN_ISSUE_AGE} minimum")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    if guaranteed_issue:
        reason = "within the 6-month federal open-enrollment window" if within_open_enrollment else "state runs continuous guaranteed issue"
        outcome.add_condition(f"Guaranteed issue — no medical underwriting ({reason})")
    else:
        outcome.add_condition("Outside the federal open-enrollment window and not a continuous-GI state — full medical underwriting applies and coverage can be declined")

    manual = (ctx.manual or {}).get("senior") or {}
    base_monthly = float(manual.get("medigap_base_rate_monthly", 165.0))
    hd_factor = float(manual.get("medigap_hd_plan_g_factor", 0.35))
    deductible = float(manual.get("medigap_hd_deductible", 2800.0))
    area_f = area_relativity(ctx)

    monthly = base_monthly * hd_factor * area_f
    annual = round(monthly * 12.0 + policy_fee(ctx), 2)

    outcome.base_premium = round(base_monthly * hd_factor * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="high_deductible_factor", amount=hd_factor, basis=f"annual deductible=${deductible:,.0f}"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "guaranteed_issue": guaranteed_issue,
            "within_open_enrollment": within_open_enrollment,
            "annual_deductible": deductible,
            "monthly_premium": round(monthly, 2),
            "state_rules_applied": state_rules,
            "exam_required": not guaranteed_issue,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="medigap_high_deductible_plan_g")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    within_open_enrollment = "open_enrollment" in (ctx.coverage_id or "").lower() or "open enrollment" in (ctx.coverage_name or "").lower()
    outcome = underwrite_hd_plan_g(ctx, within_open_enrollment=within_open_enrollment)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="senior")
