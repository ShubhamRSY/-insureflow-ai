"""Money-Back Policy Underwriting.

Money-back policies pay survival benefits at regular intervals during the term.
UW focus: cash-flow matching, persistency/lapse risk, savings vs protection balance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MoneyBackUWResult:
    """Money-back policy underwriting output."""

    # Inputs
    age: int = 30
    sex: str = "male"
    smoker: bool = False
    face_amount: float = 500_000.0
    annual_premium: float = 0.0
    term_years: int = 20
    income: float = 0.0
    payout_schedule: str = "every_5_years"  # every_5_years, every_3_years, every_year, end_only
    survival_benefit_pct: float = 20.0  # % of sum assured paid at each interval
    # Results
    total_survival_benefits: float = 0.0
    net_protection_after_benefits: float = 0.0
    premium_to_income_pct: float = 0.0
    cash_flow_gap_risk: str = "low"
    persistency_risk: str = "low"
    lapse_probability: float = 0.0
    risk_score: float = 0.0
    findings: list[str] = field(default_factory=list)
    decision: str = "REFER"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "product": "money_back",
            "total_survival_benefits": self.total_survival_benefits,
            "net_protection_after_benefits": self.net_protection_after_benefits,
            "premium_to_income_pct": self.premium_to_income_pct,
            "cash_flow_gap_risk": self.cash_flow_gap_risk,
            "persistency_risk": self.persistency_risk,
            "lapse_probability": self.lapse_probability,
            "risk_score": self.risk_score,
            "findings": self.findings,
            "decision": self.decision,
        }


def _payout_count(term: int, schedule: str) -> int:
    """Number of survival benefit payouts during the term."""
    if schedule == "every_year":
        return max(0, term - 1)
    if schedule == "every_3_years":
        return max(0, (term - 1) // 3)
    if schedule == "every_5_years":
        return max(0, (term - 1) // 5)
    return 0  # end_only


def run_money_back_uw(
    *,
    age: int = 30,
    sex: str = "male",
    smoker: bool = False,
    face_amount: float = 500_000.0,
    annual_premium: float = 0.0,
    term_years: int = 20,
    income: float = 0.0,
    payout_schedule: str = "every_5_years",
    survival_benefit_pct: float = 20.0,
    existing_liabilities: float = 0.0,
    purpose: str = "",
) -> MoneyBackUWResult:
    """Run money-back policy underwriting.

    Key UW concerns:
    1. Cash-flow matching: do survival benefit timing align with client's needs?
    2. Persistency: will the client lapse after receiving survival benefits?
    3. Net protection: how much death benefit remains after survival payouts?
    4. Lapse risk: treating policy as savings account = high lapse probability
    """
    result = MoneyBackUWResult(
        age=age,
        sex=sex,
        smoker=smoker,
        face_amount=face_amount,
        annual_premium=annual_premium,
        term_years=term_years,
        income=income,
        payout_schedule=payout_schedule,
        survival_benefit_pct=survival_benefit_pct,
    )
    findings: list[str] = []

    # ── 1. Survival Benefits Calculation ─────────────────────────
    payouts = _payout_count(term_years, payout_schedule)
    result.total_survival_benefits = round(
        face_amount * (survival_benefit_pct / 100) * payouts,
        2,
    )
    result.net_protection_after_benefits = round(
        face_amount - result.total_survival_benefits,
        2,
    )

    if result.net_protection_after_benefits <= 0:
        findings.append(f"CRITICAL: Total survival benefits (${result.total_survival_benefits:,.0f}) exceed face amount (${face_amount:,.0f}) — no death benefit remains")
    elif result.net_protection_after_benefits < face_amount * 0.30:
        findings.append(
            f"WARNING: Net protection after survival benefits is only ${result.net_protection_after_benefits:,.0f} ({(result.net_protection_after_benefits / face_amount * 100):.0f}% of face)"
        )

    # ── 2. Premium Capacity ──────────────────────────────────────
    if income > 0:
        result.premium_to_income_pct = round((annual_premium / income) * 100, 1)
    if result.premium_to_income_pct > 15:
        findings.append(f"Premium-to-income {result.premium_to_income_pct:.1f}% — exceeds 15% guideline for money-back policies")

    # ── 3. Cash-Flow Gap Risk ────────────────────────────────────
    # Does the payout timing match the client's cash-flow needs?
    result.cash_flow_gap_risk = "low"
    if purpose.lower() in ("children_education", "marriage", "retirement"):
        if payout_schedule == "every_5_years":
            result.cash_flow_gap_risk = "moderate"
            findings.append(f"CASH FLOW GAP: Purpose is '{purpose}' but payout is every 5 years — may not align with cash-flow needs")
    elif not purpose:
        result.cash_flow_gap_risk = "moderate"
        findings.append("No stated purpose — cash-flow alignment cannot be verified")

    # ── 4. Persistency / Lapse Risk ──────────────────────────────
    # Policyholders who receive survival benefits often lapse after
    base_lapse = 0.04  # 4% base lapse
    if payout_schedule == "every_year":
        base_lapse += 0.03  # annual payouts increase lapse temptation
    elif payout_schedule == "every_3_years":
        base_lapse += 0.02
    if result.premium_to_income_pct > 12:
        base_lapse += 0.02  # affordability pressure
    if result.total_survival_benefits > face_amount * 0.50:
        base_lapse += 0.01  # after receiving >50% of face, clients lapse

    result.lapse_probability = round(min(base_lapse, 0.25), 4)
    result.persistency_risk = "low"
    if base_lapse > 0.08:
        result.persistency_risk = "high"
        findings.append(f"PERSISTENCY RISK: HIGH — {base_lapse:.1%} estimated lapse probability. Client may lapse after receiving survival benefits.")
    elif base_lapse > 0.05:
        result.persistency_risk = "moderate"
        findings.append(f"Persistency risk: MODERATE — {base_lapse:.1%} lapse probability")

    # ── 5. Savings vs Protection Balance ──────────────────────────
    if annual_premium > 0 and term_years > 0:
        total_premiums = annual_premium * term_years
        savings_component = result.total_survival_benefits
        if total_premiums > 0:
            savings_ratio = round(savings_component / total_premiums, 2)
            if savings_ratio < 0.70:
                findings.append(f"Savings efficiency: {savings_ratio:.2f} — survival benefits are less than 70% of total premiums paid. Consider endowment instead.")

    # ── 6. Risk Score & Decision ─────────────────────────────────
    score = 0.0
    if result.net_protection_after_benefits <= 0:
        score += 0.35
    if result.persistency_risk == "high":
        score += 0.25
    elif result.persistency_risk == "moderate":
        score += 0.10
    if result.premium_to_income_pct > 15:
        score += 0.20
    if result.cash_flow_gap_risk == "moderate":
        score += 0.10

    result.risk_score = round(min(score, 1.0), 4)

    if score >= 0.60:
        result.decision = "DECLINE"
        findings.append("MONEY-BACK DECISION: DECLINE — unsuitable structure for applicant")
    elif score >= 0.30:
        result.decision = "REFER"
        findings.append("MONEY-BACK DECISION: REFER — persistency/cash-flow concerns")
    else:
        result.decision = "APPROVE"

    result.findings = findings
    return result
