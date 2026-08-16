"""Utmost good faith (uberrimae fides) — disclosure duty screening.

Insurance is a contract of the utmost good faith: the applicant must disclose
every material fact. This screen looks for material misrepresentation (false
statements), concealment (hidden critical facts, e.g. a loss run that reports
claims the application omits), and warranty breach (promised conditions that
were not met).
"""

from __future__ import annotations

from typing import Iterable

from insureflow.models.policy import DisclosureAssessment
from insureflow.models.submissions import ClaimRecord, SubmissionBundle

_CONCEALMENT_MARKERS = (
    "not disclosed",
    "failed to disclose",
    "withheld",
    "omitted",
    "concealed",
    "concealment",
    "hidden",
    "never reported",
    "undisclosed",
)

_WARRANTY_MARKERS = (
    "warranty",
    "warranted",
    "warranted that",
    "breach of warranty",
    "warranty violation",
)


def _claim_key(claim: ClaimRecord) -> str:
    return f"{claim.date_of_loss.isoformat()}|{round(float(claim.incurred_amount or 0), 2)}"


def _loss_run_claims(bundle: SubmissionBundle) -> list[ClaimRecord]:
    structured = bundle.structured
    if structured is None or structured.financial is None or structured.financial.loss_run is None:
        return []
    return list(structured.financial.loss_run.claims or [])


def _application_claims(bundle: SubmissionBundle) -> list[ClaimRecord]:
    structured = bundle.structured
    if structured is None or structured.risk_profile is None:
        return []
    return list(structured.risk_profile.prior_claims or [])


def _blob(bundle: SubmissionBundle) -> str:
    pieces: list[str] = []
    if bundle.structured is not None:
        pieces.append(f"{bundle.structured.risk_profile.business_description or ''} {bundle.structured.risk_profile.occupancy_type or ''}")
    for doc in (bundle.unstructured or []) + (bundle.supplemental or []):
        pieces.append(doc.raw_text)
    return " ".join(pieces).lower()


def assess_disclosure(bundle: SubmissionBundle) -> DisclosureAssessment:
    """Compare the loss run against the application's disclosed claims and scan
    the package for concealment / warranty markers."""
    assessment = DisclosureAssessment()
    findings: list[str] = []

    loss_run = {_claim_key(c) for c in _loss_run_claims(bundle)}
    application = {_claim_key(c) for c in _application_claims(bundle)}
    # Claims in the loss run that were never disclosed on the application.
    undisclosed = loss_run - application
    for key in sorted(undisclosed):
        assessment.undisclosed_claims.append(key)
    if undisclosed:
        assessment.concealment = True
        findings.append(f"{len(undisclosed)} loss-run claim(s) absent from the application — potential concealment")

    # Application claims that never appeared in the carrier loss run: the
    # applicant may be reporting losses that do not belong to this insured.
    phantom = application - loss_run
    if phantom and loss_run:
        assessment.material_misrepresentation = True
        findings.append(f"{len(phantom)} disclosed claim(s) not present in the carrier loss run — potential misrepresentation")

    blob = _blob(bundle)
    if any(m in blob for m in _CONCEALMENT_MARKERS):
        assessment.concealment = True
        findings.append("Package contains concealment / non-disclosure language")
    if any(m in blob for m in _WARRANTY_MARKERS):
        assessment.warranty_breach = True
        for marker in _WARRANTY_MARKERS:
            if marker in blob:
                assessment.warranty_breaches.append(marker)

    assessment.findings = findings
    assessment.utmost_good_faith = not (assessment.concealment or assessment.material_misrepresentation or assessment.warranty_breach)
    assessment.detail = (
        "Utmost good faith upheld — no material non-disclosure detected"
        if assessment.utmost_good_faith
        else "Material non-disclosure detected — full-disclosure duty breached"
    )
    return assessment


def assess_warranty_compliance(bundle: SubmissionBundle, warranty_terms: Iterable[str]) -> list[str]:
    """Check declared warranty terms against the submission text; return breaches."""
    blob = _blob(bundle)
    breaches: list[str] = []
    for term in warranty_terms:
        if term and term.lower() not in blob:
            breaches.append(term)
    return breaches
