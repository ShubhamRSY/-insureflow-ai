"""Beneficiary review workflow — structured review beyond simple flagging.

Provides a complete beneficiary review process including primary/contingent
designation validation, insurable interest verification, trust/estate
ownership checks, and multi-beneficiary allocation review.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from insureflow.models.agents import Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle


class BeneficiaryType(str, Enum):
    PRIMARY = "primary"
    CONTINGENT = "contingent"


class OwnershipType(str, Enum):
    INSURED = "insured"
    THIRD_PARTY = "third_party"
    TRUST = "trust"
    ESTATE = "estate"
    BUSINESS = "business"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    FLAGGED = "flagged"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


@dataclass
class BeneficiaryEntry:
    entry_id: str = field(default_factory=lambda: f"ben-{uuid.uuid4().hex[:8]}")
    name: str = ""
    relationship: str = ""
    percentage: float = 0.0
    beneficiary_type: BeneficiaryType = BeneficiaryType.PRIMARY
    ownership_type: OwnershipType = OwnershipType.INSURED
    trust_name: str = ""
    owner_name: str = ""
    owner_relationship: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "name": self.name,
            "relationship": self.relationship,
            "percentage": self.percentage,
            "beneficiary_type": self.beneficiary_type.value,
            "ownership_type": self.ownership_type.value,
            "trust_name": self.trust_name,
            "owner_name": self.owner_name,
            "owner_relationship": self.owner_relationship,
            "notes": self.notes,
        }


@dataclass
class BeneficiaryReviewRecord:
    record_id: str = field(default_factory=lambda: f"benrev-{uuid.uuid4().hex[:12]}")
    bundle_id: str = ""
    insured_name: str = ""
    face_amount: float = 0.0
    beneficiaries: list[BeneficiaryEntry] = field(default_factory=list)
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    reviewer_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "bundle_id": self.bundle_id,
            "insured_name": self.insured_name,
            "face_amount": self.face_amount,
            "beneficiaries": [b.to_dict() for b in self.beneficiaries],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "reviewer_notes": self.reviewer_notes,
        }


@dataclass
class BeneficiaryReviewResult:
    record: BeneficiaryReviewRecord
    findings: list[Finding] = field(default_factory=list)
    primary_total_pct: float = 0.0
    contingent_total_pct: float = 0.0
    allocation_valid: bool = True
    insurable_interest_flags: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "primary_total_pct": self.primary_total_pct,
            "contingent_total_pct": self.contingent_total_pct,
            "allocation_valid": self.allocation_valid,
            "insurable_interest_flags": self.insurable_interest_flags,
            "action_items": self.action_items,
            "findings_count": len(self.findings),
        }


_VALID_RELATIONSHIPS = {
    "spouse",
    "wife",
    "husband",
    "child",
    "son",
    "daughter",
    "parent",
    "mother",
    "father",
    "trust",
    "estate",
    "partner",
    "business",
    "key_person",
    "employer",
}

_QUESTIONABLE_RELATIONSHIPS = {
    "friend",
    "neighbor",
    "acquaintance",
    "unrelated",
    "other",
}


def _parse_beneficiaries_from_blob(blob: str) -> list[BeneficiaryEntry]:
    entries: list[BeneficiaryEntry] = []
    patterns = [
        r"beneficiary\s*[:=]\s*([A-Za-z][A-Za-z ,.'-]{1,60})",
        r"primary\s+beneficiary\s*[:=]\s*([A-Za-z][A-Za-z ,.'-]{1,60})",
        r"contingent\s+beneficiary\s*[:=]\s*([A-Za-z][A-Za-z ,.'-]{1,60})",
    ]
    for pat in patterns:
        for m in re.finditer(pat, blob, re.I):
            name = m.group(1).strip()
            rel_match = re.search(r"beneficiary.*?(?:relationship|rel)\s*[:=]\s*([A-Za-z][A-Za-z /-]{1,30})", blob[m.start() : m.start() + 200], re.I)
            rel = rel_match.group(1).strip() if rel_match else ""
            entries.append(BeneficiaryEntry(name=name, relationship=rel))
    return entries


def review_beneficiaries(
    bundle: SubmissionBundle,
    *,
    beneficiaries: Optional[list[BeneficiaryEntry]] = None,
) -> BeneficiaryReviewResult:
    structured = bundle.structured
    named = structured.named_insured if structured else None
    face_amount = 0.0
    if structured and hasattr(structured, "coverages"):
        for cov in structured.coverages or []:
            if hasattr(cov, "face_amount") and cov.face_amount:
                face_amount += float(cov.face_amount)

    if beneficiaries is None:
        blob = " ".join(doc.raw_text for doc in (bundle.unstructured or []) if doc.raw_text).lower() if bundle.unstructured else ""
        beneficiaries = _parse_beneficiaries_from_blob(blob)

    record = BeneficiaryReviewRecord(
        bundle_id=bundle.bundle_id or "",
        insured_name=(named.legal_name if named else "") or "",
        face_amount=face_amount,
        beneficiaries=beneficiaries,
    )

    findings: list[Finding] = []
    action_items: list[str] = []
    interest_flags: list[str] = []

    if not beneficiaries:
        findings.append(
            Finding(
                title="No beneficiaries designated",
                description="Policy must have at least one primary beneficiary before issuance.",
                severity=RiskSeverity.CRITICAL,
                category="beneficiary_review",
            )
        )
        action_items.append("Obtain beneficiary designation form from insured")
        record.status = ReviewStatus.FLAGGED
        return BeneficiaryReviewResult(
            record=record,
            findings=findings,
            allocation_valid=False,
            action_items=action_items,
        )

    primary = [b for b in beneficiaries if b.beneficiary_type == BeneficiaryType.PRIMARY]
    contingent = [b for b in beneficiaries if b.beneficiary_type == BeneficiaryType.CONTINGENT]

    primary_pct = sum(b.percentage for b in primary)
    contingent_pct = sum(b.percentage for b in contingent)

    if primary_pct > 0 and abs(primary_pct - 100.0) > 0.5:
        findings.append(
            Finding(
                title=f"Primary allocation {primary_pct:.1f}% ≠ 100%",
                description=f"Primary beneficiaries total {primary_pct:.1f}% — must equal 100%.",
                severity=RiskSeverity.HIGH,
                category="beneficiary_review",
            )
        )
        action_items.append("Correct primary beneficiary percentages")
        record.status = ReviewStatus.FLAGGED

    if primary_pct == 100.0 and not contingent:
        findings.append(
            Finding(
                title="No contingent beneficiary",
                description="Consider naming a contingent (secondary) beneficiary.",
                severity=RiskSeverity.LOW,
                category="beneficiary_review",
            )
        )

    for b in beneficiaries:
        rel_l = b.relationship.lower().strip()
        if rel_l in _QUESTIONABLE_RELATIONSHIPS:
            interest_flags.append(f"'{b.name}' — relationship '{b.relationship}' may lack insurable interest")
            findings.append(
                Finding(
                    title=f"Insurable interest concern: {b.name}",
                    description=f"Relationship '{b.relationship}' is not a recognized insurable-interest class.",
                    severity=RiskSeverity.HIGH,
                    category="beneficiary_review",
                )
            )
            record.status = ReviewStatus.FLAGGED

        if b.ownership_type == OwnershipType.TRUST and not b.trust_name:
            findings.append(
                Finding(
                    title=f"Trust beneficiary missing trust name: {b.name}",
                    description="Trust-owned beneficiary must specify trust name.",
                    severity=RiskSeverity.HIGH,
                    category="beneficiary_review",
                )
            )
            record.status = ReviewStatus.FLAGGED

    if face_amount >= 5_000_000 and not any(b.ownership_type == OwnershipType.TRUST for b in beneficiaries):
        findings.append(
            Finding(
                title="Large face — consider trust ownership",
                description=f"Face ${face_amount:,.0f} — estate planning review recommended; consider ILIT/trust ownership.",
                severity=RiskSeverity.MODERATE,
                category="beneficiary_review",
            )
        )
        action_items.append("Discuss estate planning and trust ownership with insured")

    if record.status == ReviewStatus.PENDING:
        record.status = ReviewStatus.APPROVED

    return BeneficiaryReviewResult(
        record=record,
        findings=findings,
        primary_total_pct=round(primary_pct, 1),
        contingent_total_pct=round(contingent_pct, 1),
        allocation_valid=abs(primary_pct - 100.0) <= 0.5 if primary_pct > 0 else False,
        insurable_interest_flags=interest_flags,
        action_items=action_items,
    )


_BENEFICIARY_STORE: dict[str, BeneficiaryReviewRecord] = {}


def persist_beneficiary_review(record: BeneficiaryReviewRecord) -> None:
    _BENEFICIARY_STORE[record.record_id] = record


def get_beneficiary_review(record_id: str) -> Optional[BeneficiaryReviewRecord]:
    return _BENEFICIARY_STORE.get(record_id)


def list_beneficiary_reviews(bundle_id: str = "") -> list[BeneficiaryReviewRecord]:
    records = list(_BENEFICIARY_STORE.values())
    if bundle_id:
        records = [r for r in records if r.bundle_id == bundle_id]
    return sorted(records, key=lambda r: r.created_at, reverse=True)
