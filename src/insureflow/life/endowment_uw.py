"""Endowment Plan Underwriting.

Endowment policies combine life cover with a forced maturity savings component.
UW focus: high premium capacity, financial scrutiny, short-term parking detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EndowmentUWResult:
    """Endowment plan underwriting output."""

    # Inputs
    age: int = 30
    sex: str = "male"
    smoker: bool = False
    face_amount: float = 500_000.0
    annual_premium: float = 0.0
    term_years: int = 20
    income: float = 0.0
    net_worth: float = 0.0
    existing_premiums: float = 0.0
    purpose: str = ""
    # Results
    premium_to_income_pct: float = 0.0
    premium_capacity_pass: bool = False
    short_term_parking_risk: bool = False
    savings_ratio: float = 0.0
    commitment_years: int = 0
    persistency_risk: str = "low"
    risk_score: float = 0.0
    findings: list[str] = field(default_factory=list)
    decision: str = "REFER"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "product": "endowment",
            "premium_to_income_pct": self.premium_to_income_pct,
            "premium_capacity_pass": self.premium_capacity_pass,
            "short_term_parking_risk": self.short_term_parking_risk,
            "savings_ratio": self.savings_ratio,
            "commitment_years": self.commitment_years,
            "persistency_risk": self.persistency_risk,
            "risk_score": self.risk_score,
            "findings": self.findings,
            "decision": self.decision,
        }


def run_endowment_uw(
    *,
    age: int = 30,
    sex: str = "male",
    smoker: bool = False,
    face_amount: float = 500_000.0,
    annual_premium: float = 0.0,
    term_years: int = 20,
    income: float = 0.0,
    net_worth: float = 0.0,
    existing_premiums: float = 0.0,
    purpose: str = "",
    expected_maturity_value: float = 0.0,
) -> EndowmentUWResult:
    """Run endowment-specific underwriting.

    Endowment premiums are 3-5× higher than term for the same face amount.
    Underwriters must verify:
    1. Premium-to-income ratio (max 15-20% for endowment)
    2. Not a short-term capital parking vehicle
    3. Client can sustain high premiums for full term
    4. Persistency risk (lapse = lose savings component)
    """
    result = EndowmentUWResult(
        age=age,
        sex=sex,
        smoker=smoker,
        face_amount=face_amount,
        annual_premium=annual_premium,
        term_years=term_years,
        income=income,
        net_worth=net_worth,
        existing_premiums=existing_premiums,
        purpose=purpose,
    )
    findings: list[str] = []

    # ── 1. Premium Capacity ──────────────────────────────────────
    total_premiums = annual_premium + existing_premiums
    if income > 0:
        result.premium_to_income_pct = round((total_premiums / income) * 100, 1)
    # Endowment: stricter than term — max 15% of income
    result.premium_capacity_pass = result.premium_to_income_pct <= 15.0

    if result.premium_to_income_pct > 20.0:
        findings.append(f"CRITICAL: Premium-to-income ratio {result.premium_to_income_pct:.1f}% exceeds 20% — client cannot sustain endowment commitments")
    elif result.premium_to_income_pct > 15.0:
        findings.append(f"WARNING: Premium-to-income ratio {result.premium_to_income_pct:.1f}% exceeds 15% guideline for endowment plans")
    elif result.premium_to_income_pct > 0:
        findings.append(f"Premium-to-income ratio {result.premium_to_income_pct:.1f}% — within acceptable range")

    # ── 2. Short-Term Parking Detection ──────────────────────────
    # Red flags: very short term, high face relative to income, no stated purpose
    if term_years <= 5 and face_amount > income * 5:
        result.short_term_parking_risk = True
        findings.append(f"SHORT-TERM PARKING RISK: {term_years}-yr endowment with face ${face_amount:,.0f} vs income ${income:,.0f} — likely capital parking, not protection")
    elif not purpose and term_years <= 10:
        result.short_term_parking_risk = True
        findings.append(f"SHORT-TERM PARKING RISK: No stated purpose, {term_years}-yr term — client may be using endowment as investment vehicle")

    if purpose.lower() in ("investment", "tax_benefit", "tax_benefit_under_80c", "parking", "savings_only"):
        result.short_term_parking_risk = True
        findings.append(f"SHORT-TERM PARKING: Stated purpose '{purpose}' — endowment being used as investment, not protection. Verify suitability.")

    # ── 3. Savings Ratio ─────────────────────────────────────────
    # What % of premium goes to savings vs mortality charge
    if annual_premium > 0 and expected_maturity_value > 0:
        total_premiums_paid = annual_premium * term_years
        result.savings_ratio = round(expected_maturity_value / total_premiums_paid, 2)
        if result.savings_ratio < 0.80:
            findings.append(f"Savings ratio {result.savings_ratio:.2f} — maturity payout is less than 80% of total premiums paid. Poor savings efficiency.")

    # ── 4. Commitment & Persistency ──────────────────────────────
    result.commitment_years = term_years
    lapse_base = 0.03  # 3% base lapse rate
    if term_years > 15:
        lapse_base += 0.01  # longer terms have higher lapse
    if result.premium_to_income_pct > 15:
        lapse_base += 0.02  # affordability pressure increases lapse

    result.persistency_risk = "low"
    if lapse_base > 0.06:
        result.persistency_risk = "high"
    elif lapse_base > 0.04:
        result.persistency_risk = "moderate"

    if result.persistency_risk == "high":
        findings.append(f"Persistency risk: HIGH — {term_years}-yr commitment with {result.premium_to_income_pct:.1f}% premium burden")

    # ── 5. Risk Score & Decision ─────────────────────────────────
    score = 0.0
    if not result.premium_capacity_pass:
        score += 0.40
    if result.short_term_parking_risk:
        score += 0.35
    if result.persistency_risk == "high":
        score += 0.20
    elif result.persistency_risk == "moderate":
        score += 0.10
    if result.savings_ratio > 0 and result.savings_ratio < 0.80:
        score += 0.15

    result.risk_score = round(min(score, 1.0), 4)

    if score >= 0.70:
        result.decision = "DECLINE"
        findings.append("ENDOWMENT DECISION: DECLINE — unsuitable product for applicant")
    elif score >= 0.40:
        result.decision = "REFER"
        findings.append("ENDOWMENT DECISION: REFER — additional financial documentation required")
    else:
        result.decision = "APPROVE"

    result.findings = findings
    return result
