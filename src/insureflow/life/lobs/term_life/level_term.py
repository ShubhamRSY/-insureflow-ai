"""Level Term Life — dedicated logic path (LOB 1 · Term Life).

Coverages: 10/15/20/25/30-Year Level Term.
State compliance (free-look, exam thresholds, disclosures) is applied
INSIDE this path via STATE_RULES — not bolted on afterward.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    add_common_loads,
    apply_state_filing_gate,
    band_factor,
    finish_quote,
    medical_class_factor,
    merge_state_rules,
    state_relativity,
)
from insureflow.rating.models import RateComponent

PRODUCT_ID = "level_term"
LOGIC_PATH = "insureflow.life.lobs.term_life.level_term"
PRODUCT_LABEL = "{years}-Year Level Term"

# Carrier/pilot configuration defaults — validate against DOI filings per state.
DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "paramed_exam_required": True,
    "paramed_face_threshold": 250_000.0,
    "disclosures": ["Replacement notice (state-mandated when replacing in-force coverage)"],
}

STATE_RULES: dict[str, dict[str, Any]] = {
    "FL": {"free_look_days": 14},
    "CT": {
        "free_look_days": 30,
        "paramed_face_threshold": 100_000.0,
        "disclosures": [
            "Replacement notice (state-mandated when replacing in-force coverage)",
            "CT life insurance buyer's guide acknowledgment",
        ],
    },
    "NY": {"free_look_days": 20, "paramed_face_threshold": 500_000.0},
    "CA": {"free_look_days": 10, "paramed_face_threshold": 250_000.0},
    "IL": {"free_look_days": 10, "paramed_face_threshold": 150_000.0},
}

MIN_ISSUE_AGE = 18
MAX_ISSUE_AGE = 80

_DURATION_RE = re.compile(r"(?:^|[_\s-])(10|15|20|25|30)(?:$|[_\s-]|\s*-?\s*year|_year)")


def _term_years(ctx: LifeProductContext) -> int:
    blob = f"{ctx.coverage_id or ''} {ctx.coverage_name or ''}".lower()
    match = _DURATION_RE.search(blob)
    return int(match.group(1)) if match else 20


def underwrite_level_term(ctx: LifeProductContext, years: int) -> LobOutcome:
    outcome = LobOutcome(product_label=PRODUCT_LABEL.format(years=years))

    # Product-specific issue-age gate
    if not MIN_ISSUE_AGE <= ctx.age <= MAX_ISSUE_AGE:
        outcome.eligible = False
        outcome.add_reason(f"Level term issue age {ctx.age} outside {MIN_ISSUE_AGE}-{MAX_ISSUE_AGE}")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    exam_required = state_rules["paramed_exam_required"] and ctx.face > float(state_rules["paramed_face_threshold"])
    if exam_required:
        outcome.add_condition(f"Paramedical exam required above ${float(state_rules['paramed_face_threshold']):,.0f} face ({state_rules['issue_state'] or 'carrier'} rule)")
    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    manual = ctx.manual or {}
    q_table = (manual.get("mortality_per_1000") or {}).get(ctx.sex_key) or {}
    from insureflow.rating.personal.manuals import nearest_key

    q = float(q_table.get(nearest_key(q_table, ctx.age), 1.5))

    base_premium = (ctx.face / 1000.0) * q
    class_f = medical_class_factor(ctx)
    sex_f = 1.0 if ctx.unisex_forced else float((manual.get("sex_factors") or {}).get(ctx.sex_key, 1.0))
    tobacco_f = float(manual.get("tobacco_factor", 1.85)) if ctx.smoker else 1.0
    band_f = band_factor(ctx)
    duration_factors = manual.get("term_duration_factors") or {}
    term_f = float(duration_factors.get(str(years), 1.0))
    state_rel = state_relativity(ctx)

    loaded = base_premium * class_f * sex_f * tobacco_f * band_f * term_f * state_rel
    annual = add_common_loads(ctx, loaded)

    outcome.base_premium = round(base_premium, 2)
    outcome.annual_premium = annual
    outcome.components = [
        RateComponent(name="mortality_per_1000", amount=q, basis=f"age={ctx.age}/{ctx.sex_key}"),
        RateComponent(name="underwriting_class", amount=class_f, basis=ctx.medical.underwriting_class),
        RateComponent(name="sex_factor", amount=sex_f, basis=ctx.sex_key),
        RateComponent(name="tobacco_factor", amount=tobacco_f, basis="tobacco" if ctx.smoker else "non_tobacco"),
        RateComponent(name="band_discount", amount=band_f, basis=f"face={ctx.face}"),
        RateComponent(name="term_duration", amount=term_f, basis=f"{years}yr"),
        RateComponent(name="state_relativity", amount=state_rel, basis=ctx.issue_state or ctx.filing_state),
    ]
    outcome.metadata["term_years"] = years
    outcome.metadata["state_rules_applied"] = state_rules
    outcome.metadata["exam_required"] = exam_required

    if ctx.medical.decision.value == "decline":
        outcome.eligible = False
    apply_state_filing_gate(ctx, outcome, filed_for_state=True, product_family="level_term")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    years = _term_years(ctx)
    outcome = underwrite_level_term(ctx, years)
    return finish_quote(ctx, outcome, logic_path=LOGIC_PATH, family="term")
