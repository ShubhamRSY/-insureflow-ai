"""Annuity payout illustration — fixed / variable / indexed, immediate & deferred.

An annuity converts a principal (or accumulating contributions) into a steady
income stream. This module computes an actuarially-neutral illustrative payout
from the mortality manual: the present value of a life annuity is the discounted
sum of survival probabilities, and the level annual payout is principal ÷ that
annuity factor.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult
from insureflow.rating.personal.manuals import life_manual, nearest_key
from insureflow.underwriting.personal_lines import _blob, extract_life_factors

_DEFAULT_INTEREST = 0.04
_MAX_SURVIVAL_AGE = 110


def _survival_curve(age: int, sex: str) -> list[float]:
    """Survival probabilities l(x) from the mortality manual, starting at ``age``."""
    manual = life_manual()
    sex_key = "female" if sex == "female" else "male"
    mort_table = (manual.get("mortality_per_1000") or {}).get(sex_key, {}) or {}
    survival = [1.0]
    prob = 1.0
    current = age
    while current < _MAX_SURVIVAL_AGE and prob > 1e-6:
        q = float(mort_table.get(nearest_key(mort_table, current), 5.0)) / 1000.0
        prob *= max(1.0 - q, 0.0)
        survival.append(prob)
        current += 1
    return survival


def annuity_factor(*, age: int, sex: str = "male", interest_rate: float | None = None) -> float:
    """Present value of a $1-per-year life annuity payable in arrears."""
    rate = interest_rate if interest_rate is not None else _DEFAULT_INTEREST
    survival = _survival_curve(int(age), sex)
    discount = 1.0 / (1.0 + rate)
    pv = 0.0
    factor = 1.0
    for prob in survival[1:]:
        factor *= discount
        pv += prob * factor
    return round(pv, 6)


def illustrative_payout(*, principal: float, age: int, sex: str = "male", interest_rate: float | None = None) -> dict[str, Any]:
    """Level annual income from an immediate life annuity."""
    principal = max(float(principal or 0.0), 0.0)
    af = annuity_factor(age=age, sex=sex, interest_rate=interest_rate)
    if af <= 0:
        return {"annuity_factor": 0.0, "annual_payout": 0.0, "detail": "No annuity factor — cannot illustrate"}
    payout = principal / af
    return {
        "annuity_factor": round(af, 4),
        "annual_payout": round(payout, 2),
        "monthly_payout": round(payout / 12.0, 2),
        "interest_rate": interest_rate if interest_rate is not None else _DEFAULT_INTEREST,
        "detail": f"Immediate life annuity: {principal:,.0f} ÷ factor {af:.3f} ≈ {payout:,.0f}/yr ({payout / 12:,.0f}/mo)",
    }


def annuity_subtype(blob: str) -> str:
    """Classify fixed / variable / indexed / immediate / deferred from the text."""
    lowered = blob.lower()
    if "indexed" in lowered:
        return "indexed"
    if "variable" in lowered:
        return "variable"
    if "fixed" in lowered:
        return "fixed"
    if "deferred" in lowered:
        return "deferred"
    if "immediate" in lowered:
        return "immediate"
    return "fixed"


def rate_annuity(
    bundle: SubmissionBundle,
    *,
    product_id: str | None = None,
    coverage_id: str | None = None,
    coverage_name: str | None = None,
) -> QuoteResult:
    """Illustrative annuity payout — a consultation, not an issueable premium."""
    factors = extract_life_factors(bundle)
    age = factors.age or 65
    sex = factors.sex if factors.sex in ("male", "female") else "male"
    blob = _blob(bundle)
    subtype = annuity_subtype(blob)

    principal = 0.0
    m = re.search(r"(?:principal|consideration|purchase price|premium)\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d+)?)", blob, re.I)
    if m:
        principal = float(m.group(1).replace(",", ""))
    if principal <= 0:
        principal = factors.income * 10.0 if factors.income else 500_000.0

    payout = illustrative_payout(principal=principal, age=age, sex=sex)
    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.LIFE,
        base_premium=0.0,
        adjusted_premium=0.0,
        eligible=False,
        ineligibility_reasons=["Annuity illustration only — requires a payout / consideration filing to issue"],
        metadata={
            "rating_engine": "annuity_illustration",
            "product_family": "annuity",
            "annuity_subtype": subtype,
            "product_id": product_id or "",
            "coverage_id": coverage_id or "",
            "coverage_name": coverage_name or "",
            "age": age,
            "sex": sex,
            "principal": principal,
            "illustrative_payout": payout,
        },
    )
