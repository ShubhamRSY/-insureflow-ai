"""Claim-file review as an underwriting information source — Chapter 4.

Chapter 4 lists claim files among the property-casualty underwriter's
information sources: adjusters' observations recorded in the claim file reveal
careless habits, small frequent claims point to morale hazard, and wear-and-tear
claims indicate maintenance neglect. This module reviews the claims available on
a submission for those patterns so the risk analysis can use them.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import ClaimRecord, SubmissionBundle

_SMALL_CLAIM_THRESHOLD = 2_500.0

# Wear-and-tear / maintenance-neglect causes.
_WEAR_TEAR_MARKERS = (
    "wear and tear",
    "wear & tear",
    "gradual deterioration",
    "deterioration",
    "rust",
    "corrosion",
    "rotting",
    "rot",
    "maintenance",
    "leak",
    "leaking",
    "paint",
    "replacement of worn",
    "old",
    "aged",
)

# Adjuster-observation markers in claim notes/descriptions.
_ADJUSTER_MARKERS = (
    "adjuster noted",
    "adjuster observation",
    "inspection noted",
    "noted at scene",
    "observed at",
    "housekeeping",
    "pre-existing",
)


class ClaimFileSignalType(str, Enum):
    SMALL_CLAIM_PATTERN = "small_claim_pattern"
    WEAR_AND_TEAR = "wear_and_tear"
    ADJUSTER_OBSERVATION = "adjuster_observation"


class ClaimFileSignal(BaseModel):
    signal_type: ClaimFileSignalType
    claim_id: str
    detail: str
    severity: RiskSeverity = RiskSeverity.MODERATE
    evidence: list[str] = Field(default_factory=list)


class ClaimFileReview(BaseModel):
    """What the claim files say about the insured's care of the risk."""

    signals: list[ClaimFileSignal] = Field(default_factory=list)
    small_claim_count: int = 0
    wear_tear_count: int = 0
    adjuster_observation_count: int = 0
    total_claims: int = 0
    status: str = "low"  # low | flagged | high
    summary: str = ""


def _claims(bundle: SubmissionBundle) -> list[ClaimRecord]:
    structured = bundle.structured
    if structured is None:
        return []
    claims: list[ClaimRecord] = []
    if structured.risk_profile:
        claims.extend(structured.risk_profile.prior_claims or [])
    if structured.financial and structured.financial.loss_run:
        claims.extend(structured.financial.loss_run.claims or [])
    return claims


def _claim_blob(claim: ClaimRecord) -> str:
    return f"{claim.cause} {claim.description} {claim.notes}".lower()


def review_claim_files(bundle: SubmissionBundle) -> ClaimFileReview:
    """Review the submission's claims for underwriting-relevant patterns."""
    claims = _claims(bundle)
    review = ClaimFileReview(total_claims=len(claims))

    for claim in claims:
        blob = _claim_blob(claim)
        small = claim.incurred_amount <= _SMALL_CLAIM_THRESHOLD
        wear = any(m in blob for m in _WEAR_TEAR_MARKERS)

        if small:
            review.small_claim_count += 1
            review.signals.append(
                ClaimFileSignal(
                    signal_type=ClaimFileSignalType.SMALL_CLAIM_PATTERN,
                    claim_id=claim.claim_id,
                    detail=f"Claim {claim.claim_id} ({claim.cause}) incurred ${claim.incurred_amount:,.0f} — small/attritional losses can signal carelessness or morale hazard",
                    severity=RiskSeverity.MODERATE,
                    evidence=[claim.description, claim.notes],
                )
            )
        if wear:
            review.wear_tear_count += 1
            review.signals.append(
                ClaimFileSignal(
                    signal_type=ClaimFileSignalType.WEAR_AND_TEAR,
                    claim_id=claim.claim_id,
                    detail=f"Claim {claim.claim_id} cause '{claim.cause}' reads as wear-and-tear / maintenance neglect",
                    severity=RiskSeverity.HIGH,
                    evidence=[claim.description, claim.notes],
                )
            )

    for doc in (bundle.unstructured or []) + (bundle.supplemental or []):
        lowered = doc.raw_text.lower()
        if any(m in lowered for m in _ADJUSTER_MARKERS):
            review.adjuster_observation_count += 1
            review.signals.append(
                ClaimFileSignal(
                    signal_type=ClaimFileSignalType.ADJUSTER_OBSERVATION,
                    claim_id=doc.document_type,
                    detail=f"Adjuster observation found in {doc.document_type} — inspect the claim file for scene observations",
                    severity=RiskSeverity.MODERATE,
                )
            )

    if review.wear_tear_count >= 2 or (review.small_claim_count >= 3 and review.wear_tear_count >= 1):
        review.status = "high"
    elif review.wear_tear_count or review.small_claim_count >= 3 or review.adjuster_observation_count:
        review.status = "flagged"
    else:
        review.status = "low"

    pieces = []
    if review.small_claim_count:
        pieces.append(f"{review.small_claim_count} small claim(s)")
    if review.wear_tear_count:
        pieces.append(f"{review.wear_tear_count} wear-and-tear claim(s)")
    if review.adjuster_observation_count:
        pieces.append(f"{review.adjuster_observation_count} adjuster observation(s)")
    review.summary = "; ".join(pieces) if pieces else "No concerning claim-file patterns detected"

    return review
