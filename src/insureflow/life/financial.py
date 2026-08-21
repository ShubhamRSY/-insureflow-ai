"""Step 4 — Financial Underwriting & Needs Analysis.

HLV / income multiples, net worth for estate cases, table rating formulas,
and reinsurance cession calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.life_financial import LifeFinancialResult, evaluate_life_financial
from insureflow.underwriting.life_reinsurance import LifeReinsuranceResult, evaluate_life_reinsurance
from insureflow.underwriting.personal_lines import _blob, extract_life_factors

# Age-based income multiples (HLV-derived)
AGE_INCOME_MULTIPLIERS: list[dict[str, Any]] = [
    {"min_age": 0, "max_age": 30, "low": 25, "high": 30, "label": "Ages 18–30"},
    {"min_age": 31, "max_age": 40, "low": 20, "high": 25, "label": "Ages 31–40"},
    {"min_age": 41, "max_age": 50, "low": 15, "high": 20, "label": "Ages 41–50"},
    {"min_age": 51, "max_age": 60, "low": 10, "high": 15, "label": "Ages 51–60"},
    {"min_age": 61, "max_age": 120, "low": 5, "high": 5, "label": "Ages 60+"},
]


def get_age_income_multiplier(age: int | None) -> dict[str, Any]:
    if not age:
        return {"low": 20, "high": 25, "label": "Unknown age (defaulting to 20×–25×)"}
    for band in AGE_INCOME_MULTIPLIERS:
        if band["min_age"] <= age <= band["max_age"]:
            return band
    return AGE_INCOME_MULTIPLIERS[-1]


def calculate_hlv(annual_income: float, age: int | None) -> dict[str, Any]:
    """Human Life Value = Annual Income × Age Multiplier."""
    band = get_age_income_multiplier(age)
    max_face_low = annual_income * band["low"]
    max_face_high = annual_income * band["high"]
    return {
        "annual_income": annual_income,
        "age_band": band["label"],
        "multiplier_low": band["low"],
        "multiplier_high": band["high"],
        "max_face_low": round(max_face_low, 2),
        "max_face_high": round(max_face_high, 2),
        "hlv_midpoint": round((max_face_low + max_face_high) / 2, 2),
    }


def calculate_estate_face_amount(net_worth: float, tax_pct: float = 0.15) -> float:
    """Net Worth Multiple for estate/wealth preservation cases.
    Max Estate Face Amount = Net Worth × Expected Tax/Liquidity Percentage
    Typically capped at 10–20% of net worth.
    """
    return round(net_worth * tax_pct, 2)


def calculate_table_rating_surcharge(table_index: int) -> dict[str, Any]:
    """Table Rating Premium Surcharge.
    Each table step increases the base standard premium by 25%.
    Final Premium = Standard Premium × (1 + 0.25 × Table Index)
    """
    surcharge_pct = 0.25 * table_index
    multiplier = 1.0 + surcharge_pct
    # Map index to letter
    letter = chr(ord("A") + table_index - 1) if 1 <= table_index <= 16 else f"T{table_index}"
    return {
        "table_index": table_index,
        "table_letter": f"Table {letter}",
        "surcharge_pct": round(surcharge_pct * 100, 1),
        "multiplier": round(multiplier, 2),
        "description": f"Table {letter} adds {surcharge_pct * 100:.0f}% surcharge ({multiplier:.2f}× standard premium)",
    }


def calculate_facultative_cession(face_amount: float, retention_limit: float) -> dict[str, Any]:
    """Facultative Cession = Requested Face - Company Retention Limit."""
    cession = max(0.0, face_amount - retention_limit)
    return {
        "requested_face": face_amount,
        "retention_limit": retention_limit,
        "cessation_amount": round(cession, 2),
        "retained_in_house": round(min(face_amount, retention_limit), 2),
        "requires_facultative": cession > 0,
    }


@dataclass
class FinancialAnalysisResult:
    hlv: dict[str, Any] = field(default_factory=dict)
    estate_face: float = 0.0
    table_rating: dict[str, Any] = field(default_factory=dict)
    reinsurance: LifeReinsuranceResult | None = None
    financial_result: LifeFinancialResult | None = None
    findings: list[Finding] = field(default_factory=list)
    decision: UWDecision = UWDecision.ACCEPT

    def to_metadata(self) -> dict[str, Any]:
        return {
            "hlv": self.hlv,
            "estate_face": self.estate_face,
            "table_rating": self.table_rating,
            "reinsurance": self.reinsurance.to_metadata() if self.reinsurance else None,
            "financial": self.financial_result.to_metadata() if self.financial_result else None,
        }


def run_financial_analysis(bundle: SubmissionBundle) -> FinancialAnalysisResult:
    _blob(bundle)
    factors = extract_life_factors(bundle)
    result = FinancialAnalysisResult()

    face = float(factors.face_amount or 0)
    income = float(factors.income or 0)
    net_worth = float(getattr(factors, "net_worth", 0) or 0)
    age = factors.age

    # HLV calculation
    if income > 0:
        result.hlv = calculate_hlv(income, age)
        if face > result.hlv.get("max_face_high", 0) * 1.05:
            result.findings.append(
                Finding(
                    title=f"Face amount ${face:,.0f} exceeds HLV ceiling ${result.hlv['max_face_high']:,.0f}",
                    description=(
                        f"Income ${income:,.0f} × {result.hlv['multiplier_high']}× (age {result.hlv['age_band']}) "
                        f"= ${result.hlv['max_face_high']:,.0f} max. Exceeds by ${(face - result.hlv['max_face_high']):,.0f}."
                    ),
                    severity=RiskSeverity.HIGH,
                    category="life_financial",
                )
            )
            result.decision = UWDecision.REFER

    # Estate face amount for net-worth cases
    if net_worth > 0 and income <= 0:
        result.estate_face = calculate_estate_face_amount(net_worth)
        if face > result.estate_face * 1.2:
            result.findings.append(
                Finding(
                    title=f"Face amount ${face:,.0f} exceeds estate need ${result.estate_face:,.0f}",
                    description=f"Net worth ${net_worth:,.0f} × 15% tax/liquidity = ${result.estate_face:,.0f} max estate face.",
                    severity=RiskSeverity.MODERATE,
                    category="life_financial",
                )
            )

    # Delegate to existing financial UW
    fin = evaluate_life_financial(bundle)
    result.financial_result = fin
    result.findings.extend(fin.findings)
    if fin.decision_hint.value > result.decision.value:
        result.decision = fin.decision_hint

    # Table rating (based on medical class)
    result.table_rating = calculate_table_rating_surcharge(0)  # No table by default

    # Reinsurance
    reinsurance = evaluate_life_reinsurance(bundle)
    result.reinsurance = reinsurance
    result.findings.extend(reinsurance.findings)

    return result
