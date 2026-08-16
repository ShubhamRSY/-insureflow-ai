"""Insurability criteria — the fundamental traits a risk needs to be insurable.

A risk is insurable only if the loss is definite and measurable, accidental /
fortuitous, pooled over a large number of similar exposure units, has a
calculable probability, carries a premium affordable relative to the potential
loss, and is not a systemic catastrophic hazard.
"""

from __future__ import annotations

from insureflow.models.policy import InsurabilityCriteria
from insureflow.models.submissions import ClaimRecord, SubmissionBundle

_FORTUITOUS_VIOLATION_MARKERS = (
    "intentional",
    "deliberately",
    "on purpose",
    "fraud",
    "willful",
    "pre-existing damage known",
)


def _all_claims(bundle: SubmissionBundle) -> list[ClaimRecord]:
    claims: list[ClaimRecord] = []
    structured = bundle.structured
    if structured is None:
        return claims
    if structured.risk_profile:
        claims.extend(structured.risk_profile.prior_claims or [])
    if structured.financial and structured.financial.loss_run:
        claims.extend(structured.financial.loss_run.claims or [])
    return claims


def assess_insurability(bundle: SubmissionBundle) -> InsurabilityCriteria:
    """Check each insurability requirement against the submission, degrading
    gracefully when inputs are missing (unknown criteria count as failures)."""
    structured = bundle.structured
    failed: list[str] = []
    detail: list[str] = []

    # 1. Fortuitous — the loss must be accidental, not intentionally caused.
    fortuitous = True
    for claim in _all_claims(bundle):
        blob = f"{claim.cause} {claim.description} {claim.notes}".lower()
        if any(m in blob for m in _FORTUITOUS_VIOLATION_MARKERS):
            fortuitous = False
            failed.append("fortuitous")
            detail.append(f"Claim {claim.claim_id} shows intentional / non-accidental markers")
            break
    if fortuitous:
        detail.append("No intentional-loss markers in the claim history")

    # 2. Measurable — the potential loss must be definite and quantifiable.
    measurable = False
    if structured is not None:
        has_values = bool(structured.schedule_of_values) or bool(structured.coverages)
        if structured.financial is not None:
            has_values = has_values or (structured.financial.total_asset_value is not None or structured.financial.annual_revenue is not None or structured.financial.payroll is not None)
        measurable = has_values
    if measurable:
        detail.append("Loss exposure is quantified (values / coverages declared)")
    else:
        failed.append("measurable")
        detail.append("No quantified loss exposure — cannot size the risk")

    # 3. Large pool — a sufficient number of similar exposure units.
    large_pool = False
    if structured is not None:
        if structured.financial is not None and structured.financial.employee_count is not None:
            large_pool = structured.financial.employee_count >= 5
        elif structured.risk_profile is not None and structured.risk_profile.naics_code:
            large_pool = True
    if large_pool:
        detail.append("Risk belongs to a class with a large pool of similar units")
    else:
        failed.append("large_pool")
        detail.append("No evidence of a large pool of similar exposure units")

    # 4. Calculable probability — historical / industry data to estimate frequency.
    calculable = False
    if structured is not None:
        if structured.financial and structured.financial.loss_run:
            calculable = True
        elif structured.risk_profile and structured.risk_profile.prior_claims:
            calculable = True
    if calculable:
        detail.append("Claims history supports frequency/severity estimation")
    else:
        failed.append("calculable_probability")
        detail.append("No claims history for probability estimation")

    # 5. Affordable premium — premium should be small relative to the loss it
    # would compensate (proxy: implied premium vs annual revenue).
    affordable = True
    if structured is not None and structured.financial is not None:
        revenue = structured.financial.annual_revenue or 0.0
        premium = float(sum(float(c.premium or 0) for c in structured.coverages or []))
        if revenue > 0 and premium > 0:
            affordable = (premium / revenue) <= 0.10
            if not affordable:
                failed.append("affordable_premium")
                detail.append(f"Implied premium is {premium / revenue:.1%} of revenue — likely unaffordable")
    if affordable:
        detail.append("Premium appears affordable relative to the exposure")

    # 6. No systemic catastrophic hazard (unless government-backstopped).
    no_cat = True
    blob = ""
    if structured is not None and structured.risk_profile is not None:
        blob = f"{structured.risk_profile.business_description or ''} {structured.risk_profile.occupancy_type or ''}".lower()
    for marker in ("flood zone", "terrorism", "war", "nuclear", "radiation"):
        if marker in blob:
            no_cat = False
            failed.append("no_catastrophic_exclusion")
            detail.append(f"Catastrophic/systemic exposure indicated: {marker}")
            break

    insurable = not failed
    return InsurabilityCriteria(
        fortuitous=fortuitous,
        measurable=measurable,
        large_pool=large_pool,
        calculable_probability=calculable,
        affordable_premium=affordable,
        no_catastrophic_exclusion=no_cat,
        insurable=insurable,
        failed_criteria=failed,
        detail="; ".join(detail),
    )
