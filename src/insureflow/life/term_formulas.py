"""Term Life Insurance actuarial formulas.

Implements:
  - Discount factor v = 1/(1+i)
  - Survival / mortality probabilities
  - Actuarial Present Value of Benefits A_{x:n}^1
  - Actuarial Present Value of Premiums ä_{x:n}
  - Level Net Premium P (Equivalence Principle)
  - Prospective Reserve _tV
  - Recursive Reserve formula
  - Gross Premium Loading
  - Net Single Premium (NSP)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .mortality import k_p_x, k_q_x, q_x, v_k


@dataclass
class TermLifeQuote:
    """Complete term life insurance actuarial output."""

    # Inputs
    age: int = 30
    sex: str = "male"
    smoker: bool = False
    face_amount: float = 500_000.0
    term_years: int = 20
    interest_rate: float = 0.04  # 4% assumed investment return
    expense_loading_pct: float = 0.25  # 25% loading for expenses/commissions/tax/profit
    policy_fee: float = 60.0  # flat annual policy fee
    # Results
    nsp: float = 0.0  # Net Single Premium
    level_net_premium: float = 0.0  # P × face
    gross_premium: float = 0.0  # including loading
    present_value_benefits: float = 0.0
    present_value_premiums: float = 0.0
    reserves: list[float] = field(default_factory=list)
    # Per-year detail
    yearly_detail: list[dict[str, Any]] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "age": self.age,
            "sex": self.sex,
            "smoker": self.smoker,
            "face_amount": self.face_amount,
            "term_years": self.term_years,
            "interest_rate": self.interest_rate,
            "nsp": self.nsp,
            "level_net_premium": self.level_net_premium,
            "gross_premium": self.gross_premium,
            "present_value_benefits": self.present_value_benefits,
            "present_value_premiums": self.present_value_premiums,
            "reserves": self.reserves,
        }


def present_value_benefits(
    age: int,
    term: int,
    sex: str,
    smoker: bool,
    interest: float,
) -> float:
    """A_{x:n}^1 = Σ_{k=0}^{n-1} v^{k+1} × _k|q_x

    Actuarial Present Value of Benefits for an n-year term policy
    with unit ($1) death benefit.
    """
    total = 0.0
    for k in range(term):
        prob_death = k_q_x(age, k, sex, smoker)
        disc = v_k(interest, k + 1)
        total += disc * prob_death
    return round(total, 10)


def present_value_annuity_due(
    age: int,
    term: int,
    sex: str,
    smoker: bool,
    interest: float,
) -> float:
    """ä_{x:n} = Σ_{k=0}^{n-1} v^k × _k p_x

    Actuarial Present Value of a temporary life annuity-due
    (premiums paid at the beginning of each year while alive).
    """
    total = 0.0
    for k in range(term):
        surv = k_p_x(age, k, sex, smoker)
        disc = v_k(interest, k)
        total += disc * surv
    return round(total, 10)


def level_net_premium(
    age: int,
    term: int,
    sex: str,
    smoker: bool,
    interest: float,
) -> float:
    """P = A_{x:n}^1 / ä_{x:n}

    Equivalence Principle: the annual net premium per dollar of coverage
    where PV(future premiums) = PV(future benefits).
    """
    pvb = present_value_benefits(age, term, sex, smoker, interest)
    pva = present_value_annuity_due(age, term, sex, smoker, interest)
    if pva <= 0:
        return 0.0
    return round(pvb / pva, 10)


def net_single_premium(
    age: int,
    term: int,
    sex: str,
    smoker: bool,
    interest: float,
    face: float,
) -> float:
    """NSP = face × A_{x:n}^1

    The theoretical lump sum needed upfront to cover all expected claims.
    """
    return round(face * present_value_benefits(age, term, sex, smoker, interest), 2)


def gross_premium_with_loading(
    net_premium: float,
    face: float,
    loading_pct: float = 0.25,
    policy_fee: float = 60.0,
) -> float:
    """Gross Premium = Net Premium + Loading + Policy Fee

    Loading covers: admin expenses, commissions, taxes, profit margin.
    """
    loading = net_premium * loading_pct
    return round(net_premium + loading + policy_fee, 2)


def prospective_reserve(
    age: int,
    term: int,
    sex: str,
    smoker: bool,
    interest: float,
    net_premium_rate: float,
    duration: int,
) -> float:
    """_tV = A_{x+t:n-t}^1 − P × ä_{x+t:n-t}

    Prospective reserve at policy year t: the difference between the
    actuarial present value of remaining benefits and remaining premiums.
    """
    remaining = term - duration
    if remaining <= 0:
        return 0.0
    attained = age + duration
    pvb = present_value_benefits(attained, remaining, sex, smoker, interest)
    pva = present_value_annuity_due(attained, remaining, sex, smoker, interest)
    reserve = pvb - net_premium_rate * pva
    return round(reserve, 4)


def recursive_reserve(
    prev_reserve: float,
    net_premium: float,
    interest: float,
    mortality_prob: float,
    face: float,
    survival_prob: float,
) -> float:
    """(_tV + P)(1+i) = q_{x+t} × F + p_{x+t} × _{t+1}V

    Solving for _{t+1}V:
    _{t+1}V = [(_tV + P)(1+i) − q_{x+t} × F] / p_{x+t}
    """
    if survival_prob <= 0:
        return 0.0
    accumulated = (prev_reserve + net_premium) * (1.0 + interest)
    death_cost = mortality_prob * face
    terminal = (accumulated - death_cost) / survival_prob
    return round(terminal, 4)


def compute_full_quote(
    age: int,
    sex: str = "male",
    smoker: bool = False,
    face_amount: float = 500_000.0,
    term_years: int = 20,
    interest_rate: float = 0.04,
    expense_loading_pct: float = 0.25,
    policy_fee: float = 60.0,
) -> TermLifeQuote:
    """Compute the complete term life insurance quote with reserves."""
    quote = TermLifeQuote(
        age=age,
        sex=sex,
        smoker=smoker,
        face_amount=face_amount,
        term_years=term_years,
        interest_rate=interest_rate,
        expense_loading_pct=expense_loading_pct,
        policy_fee=policy_fee,
    )

    # Step 1: Present Value of Benefits
    pvb = present_value_benefits(age, term_years, sex, smoker, interest_rate)
    quote.present_value_benefits = round(pvb * face_amount, 2)

    # Step 2: Present Value of Annuity-Due
    pva = present_value_annuity_due(age, term_years, sex, smoker, interest_rate)
    quote.present_value_premiums = round(pva * face_amount, 2)

    # Step 3: NSP
    quote.nsp = net_single_premium(age, term_years, sex, smoker, interest_rate, face_amount)

    # Step 4: Level Net Premium (Equivalence Principle)
    p = level_net_premium(age, term_years, sex, smoker, interest_rate)
    quote.level_net_premium = round(p * face_amount, 2)

    # Step 5: Gross Premium with loading
    quote.gross_premium = gross_premium_with_loading(
        quote.level_net_premium,
        face_amount,
        expense_loading_pct,
        policy_fee,
    )

    # Step 6: Prospective Reserves for each policy year
    reserves = []
    yearly = []
    for t in range(term_years + 1):
        res = prospective_reserve(age, term_years, sex, smoker, interest_rate, p, t)
        reserves.append(round(res * face_amount, 2))
        yearly.append(
            {
                "year": t,
                "attained_age": age + t,
                "q_x": round(q_x(age + t, sex, smoker), 6),
                "survival_prob": round(k_p_x(age, t, sex, smoker), 6),
                "reserve": round(res * face_amount, 2),
            }
        )
    quote.reserves = reserves
    quote.yearly_detail = yearly

    return quote
