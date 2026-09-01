"""Disease-Specific Critical Illness — dedicated logic path.

Coverages: Cancer Care, Cardiac Care, Diabetes/Kidney Care — one condition
family per coverage rather than the broad multi-condition standalone CI
plan, each with its own disease load and its own reused evidence gate
(cardiac requires an ECG on file; cancer and diabetes/kidney do not).
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
    tobacco_surcharge,
)
from insureflow.health.lobs.critical_illness.critical_illness_standalone import _nearest_age
from insureflow.rating.models import RateComponent

PRODUCT_ID = "disease_specific_critical_illness"
LOGIC_PATH = "insureflow.health.lobs.critical_illness.disease_specific"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "disclosures": ["Pays only on diagnosis of the named condition — not a substitute for major medical or standalone critical illness cover"],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "NY": {"free_look_days": 30},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 70

_COVERAGE_TO_HANDLER = {
    "cancer_care": "cancer_care",
    "cardiac_care": "cardiac_care",
    "diabetes_kidney_care": "diabetes_kidney_care",
}
_COVERAGE_LABELS = {
    "cancer_care": "Cancer Care",
    "cardiac_care": "Cardiac Care",
    "diabetes_kidney_care": "Diabetes / Kidney Care",
}


def underwrite_disease_specific(ctx: HealthProductContext, coverage_key: str) -> LobOutcome:
    from insureflow.underwriting.health_uw import underwrite_health

    ctx.uw = underwrite_health(ctx.bundle, product_id="disease_specific", coverage_id=_COVERAGE_TO_HANDLER.get(coverage_key, "cancer_care"))

    label = _COVERAGE_LABELS.get(coverage_key, "Disease-Specific Critical Illness")
    outcome = LobOutcome(product_label=label)

    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"{label} issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")
    if ctx.benefit_amount <= 0:
        outcome.eligible = False
        outcome.add_reason("Lump-sum benefit amount missing — cannot rate without a coverage amount")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    ci_manual = (ctx.manual or {}).get("critical_illness") or {}
    sex_key = ctx.sex_key if ctx.sex_key in ("male", "female") else "male"
    table = (ci_manual.get("morbidity_per_1000") or {}).get(sex_key) or {}
    rate_per_1000 = float(table.get(_nearest_age(table, ctx.age), 3.0)) if table else 3.0
    disease_load = float((ci_manual.get("disease_specific_load") or {}).get(coverage_key, 1.0))

    tobacco_f = tobacco_surcharge(ctx)
    area_f = area_relativity(ctx)

    base_premium = (ctx.benefit_amount / 1000.0) * rate_per_1000 * disease_load
    annual = round(base_premium * tobacco_f * area_f + policy_fee(ctx), 2)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="morbidity_per_1000", amount=rate_per_1000, basis=f"age={ctx.age}/{sex_key}"),
        RateComponent(name="disease_specific_load", amount=disease_load, basis=coverage_key),
        RateComponent(name="tobacco_surcharge", amount=tobacco_f, basis="tobacco" if ctx.tobacco else "non_tobacco"),
        RateComponent(name="area_relativity", amount=area_f, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata.update(
        {
            "covered_condition": coverage_key,
            "lump_sum_benefit": ctx.benefit_amount,
            "state_rules_applied": state_rules,
            "exam_required": coverage_key == "cardiac_care",
        }
    )

    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="disease_specific_critical_illness")
    return outcome


def build_quote(ctx: HealthProductContext) -> Any:
    coverage_key = (ctx.coverage_id or "cancer_care").lower().replace("-", "_")
    if coverage_key not in _COVERAGE_TO_HANDLER:
        coverage_key = "cancer_care"
    outcome = underwrite_disease_specific(ctx, coverage_key)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="critical_illness")
