"""Cryptographic hash chain for tamper-evident audit records.

Every audit event is linked to its predecessor via SHA-256 hashes, creating an
append-only chain. Any modification to a historical record breaks the chain and
is detectable via ``verify_chain``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ChainedAuditRecord(BaseModel):
    record_id: str
    bundle_id: str
    org_id: str
    event_kind: str
    severity: str = "info"
    agent_name: str = ""
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    previous_hash: str = ""
    record_hash: str = ""

    def compute_hash(self) -> str:
        payload = {
            "record_id": self.record_id,
            "bundle_id": self.bundle_id,
            "org_id": self.org_id,
            "event_kind": self.event_kind,
            "severity": self.severity,
            "agent_name": self.agent_name,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "previous_hash": self.previous_hash,
        }
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


class ChainVerificationResult(BaseModel):
    chain_length: int = 0
    valid: bool = True
    broken_at: str | None = None
    broken_record_id: str | None = None
    expected_hash: str = ""
    actual_hash: str = ""
    verified_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class AuditHashChain:
    def __init__(self, org_id: str = "default") -> None:
        self.org_id = org_id
        self._records: list[ChainedAuditRecord] = []
        self._index: dict[str, ChainedAuditRecord] = {}

    @property
    def head_hash(self) -> str:
        if not self._records:
            return ""
        return self._records[-1].record_hash

    @property
    def length(self) -> int:
        return len(self._records)

    def append(
        self,
        record_id: str,
        bundle_id: str,
        event_kind: str,
        message: str = "",
        severity: str = "info",
        agent_name: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ChainedAuditRecord:
        record = ChainedAuditRecord(
            record_id=record_id,
            bundle_id=bundle_id,
            org_id=self.org_id,
            event_kind=event_kind,
            severity=severity,
            agent_name=agent_name,
            message=message,
            metadata=metadata or {},
            previous_hash=self.head_hash,
        )
        record.record_hash = record.compute_hash()
        self._records.append(record)
        self._index[record_id] = record
        return record

    def get(self, record_id: str) -> ChainedAuditRecord | None:
        return self._index.get(record_id)

    def records_for_bundle(self, bundle_id: str) -> list[ChainedAuditRecord]:
        return [r for r in self._records if r.bundle_id == bundle_id]

    def verify(self) -> ChainVerificationResult:
        if not self._records:
            return ChainVerificationResult(chain_length=0, valid=True)
        for i, record in enumerate(self._records):
            expected_hash = record.compute_hash()
            if record.record_hash != expected_hash:
                return ChainVerificationResult(
                    chain_length=i + 1,
                    valid=False,
                    broken_at=record.timestamp.isoformat(),
                    broken_record_id=record.record_id,
                    expected_hash=expected_hash,
                    actual_hash=record.record_hash,
                )
            if i > 0 and record.previous_hash != self._records[i - 1].record_hash:
                return ChainVerificationResult(
                    chain_length=i + 1,
                    valid=False,
                    broken_at=record.timestamp.isoformat(),
                    broken_record_id=record.record_id,
                    expected_hash=self._records[i - 1].record_hash,
                    actual_hash=record.previous_hash,
                )
        return ChainVerificationResult(chain_length=len(self._records), valid=True)

    def export_chain(self) -> list[dict[str, Any]]:
        return [r.model_dump(mode="json") for r in self._records]

    @classmethod
    def from_export(cls, data: list[dict[str, Any]], org_id: str = "default") -> AuditHashChain:
        chain = cls(org_id=org_id)
        for item in data:
            record = ChainedAuditRecord(**item)
            chain._records.append(record)
            chain._index[record.record_id] = record
        return chain
