"""Medicare Supplement (Medigap) — dedicated logic path.

Coverages: standardized Plans A, F, G, N. The real underwriting fork is
TIMING, not the plan letter: during the 6-month federal open-enrollment
window starting the month someone turns 65 and enrolls in Medicare Part B,
enrollment is guaranteed issue with no medical questions; outside that
window, most states allow full medical underwriting and can decline. A few
states (CT/MA/NY/ME) run continuous guaranteed issue instead, and
"birthday rule" states let policyholders switch plans near their birthday
without underwriting regardless of the federal window.
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

PRODUCT_ID = "medicare_supplement"
LOGIC_PATH = "insureflow.health.lobs.senior.medicare_supplement"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 30,
    "disclosures": ["Medigap does not include prescription drug coverage — a separate Part D plan is required"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 65


def underwrite_medicare_supplement(ctx: HealthProductContext, plan_letter: str, *, within_open_enrollment: bool) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    # Guaranteed-issue window uses the no-medical-questions handler; outside
    # it, most states allow full medical underwriting (senior_standard).
    ctx.uw = underwrite_health(ctx.bundle, product_id="senior_no_medical" if within_open_enrollment else "senior_standard")

    outcome = LobOutcome(product_label=f"Medicare Supplement Plan {plan_letter}")

    if ctx.age < MIN_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Medicare Supplement requires Medicare Part B enrollment — applicant age {ctx.age} is below the {MIN_ISSUE_AGE} minimum")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    enrollment = medigap_enrollment_rules(ctx.issue_state)
    guaranteed_issue = within_open_enrollment or enrollment["continuous_guaranteed_issue"]
    if guaranteed_issue:
        if enrollment["continuous_guaranteed_issue"] and not within_open_enrollment:
            reason = "state runs continuous guaranteed issue"
        else:
            reason = "within the 6-month federal open-enrollment window"
        outcome.add_condition(f"Guaranteed issue — no medical underwriting ({reason})")
    else:
        outcome.add_condition("Outside the federal open-enrollment window and not a continuous-GI state — full medical underwriting applies and coverage can be declined")
    if enrollment["birthday_rule"]:
        outcome.add_condition(f"{ctx.issue_state} birthday rule: may switch to an equal-or-lesser-value plan within 30-63 days of birthday without underwriting")

    manual = (ctx.manual or {}).get("senior") or {}
    base_monthly = float(manual.get("medigap_base_rate_monthly", 165.0))
    plan_f = float((manual.get("medigap_plan_factors") or {}).get(plan_letter, 1.0))
    area_f = area_relativity(ctx)

    monthly = base_monthly * plan_f * area_f
    annual = round(monthly * 12.0 + policy_fee(ctx), 2)

    outcome.base_premium = round(base_monthly * plan_f * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="plan_letter_factor", amount=plan_f, basis=f"Plan {plan_letter}"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "plan_letter": plan_letter,
            "guaranteed_issue": guaranteed_issue,
            "within_open_enrollment": within_open_enrollment,
            "monthly_premium": round(monthly, 2),
            "state_rules_applied": state_rules,
            "exam_required": not guaranteed_issue,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="medicare_supplement")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    import re

    blob = f"{ctx.coverage_id or ''} {ctx.coverage_name or ''}"
    match = re.search(r"plan[_\s-]?([afgn])\b", blob, re.I)
    plan_letter = match.group(1).upper() if match else "G"
    within_open_enrollment = "open_enrollment" in (ctx.coverage_id or "").lower() or "open enrollment" in (ctx.coverage_name or "").lower()
    outcome = underwrite_medicare_supplement(ctx, plan_letter, within_open_enrollment=within_open_enrollment)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="senior")
