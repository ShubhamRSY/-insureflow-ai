"""Medicare Part D (Prescription Drug Plan) — dedicated logic path.

Every Medigap disclosure in this package tells the applicant "a separate
Part D plan is required" — this is that plan. Guaranteed issue during the
Initial Enrollment Period (same window Medicare Part B itself opens) or an
annual Open Enrollment window; the real, distinct underwriting feature is
the late-enrollment penalty — a permanent 1%-of-national-base-premium
surcharge for every full month without Part D or other creditable drug
coverage since first becoming eligible, which no other product in this
package has an equivalent of.
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
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "medicare_part_d"
LOGIC_PATH = "insureflow.health.lobs.senior.medicare_part_d"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 14,
    "disclosures": ["Coverage gap ('donut hole') cost-sharing rules apply once total drug spend crosses the annual threshold — do not invent the dollar threshold, it is filing-specific"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 65


def _months_without_creditable_coverage(blob: str) -> int:
    import re

    match = re.search(r"(\d+)\s*months?\s*without\s*(?:creditable\s*)?(?:drug\s*)?coverage", blob, re.I)
    return int(match.group(1)) if match else 0


def underwrite_part_d(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    # No handler in health_uw.py models a drug-only plan; guaranteed issue
    # during enrollment windows means no medical underwriting applies at
    # all — the generic KYC-only baseline is the correct fit, same as
    # Medicare Advantage.
    ctx.uw = underwrite_health(ctx.bundle)

    outcome = LobOutcome(product_label="Medicare Part D (Prescription Drug Plan)")

    if ctx.age < MIN_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Medicare Part D requires Medicare eligibility — applicant age {ctx.age} is below the {MIN_ISSUE_AGE} minimum")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition("Guaranteed issue — Part D cannot be declined on health status during an eligible enrollment period")

    manual = (ctx.manual or {}).get("senior") or {}
    base_monthly = float(manual.get("part_d_base_rate_monthly", 45.0))
    penalty_pct_per_month = float(manual.get("part_d_late_enrollment_penalty_pct_per_month", 0.01))
    area_f = area_relativity(ctx)

    months_uncovered = _months_without_creditable_coverage(ctx.blob)
    penalty_f = 1.0 + (penalty_pct_per_month * months_uncovered)
    if months_uncovered:
        outcome.add_condition(f"Late-enrollment penalty applies — {months_uncovered} month(s) without creditable drug coverage, permanent surcharge for the life of the plan")

    monthly = base_monthly * penalty_f * area_f
    annual = round(monthly * 12.0, 2)

    outcome.base_premium = round(base_monthly * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="late_enrollment_penalty", amount=round(penalty_f, 4), basis=f"{months_uncovered} month(s) uncovered" if months_uncovered else "none"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "guaranteed_issue": True,
            "months_without_creditable_coverage": months_uncovered,
            "late_enrollment_penalty_applies": months_uncovered > 0,
            "monthly_premium": round(monthly, 2),
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="medicare_part_d")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_part_d(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="senior")
