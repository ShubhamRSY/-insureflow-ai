"""Permanent Partial Disability (PPD) — dedicated logic path.

A scheduled-injury lump sum (loss of a limb, sight in one eye, hearing,
etc.) — no income proof required, unlike STD/LTD/PTD, since the payout is
fixed by the schedule and doesn't depend on replacing lost earnings. The
schedule percentage is parsed from the coverage text; an unmatched
injury type falls back to the manual's "unscheduled" mid-tier factor
rather than guessing a specific body part.
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
from insureflow.rating.models import RateComponent

PRODUCT_ID = "disability_ppd"
LOGIC_PATH = "insureflow.health.lobs.disability.permanent_partial_disability"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Pays a fixed percentage of the principal sum per the injury schedule — not an income-replacement benefit"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 70

_SCHEDULE_KEYWORDS: dict[str, str] = {
    "loss_of_two_limbs": "loss_of_two_limbs",
    "loss_of_one_limb": "loss_of_one_limb",
    "loss_of_sight_both_eyes": "loss_of_sight_both_eyes",
    "loss_of_sight_one_eye": "loss_of_sight_one_eye",
    "loss_of_hearing": "loss_of_hearing",
}


def _schedule_key(blob: str) -> str:
    for needle, key in _SCHEDULE_KEYWORDS.items():
        if needle.replace("_", " ") in blob or needle in blob:
            return key
    return "unscheduled"


def underwrite_ppd(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="disability_ppd")

    outcome = LobOutcome(product_label="Permanent Partial Disability")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"PPD issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Principal sum missing — cannot rate without a coverage amount")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    schedule_key = _schedule_key(f"{ctx.coverage_id or ''} {ctx.coverage_name or ''}".lower())
    disability_manual = (ctx.manual or {}).get("disability") or {}
    schedule_factors = disability_manual.get("ppd_schedule_factors") or {}
    schedule_f = float(schedule_factors.get(schedule_key, 0.5))
    rate_per_1000 = float(disability_manual.get("ptd_lump_sum_rate_per_1000", 4.5)) * 0.8  # PPD's base rate is a discount off PTD's — same injury pool, partial payout
    area_f = area_relativity(ctx)

    base_premium = (ctx.benefit_amount / 1000.0) * rate_per_1000 * schedule_f
    annual = round(base_premium * area_f + policy_fee(ctx), 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="ppd_rate_per_1000", amount=rate_per_1000, basis="annual"),
        RateComponent(name="schedule_factor", amount=schedule_f, basis=schedule_key),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "principal_sum": ctx.benefit_amount,
            "schedule_key": schedule_key,
            "benefit_type": "permanent_partial_disability",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="disability_ppd")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_ppd(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="disability")
