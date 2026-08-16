"""Policyholder surplus and simplified Risk-Based Capital (RBC) solvency screen.

Policyholder surplus = assets − liabilities; it is the cushion that absorbs
catastrophic claims. RBC is the regulatory capital standard: the insurer must
hold capital proportional to its risk profile. This is a transparent,
factor-based approximation of the NAIC RBC covariance formula (R1..R5) so the
screen degrades gracefully when insurer inputs are sparse.
"""

from __future__ import annotations

from typing import Any

from insureflow.models.policy import SolvencyAssessment

# Factor charges per RBC component (NAIC-simplified, decimal of exposure).
_RBC_FACTORS = {
    "fixed_income": 0.02,  # R1 — bonds & fixed income
    "equity": 0.15,  # R2 — common stock / equity investments
    "credit": 0.10,  # R3 — receivables & counterparty credit
    "reserves": 0.10,  # R4a — loss & LAE reserve risk
    "net_written_premium": 0.15,  # R4b — premium/written risk
    "reinsurance_ceded": 0.10,  # R5 — off-balance-sheet / ceded risk
}


def rbc_requirement(
    *,
    fixed_income_assets: float = 0.0,
    equity_investments: float = 0.0,
    receivables: float = 0.0,
    loss_reserves: float = 0.0,
    net_written_premium: float = 0.0,
    reinsurance_ceded: float = 0.0,
) -> tuple[float, dict[str, float]]:
    """Compute the covariance-adjusted RBC requirement and its component charges."""
    r1 = _RBC_FACTORS["fixed_income"] * max(float(fixed_income_assets or 0.0), 0.0)
    r2 = _RBC_FACTORS["equity"] * max(float(equity_investments or 0.0), 0.0)
    r3 = _RBC_FACTORS["credit"] * max(float(receivables or 0.0), 0.0)
    r4 = _RBC_FACTORS["reserves"] * max(float(loss_reserves or 0.0), 0.0) + _RBC_FACTORS["net_written_premium"] * max(float(net_written_premium or 0.0), 0.0)
    r5 = _RBC_FACTORS["reinsurance_ceded"] * max(float(reinsurance_ceded or 0.0), 0.0)
    # Covariance adjustment — the classic square-root formula.
    requirement = (r1 + r3) ** 2 + r2**2 + r4**2
    requirement = requirement**0.5 + r5
    charges = {"R1_fixed_income": round(r1, 2), "R2_equity": round(r2, 2), "R3_credit": round(r3, 2), "R4_underwriting": round(r4, 2), "R5_off_balance_sheet": round(r5, 2)}
    return round(requirement, 2), charges


def assess_solvency(
    *,
    total_assets: float,
    total_liabilities: float,
    fixed_income_assets: float | None = None,
    equity_investments: float | None = None,
    receivables: float | None = None,
    loss_reserves: float | None = None,
    net_written_premium: float | None = None,
    reinsurance_ceded: float | None = None,
) -> SolvencyAssessment:
    """Surplus = assets − liabilities; solvent when surplus ≥ RBC requirement."""
    assets = max(float(total_assets or 0.0), 0.0)
    liabilities = max(float(total_liabilities or 0.0), 0.0)
    surplus = round(assets - liabilities, 2)

    requirement, charges = rbc_requirement(
        fixed_income_assets=assets if fixed_income_assets is None else fixed_income_assets,
        equity_investments=equity_investments or 0.0,
        receivables=receivables or 0.0,
        loss_reserves=loss_reserves or 0.0,
        net_written_premium=net_written_premium or 0.0,
        reinsurance_ceded=reinsurance_ceded or 0.0,
    )

    ratio = round(surplus / requirement, 4) if requirement > 0 else None
    solvent = ratio >= 1.0 if ratio is not None else None
    detail = (
        f"Policyholder surplus {surplus:,.0f} (assets {assets:,.0f} − liabilities {liabilities:,.0f}); "
        f"RBC requirement {requirement:,.0f}" + (f"; RBC ratio {ratio:.2f}" if ratio is not None else "") + ("" if ratio is None else (" — solvent" if solvent else " — RBC action level"))
    )
    return SolvencyAssessment(
        policyholder_surplus=surplus,
        total_assets=assets,
        total_liabilities=liabilities,
        required_risk_based_capital=requirement,
        rbc_ratio=ratio,
        solvent=solvent,
        risk_grades=charges,
        detail=detail,
    )


def solvency_from_inputs(inputs: dict[str, Any]) -> SolvencyAssessment:
    """Convenience wrapper for calling code with a plain mapping."""
    return assess_solvency(**inputs)
