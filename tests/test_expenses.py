from __future__ import annotations

import pytest

from insureflow.rating.expenses import (
    ExpenseBasis,
    allocate_general_admin,
    allocate_general_admin_across_all_lines,
    line_premium_default,
    project_expenses,
)
from insureflow.rating.models import InsuranceLine


def test_budgeted_expenses_override_historical() -> None:
    projections = project_expenses(
        {"acquisition": 1_500_000, "general_admin": 800_000},
        budgeted={"acquisition": 1_800_000},
    )
    by_name = {p.expense: p for p in projections}
    assert by_name["acquisition"].projected == 1_800_000
    assert by_name["acquisition"].basis == ExpenseBasis.BUDGETED
    assert by_name["acquisition"].change_pct == round((1_800_000 - 1_500_000) / 1_500_000 * 100, 2)
    assert by_name["general_admin"].projected == 800_000
    assert by_name["general_admin"].basis == ExpenseBasis.PAST_EXPERIENCE
    assert by_name["general_admin"].change_pct == 0.0


def test_judgment_basis_when_flagged() -> None:
    projections = project_expenses({"acquisition": 1_500_000}, use_judgment=True)
    assert projections[0].basis == ExpenseBasis.JUDGMENT
    assert "judgment" in projections[0].detail


def test_no_zero_change_division_error() -> None:
    projections = project_expenses({"general_admin": 0.0}, budgeted={"general_admin": 100_000})
    assert projections[0].projected == 100_000
    assert projections[0].change_pct == 0.0


def test_allocation_sums_to_total() -> None:
    lines = list(InsuranceLine)
    total = 1_000_000.0
    allocations = allocate_general_admin(total, [(line, line_premium_default(line)) for line in lines])
    assert len(allocations) == len(lines)
    assert sum(a.allocated_general_admin for a in allocations) == pytest.approx(total, abs=1.0)
    assert sum(a.premium_share for a in allocations) == pytest.approx(1.0, abs=1e-3)


def test_allocation_shares_follow_premium() -> None:
    allocations = allocate_general_admin(1_000_000, [(InsuranceLine.COMMERCIAL_PROPERTY, 10_000_000), (InsuranceLine.GENERAL_LIABILITY, 30_000_000)])
    assert allocations[0].premium_share == pytest.approx(0.25)
    assert allocations[1].premium_share == pytest.approx(0.75)
    assert allocations[1].allocated_general_admin == pytest.approx(750_000)


def test_empty_or_zero_premium_returns_empty() -> None:
    assert allocate_general_admin(1_000_000, []) == []
    assert allocate_general_admin(1_000_000, [(InsuranceLine.COMMERCIAL_PROPERTY, 0.0)]) == []


def test_across_all_lines_allocation() -> None:
    allocations = allocate_general_admin_across_all_lines()
    assert {a.line for a in allocations} == {line.value for line in InsuranceLine}
    assert sum(a.allocated_general_admin for a in allocations) == pytest.approx(1_000_000)
