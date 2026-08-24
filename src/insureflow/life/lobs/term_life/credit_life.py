"""Credit Life Insurance — dedicated logic path (LOB 1 · Term Life).

Coverages: Outstanding Balance Credit Life, Simplified Issue Credit Life.
Declining balance matched to the debt; simplified health only (no exam);
face capped at the loan balance class of risk.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    add_common_loads,
    apply_state_filing_gate,
    finish_quote,
    merge_state_rules,
    stack_shape_ratio,
    state_relativity,
)
from insureflow.life.product_variants import compute_decreasing_term
from insureflow.rating.models import RateComponent

PRODUCT_ID = "credit_life"
LOGIC_PATH = "insureflow.life.lobs.term_life.credit_life"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": False,
    "max_credit_face": 250_000.0,
    "max_issue_age": 70,
    "disclosures": ["Credit life is optional — declining it cannot affect the loan decision"],
}

COVERAGE_PROFILES: dict[str, dict[str, Any]] = {
    "loan_balance": {"label": "Outstanding Balance Credit Life"},
    "simplified_credit": {"label": "Simplified Issue Credit Life"},
}

STATE_RULES: dict[str, dict[str, Any]] = {
    "CT": {"free_look_days": 30},
    "NY": {"free_look_days": 20},
}


def _coverage_label(ctx: LifeProductContext) -> str:
    coverage = (ctx.coverage_id or "").lower()
    if coverage in COVERAGE_PROFILES:
        return str(COVERAGE_PROFILES[coverage]["label"])
    return "Simplified Issue Credit Life" if "simplified" in (ctx.coverage_name or "").lower() else "Outstanding Balance Credit Life"


def underwrite_credit_life(ctx: LifeProductContext) -> LobOutcome:
    label = _coverage_label(ctx)
    outcome = LobOutcome(product_label=label)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    max_face = float(state_rules["max_credit_face"])
    effective_face = min(ctx.face, max_face)
    if ctx.face > max_face:
        outcome.add_reason(f"Requested face ${ctx.face:,.0f} capped to credit-life maximum ${max_face:,.0f}")
        ctx.face = effective_face
    if ctx.age > int(state_rules["max_issue_age"]):
        outcome.eligible = False
        outcome.add_reason(f"Credit life issue age {ctx.age} above maximum {state_rules['max_issue_age']}")

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)
    outcome.add_condition("Loan agreement / creditor details required; benefit assigned to lender")

    years = 5  # typical consumer-loan horizon
    variant = compute_decreasing_term(
        age=ctx.age,
        sex=ctx.sex_key,
        smoker=ctx.smoker,
        initial_face=effective_face,
        term_years=years,
        amortize=False,
        reduction_rate=0.0,
    )

    # Simplified issue priced on the filed exhibit reshaped to the declining
    # balance, with an explicit no-exam anti-selection load.
    q_table = ((ctx.manual or {}).get("mortality_per_1000") or {}).get(ctx.sex_key) or {}
    from insureflow.rating.personal.manuals import nearest_key

    q = float(q_table.get(nearest_key(q_table, ctx.age), 1.5))
    state_rel = state_relativity(ctx)
    base_premium = (effective_face / 1000.0) * q
    shape = stack_shape_ratio(ctx, variant.level_premium, years)
    loaded = base_premium * shape * 1.15 * state_rel
    annual = add_common_loads(ctx, loaded)

    outcome.base_premium = round(base_premium * shape, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="manual_level_base", amount=round(base_premium, 2), basis=f"declining {years}yr per filed exhibit"),
        RateComponent(name="credit_shape_ratio", amount=round(shape, 4), basis="outstanding-balance decline vs level"),
        RateComponent(name="simplified_issue_load", amount=1.15, basis="no-exam anti-selection load"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["term_years"] = years
    outcome.metadata["capped_face"] = effective_face
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = False
    outcome.metadata["simplified_underwriting"] = True

    # Simplified issue: hard medical knockouts still decline, but rated classes
    # are accepted without individual review.
    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="credit_life")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_credit_life(ctx)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="term")
