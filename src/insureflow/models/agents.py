from __future__ import annotations

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


class RiskSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class UWDecision(str, Enum):
    ACCEPT = "accept"
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

    recommendation: Optional[Recommendation] = None
    conditions: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    human_review_reasons: list[str] = Field(default_factory=list)

    agent_results: dict[str, AgentResult] = Field(default_factory=dict)

    # Licensed UW sign-off
    approved_by: str = ""
    approved_at: Optional[datetime] = None
    license_number: str = ""
    sign_off_notes: str = ""
    sign_off_action: str = ""
    workflow_state: str = "pending_review"
