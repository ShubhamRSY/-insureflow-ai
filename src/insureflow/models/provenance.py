from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"
    SUPPLEMENTAL = "supplemental"


class TrustLevel(str, Enum):
    AUTHORITATIVE = "authoritative"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    UNVERIFIED = "unverified"
    PARTIALLY_VERIFIED = "partially_verified"
    AMBIGUOUS = "ambiguous"


class DataSource(BaseModel):
    source_id: str
    source_type: SourceType
    source_name: str
    received_at: datetime
    trust_level: TrustLevel = TrustLevel.UNVERIFIED
    hierarchy_rank: int = 0


class ProvenanceNode(BaseModel):
    node_id: str
    field_path: str
    value: Any
    source: DataSource
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    confidence: float = 0.0
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verified_against: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ProvenanceHierarchy(BaseModel):
    hierarchy_name: str = "underwriting_provenance"
    levels: list[str] = Field(
        default_factory=lambda: [
            "signed_legal_submission",
            "broker_acord_xml",
            "underwriter_notes",
            "inspection_report",
            "supplemental_document",
        ]
    )

    def rank_for_source(self, source_name: str) -> int:
        for i, level in enumerate(self.levels):
            if source_name in level or level in source_name:
                return len(self.levels) - i
        return 0

    def higher_ranked(self, source_a: str, source_b: str) -> str:
        rank_a = self.rank_for_source(source_a)
        rank_b = self.rank_for_source(source_b)
        return source_a if rank_a >= rank_b else source_b


class ProvenanceRecord(BaseModel):
    record_id: str
    bundle_id: str
    nodes: dict[str, list[ProvenanceNode]] = Field(default_factory=dict)
    hierarchy: ProvenanceHierarchy = Field(default_factory=ProvenanceHierarchy)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    resolved_at: Optional[datetime] = None

    def record_count(self) -> int:
        return sum(len(nodes) for nodes in self.nodes.values())

    def verified_count(self) -> int:
        count = 0
        for nodes in self.nodes.values():
            for node in nodes:
                if node.verification_status == VerificationStatus.VERIFIED:
                    count += 1
        return count

    def discrepancy_count(self) -> int:
        count = 0
        for nodes in self.nodes.values():
            for node in nodes:
                if node.verification_status == VerificationStatus.CONTRADICTED:
                    count += 1
        return count
