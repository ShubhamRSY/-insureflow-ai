"""Permanent Total Disability (PTD) — dedicated logic path.

Structurally distinct from STD/LTD: a lump-sum-or-extended-benefit payout
triggered by a *permanent* and total inability to work, not a periodic
income-replacement benefit for a recoverable disability. Priced per $1,000
of the elected benefit amount, like AD&D/CI, rather than as a percentage of
monthly income the way STD/LTD are.
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
from insureflow.underwriting.health_uw import _occupation_class

PRODUCT_ID = "disability_ptd"
LOGIC_PATH = "insureflow.health.lobs.disability.permanent_total_disability"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Pays only on a permanent and total disability determination — not a periodic income-replacement benefit"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 60


def underwrite_ptd(ctx: HealthProductContext) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="disability_ptd")

    outcome = LobOutcome(product_label="Permanent Total Disability")

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"PTD issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Lump-sum benefit amount missing — cannot rate without a coverage amount")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    occ_class = _occupation_class(ctx.blob) or "II"
    disability_manual = (ctx.manual or {}).get("disability") or {}
    rate_per_1000 = float(disability_manual.get("ptd_lump_sum_rate_per_1000", 4.5))
    occ_f = float((disability_manual.get("occupation_class_factors") or {}).get(occ_class, 1.0))
    area_f = area_relativity(ctx)

    base_premium = (ctx.benefit_amount / 1000.0) * rate_per_1000
    annual = round(base_premium * occ_f * area_f + policy_fee(ctx), 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="ptd_rate_per_1000", amount=rate_per_1000, basis="annual"),
        RateComponent(name="occupation_class", amount=occ_f, basis=f"Class {occ_class}"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "lump_sum_benefit": ctx.benefit_amount,
            "occupation_class": occ_class,
            "benefit_type": "permanent_total_disability",
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="disability_ptd")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    outcome = underwrite_ptd(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="disability")
