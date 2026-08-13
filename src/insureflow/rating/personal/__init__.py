"""Personal lines filing-style rating entrypoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from insureflow.models.submissions import SubmissionBundle
    from insureflow.rating.models import InsuranceLine, QuoteResult


def rate_personal_line(
    bundle: "SubmissionBundle",
    line: "InsuranceLine",
    *,
    state: str = "",
    deductible: float = 1000.0,
    coverage_id: str | None = None,
    coverage_name: str | None = None,
    product_id: str | None = None,
) -> "QuoteResult":
    from insureflow.rating.models import InsuranceLine
    from insureflow.rating.personal.auto_rating import rate_personal_auto
    from insureflow.rating.personal.homeowners_rating import rate_homeowners
    from insureflow.rating.personal.general_rating import rate_general
    from insureflow.rating.personal.health_rating import rate_health
    from insureflow.rating.personal.life_rating import rate_life

    if line == InsuranceLine.PERSONAL_HOMEOWNERS:
        return rate_homeowners(bundle, state=state, deductible=deductible)
    if line == InsuranceLine.PERSONAL_AUTO:
        return rate_personal_auto(bundle, state=state)
    if line == InsuranceLine.LIFE:
        return rate_life(bundle, coverage_id=coverage_id, coverage_name=coverage_name, product_id=product_id, state=state)
    if line == InsuranceLine.HEALTH:
        return rate_health(bundle, coverage_id=coverage_id, coverage_name=coverage_name, product_id=product_id, state=state)
    if line == InsuranceLine.GENERAL:
        return rate_general(bundle, coverage_id=coverage_id, coverage_name=coverage_name, product_id=product_id, state=state)
    raise ValueError(f"Not a personal line: {line}")
