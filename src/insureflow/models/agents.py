from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    RISK_ANALYST = "risk_analyst"
    LOSS_RUN_ANALYST = "loss_run_analyst"
    COMPLIANCE_AGENT = "compliance_agent"
    FRAUD_DETECTION = "fraud_detection"
    UW_DECISION = "uw_decision"
    SUPERVISOR = "supervisor"
    APPETITE_FILTER = "appetite_filter"
    ORACLE_AGENT = "oracle_agent"
    PORTFOLIO_RISK = "portfolio_risk"
    REINSURANCE = "reinsurance"
    SELECTION_STANDARDS = "selection_standards"
    PRODUCER_EXPERIENCE = "producer_experience"
    ADVERSE_SELECTION = "adverse_selection"
    MORAL_HAZARD = "moral_hazard"


class RiskSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class UWDecision(str, Enum):
    ACCEPT = "accept"
    CONDITIONAL_ACCEPT = "conditional_accept"
    REFER = "refer"
    DECLINE = "decline"


class Finding(BaseModel):
    finding_id: str = ""
    title: str
    description: str
    severity: RiskSeverity = RiskSeverity.MODERATE
    category: str = ""
    field_path: str = ""
    source_value: Optional[Any] = None
    recommended_value: Optional[Any] = None
    confidence: float = 0.8
    evidence: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    action: str = ""
    rationale: str = ""
    conditions: list[str] = Field(default_factory=list)
    suggested_premium_modification: Optional[float] = None
    suggested_limit: Optional[float] = None
    suggested_deductible: Optional[float] = None


class CommunicationEntry(BaseModel):
    """One entry in the underwriting worksheet's communication log.

    Mirrors the classical worksheet item: records of telephone calls and other
    communications between the case underwriter and brokers / applicants /
    other parties from submission to issuance.
    """

    entry_id: str = Field(default_factory=lambda: f"comm-{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.now)
    direction: str = "outbound"  # inbound | outbound
    channel: str = "email"  # phone | email | fax | meeting | portal | letter
    party: str = ""
    party_role: str = "broker"  # broker | applicant | underwriter | claims | reinsurer | other
    summary: str = ""
    detail: str = ""
    author: str = ""
    related_entries: list[str] = Field(default_factory=list)


class ReinsuranceRequest(BaseModel):
    """Documentation of a request for reinsurance on a particular case.

    Mirrors the classical worksheet item: documentation of requests for
    reinsurance, the market approached, and the disposition.
    """

    request_id: str = Field(default_factory=lambda: f"re-{uuid.uuid4().hex[:8]}")
    requested_at: datetime = Field(default_factory=datetime.now)
    request_type: str = "facultative"  # facultative | treaty | retrocession
    structure: str = ""  # quota_share | surplus_share | excess_of_loss | stop_loss
    layer_limit: float = 0.0
    attachment_point: float = 0.0
    retention: float = 0.0
    ceded_pct: float = 0.0
    ceding_commission_pct: float = 0.0
    market: str = ""  # lead reinsurer or broker
    reason: str = ""
    status: str = "requested"  # requested | quoted | bound | declined | pending
    premium: float = 0.0
    notes: str = ""


class AgentResult(BaseModel):
    agent_type: AgentType
    agent_name: str
    processed_at: datetime = Field(default_factory=datetime.now)
    success: bool = True
    findings: list[Finding] = Field(default_factory=list)
    risk_score: float = 0.5
    risk_severity: RiskSeverity = RiskSeverity.MODERATE
    recommendation: Optional[Recommendation] = None
    summary: str = ""
    errors: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    data_sources_used: list[str] = Field(default_factory=list)


class AgentMessage(BaseModel):
    sender: AgentType
    recipient: AgentType
    message_type: str = "finding"
    content: str = ""
    findings: list[Finding] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class UnderwritingMemo(BaseModel):
    bundle_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    insured_name: str = ""
    decision: UWDecision = UWDecision.REFER
    overall_risk_score: float = 0.5
    overall_risk_severity: RiskSeverity = RiskSeverity.MODERATE

    summary: str = ""
    key_findings: list[Finding] = Field(default_factory=list)
    risk_analyst_findings: list[Finding] = Field(default_factory=list)
    loss_run_findings: list[Finding] = Field(default_factory=list)
    compliance_findings: list[Finding] = Field(default_factory=list)
    fraud_findings: list[Finding] = Field(default_factory=list)
    moral_hazard_findings: list[Finding] = Field(default_factory=list)

    recommendation: Optional[Recommendation] = None
    conditions: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    human_review_reasons: list[str] = Field(default_factory=list)

    # Underwriting worksheet — communication log & reinsurance request records
    communications_log: list[CommunicationEntry] = Field(default_factory=list)
    reinsurance_requests: list[ReinsuranceRequest] = Field(default_factory=list)

    agent_results: dict[str, AgentResult] = Field(default_factory=dict)

    # Licensed UW sign-off
    approved_by: str = ""
    approved_at: Optional[datetime] = None
    license_number: str = ""
    sign_off_notes: str = ""
    sign_off_action: str = ""
    workflow_state: str = "pending_review"

    def add_communication(
        self,
        *,
        direction: str = "outbound",
        channel: str = "email",
        party: str = "",
        party_role: str = "broker",
        summary: str = "",
        detail: str = "",
        author: str = "",
        related_entries: Optional[list[str]] = None,
    ) -> CommunicationEntry:
        """Append a communication-log entry and return it (worksheet record)."""
        entry = CommunicationEntry(
            direction=direction,
            channel=channel,
            party=party,
            party_role=party_role,
            summary=summary,
            detail=detail,
            author=author,
            related_entries=list(related_entries or []),
        )
        self.communications_log.append(entry)
        return entry

    def add_reinsurance_request(
        self,
        *,
        request_type: str = "facultative",
        structure: str = "",
        layer_limit: float = 0.0,
        attachment_point: float = 0.0,
        retention: float = 0.0,
        ceded_pct: float = 0.0,
        ceding_commission_pct: float = 0.0,
        market: str = "",
        reason: str = "",
        status: str = "requested",
        premium: float = 0.0,
        notes: str = "",
    ) -> ReinsuranceRequest:
        """Append a reinsurance-request record and return it (worksheet record)."""
        request = ReinsuranceRequest(
            request_type=request_type,
            structure=structure,
            layer_limit=layer_limit,
            attachment_point=attachment_point,
            retention=retention,
            ceded_pct=ceded_pct,
            ceding_commission_pct=ceding_commission_pct,
            market=market,
            reason=reason,
            status=status,
            premium=premium,
            notes=notes,
        )
        self.reinsurance_requests.append(request)
        return request
