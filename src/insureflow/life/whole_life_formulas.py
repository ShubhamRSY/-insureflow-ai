"""Whole Life Insurance actuarial formulas.

Implements:
  - Actuarial Present Value of Whole Life Benefits A_x
  - Whole Life Annuity-Due ä_x
  - Level Annual Net Premium P_x
  - Cash Value (Prospective Reserve) _tV
  - Retrospective Cash Value formula
  - Standard Nonforfeiture CSV
  - Final Net Cash Surrender Value
  - 20-Pay and Limited Pay variants
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .mortality import LIMITING_AGE, k_p_x, k_q_x, q_x, v_k


@dataclass
class WholeLifeQuote:
    """Complete whole life insurance actuarial output."""

    # Inputs
    age: int = 30
    sex: str = "male"
    smoker: bool = False
    face_amount: float = 500_000.0
    interest_rate: float = 0.04
    expense_loading_pct: float = 0.30
    policy_fee: float = 75.0
    premium_term: int = 0  # 0 = lifetime, 20 = 20-pay, etc.
    surrender_charge_years: int = 15
    # Results
    pv_whole_life_benefits: float = 0.0  # A_x
    whole_life_annuity_due: float = 0.0  # ä_x
    level_net_premium: float = 0.0  # P_x × face
    gross_premium: float = 0.0
    reserves: list[float] = field(default_factory=list)
    cash_values: list[float] = field(default_factory=list)
    csv_values: list[float] = field(default_factory=list)
    yearly_detail: list[dict[str, Any]] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "age": self.age,
            "sex": self.sex,
            "smoker": self.smoker,
            "face_amount": self.face_amount,
            "interest_rate": self.interest_rate,
            "premium_term": self.premium_term,
            "pv_whole_life_benefits": self.pv_whole_life_benefits,
            "whole_life_annuity_due": self.whole_life_annuity_due,
            "level_net_premium": self.level_net_premium,
            "gross_premium": self.gross_premium,
            "reserves": self.reserves[-1] if self.reserves else 0.0,
            "cash_values": self.cash_values[-1] if self.cash_values else 0.0,
        }


def pv_whole_life_benefits(
    age: int,
    sex: str,
    smoker: bool,
    interest: float,
) -> float:
    """A_x = Σ_{k=0}^{ω-x-1} v^{k+1} × _k|q_x

    Actuarial Present Value of whole life benefits (unit benefit).
    Sums over the entire lifetime (to limiting age ω).
    """
    total = 0.0
    max_years = LIMITING_AGE - age
    for k in range(max_years):
        prob_death = k_q_x(age, k, sex, smoker)
        disc = v_k(interest, k + 1)
        total += disc * prob_death
    return round(total, 10)


def whole_life_annuity_due(
    age: int,
    sex: str,
    smoker: bool,
    interest: float,
) -> float:
    """ä_x = Σ_{k=0}^{ω-x-1} v^k × _k p_x

    Whole life annuity-due: present value of $1 paid at the beginning
    of each year while the insured survives.
    """
    total = 0.0
    max_years = LIMITING_AGE - age
    for k in range(max_years):
        surv = k_p_x(age, k, sex, smoker)
        disc = v_k(interest, k)
        total += disc * surv
    return round(total, 10)


def whole_life_net_premium(
    age: int,
    sex: str,
    smoker: bool,
    interest: float,
    premium_term: int = 0,
) -> float:
    """P_x = A_x / ä_x  (lifetime pay)
    P_{x:n} = A_x / ä_{x:n}  (limited pay, n years)

    Equivalence Principle applied to whole life benefits.
    """
    ax = pv_whole_life_benefits(age, sex, smoker, interest)
    if premium_term > 0:
        aix = whole_life_annuity_due_limited(age, premium_term, sex, smoker, interest)
    else:
        aix = whole_life_annuity_due(age, sex, smoker, interest)
    if aix <= 0:
        return 0.0
    return round(ax / aix, 10)


def whole_life_annuity_due_limited(
    age: int,
    term: int,
    sex: str,
    smoker: bool,
    interest: float,
) -> float:
    """ä_{x:n} = Σ_{k=0}^{n-1} v^k × _k p_x

    Temporary life annuity-due for limited-pay whole life.
    """
    total = 0.0
    for k in range(term):
        surv = k_p_x(age, k, sex, smoker)
        disc = v_k(interest, k)
        total += disc * surv
    return round(total, 10)


def prospective_reserve_whole_life(
    age: int,
    sex: str,
    smoker: bool,
    interest: float,
    net_premium_rate: float,
    duration: int,
    premium_term: int = 0,
) -> float:
    """_tV = A_{x+t} − P × ä_{x+t:n-t}

    For lifetime pay: _tV = A_{x+t} − P × ä_{x+t}
    For limited pay after premium period: _tV = A_{x+t} (no more premiums)
    """
    attained = age + duration
    if attained >= LIMITING_AGE:
        return 0.0

    ax_t = pv_whole_life_benefits(attained, sex, smoker, interest)

    if premium_term > 0 and duration >= premium_term:
        # Premiums fully paid — reserve equals remaining benefit PV
        return round(ax_t, 4)
    elif premium_term > 0:
        remaining_pay = premium_term - duration
        aix_t = whole_life_annuity_due_limited(attained, remaining_pay, sex, smoker, interest)
    else:
        aix_t = whole_life_annuity_due(attained, sex, smoker, interest)

    reserve = ax_t - net_premium_rate * aix_t
    return round(reserve, 4)


def retrospective_cash_value(
    accumulated_past_premiums: float,
    interest_earned: float,
    claims_paid: float,
    survival_prob: float,
) -> float:
    """_tV = [(P + _t-1V)(1+i) − q_{x+t-1} × 1] / p_{x+t-1}

    Retrospective reserve: accumulated past premiums + interest − claims,
    normalized by survival probability.
    """
    if survival_prob <= 0:
        return 0.0
    return round((accumulated_past_premiums + interest_earned - claims_paid) / survival_prob, 4)


def standard_nonforfeiture_csv(
    pv_future_benefits: float,
    pv_adjusted_premiums: float,
    face_amount: float,
) -> float:
    """CSV = PV(Future Benefits) − PV(Future Adjusted Premiums)

    Adjusted premiums amortize heavy first-year acquisition expenses
    (commissions, underwriting costs) over the premium-paying period.
    The initial expense allowance is typically 1% of face + % of gross premium.
    """
    return round(max(0.0, pv_future_benefits - pv_adjusted_premiums) * face_amount, 2)


def surrender_charges(
    year: int,
    max_years: int = 15,
    max_charge_pct: float = 0.10,
) -> float:
    """Surrender charges scale linearly from max to zero over max_years."""
    if year >= max_years:
        return 0.0
    return round(max_charge_pct * (1.0 - year / max_years), 6)


def net_cash_surrender_value(
    guaranteed_cash_value: float,
    year: int,
    policy_loans: float = 0.0,
    dividend_additions: float = 0.0,
    face_amount: float = 500_000.0,
    max_surrender_years: int = 15,
    max_charge_pct: float = 0.10,
) -> float:
    """Net CSV = Guaranteed CSV − Surrender Charges − Loans + Dividends

    The final amount paid to the policyholder upon surrender.
    """
    charge = surrender_charges(year, max_surrender_years, max_charge_pct) * face_amount
    return round(
        guaranteed_cash_value - charge - policy_loans + dividend_additions,
        2,
    )


def compute_full_whole_life_quote(
    age: int,
    sex: str = "male",
    smoker: bool = False,
    face_amount: float = 500_000.0,
    interest_rate: float = 0.04,
    expense_loading_pct: float = 0.30,
    policy_fee: float = 75.0,
    premium_term: int = 0,
    surrender_charge_years: int = 15,
) -> WholeLifeQuote:
    """Compute complete whole life insurance quote with reserves and CSV."""
    quote = WholeLifeQuote(
        age=age,
        sex=sex,
        smoker=smoker,
        face_amount=face_amount,
        interest_rate=interest_rate,
        expense_loading_pct=expense_loading_pct,
        policy_fee=policy_fee,
        premium_term=premium_term,
        surrender_charge_years=surrender_charge_years,
    )

    # Step 1: A_x
    ax = pv_whole_life_benefits(age, sex, smoker, interest_rate)
    quote.pv_whole_life_benefits = round(ax * face_amount, 2)

    # Step 2: ä_x or ä_{x:n}
    if premium_term > 0:
        aix = whole_life_annuity_due_limited(age, premium_term, sex, smoker, interest_rate)
    else:
        aix = whole_life_annuity_due(age, sex, smoker, interest_rate)
    quote.whole_life_annuity_due = round(aix * face_amount, 2)

    # Step 3: Net Premium
    p = whole_life_net_premium(age, sex, smoker, interest_rate, premium_term)
    quote.level_net_premium = round(p * face_amount, 2)

    # Step 4: Gross Premium
    loading = quote.level_net_premium * expense_loading_pct
    quote.gross_premium = round(quote.level_net_premium + loading + policy_fee, 2)

    # Step 5: Year-by-year reserves and cash values
    reserves = []
    cash_values = []
    yearly = []
    max_years = LIMITING_AGE - age

    for t in range(max_years + 1):
        res = prospective_reserve_whole_life(
            age,
            sex,
            smoker,
            interest_rate,
            p,
            t,
            premium_term,
        )
        res_dollar = round(res * face_amount, 2)
        reserves.append(res_dollar)

        # Cash value ≈ reserve after surrender charges
        csv = net_cash_surrender_value(
            res_dollar,
            t,
            face_amount=face_amount,
            max_surrender_years=surrender_charge_years,
        )
        cash_values.append(csv)

        yearly.append(
            {
                "year": t,
                "attained_age": age + t,
                "q_x": round(q_x(age + t, sex, smoker), 6),
                "survival_prob": round(k_p_x(age, t, sex, smoker), 6),
                "reserve": res_dollar,
                "cash_value": csv,
            }
        )

    quote.reserves = reserves
    quote.cash_values = cash_values
    quote.yearly_detail = yearly

    return quote
