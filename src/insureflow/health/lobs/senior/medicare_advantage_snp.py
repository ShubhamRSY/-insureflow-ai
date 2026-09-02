"""Medicare Advantage Special Needs Plan (SNP) — dedicated logic path.

Same guaranteed-issue, no-medical-underwriting posture as standard Medicare
Advantage — the real, distinct feature is the OPPOSITE of a knockout gate:
enrollment is *restricted* to applicants who declare a qualifying chronic
condition (C-SNP) or dual Medicare/Medicaid eligibility (D-SNP). No handler
in health_uw.py models "require the condition to enroll" (every reused
handler there only ever knocks people OUT for a declared condition), so
this eligibility gate is implemented directly at the LOB layer.
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

PRODUCT_ID = "medicare_advantage_snp"
LOGIC_PATH = "insureflow.health.lobs.senior.medicare_advantage_snp"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 30,
    "disclosures": ["Replaces Original Medicare — must be used at in-network providers per the plan's network type (HMO/PPO)"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 65
_QUALIFYING_CHRONIC_CONDITIONS = ("diabetes", "chronic heart failure", "esrd", "end-stage renal", "copd", "chronic obstructive")
_DUAL_ELIGIBLE_NEEDLES = ("dual eligible", "medicare and medicaid", "medicaid enrolled", "dual-eligible")


def _snp_eligibility(blob: str) -> tuple[bool, str]:
    from insureflow.underwriting.health_uw import _applicant_only_text

    # SNP eligibility turns on the APPLICANT'S own diagnosis or dual-eligible
    # status, not a relative's — "mother has diabetes" must not qualify the
    # applicant. Reuses the same family-context filter occupation-class
    # rating uses, rather than a separate ad hoc implementation.
    blob = _applicant_only_text(blob)
    if any(k in blob for k in _DUAL_ELIGIBLE_NEEDLES):
        return True, "dual_eligible"
    for condition in _QUALIFYING_CHRONIC_CONDITIONS:
        if condition in blob:
            return True, "chronic_condition"
    return False, ""


def underwrite_ma_snp(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle)

    outcome = LobOutcome(product_label="Medicare Advantage Special Needs Plan")

    if ctx.age < MIN_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Medicare Advantage requires Medicare eligibility — applicant age {ctx.age} is below the {MIN_ISSUE_AGE} minimum")

    snp_eligible, snp_basis = _snp_eligibility(ctx.blob)
    if not snp_eligible:
        outcome.eligible = False
        outcome.add_reason("Special Needs Plan enrollment requires a documented qualifying chronic condition (C-SNP) or dual Medicare/Medicaid eligibility (D-SNP)")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition("Guaranteed issue for qualifying applicants — cannot be declined on health status once SNP eligibility is confirmed")

    manual = (ctx.manual or {}).get("senior") or {}
    base_monthly = float(manual.get("medicare_advantage_base_rate_monthly", 0.0))
    admin_fee = float(manual.get("medicare_advantage_admin_fee_monthly", 25.0))
    care_coordination_fee = float(manual.get("snp_care_coordination_fee_monthly", 40.0))
    area_f = area_relativity(ctx)

    monthly = (base_monthly + admin_fee + care_coordination_fee) * area_f
    annual = round(monthly * 12.0, 2)

    outcome.base_premium = round(base_monthly * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="plan_base_premium", amount=base_monthly, basis="CMS-capitated, often $0"),
        RateComponent(name="administrative_fee", amount=admin_fee, basis="monthly"),
        RateComponent(name="care_coordination_fee", amount=care_coordination_fee, basis="SNP care-management overhead"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "guaranteed_issue": True,
            "snp_eligibility_basis": snp_basis or None,
            "monthly_premium": round(monthly, 2),
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="medicare_advantage_snp")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_ma_snp(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="senior")
