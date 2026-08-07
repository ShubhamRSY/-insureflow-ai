"""Expense projection and allocation in ratemaking.

Chapter 5: insurance rates are also based on the insurer's projected expenses.
Like losses, expenses can change over time, and any projected changes must be
considered in the ratemaking process. Rather than using past expenses, it is
sometimes more relevant to use judgment or budgeted expenses, especially when
conditions change dramatically. Ratemakers must also allocate general
administrative expenses properly among different types of insurance, so that no
line subsidizes another.

This module projects expenses onto the future (past experience vs judgment vs
budgeted) and allocates general administrative expenses across lines on a
premium-proportional basis.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from insureflow.rating.models import InsuranceLine


class ExpenseBasis(str, Enum):
    PAST_EXPERIENCE = "past_experience"
    JUDGMENT = "judgment"
    BUDGETED = "budgeted"


class ExpenseProjection(BaseModel):
    """A single expense item projected into the future."""

    expense: str
    historical: float = 0.0
    projected: float = 0.0
    basis: ExpenseBasis = ExpenseBasis.PAST_EXPERIENCE
    change_pct: float = 0.0
    detail: str = ""


def project_expenses(
    historical: dict[str, float],
    *,
    budgeted: Optional[dict[str, float]] = None,
    use_judgment: bool = False,
) -> list[ExpenseProjection]:
    """Project expenses forward for ratemaking.

    Budgeted expenses override past experience when provided; the judgment basis
    is used when conditions have changed dramatically and past expenses are no
    longer representative.
    """
    budgeted = budgeted or {}
    projections: list[ExpenseProjection] = []
    for name, past in historical.items():
        projected = budgeted.get(name, past)
        if name in budgeted:
            basis = ExpenseBasis.BUDGETED
            reason = "budgeted"
        elif use_judgment:
            basis = ExpenseBasis.JUDGMENT
            reason = "judgment-adjusted for changing conditions"
        else:
            basis = ExpenseBasis.PAST_EXPERIENCE
            reason = "past experience"
        change_pct = round((projected - past) / past * 100.0, 2) if past else 0.0
        projections.append(
            ExpenseProjection(
                expense=name,
                historical=round(past, 2),
                projected=round(projected, 2),
                basis=basis,
                change_pct=change_pct,
                detail=f"{name} {reason}: ${past:,.0f} → ${projected:,.0f} ({change_pct:+.1f}%)",
            )
        )
    return projections


class ExpenseAllocation(BaseModel):
    """General administrative expense allocated to a line of insurance."""

    line: str
    premium_share: float = 0.0
    allocated_general_admin: float = 0.0
    method: str = "premium-proportional"
    detail: str = ""


def allocate_general_admin(
    general_admin_total: float,
    lines_and_premium: list[tuple[InsuranceLine, float]],
) -> list[ExpenseAllocation]:
    """Allocate general administrative expenses across lines.

    Premium-proportional allocation keeps a high-expense line from being
    subsidized by (or subsidizing) the rest of the book.
    """
    total_premium = sum(premium for _, premium in lines_and_premium)
    if total_premium <= 0:
        return []
    allocations: list[ExpenseAllocation] = []
    for line, premium in lines_and_premium:
        share = premium / total_premium
        allocated = general_admin_total * share
        allocations.append(
            ExpenseAllocation(
                line=line.value,
                premium_share=round(share, 4),
                allocated_general_admin=round(allocated, 2),
                detail=f"{share:.1%} of premium → ${allocated:,.0f} of ${general_admin_total:,.0f} general admin",
            )
        )
    return allocations


def allocate_general_admin_across_all_lines(general_admin_total: float = 1_000_000.0) -> list[ExpenseAllocation]:
    """Allocate general admin across every rating line with a demo premium split."""
    premiums = [line_premium_default(line) for line in InsuranceLine]
    return allocate_general_admin(general_admin_total, list(zip(list(InsuranceLine), premiums)))


def line_premium_default(line: InsuranceLine) -> float:
    """A representative annual premium for demo allocation purposes."""
    _premiums: dict[str, float] = {
        "commercial_property": 40_000_000.0,
        "general_liability": 55_000_000.0,
        "workers_comp": 60_000_000.0,
        "business_owners_policy": 25_000_000.0,
        "umbrella": 15_000_000.0,
        "directors_and_officers": 18_000_000.0,
        "trade_credit": 12_000_000.0,
        "errors_and_omissions": 16_000_000.0,
        "key_person": 8_000_000.0,
        "personal_homeowners": 50_000_000.0,
        "personal_auto": 70_000_000.0,
        "life": 20_000_000.0,
    }
    return _premiums.get(line.value, 10_000_000.0)
