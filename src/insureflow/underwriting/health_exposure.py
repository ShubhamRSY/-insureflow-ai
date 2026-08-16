"""Health exposure base — covered lives.

For health cover, the exposure base is the number of lives covered, not a dollar
measure. Group plans expose every enrolled life; the base is the headcount of
employees plus their dependents.
"""

from __future__ import annotations

from typing import Any

from insureflow.models.submissions import SubmissionBundle

# Representative dependents per employee for group benefit exposure.
_DEFAULT_DEPENDENTS_PER_EMPLOYEE = 2.2


def covered_lives(*, employee_count: int | None, dependents_per_employee: float | None = None) -> float:
    """Total lives exposed = employees + dependents."""
    if not employee_count or employee_count <= 0:
        return 0.0
    deps = float(dependents_per_employee) if dependents_per_employee is not None else _DEFAULT_DEPENDENTS_PER_EMPLOYEE
    return round(float(employee_count) * (1.0 + max(deps, 0.0)), 2)


def health_exposure_base(bundle: SubmissionBundle | None) -> dict[str, Any]:
    """Derive the covered-lives exposure base for a health submission."""
    if bundle is None or bundle.structured is None:
        return {"employee_count": None, "covered_lives": 0.0, "exposure_base": "unknown", "detail": "No structured submission"}
    fin = bundle.structured.financial
    employees = fin.employee_count if fin is not None else None
    lives = covered_lives(employee_count=employees)
    if lives <= 0:
        return {
            "employee_count": employees,
            "covered_lives": 0.0,
            "exposure_base": "unknown",
            "detail": "No employee census — covered lives unknown",
        }
    return {
        "employee_count": employees,
        "covered_lives": lives,
        "exposure_base": "lives",
        "detail": f"Group exposure base: {employees:,.0f} employee(s) × 1.0 + {_DEFAULT_DEPENDENTS_PER_EMPLOYEE:,.1f} dependents = {lives:,.0f} covered lives",
    }
