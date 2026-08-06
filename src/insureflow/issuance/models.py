"""Issuance records — binder, policy worksheet, certificate of insurance.

Step 5b of the underwriting process: after an approved decision, the
carrier puts coverage into effect by issuing a binder, sending a policy
worksheet to the policy unit, and preparing certificates of insurance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class IssuedDocumentType(str, Enum):
    BINDER = "binder"
    POLICY_WORKSHEET = "policy_worksheet"
    CERTIFICATE = "certificate"


class IssuedDocument(BaseModel):
    doc_id: str
    doc_type: IssuedDocumentType
    title: str
    filename: str
    content_type: str = "text/html"
    html: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class IssuanceRecord(BaseModel):
    """The coverage-in-effect artifacts produced at bind time."""

    issuance_id: str
    bundle_id: str
    org_id: str = "default"
    policy_number: str = ""
    insured_name: str = ""
    broker_name: str = ""
    line_of_business: str = ""
    premium: float = 0.0
    tiv: float = 0.0
    effective_date: str = ""
    expiry_date: str = ""
    bound_by: str = ""
    bound_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    status: str = "issued"
    documents: list[IssuedDocument] = Field(default_factory=list)

    @property
    def binder(self) -> IssuedDocument | None:
        return next((d for d in self.documents if d.doc_type == IssuedDocumentType.BINDER), None)

    @property
    def policy_worksheet(self) -> IssuedDocument | None:
        return next((d for d in self.documents if d.doc_type == IssuedDocumentType.POLICY_WORKSHEET), None)

    @property
    def certificate(self) -> IssuedDocument | None:
        return next((d for d in self.documents if d.doc_type == IssuedDocumentType.CERTIFICATE), None)
