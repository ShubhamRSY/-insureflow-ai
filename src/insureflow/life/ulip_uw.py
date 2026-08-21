"""ULIP (Unit-Linked Insurance Plan) Underwriting.

ULIPs combine life insurance with mutual fund investments.
UW focus: investor profiling, suitability, risk appetite, fund allocation,
regulatory compliance, mortality charge separation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .mortality import q_x


class RiskAppetite(str):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    VERY_AGGRESSIVE = "very_aggressive"


@dataclass
class InvestorProfile:
    """Client's investment risk profile."""

    age: int = 30
    annual_income: float = 0.0
    net_worth: float = 0.0
    investment_horizon_years: int = 10
    risk_appetite: str = "moderate"  # conservative, moderate, aggressive, very_aggressive
    existing_market_exposure: float = 0.0  # existing equity/market-linked investments
    loss_tolerance_pct: float = 20.0  # max % portfolio loss client can tolerate
    financial_dependents: int = 0
    emergency_fund_months: int = 0


@dataclass
class ULIPUWResult:
    """ULIP underwriting output."""

    # Inputs
    age: int = 30
    sex: str = "male"
    smoker: bool = False
    face_amount: float = 500_000.0
    annual_premium: float = 0.0
    income: float = 0.0
    net_worth: float = 0.0
    # Fund allocation
    equity_pct: float = 60.0  # % allocated to equity
    debt_pct: float = 30.0
    balanced_pct: float = 10.0
    # Investor profile
    investor_profile: InvestorProfile | None = None
    # Results
    mortality_charge: float = 0.0
    premium_to_income_pct: float = 0.0
    suitability_pass: bool = False
    risk_appetite_aligned: bool = False
    regulatory_compliant: bool = False
    fund_allocation_valid: bool = False
    disclosure_complete: bool = False
    risk_score: float = 0.0
    findings: list[str] = field(default_factory=list)
    decision: str = "REFER"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "product": "ulip",
            "mortality_charge": self.mortality_charge,
            "premium_to_income_pct": self.premium_to_income_pct,
            "suitability_pass": self.suitability_pass,
            "risk_appetite_aligned": self.risk_appetite_aligned,
            "regulatory_compliant": self.regulatory_compliant,
            "fund_allocation_valid": self.fund_allocation_valid,
            "disclosure_complete": self.disclosure_complete,
            "equity_pct": self.equity_pct,
            "debt_pct": self.debt_pct,
            "risk_score": self.risk_score,
            "findings": self.findings,
            "decision": self.decision,
        }


def _estimate_mortality_charge(face: float, age: int, sex: str, smoker: bool) -> float:
    """Annual mortality charge = face × q_x × loading factor."""
    base_q = q_x(age, sex, smoker)
    loading = 1.5  # 50% loading for ULIP mortality charge
    return round(face * base_q * loading, 2)


def _fund_allocation_valid(eq: float, debt: float, bal: float) -> bool:
    """Fund allocation must sum to ~100% and not exceed risk limits."""
    total = eq + debt + bal
    if abs(total - 100) > 5:
        return False
    if eq > 80:
        return False  # max 80% equity for retail ULIPs
    return True


def run_ulip_uw(
    *,
    age: int = 30,
    sex: str = "male",
    smoker: bool = False,
    face_amount: float = 500_000.0,
    annual_premium: float = 0.0,
    income: float = 0.0,
    net_worth: float = 0.0,
    equity_pct: float = 60.0,
    debt_pct: float = 30.0,
    balanced_pct: float = 10.0,
    investment_horizon_years: int = 10,
    risk_appetite: str = "moderate",
    loss_tolerance_pct: float = 20.0,
    financial_dependents: int = 0,
    emergency_fund_months: int = 0,
    existing_market_exposure: float = 0.0,
    disclosures_complete: bool = False,
) -> ULIPUWResult:
    """Run ULIP-specific underwriting.

    ULIPs require TWO parallel underwriting tracks:
    1. Medical: determines the mortality charge (insurance cost)
    2. Suitability: ensures the investment product matches the client's profile

    Red flags:
    - Aggressive fund allocation for conservative investor
    - Premium exceeds affordable threshold
    - Short investment horizon with high equity
    - Incomplete disclosures (regulatory risk)
    """
    result = ULIPUWResult(
        age=age,
        sex=sex,
        smoker=smoker,
        face_amount=face_amount,
        annual_premium=annual_premium,
        income=income,
        net_worth=net_worth,
        equity_pct=equity_pct,
        debt_pct=debt_pct,
        balanced_pct=balanced_pct,
    )
    findings: list[str] = []

    # Build investor profile
    profile = InvestorProfile(
        age=age,
        annual_income=income,
        net_worth=net_worth,
        investment_horizon_years=investment_horizon_years,
        risk_appetite=risk_appetite,
        existing_market_exposure=existing_market_exposure,
        loss_tolerance_pct=loss_tolerance_pct,
        financial_dependents=financial_dependents,
        emergency_fund_months=emergency_fund_months,
    )
    result.investor_profile = profile

    # ── 1. Mortality Charge (Medical Track) ──────────────────────
    result.mortality_charge = _estimate_mortality_charge(face_amount, age, sex, smoker)
    findings.append(f"Mortality charge: ${result.mortality_charge:,.2f}/yr")

    # ── 2. Premium Capacity ──────────────────────────────────────
    if income > 0:
        result.premium_to_income_pct = round((annual_premium / income) * 100, 1)
    # ULIPs: max 10-12% of income (lower than endowment because investment risk is additive)
    if result.premium_to_income_pct > 15:
        findings.append(f"CRITICAL: Premium-to-income {result.premium_to_income_pct:.1f}% exceeds 15% — ULIP unsuitable, client cannot absorb investment losses")
    elif result.premium_to_income_pct > 12:
        findings.append(f"WARNING: Premium-to-income {result.premium_to_income_pct:.1f}% exceeds 12% guideline for ULIPs")

    # ── 3. Fund Allocation Validation ────────────────────────────
    result.fund_allocation_valid = _fund_allocation_valid(equity_pct, debt_pct, balanced_pct)
    if not result.fund_allocation_valid:
        findings.append(f"Fund allocation invalid: equity={equity_pct}%, debt={debt_pct}%, balanced={balanced_pct}% — must sum to ~100%, equity max 80%")

    # ── 4. Risk Appetite Alignment ───────────────────────────────
    result.risk_appetite_aligned = True
    if risk_appetite in ("conservative", "moderate") and equity_pct > 60:
        result.risk_appetite_aligned = False
        findings.append(f"RISK MISMATCH: {risk_appetite} investor with {equity_pct}% equity — fund allocation too aggressive for stated risk appetite")
    elif risk_appetite == "conservative" and equity_pct > 40:
        result.risk_appetite_aligned = False
        findings.append(f"RISK MISMATCH: conservative investor with {equity_pct}% equity — should be ≤40% equity")

    # ── 5. Investment Horizon Check ──────────────────────────────
    if investment_horizon_years < 10 and equity_pct > 50:
        findings.append(f"WARNING: {investment_horizon_years}-yr horizon with {equity_pct}% equity — short horizon increases sequence-of-returns risk")

    # ── 6. Loss Tolerance vs Fund Volatility ─────────────────────
    if equity_pct > 60 and loss_tolerance_pct < 15:
        findings.append(f"LOSS TOLERANCE MISMATCH: {loss_tolerance_pct}% tolerance with {equity_pct}% equity — potential 30-40% drawdown in stress scenario")

    # ── 7. Regulatory Compliance ─────────────────────────────────
    result.disclosure_complete = disclosures_complete
    result.regulatory_compliant = disclosures_complete and result.fund_allocation_valid and result.risk_appetite_aligned
    if not disclosures_complete:
        findings.append("REGULATORY: Incomplete investor profiling disclosures — SEBI/IRDAI compliance requires full risk appetite documentation")

    # ── 8. Suitability Determination ─────────────────────────────
    result.suitability_pass = result.regulatory_compliant and result.risk_appetite_aligned and result.premium_to_income_pct <= 15 and result.fund_allocation_valid

    # ── 9. Risk Score & Decision ─────────────────────────────────
    score = 0.0
    if not result.suitability_pass:
        score += 0.30
    if not result.risk_appetite_aligned:
        score += 0.25
    if not result.regulatory_compliant:
        score += 0.20
    if result.premium_to_income_pct > 15:
        score += 0.25
    elif result.premium_to_income_pct > 12:
        score += 0.10

    result.risk_score = round(min(score, 1.0), 4)

    if score >= 0.60:
        result.decision = "DECLINE"
        findings.append("ULIP DECISION: DECLINE — suitability assessment failed")
    elif score >= 0.30:
        result.decision = "REFER"
        findings.append("ULIP DECISION: REFER — additional suitability documentation required")
    else:
        result.decision = "APPROVE"

    result.findings = findings
    return result
