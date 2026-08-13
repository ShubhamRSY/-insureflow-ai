"""Health rating stub — catalog-only until a filed health manual is imported."""

from __future__ import annotations

from typing import Any

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult
from insureflow.underwriting.health_product import is_filed_health_product
from insureflow.underwriting.health_uw import health_product_terms


def rate_health(
    bundle: SubmissionBundle,
    *,
    coverage_id: str | None = None,
    coverage_name: str | None = None,
    product_id: str | None = None,
    state: str = "",
) -> QuoteResult:
    """Refuse invented health premiums. Filed products can be added later.

    Product terms (benefit type, deductible basis) still differ per leaf.
    """
    terms = health_product_terms(product_id, coverage_id)
    meta: dict[str, Any] = {
        "rating_engine": "catalog_only",
        "insurance_line": "health",
        "product_id": product_id or "",
        "coverage_id": coverage_id or "",
        "coverage_name": coverage_name or "",
        "state": state,
        "filed": is_filed_health_product(product_id),
        **terms,
    }
    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.HEALTH,
        base_premium=0.0,
        adjusted_premium=0.0,
        eligible=False,
        ineligibility_reasons=[
            f"{terms.get('benefit_type') or 'health'} is catalog-only until a filed health rate manual is imported — will not invent premium",
        ],
        metadata=meta,
    )
