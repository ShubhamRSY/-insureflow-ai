"""Financial analysis of commercial risks — Chapter 4.

Chapter 4 lists financial rating services (Dun & Bradstreet, Standard &
Poor's) and the insured's own financial statements as information sources for
underwriting a commercial risk. This module grades a commercial insured's
financial condition from the structured financial data (assets, revenue,
credit rating) plus any balance-sheet figures recoverable from the submission,
using the classic liquidity / leverage / profitability ratios.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import FinancialData, SubmissionBundle


class FinancialGrade(str, Enum):
    STRONG = "strong"
    ADEQUATE = "adequate"
    WEAK = "weak"
    CRITICAL = "critical"


_GRADE_ORDER: dict[FinancialGrade, int] = {
    FinancialGrade.STRONG: 0,
    FinancialGrade.ADEQUATE: 1,
    FinancialGrade.WEAK: 2,
    FinancialGrade.CRITICAL: 3,
}


class FinancialRatioAnalysis(BaseModel):
    """The liquidity / leverage / profitability ratios of a commercial risk."""

    current_ratio: Optional[float] = None  # current assets / current liabilities
    quick_ratio: Optional[float] = None  # (current assets - inventory) / current liabilities
    debt_ratio: Optional[float] = None  # total liabilities / total assets
    debt_to_equity: Optional[float] = None  # total liabilities / equity
    net_margin: Optional[float] = None  # net income / revenue
    roa: Optional[float] = None  # net income / total assets
    sources: list[str] = Field(default_factory=list)


class FinancialConditionAssessment(BaseModel):
    """Overall financial-condition grade for a commercial insured."""

    grade: FinancialGrade = FinancialGrade.ADEQUATE
    severity: RiskSeverity = RiskSeverity.LOW
    ratios: Optional[FinancialRatioAnalysis] = None
    credit_rating: str = ""
    summary: str = ""
    findings: list[str] = Field(default_factory=list)


# Balance-sheet figures recovered from submission text / extracted fields.
_BALANCE_KEYS = (
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_liabilities",
    "inventory",
    "net_income",
    "shareholder_equity",
    "total_equity",
    "annual_revenue",
)


def _extract_balance_figures(bundle: SubmissionBundle) -> dict[str, float]:
    figures: dict[str, float] = {}
    for doc in (bundle.unstructured or []) + (bundle.supplemental or []):
        for key in _BALANCE_KEYS:
            for field_value in doc.extracted_fields.get(key, []):
                try:
                    figures[key] = float(field_value.value)
                except (TypeError, ValueError):
                    continue
    return figures


def _grade_severity(grade: FinancialGrade) -> RiskSeverity:
    return {
        FinancialGrade.STRONG: RiskSeverity.LOW,
        FinancialGrade.ADEQUATE: RiskSeverity.MODERATE,
        FinancialGrade.WEAK: RiskSeverity.HIGH,
        FinancialGrade.CRITICAL: RiskSeverity.CRITICAL,
    }[grade]


def _grade_from_ratios(ratios: FinancialRatioAnalysis) -> tuple[FinancialGrade, list[str]]:
    findings: list[str] = []
    weaknesses = 0

    if ratios.current_ratio is not None:
        if ratios.current_ratio < 1.0:
            weaknesses += 1
            findings.append(f"Current ratio {ratios.current_ratio:.2f} < 1.0 — liquidity concern")
        elif ratios.current_ratio < 1.5:
            findings.append(f"Current ratio {ratios.current_ratio:.2f} — adequate")
        else:
            findings.append(f"Current ratio {ratios.current_ratio:.2f} — strong")

    if ratios.debt_ratio is not None:
        if ratios.debt_ratio > 0.8:
            weaknesses += 1
            findings.append(f"Debt ratio {ratios.debt_ratio:.2f} > 0.8 — heavy leverage")
        elif ratios.debt_ratio > 0.6:
            findings.append(f"Debt ratio {ratios.debt_ratio:.2f} — moderate leverage")

    if ratios.net_margin is not None and ratios.net_margin < 0:
        weaknesses += 1
        findings.append(f"Net margin {ratios.net_margin:.1%} is negative — operating loss")

    if ratios.roa is not None and ratios.roa < 0.0:
        findings.append(f"ROA {ratios.roa:.1%} is negative")

    if weaknesses >= 2:
        return FinancialGrade.WEAK, findings
    if weaknesses == 1:
        return FinancialGrade.ADEQUATE, findings
    return FinancialGrade.STRONG, findings


def _credit_rating_grade(rating: str) -> Optional[tuple[FinancialGrade, str]]:
    lowered = (rating or "").strip().lower()
    if not lowered:
        return None
    if any(k in lowered for k in ("aaa", "aa", "a+", "a1", "a2", "excellent", "very good", "750", "800")):
        return FinancialGrade.STRONG, f"Credit rating '{rating}' indicates strong financial standing"
    if any(k in lowered for k in ("bbb", "a-", "good", "fair", "650")):
        return FinancialGrade.ADEQUATE, f"Credit rating '{rating}' indicates adequate financial standing"
    if any(k in lowered for k in ("bb", "b+", "b", "poor", "below average", "550")):
        return FinancialGrade.WEAK, f"Credit rating '{rating}' indicates weak financial standing"
    if any(k in lowered for k in ("ccc", "cc", "c", "d", "default", "very poor")):
        return FinancialGrade.CRITICAL, f"Credit rating '{rating}' indicates critical financial standing"
    return None


def assess_financial_condition(
    bundle: SubmissionBundle,
    financial: Optional[FinancialData] = None,
) -> FinancialConditionAssessment:
    """Grade the commercial insured's financial condition.

    Uses the structured financial data and any balance-sheet figures recovered
    from the submission to compute the classic ratios, then combines the ratio
    grade with the credit-rating-service grade (D&B / S&P style).
    """
    financial = financial or (bundle.structured.financial if bundle.structured else None)
    figures = _extract_balance_figures(bundle)
    sources: list[str] = []

    if financial:
        if financial.total_asset_value is not None:
            figures.setdefault("total_assets", financial.total_asset_value)
            sources.append("structured financial data")
        if financial.annual_revenue is not None:
            figures.setdefault("annual_revenue", financial.annual_revenue)
            sources.append("structured financial data")

    ratios = FinancialRatioAnalysis(sources=list(dict.fromkeys(sources)))

    ca = figures.get("current_assets")
    cl = figures.get("current_liabilities")
    if ca is not None and cl and cl > 0:
        ratios.current_ratio = round(ca / cl, 2)
        inventory = figures.get("inventory") or 0.0
        ratios.quick_ratio = round((ca - inventory) / cl, 2)

    ta = figures.get("total_assets")
    tl = figures.get("total_liabilities")
    if ta and ta > 0:
        if tl is not None:
            ratios.debt_ratio = round(tl / ta, 2)
            equity = figures.get("total_equity") or figures.get("shareholder_equity")
            if equity and equity > 0:
                ratios.debt_to_equity = round(tl / equity, 2)
        ni = figures.get("net_income")
        if ni is not None:
            ratios.roa = round(ni / ta, 4)

    revenue = figures.get("annual_revenue") or (financial.annual_revenue if financial else None)
    ni = figures.get("net_income")
    if revenue and revenue > 0 and ni is not None:
        ratios.net_margin = round(ni / revenue, 4)

    rating_grade = None
    if financial:
        rating_grade = _credit_rating_grade(financial.credit_rating or "")

    findings: list[str] = []
    grade = FinancialGrade.ADEQUATE
    if ratios.current_ratio or ratios.debt_ratio is not None or ratios.net_margin is not None:
        grade, findings = _grade_from_ratios(ratios)
    elif rating_grade:
        grade, rating_finding = rating_grade
        findings.append(rating_finding)
    else:
        grade = FinancialGrade.ADEQUATE
        findings.append("Insufficient financial data to grade — treat as adequate pending financial statement")

    # The worse of the ratio grade and the credit-rating grade governs.
    if rating_grade and _GRADE_ORDER[grade] < _GRADE_ORDER[rating_grade[0]]:
        grade = rating_grade[0]
        findings.append(rating_grade[1])

    return FinancialConditionAssessment(
        grade=grade,
        severity=_grade_severity(grade),
        ratios=ratios if ratios.current_ratio or ratios.debt_ratio is not None or ratios.net_margin is not None else None,
        credit_rating=(financial.credit_rating if financial else "") or "",
        summary=f"Financial condition graded {grade.value}",
        findings=findings,
    )
