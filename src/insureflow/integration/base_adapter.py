from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PolicySubmissionPayload:
    """Standardized payload to push into policy admin / rating systems."""

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
    def bind_policy(
        self, payload: PolicySubmissionPayload, quote_reference: str
    ) -> IntegrationResult: ...

    @abstractmethod
    def get_system_name(self) -> str: ...
