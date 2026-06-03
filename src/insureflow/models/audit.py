from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PipelineEvent(str, Enum):
    SUBMISSION_RECEIVED = "submission_received"
    STRUCTURED_PARSE_START = "structured_parse_start"
    STRUCTURED_PARSE_COMPLETE = "structured_parse_complete"
    EXTRACTION_START = "extraction_start"
    EXTRACTION_COMPLETE = "extraction_complete"
    RECONCILIATION_START = "reconciliation_start"
    RECONCILIATION_COMPLETE = "reconciliation_complete"
    PROVENANCE_CHECK = "provenance_check"
    DISCREPANCY_DETECTED = "discrepancy_detected"
    DISCREPANCY_RESOLVED = "discrepancy_resolved"
    VERIFICATION_COMPLETE = "verification_complete"
    SYNTHESIS_START = "synthesis_start"
    SYNTHESIS_COMPLETE = "synthesis_complete"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_FAILED = "pipeline_failed"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class DiscrepancyRecord(BaseModel):
    field_path: str
    structured_value: Optional[Any] = None
    unstructured_value: Optional[Any] = None
    severity: EventSeverity = EventSeverity.WARNING
    description: str = ""
    source_a: str = ""
    source_b: str = ""
    resolved: bool = False
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    provenance_node_ids: list[str] = Field(default_factory=list)


class ReconciliationResult(BaseModel):
    bundle_id: str
    field_reconciliation: dict[str, dict[str, Any]] = Field(default_factory=dict)
    discrepancies: list[DiscrepancyRecord] = Field(default_factory=list)
    matched_fields: int = 0
    total_fields: int = 0
    match_rate: float = 0.0
    reconciled_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    overall_status: str = "pending"


class AuditEntry(BaseModel):
    entry_id: str
    bundle_id: str
    event: PipelineEvent
    severity: EventSeverity = EventSeverity.INFO
    agent_name: str = ""
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class AuditTrail(BaseModel):
    trail_id: str
    bundle_id: str
    entries: list[AuditEntry] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    completed_at: Optional[datetime] = None

    def add_entry(self, entry: AuditEntry) -> None:
        self.entries.append(entry)

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.entries:
            counts[entry.event.value] = counts.get(entry.event.value, 0) + 1
        return counts


class SynthesisOutput(BaseModel):
    bundle_id: str
    synthesized_profile: dict[str, Any] = Field(default_factory=dict)
    confidence_scores: dict[str, float] = Field(default_factory=dict)
    provenance_summary: dict[str, Any] = Field(default_factory=dict)
    discrepancies_found: int = 0
    discrepancies_resolved: int = 0
    human_review_required: bool = False
    review_fields: list[str] = Field(default_factory=list)
    rag_context_used: bool = False
    completed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
