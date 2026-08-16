"""Valuation standards — replacement cost, actual cash value, agreed value.

RCV indemnifies the full replacement cost; ACV pays replacement cost minus
physical depreciation; agreed value pays a pre-agreed amount regardless of
depreciation (typically for fine art / collectibles / specialty schedules).
"""

from __future__ import annotations

from typing import Any

from insureflow.models.policy import ValuationAssessment, ValuationBasis
from insureflow.models.submissions import SubmissionBundle

_DEFAULT_USEFUL_LIFE_YEARS = 25.0


def depreciation_for_age(age_years: float | None, useful_life_years: float | None = None) -> float:
    """Straight-line physical depreciation, capped between 0% and 90%."""
    if age_years is None or age_years <= 0:
        return 0.0
    life = useful_life_years or _DEFAULT_USEFUL_LIFE_YEARS
    if life <= 0:
        return 0.0
    return max(min(float(age_years) / float(life), 0.90), 0.0)


def valuation_assessment(
    *,
    basis: ValuationBasis | str,
    replacement_cost: float | None = None,
    age_years: float | None = None,
    agreed_value: float | None = None,
    useful_life_years: float | None = None,
    source: str = "",
) -> ValuationAssessment:
    """Valuation of an asset under the requested basis."""
    basis = ValuationBasis(basis) if isinstance(basis, str) else basis
    rcv = max(float(replacement_cost or 0.0), 0.0)
    dep_pct = depreciation_for_age(age_years, useful_life_years)
    acv = rcv * (1.0 - dep_pct)

    if basis is ValuationBasis.AGREED_VALUE:
        effective = float(agreed_value or rcv)
        detail = f"Agreed-value valuation {effective:,.0f} — depreciation not applied"
    elif basis is ValuationBasis.ACV:
        effective = acv
        detail = f"ACV {acv:,.0f} = replacement cost {rcv:,.0f} − {dep_pct:.1%} depreciation" + (f" over {age_years:.0f} years" if age_years else "")
    else:
        effective = rcv
        detail = f"Replacement cost valuation {rcv:,.0f} — no depreciation applied"

    return ValuationAssessment(
        basis=basis,
        replacement_cost=rcv if rcv else None,
        acv=round(acv, 2) if rcv else None,
        agreed_value=float(agreed_value) if agreed_value is not None else None,
        depreciation_amount=round(rcv - acv, 2) if rcv else None,
        depreciation_pct=round(dep_pct, 4) if rcv else None,
        effective_value=round(effective, 2),
        source=source,
        detail=detail,
    )


def valuation_from_bundle(
    bundle: SubmissionBundle | None,
    *,
    basis: ValuationBasis | str = ValuationBasis.RCV,
    source: str = "schedule_of_values",
) -> dict[str, Any]:
    """Valuation assessment for the primary insurable value of a submission."""
    if bundle is None or bundle.structured is None:
        return {"assets": [], "total_effective_value": 0.0, "basis": ValuationBasis(basis).value, "detail": "No structured submission"}

    structured = bundle.structured
    items: list[dict[str, Any]] = []
    total = 0.0
    seen_ages = False

    for sov in structured.schedule_of_values:
        for item in sov.items:
            age = getattr(item, "age_years", None)
            seen_ages = seen_ages or age is not None
            assessment = valuation_assessment(
                basis=basis,
                replacement_cost=item.value,
                age_years=age,
                agreed_value=item.limit if item.limit is not None else None,
                source=source,
            )
            items.append(
                {
                    "item": item.description,
                    "schedule": sov.schedule_type,
                    "replacement_cost": item.value,
                    "effective_value": assessment.effective_value,
                    "detail": assessment.detail,
                }
            )
            total += assessment.effective_value or 0.0

    if not items:
        # Fall back to the property building value when no schedule exists.
        building = next((loc.building_value for loc in (structured.locations or []) if loc.building_value), None)
        if building:
            assessment = valuation_assessment(
                basis=basis,
                replacement_cost=building,
                age_years=None,
                source="location_building_value",
            )
            items.append(
                {
                    "item": "Primary building",
                    "schedule": "location",
                    "replacement_cost": building,
                    "effective_value": assessment.effective_value,
                    "detail": assessment.detail,
                }
            )
            total = assessment.effective_value or 0.0

    basis_label = ValuationBasis(basis).value
    return {
        "assets": items,
        "total_effective_value": round(total, 2),
        "basis": basis_label,
        "depreciation_applied": seen_ages or basis_label == "acv",
        "detail": f"{len(items)} asset(s) valued on a {basis_label} basis — total {total:,.0f}",
    }
