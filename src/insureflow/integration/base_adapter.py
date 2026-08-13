from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PolicySubmissionPayload:
    """Standardized payload to push into policy admin / rating systems.

    Rich enough to bind in Guidewire/BriteCore without re-keying limits,
    deductibles, filing IDs, or subjectivities.
    """

    bundle_id: str
    org_id: str
    insured_name: str
    naics_code: str = ""
    state: str = ""
    tiv: float = 0.0
    base_premium: float = 0.0
    adjusted_premium: float = 0.0
    uw_decision: str = ""
    coverages: list[dict[str, Any]] = field(default_factory=list)
    locations: list[dict[str, Any]] = field(default_factory=list)
    risk_profile: dict[str, Any] = field(default_factory=dict)
    memo_summary: str = ""
    key_findings: list[dict[str, Any]] = field(default_factory=list)
    raw_json: dict[str, Any] = field(default_factory=dict)
    policy_period: dict[str, Any] = field(default_factory=dict)
    rating: dict[str, Any] = field(default_factory=dict)
    subjectivities: list[dict[str, Any]] = field(default_factory=list)
    validated_terms: dict[str, Any] = field(default_factory=dict)
    commercial_product_id: str = ""
    insurance_line: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "org_id": self.org_id,
            "insured_name": self.insured_name,
            "naics_code": self.naics_code,
            "state": self.state,
            "tiv": self.tiv,
            "base_premium": self.base_premium,
            "adjusted_premium": self.adjusted_premium,
            "uw_decision": self.uw_decision,
            "coverages": list(self.coverages),
            "locations": list(self.locations),
            "risk_profile": dict(self.risk_profile),
            "memo_summary": self.memo_summary,
            "key_findings": list(self.key_findings),
            "policy_period": dict(self.policy_period),
            "rating": dict(self.rating),
            "subjectivities": list(self.subjectivities),
            "validated_terms": dict(self.validated_terms),
            "commercial_product_id": self.commercial_product_id,
            "insurance_line": self.insurance_line,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicySubmissionPayload:
        return cls(
            bundle_id=str(data.get("bundle_id") or ""),
            org_id=str(data.get("org_id") or "default"),
            insured_name=str(data.get("insured_name") or ""),
            naics_code=str(data.get("naics_code") or ""),
            state=str(data.get("state") or ""),
            tiv=float(data.get("tiv") or 0),
            base_premium=float(data.get("base_premium") or 0),
            adjusted_premium=float(data.get("adjusted_premium") or 0),
            uw_decision=str(data.get("uw_decision") or ""),
            coverages=list(data.get("coverages") or []),
            locations=list(data.get("locations") or []),
            risk_profile=dict(data.get("risk_profile") or {}),
            memo_summary=str(data.get("memo_summary") or ""),
            key_findings=list(data.get("key_findings") or []),
            raw_json=dict(data.get("raw_json") or {}),
            policy_period=dict(data.get("policy_period") or {}),
            rating=dict(data.get("rating") or {}),
            subjectivities=list(data.get("subjectivities") or []),
            validated_terms=dict(data.get("validated_terms") or {}),
            commercial_product_id=str(data.get("commercial_product_id") or ""),
            insurance_line=str(data.get("insurance_line") or ""),
        )


@dataclass
class IntegrationResult:
    success: bool
    system: str
    external_reference: str = ""
    policy_number: str = ""
    error: str = ""
    response_payload: dict[str, Any] = field(default_factory=dict)


class BasePolicyAdminAdapter(ABC):
    """Abstract adapter for core system integration (BriteCore, Guidewire, etc.)."""

    @abstractmethod
    def submit_quote(self, payload: PolicySubmissionPayload) -> IntegrationResult: ...

    @abstractmethod
    def bind_policy(self, payload: PolicySubmissionPayload, quote_reference: str) -> IntegrationResult: ...

    @abstractmethod
    def get_system_name(self) -> str: ...
