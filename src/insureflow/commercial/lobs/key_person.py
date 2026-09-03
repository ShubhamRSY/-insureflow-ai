"""Key Person Insurance — dedicated logic path.

Key person coverage IS, economically, a term life policy purchased by the
employer on a critical employee — so it is priced that way: real mortality
(q_x per $1,000 of face, from the same filed life manual
``insureflow.life.lobs.term_life.level_term`` uses), not the flat
"loss-cost per $100 of face" heuristic ``commercial_specialty`` applies to
the other three specialty lines (which fits limit-driven liability, not a
mortality-driven death benefit). State law has no material national
variance for this product — see ``state_law.py``'s docstring — so this
path's other real addition is the IRC 101(j) notice-and-consent condition.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.commercial.lobs.base import CommercialProductContext, LobOutcome, add_common_life_loads, finish_quote, merge_state_rules
from insureflow.rating.commercial_specialty import estimate_specialty_exposure
from insureflow.rating.models import InsuranceLine, QuoteResult
from insureflow.underwriting.personal_lines import _blob, _int_field

PRODUCT_ID = "key_person"
LOGIC_PATH = "insureflow.commercial.lobs.key_person"
PRODUCT_LABEL = "Key Person Insurance"

DEFAULT_STATE_RULES: dict[str, Any] = {}
STATE_RULES: dict[str, dict[str, Any]] = {}

_CONSENT_RE = r"101\(j\)|notice.{0,10}consent|employer.owned life"
DEFAULT_ASSUMED_AGE = 45


def _key_employee_age(blob: str) -> int | None:
    return _int_field(blob, "key employee age", "key person age", "key employee's age", "insured employee age", "insured age", "age")


def _key_employee_sex(blob: str) -> str:
    from insureflow.health.lobs.base import _extract_sex

    return _extract_sex(blob)


def _key_employee_smoker(blob: str) -> bool:
    from insureflow.health.lobs.base import _extract_tobacco

    return _extract_tobacco(blob)


def underwrite_key_person(ctx: CommercialProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label=PRODUCT_LABEL)
    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.metadata["state_rules_applied"] = state_rules

    blob = _blob(ctx.bundle)
    if not re.search(_CONSENT_RE, blob, re.I):
        outcome.add_condition(
            "IRC 101(j) employer-owned life insurance notice-and-consent not documented — "
            "written notice and consent must be obtained from the insured employee BEFORE issue "
            "or the death benefit loses its income-tax-free treatment"
        )

    face, exposure_basis, used_default_exposure = estimate_specialty_exposure(ctx.bundle, InsuranceLine.KEY_PERSON)
    outcome.metadata["exposure"] = face
    outcome.metadata["exposure_basis"] = exposure_basis
    if used_default_exposure:
        outcome.add_reason(f"No explicit face amount found — rated on default {exposure_basis.replace('_', ' ')} ${face:,.0f}")

    from insureflow.rating.personal.manuals import life_manual, nearest_key

    manual = life_manual()
    q_table = manual.get("mortality_per_1000") or {}
    age = _key_employee_age(blob)
    sex_key = _key_employee_sex(blob)

    if age is not None and sex_key in ("male", "female"):
        table = q_table.get(sex_key) or {}
        q = float(table.get(nearest_key(table, age), 1.5))
        assumption_note = None
    else:
        # No disclosed age/sex — never invent one silently. Rate on an
        # illustrative age-45, unisex-average mortality rate (mirrors the
        # "used_default" honesty pattern in commercial_specialty's exposure
        # sizing) and say so explicitly rather than picking a sex/age.
        male_table = q_table.get("male") or {}
        female_table = q_table.get("female") or {}
        male_q = float(male_table.get(nearest_key(male_table, DEFAULT_ASSUMED_AGE), 1.5)) if male_table else 1.5
        female_q = float(female_table.get(nearest_key(female_table, DEFAULT_ASSUMED_AGE), 1.5)) if female_table else 1.5
        q = (male_q + female_q) / 2.0
        age = DEFAULT_ASSUMED_AGE
        assumption_note = (
            f"Key employee age/sex not disclosed — rated on an illustrative age-{DEFAULT_ASSUMED_AGE} unisex-average mortality assumption; obtain the actual age, sex, and health history before bind"
        )
        outcome.add_condition(assumption_note)

    smoker = _key_employee_smoker(blob)
    tobacco_f = float(manual.get("tobacco_factor", 1.85)) if smoker else 1.0

    base_premium = (face / 1000.0) * q * tobacco_f
    annual_premium = add_common_life_loads(manual, base_premium, face)

    outcome.base_premium = round(base_premium, 2)
    outcome.adjusted_premium = round(annual_premium, 2)
    outcome.metadata["mortality_rate_per_1000"] = q
    outcome.metadata["key_employee_age"] = age
    outcome.metadata["key_employee_sex"] = sex_key if sex_key in ("male", "female") else "unisex_average_assumed"
    outcome.metadata["tobacco_factor"] = tobacco_f
    outcome.metadata["rating_engine"] = "key_person_mortality"

    if re.search(r"heart attack|cancer|stroke|kidney (?:failure|disease)|terminal", blob, re.I):
        outcome.add_condition("Adverse health history disclosed in the submission — refer for individual mortality rating before bind (not priced into this standard-class illustrative premium)")

    return outcome


def build_quote(ctx: CommercialProductContext) -> QuoteResult:
    outcome = underwrite_key_person(ctx)
    exposure = float(outcome.metadata.get("exposure") or 0.0)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="key_person",
        exposure=exposure,
        exposure_basis=str(outcome.metadata.get("exposure_basis") or "face_amount"),
    )
