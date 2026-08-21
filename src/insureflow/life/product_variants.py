"""Term Life Insurance product variants.

Implements:
  - Decreasing Term: face reduces annually (e.g., mortgage-matching)
  - Increasing Term: face increases by fixed % or COLI
  - Convertible Term: conversion privilege to permanent without evidence
  - Renewable Term: automatic renewal right, premium steps up at attained age
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .mortality import k_p_x, k_q_x, q_x
from .term_formulas import (
    level_net_premium as term_level_net_premium,
)
from .term_formulas import (
    present_value_annuity_due,
)


@dataclass
class DecreasingTermQuote:
    """Decreasing term: face reduces annually, premium is level."""

    age: int = 30
    sex: str = "male"
    smoker: bool = False
    initial_face: float = 500_000.0
    term_years: int = 20
    interest_rate: float = 0.04
    reduction_rate: float = 0.0  # annual % reduction (0 = match amortization)
    amortize: bool = False  # True = reduction matches mortgage amortization
    annual_rate_pct: float = 5.5  # mortgage rate for amortization calc
    level_premium: float = 0.0
    yearly_detail: list[dict[str, Any]] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "variant": "decreasing_term",
            "age": self.age,
            "initial_face": self.initial_face,
            "term_years": self.term_years,
            "level_premium": self.level_premium,
            "amortize": self.amortize,
        }


@dataclass
class IncreasingTermQuote:
    """Increasing term: face increases annually by fixed percentage."""

    age: int = 30
    sex: str = "male"
    smoker: bool = False
    initial_face: float = 500_000.0
    term_years: int = 20
    interest_rate: float = 0.04
    annual_increase_pct: float = 3.0  # 3% per year
    use_coli: bool = False  # True = increase tied to Cost of Living Index
    coli_rate: float = 2.5  # assumed COLI rate
    level_premium: float = 0.0
    yearly_detail: list[dict[str, Any]] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "variant": "increasing_term",
            "age": self.age,
            "initial_face": self.initial_face,
            "term_years": self.term_years,
            "annual_increase_pct": self.annual_increase_pct,
            "level_premium": self.level_premium,
        }


@dataclass
class ConvertibleTermQuote:
    """Convertible term: conversion privilege to permanent without evidence."""

    age: int = 30
    sex: str = "male"
    smoker: bool = False
    face_amount: float = 500_000.0
    term_years: int = 20
    interest_rate: float = 0.04
    convert_to: str = "whole_life"  # whole_life, universal_life, endowment
    convert_by_age: int = 65  # must convert before this age
    no_evidence: bool = True  # no new medical exam required
    level_premium: float = 0.0
    # Premium comparison
    term_premium: float = 0.0
    converted_premium: float = 0.0
    yearly_detail: list[dict[str, Any]] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "variant": "convertible_term",
            "age": self.age,
            "face_amount": self.face_amount,
            "term_years": self.term_years,
            "convert_to": self.convert_to,
            "convert_by_age": self.convert_by_age,
            "no_evidence": self.no_evidence,
            "term_premium": self.term_premium,
            "converted_premium": self.converted_premium,
        }


@dataclass
class RenewableTermQuote:
    """Renewable term: automatic renewal right without evidence."""

    age: int = 30
    sex: str = "male"
    smoker: bool = False
    face_amount: float = 500_000.0
    initial_term_years: int = 10
    max_renewal_age: int = 75
    interest_rate: float = 0.04
    renewal_periods: list[dict[str, Any]] = field(default_factory=list)
    yearly_detail: list[dict[str, Any]] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "variant": "renewable_term",
            "age": self.age,
            "face_amount": self.face_amount,
            "initial_term_years": self.initial_term_years,
            "max_renewal_age": self.max_renewal_age,
            "renewal_periods": self.renewal_periods,
        }


def _mortgage_balance(
    principal: float,
    annual_rate_pct: float,
    term_years: int,
    year: int,
) -> float:
    """Remaining balance on a standard amortizing mortgage."""
    r = annual_rate_pct / 100.0 / 12.0
    n = term_years * 12
    if r <= 0:
        return max(0.0, principal * (1.0 - year / term_years))
    payment = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    balance = principal
    months_elapsed = min(year * 12, n)
    for _ in range(months_elapsed):
        interest = balance * r
        principal_paid = payment - interest
        balance -= principal_paid
    return round(max(0.0, balance), 2)


def compute_decreasing_term(
    age: int,
    sex: str = "male",
    smoker: bool = False,
    initial_face: float = 500_000.0,
    term_years: int = 20,
    interest_rate: float = 0.04,
    reduction_rate: float = 0.0,
    amortize: bool = False,
    annual_rate_pct: float = 5.5,
) -> DecreasingTermQuote:
    """Decreasing term: face reduces annually, premium is level.

    If amortize=True, face matches mortgage amortization schedule.
    If reduction_rate > 0, face decreases by that % each year.
    Otherwise face decreases linearly to zero at term end.
    """
    quote = DecreasingTermQuote(
        age=age,
        sex=sex,
        smoker=smoker,
        initial_face=initial_face,
        term_years=term_years,
        interest_rate=interest_rate,
        reduction_rate=reduction_rate,
        amortize=amortize,
        annual_rate_pct=annual_rate_pct,
    )

    # Compute PV of decreasing death benefits
    total_pvb = 0.0
    for k in range(term_years):
        face_k = _decreasing_face(
            initial_face,
            term_years,
            k,
            reduction_rate,
            amortize,
            annual_rate_pct,
        )
        prob_death = k_q_x(age, k, sex, smoker)
        disc = (1.0 / (1.0 + interest_rate)) ** (k + 1)
        total_pvb += disc * prob_death * face_k

    # Level premium via equivalence principle
    pva = present_value_annuity_due(age, term_years, sex, smoker, interest_rate)
    if pva > 0:
        quote.level_premium = round(total_pvb / pva, 2)

    # Yearly detail
    yearly = []
    for t in range(term_years + 1):
        face_t = _decreasing_face(
            initial_face,
            term_years,
            t,
            reduction_rate,
            amortize,
            annual_rate_pct,
        )
        yearly.append(
            {
                "year": t,
                "attained_age": age + t,
                "face_amount": round(face_t, 2),
                "q_x": round(q_x(age + t, sex, smoker), 6),
                "survival_prob": round(k_p_x(age, t, sex, smoker), 6),
            }
        )
    quote.yearly_detail = yearly

    return quote


def _decreasing_face(
    initial: float,
    term: int,
    year: int,
    reduction_rate: float,
    amortize: bool,
    annual_rate_pct: float,
) -> float:
    """Calculate the face amount at a given policy year."""
    if amortize:
        return _mortgage_balance(initial, annual_rate_pct, term, year)
    if reduction_rate > 0:
        return round(initial * (1.0 - reduction_rate / 100.0) ** year, 2)
    # Linear decrease to zero
    if term <= 0:
        return initial
    return round(initial * max(0.0, 1.0 - year / term), 2)


def compute_increasing_term(
    age: int,
    sex: str = "male",
    smoker: bool = False,
    initial_face: float = 500_000.0,
    term_years: int = 20,
    interest_rate: float = 0.04,
    annual_increase_pct: float = 3.0,
    use_coli: bool = False,
    coli_rate: float = 2.5,
) -> IncreasingTermQuote:
    """Increasing term: face increases annually by fixed %, premium is level."""
    quote = IncreasingTermQuote(
        age=age,
        sex=sex,
        smoker=smoker,
        initial_face=initial_face,
        term_years=term_years,
        interest_rate=interest_rate,
        annual_increase_pct=annual_increase_pct,
        use_coli=use_coli,
        coli_rate=coli_rate,
    )

    increase = coli_rate if use_coli else annual_increase_pct

    # PV of increasing death benefits
    total_pvb = 0.0
    for k in range(term_years):
        face_k = initial_face * (1.0 + increase / 100.0) ** k
        prob_death = k_q_x(age, k, sex, smoker)
        disc = (1.0 / (1.0 + interest_rate)) ** (k + 1)
        total_pvb += disc * prob_death * face_k

    pva = present_value_annuity_due(age, term_years, sex, smoker, interest_rate)
    if pva > 0:
        quote.level_premium = round(total_pvb / pva, 2)

    yearly = []
    for t in range(term_years + 1):
        face_t = initial_face * (1.0 + increase / 100.0) ** t
        yearly.append(
            {
                "year": t,
                "attained_age": age + t,
                "face_amount": round(face_t, 2),
                "q_x": round(q_x(age + t, sex, smoker), 6),
                "survival_prob": round(k_p_x(age, t, sex, smoker), 6),
            }
        )
    quote.yearly_detail = yearly

    return quote


def compute_convertible_term(
    age: int,
    sex: str = "male",
    smoker: bool = False,
    face_amount: float = 500_000.0,
    term_years: int = 20,
    interest_rate: float = 0.04,
    convert_to: str = "whole_life",
    convert_by_age: int = 65,
) -> ConvertibleTermQuote:
    """Convertible term: same premium as level term, plus conversion privilege.

    The conversion value is the guaranteed issue amount for the permanent
    product — no new medical exam required (no evidence of insurability).
    """
    quote = ConvertibleTermQuote(
        age=age,
        sex=sex,
        smoker=smoker,
        face_amount=face_amount,
        term_years=term_years,
        interest_rate=interest_rate,
        convert_to=convert_to,
        convert_by_age=convert_by_age,
    )

    # Level term premium
    p = term_level_net_premium(age, term_years, sex, smoker, interest_rate)
    quote.level_premium = round(p * face_amount, 2)
    quote.term_premium = quote.level_premium

    # Converted premium estimate (whole life rate — higher than term)
    from .whole_life_formulas import whole_life_net_premium

    wl_p = whole_life_net_premium(age, sex, smoker, interest_rate)
    quote.converted_premium = round(wl_p * face_amount * 1.30, 2)  # 30% loading for permanent

    yearly = []
    for t in range(term_years + 1):
        can_convert = (age + t) <= convert_by_age
        yearly.append(
            {
                "year": t,
                "attained_age": age + t,
                "face_amount": face_amount,
                "can_convert": can_convert,
                "q_x": round(q_x(age + t, sex, smoker), 6),
                "survival_prob": round(k_p_x(age, t, sex, smoker), 6),
            }
        )
    quote.yearly_detail = yearly

    return quote


def compute_renewable_term(
    age: int,
    sex: str = "male",
    smoker: bool = False,
    face_amount: float = 500_000.0,
    initial_term_years: int = 10,
    max_renewal_age: int = 75,
    interest_rate: float = 0.04,
) -> RenewableTermQuote:
    """Renewable term: guaranteed renewal right at attained age, no evidence.

    Each renewal period uses the premium rate for the attained age at renewal.
    """
    quote = RenewableTermQuote(
        age=age,
        sex=sex,
        smoker=smoker,
        face_amount=face_amount,
        initial_term_years=initial_term_years,
        max_renewal_age=max_renewal_age,
        interest_rate=interest_rate,
    )

    renewals: list[dict[str, Any]] = []
    current_age = age

    while current_age < max_renewal_age:
        remaining = min(initial_term_years, max_renewal_age - current_age)
        p = term_level_net_premium(current_age, remaining, sex, smoker, interest_rate)
        premium = round(p * face_amount, 2)

        renewals.append(
            {
                "renewal_period": len(renewals) + 1,
                "start_age": current_age,
                "end_age": current_age + remaining,
                "term_years": remaining,
                "annual_premium": premium,
            }
        )

        if len(renewals) == 1:
            pass

        current_age += initial_term_years

    quote.renewal_periods = renewals

    yearly = []
    for t in range(max_renewal_age - age + 1):
        att = age + t
        yearly.append(
            {
                "year": t,
                "attained_age": att,
                "face_amount": face_amount,
                "q_x": round(q_x(att, sex, smoker), 6),
                "survival_prob": round(k_p_x(age, t, sex, smoker), 6),
            }
        )
    quote.yearly_detail = yearly

    return quote
