"""Annuity & Pension Underwriting.

Annuities pay an income stream at retirement — the inverse of life insurance.
UW focus: LONGEVITY RISK (not mortality), family longevity history,
payout risk scoring, suitability for immediate vs deferred annuities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .mortality import LIMITING_AGE, q_x


@dataclass
class AnnuityUWResult:
    """Annuity underwriting output."""

    # Inputs
    age: int = 55
    sex: str = "male"
    smoker: bool = False
    purchase_price: float = 500_000.0
    annuity_type: str = "immediate"  # immediate, deferred, joint, variable
    payout_frequency: str = "monthly"
    guaranteed_period: int = 10  # years of guaranteed payouts
    deferral_period: int = 0  # years until payouts start (deferred only)
    income: float = 0.0
    net_worth: float = 0.0
    # Family longevity
    parent_ages_at_death: list[int] = field(default_factory=list)
    # Results
    life_expectancy: float = 0.0
    payout_risk_years: float = 0.0
    longevity_premium: float = 0.0
    expected_total_payouts: float = 0.0
    family_longevity_factor: float = 1.0
    health_longevity_adjustment: float = 0.0
    risk_score: float = 0.0
    findings: list[str] = field(default_factory=list)
    decision: str = "REFER"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "product": "annuity",
            "annuity_type": self.annuity_type,
            "life_expectancy": self.life_expectancy,
            "payout_risk_years": self.payout_risk_years,
            "longevity_premium": self.longevity_premium,
            "expected_total_payouts": self.expected_total_payouts,
            "family_longevity_factor": self.family_longevity_factor,
            "health_longevity_adjustment": self.health_longevity_adjustment,
            "risk_score": self.risk_score,
            "findings": self.findings,
            "decision": self.decision,
        }


def _estimate_life_expectancy(age: int, sex: str, smoker: bool) -> float:
    """Estimate remaining life expectancy from mortality table.

    Uses the curtate life expectancy formula:
    e_x = Σ_{k=1}^{ω-x} k × _k|q_x
    """
    exp = 0.0
    max_years = LIMITING_AGE - age
    for k in range(1, max_years + 1):
        prob_die = 0.0
        for j in range(k):
            # Probability of dying in year k+1 given alive at age x+j
            surv = 1.0
            for m in range(j):
                surv *= 1 - q_x(age + m, sex, smoker)
            prob_die += surv * q_x(age + j, sex, smoker)
        exp += k * prob_die
    return round(exp, 1)


def _family_longevity_factor(parent_ages: list[int]) -> float:
    """Adjust longevity based on family history.

    Parents who lived past 80 → factor > 1.0 (longer expected life = higher payout)
    Parents who died before 65 → factor < 1.0 (shorter expected life = lower payout)
    """
    if not parent_ages:
        return 1.0
    avg = sum(parent_ages) / len(parent_ages)
    if avg >= 90:
        return 1.15  # exceptional longevity
    if avg >= 80:
        return 1.08  # above-average longevity
    if avg >= 70:
        return 1.00  # average
    if avg >= 60:
        return 0.92  # below average
    return 0.85  # significantly below average


def run_annuity_uw(
    *,
    age: int = 55,
    sex: str = "male",
    smoker: bool = False,
    purchase_price: float = 500_000.0,
    annuity_type: str = "immediate",
    payout_frequency: str = "monthly",
    guaranteed_period: int = 10,
    deferral_period: int = 0,
    income: float = 0.0,
    net_worth: float = 0.0,
    parent_ages_at_death: list[int] | None = None,
    has_heart_disease: bool = False,
    has_cancer_history: bool = False,
    has_diabetes: bool = False,
) -> AnnuityUWResult:
    """Run annuity-specific underwriting.

    Annuities are the INVERSE of life insurance:
    - Life insurance: insurer pays on DEATH → insurer wants you to live long
    - Annuity: insurer pays while ALIVE → insurer wants you to die soon

    For the CLIENT: longer life = more payouts = better deal.
    For the CARRIER: longer life = higher payout liability = more risk.

    UW considerations:
    1. Longevity risk: how long will the annuitant live?
    2. Family longevity history: parents' ages at death
    3. Health status: chronic conditions that may shorten life
    4. Suitability: is the annuity appropriate for the client's needs?
    5. Tax implications: annuity vs alternative income sources
    """
    parent_ages = parent_ages_at_death or []
    result = AnnuityUWResult(
        age=age,
        sex=sex,
        smoker=smoker,
        purchase_price=purchase_price,
        annuity_type=annuity_type,
        payout_frequency=payout_frequency,
        guaranteed_period=guaranteed_period,
        deferral_period=deferral_period,
        income=income,
        net_worth=net_worth,
        parent_ages_at_death=parent_ages,
    )
    findings: list[str] = []

    # ── 1. Life Expectancy ───────────────────────────────────────
    result.life_expectancy = _estimate_life_expectancy(age, sex, smoker)

    # ── 2. Family Longevity Factor ───────────────────────────────
    result.family_longevity_factor = _family_longevity_factor(parent_ages)
    if result.family_longevity_factor > 1.08:
        findings.append(f"LONGEVITY ALERT: Family history shows exceptional longevity (avg parent age at death: {sum(parent_ages) / len(parent_ages):.0f}) — higher payout risk for insurer")
    elif result.family_longevity_factor < 0.92:
        findings.append(f"Family longevity below average (avg parent age at death: {sum(parent_ages) / len(parent_ages):.0f}) — lower payout risk")

    # ── 3. Health Adjustment ─────────────────────────────────────
    result.health_longevity_adjustment = 0.0
    if has_heart_disease:
        result.health_longevity_adjustment -= 3.0
        findings.append("Heart disease history: -3 years life expectancy adjustment")
    if has_cancer_history:
        result.health_longevity_adjustment -= 2.0
        findings.append("Cancer history: -2 years life expectancy adjustment")
    if has_diabetes:
        result.health_longevity_adjustment -= 2.5
        findings.append("Diabetes: -2.5 years life expectancy adjustment")
    if smoker:
        result.health_longevity_adjustment -= 4.0
        findings.append("Smoker: -4 years life expectancy adjustment")

    adjusted_le = result.life_expectancy + result.health_longevity_adjustment
    adjusted_le = max(adjusted_le, 2.0)

    # ── 4. Payout Risk Calculation ───────────────────────────────
    # How many years of payouts the insurer expects to make
    if annuity_type == "deferred":
        payout_start = age + deferral_period
        remaining = max(0, LIMITING_AGE - payout_start)
        result.payout_risk_years = min(remaining, adjusted_le)
    else:
        result.payout_risk_years = adjusted_le

    # Expected total payouts
    if payout_frequency == "monthly":
        annual_payout = purchase_price * 0.06  # ~6% annual payout rate
        result.expected_total_payouts = round(annual_payout * result.payout_risk_years, 2)
    elif payout_frequency == "quarterly":
        annual_payout = purchase_price * 0.058
        result.expected_total_payouts = round(annual_payout * result.payout_risk_years, 2)
    else:  # annual
        annual_payout = purchase_price * 0.055
        result.expected_total_payouts = round(annual_payout * result.payout_risk_years, 2)

    # Longevity premium: how much extra the insurer should charge
    result.longevity_premium = round(
        max(0, result.expected_total_payouts - purchase_price) / purchase_price * 100,
        2,
    )

    findings.append(f"Adjusted life expectancy: {adjusted_le:.1f} years, payout risk: {result.payout_risk_years:.1f} years, expected total payouts: ${result.expected_total_payouts:,.0f}")

    # ── 5. Suitability Checks ────────────────────────────────────
    if annuity_type == "immediate" and age < 50:
        findings.append(f"WARNING: Immediate annuity at age {age} — very long payout horizon, consider deferred annuity instead")

    if purchase_price > net_worth * 0.60 and net_worth > 0:
        findings.append(f"WARNING: Annuity purchase price ${purchase_price:,.0f} is {(purchase_price / net_worth * 100):.0f}% of net worth — concentration risk")

    if income > 0 and purchase_price > income * 10:
        findings.append(f"Annuity purchase price is {purchase_price / income:.1f}× annual income — verify client has sufficient liquid assets")

    # ── 6. Risk Score & Decision ─────────────────────────────────
    score = 0.0
    if result.family_longevity_factor > 1.10:
        score += 0.25
    if adjusted_le > 25:
        score += 0.20
    if purchase_price > net_worth * 0.60 and net_worth > 0:
        score += 0.20
    if annuity_type == "immediate" and age < 50:
        score += 0.15
    if result.longevity_premium > 30:
        score += 0.15

    result.risk_score = round(min(score, 1.0), 4)

    if score >= 0.60:
        result.decision = "DECLINE"
        findings.append("ANNUITY DECISION: DECLINE — excessive longevity/payout risk")
    elif score >= 0.30:
        result.decision = "REFER"
        findings.append("ANNUITY DECISION: REFER — longevity risk requires actuarial review")
    else:
        result.decision = "APPROVE"

    result.findings = findings
    return result
