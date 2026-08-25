"""Group Term Life — dedicated logic path (LOB 1 · Term Life).

Coverages: Basic Group Life, Supplemental Group Life, Dependent Group Life.
Simplified underwriting (no paramedical exam at these limits); group pricing
factors and IRC §79 imputed-income review above $50k.
"""

from __future__ import annotations

from typing import Any

from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    add_common_loads,
    apply_state_filing_gate,
    finish_quote,
    medical_class_factor,
    merge_state_rules,
    state_relativity,
)
from insureflow.rating.models import RateComponent
from insureflow.rating.personal.manuals import nearest_key

PRODUCT_ID = "group_term_life"
LOGIC_PATH = "insureflow.life.lobs.term_life.group_term"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": False,  # simplified/group underwriting
    "irc79_imputed_threshold": 50_000.0,
    "max_group_face": 2_000_000.0,
    "disclosures": ["Enrollment via employer; beneficiary designation is a separate individual form"],
}

# Group factors are per-coverage: Basic / Supplemental / Dependent price very differently.
COVERAGE_FACTORS: dict[str, dict[str, Any]] = {
    "basic_group": {"factor": 0.35, "label": "Basic Group Term Life"},
    "supplemental_group": {"factor": 0.55, "label": "Supplemental Group Term Life"},
    "dependent_group": {"factor": 0.18, "label": "Dependent Group Term Life"},
}

STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "NY": {"free_look_days": 20},
}


def _coverage_profile(ctx: LifeProductContext) -> dict[str, Any]:
    coverage = (ctx.coverage_id or "").lower()
    for key, profile in COVERAGE_FACTORS.items():
        if key in coverage or profile["label"].lower() in (ctx.coverage_name or "").lower():
            return profile
    return COVERAGE_FACTORS["basic_group"]


def underwrite_group_term(ctx: LifeProductContext, profile: dict[str, Any]) -> LobOutcome:
    label = str(profile["label"])
    outcome = LobOutcome(product_label=label)

    if ctx.age < 18 or ctx.age > 70:
        outcome.eligible = False
        outcome.add_reason(f"Group life issue age {ctx.age} outside 18–70")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    if ctx.face > float(state_rules["max_group_face"]):
        outcome.eligible = False
        outcome.add_reason(f"Face ${ctx.face:,.0f} exceeds group maximum ${float(state_rules['max_group_face']):,.0f}")
    if ctx.face > float(state_rules["irc79_imputed_threshold"]):
        outcome.add_condition(f"IRC §79 imputed income review — basic coverage above ${float(state_rules['irc79_imputed_threshold']):,.0f}")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    manual = ctx.manual or {}
    q_table = (manual.get("mortality_per_1000") or {}).get(ctx.sex_key) or {}
    q = float(q_table.get(nearest_key(q_table, ctx.age), 1.5))

    base_premium = (ctx.face / 1000.0) * q
    class_f = medical_class_factor(ctx, cap=1.25)
    group_f = float(profile["factor"])
    state_rel = state_relativity(ctx)

    loaded = base_premium * class_f * group_f * state_rel
    annual = add_common_loads(ctx, loaded)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="individual_mortality_per_1000", amount=q, basis=f"age={ctx.age}/{ctx.sex_key}"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="group_coverage_factor", amount=group_f, basis=label),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = False
    outcome.metadata["simplified_underwriting"] = True
    outcome.metadata["group_factor"] = group_f

    # Simplified issue: medical declines do not auto-decline the group case;
    # evidence of insurability is handled through the EOI process instead.
    # ctx.medical is mined from free-text disclosures with no product
    # awareness — without this opt-out, the platform's shared binding gate
    # would auto-decline the group case anyway, contradicting the line
    # above and this product's guaranteed-issue design at these limits.
    outcome.metadata["_skip_medical_gate"] = True
    if ctx.medical.decision.value == "decline":
        outcome.add_condition("Evidence of insurability (EOI) required before supplemental coverage becomes effective")
    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="group_term_life")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    profile = _coverage_profile(ctx)
    outcome = underwrite_group_term(ctx, profile)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="term")
