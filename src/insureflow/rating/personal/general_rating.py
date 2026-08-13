"""General / non-life rating stub — catalog-only until a filed manual is imported."""

from __future__ import annotations

from typing import Any

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult
from insureflow.underwriting.general_product import is_filed_general_product
from insureflow.underwriting.general_uw import general_product_terms


def rate_general(
    bundle: SubmissionBundle,
    *,
    coverage_id: str | None = None,
    coverage_name: str | None = None,
    product_id: str | None = None,
    state: str = "",
) -> QuoteResult:
    terms = general_product_terms(product_id, coverage_id)
    meta: dict[str, Any] = {
        "rating_engine": "catalog_only",
        "insurance_line": "general",
        "product_id": product_id or "",
        "coverage_id": coverage_id or "",
        "coverage_name": coverage_name or "",
        "state": state,
        "filed": is_filed_general_product(product_id),
        **terms,
    }
    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.GENERAL,
        base_premium=0.0,
        adjusted_premium=0.0,
        eligible=False,
        ineligibility_reasons=[
            f"{terms.get('benefit_type') or 'general'} is catalog-only until a filed general rate manual is imported — will not invent premium",
        ],
        metadata=meta,
    )
