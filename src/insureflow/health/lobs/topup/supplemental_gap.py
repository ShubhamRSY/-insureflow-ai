"""Supplemental / Gap Health Coverage — dedicated logic path.

Coverages: Standard Gap (per-incident deductible) and Super Gap (annual
aggregate deductible). Sits on top of a high-deductible base plan and pays
once the base plan's deductible is exhausted — real US practice alongside
HDHPs, distinct from a second, duplicate major-medical policy. Priced as a
credit against the standalone individual rate: a higher base deductible
means a cheaper gap policy, since less exposure sits below it.
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
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "supplemental_gap_coverage"
LOGIC_PATH = "insureflow.health.lobs.topup.supplemental_gap"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Pays only above the stated base-plan deductible — does not replace a primary major-medical policy"],
}
STATE_RULES: dict[str, dict[str, Any]] = {}

MIN_ISSUE_AGE = 0
MAX_ISSUE_AGE = 64


def _nearest_deductible(table: dict[str, float], deductible: float) -> str:
    keys = sorted((int(k) for k in table))
    best = keys[0]
    for k in keys:
        if k <= deductible:
            best = k
    return str(best)


def underwrite_gap_coverage(ctx: HealthProductContext, *, is_super: bool) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="super_topup_plan" if is_super else "topup_plan")

    label = "Super Gap Coverage" if is_super else "Standard Gap Coverage"
    outcome = LobOutcome(product_label=label)

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"{label} issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Base-plan deductible amount missing — a gap policy cannot be rated without knowing what it sits above")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition(f"Deductible basis: {'annual aggregate' if is_super else 'per hospitalization/incident'}")

    manual = (ctx.manual or {}).get("individual") or {}
    topup_manual = (ctx.manual or {}).get("topup") or {}
    silver_base = float(manual.get("silver_base_rate_monthly", 380.0))
    age_f = age_band_factor(ctx)
    area_f = area_relativity(ctx)
    credit_table = topup_manual.get("deductible_credit_factors") or {}
    credit_f = float(credit_table.get(_nearest_deductible(credit_table, ctx.benefit_amount), 1.0)) if credit_table else 1.0

    # A gap policy sits above a base deductible, so it is priced off a share of the major-medical rate, not the full Silver rate.
    gap_share = float(topup_manual.get("gap_base_share_of_silver", 1.0))
    basis_key = "super" if is_super else "standard"
    basis_f = float((topup_manual.get("gap_basis_factors") or {}).get(basis_key, 1.0))  # aggregate deductible accumulates across claims -> pays more often

    monthly = silver_base * gap_share * basis_f * age_f * area_f * credit_f
    annual = round(monthly * 12.0 + policy_fee(ctx), 2)

    outcome.base_premium = round(silver_base * 12.0, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="age_band", amount=age_f, basis=f"age={ctx.age}"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
        RateComponent(name="gap_base_share", amount=gap_share, basis="share of Silver major-medical rate"),
        RateComponent(name="deductible_basis", amount=basis_f, basis=basis_key),
        RateComponent(name="deductible_credit", amount=credit_f, basis=f"base deductible ${ctx.benefit_amount:,.0f}"),
    ]
    outcome.metadata.update(
        {
            "base_plan_deductible": ctx.benefit_amount,
            "deductible_basis": "annual_aggregate" if is_super else "per_incident",
            "monthly_premium": round(monthly, 2),
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="supplemental_gap_coverage")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    is_super = "super" in (ctx.coverage_id or "").lower() or "super" in (ctx.coverage_name or "").lower()
    outcome = underwrite_gap_coverage(ctx, is_super=is_super)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="topup")
