"""Document retention policy engine — automated enforcement with legal holds.

Enforces per-artifact-type retention schedules, supports legal holds to prevent
deletion of records under investigation, and implements DOI-specific retention
requirements (typically 5–7 years for underwriting files, 10+ years for claims).
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ArtifactType(str, Enum):
    SUBMISSION_BUNDLE = "submission_bundle"
    AUDIT_TRAIL = "audit_trail"
    PROVENANCE_RECORD = "provenance_record"
    RECONCILIATION = "reconciliation"
    UNDERWRITING_MEMO = "underwriting_memo"
    SYNTHESIS_OUTPUT = "synthesis_output"
    REGULATORY_PACKAGE = "regulatory_package"
    QUOTE = "quote"
    SIGN_OFF = "sign_off"


class RetentionPolicy(BaseModel):
    """Retention configuration for a specific artifact type."""

    artifact_type: ArtifactType
    retention_days: int = 2555  # ~7 years default
    legal_hold_allowed: bool = True
    description: str = ""


class LegalHold(BaseModel):
    """An active legal hold preventing deletion."""

    hold_id: str = Field(default_factory=lambda: f"hold-{uuid4().hex[:8]}")
    bundle_id: str = ""
    org_id: str = "default"
    reason: str = ""
    applied_by: str = "system"
    applied_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    expires_at: Optional[datetime] = None


class RetentionRecord(BaseModel):
    """Tracks the retention lifecycle of a single artifact."""

    artifact_type: ArtifactType
    bundle_id: str
    org_id: str = "default"
    file_path: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    archived: bool = False
    deleted: bool = False
    legal_holds: list[str] = Field(default_factory=list)  # hold_ids


class EnforcementReport(BaseModel):
    """Summary of a retention enforcement run."""

    org_id: str = "default"
    checked_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    total_artifacts: int = 0
    expired: int = 0
    deleted: int = 0
    archived: int = 0
    held: int = 0  # blocked by legal hold
    errors: list[str] = Field(default_factory=list)


DEFAULT_POLICIES: list[RetentionPolicy] = [
    RetentionPolicy(
        artifact_type=ArtifactType.SUBMISSION_BUNDLE,
        retention_days=2555,
        description="Core submission data — 7 years minimum per DOI regulations",
    ),
    RetentionPolicy(
        artifact_type=ArtifactType.AUDIT_TRAIL,
        retention_days=3650,
        description="Pipeline audit events — 10 years for examination purposes",
    ),
    RetentionPolicy(
        artifact_type=ArtifactType.PROVENANCE_RECORD,
        retention_days=2555,
        description="Source attribution records — 7 years minimum",
    ),
    RetentionPolicy(
        artifact_type=ArtifactType.RECONCILIATION,
        retention_days=2555,
        description="Cross-source reconciliation results — 7 years",
    ),
    RetentionPolicy(
        artifact_type=ArtifactType.UNDERWRITING_MEMO,
        retention_days=3650,
        description="Underwriting decision memos — 10 years for regulatory review",
    ),
    RetentionPolicy(
        artifact_type=ArtifactType.SYNTHESIS_OUTPUT,
        retention_days=2555,
        description="Synthesized profiles — 7 years",
    ),
    RetentionPolicy(
        artifact_type=ArtifactType.REGULATORY_PACKAGE,
        retention_days=3650,
        description="Examiner-ready packages — 10 years",
    ),
    RetentionPolicy(
        artifact_type=ArtifactType.QUOTE,
        retention_days=1825,
        description="Quote artifacts — 5 years minimum",
    ),
    RetentionPolicy(
        artifact_type=ArtifactType.SIGN_OFF,
        retention_days=3650,
        description="Human sign-off records — 10 years for accountability",
    ),
]


class RetentionEngine:
    """Manages retention policies, legal holds, and automated enforcement."""

    def __init__(
        self,
        base_path: Path | str = "./audit_logs",
        policies: list[RetentionPolicy] | None = None,
    ) -> None:
        self.base_path = Path(base_path)
        self.policies = {p.artifact_type: p for p in (policies or DEFAULT_POLICIES)}
        self._holds: dict[str, LegalHold] = {}
        self._records: dict[str, RetentionRecord] = {}

    def get_policy(self, artifact_type: ArtifactType) -> RetentionPolicy:
        """Get retention policy for an artifact type."""
        return self.policies.get(
            artifact_type,
            RetentionPolicy(artifact_type=artifact_type),
        )

    def apply_legal_hold(
        self,
        bundle_id: str,
        reason: str,
        org_id: str = "default",
        applied_by: str = "system",
        expires_at: datetime | None = None,
    ) -> LegalHold:
        """Place a legal hold on a bundle to prevent retention enforcement."""
        hold = LegalHold(
            bundle_id=bundle_id,
            org_id=org_id,
            reason=reason,
            applied_by=applied_by,
            expires_at=expires_at,
        )
        self._holds[hold.hold_id] = hold
        # Attach to all existing records for this bundle
        for record in self._records.values():
            if record.bundle_id == bundle_id and record.org_id == org_id:
                if hold.hold_id not in record.legal_holds:
                    record.legal_holds.append(hold.hold_id)
        logger.info("Legal hold %s applied to bundle %s: %s", hold.hold_id, bundle_id, reason)
        return hold

    def remove_hold(self, hold_id: str) -> bool:
        """Remove a legal hold."""
        if hold_id not in self._holds:
            return False
        hold = self._holds.pop(hold_id)
        for record in self._records.values():
            if hold.bundle_id in record.legal_holds:
                record.legal_holds.remove(hold.hold_id)
        logger.info("Legal hold %s removed", hold_id)
        return True

    def is_held(self, bundle_id: str, org_id: str = "default") -> bool:
        """Check if a bundle has any active legal holds."""
        for hold in self._holds.values():
            if hold.bundle_id == bundle_id and hold.org_id == org_id:
                if hold.expires_at is None or hold.expires_at > datetime.now(timezone.utc):
                    return True
        return False

    def active_holds(self, org_id: str = "default") -> list[LegalHold]:
        """Return all active legal holds for an org."""
        now = datetime.now(timezone.utc)
        return [
            h
            for h in self._holds.values()
            if h.org_id == org_id and (h.expires_at is None or h.expires_at > now)
        ]

    def register_artifact(
        self,
        artifact_type: ArtifactType,
        bundle_id: str,
        org_id: str = "default",
        file_path: str = "",
        created_at: datetime | None = None,
    ) -> RetentionRecord:
        """Register an artifact for retention tracking."""
        policy = self.get_policy(artifact_type)
        created = created_at or datetime.now(timezone.utc)
        expires = created + timedelta(days=policy.retention_days)

        record = RetentionRecord(
            artifact_type=artifact_type,
            bundle_id=bundle_id,
            org_id=org_id,
            file_path=file_path,
            created_at=created,
            expires_at=expires,
        )

        if self.is_held(bundle_id, org_id):
            holds = [
                h.hold_id
                for h in self._holds.values()
                if h.bundle_id == bundle_id and h.org_id == org_id
            ]
            record.legal_holds = holds

        key = f"{org_id}:{bundle_id}:{artifact_type.value}"
        self._records[key] = record
        return record

    def check_expired(self, org_id: str = "default") -> list[RetentionRecord]:
        """Find artifacts that have passed their retention deadline."""
        now = datetime.now(timezone.utc)
        expired: list[RetentionRecord] = []
        for record in self._records.values():
            if record.org_id != org_id:
                continue
            if record.deleted or record.archived:
                continue
            if record.expires_at <= now:
                expired.append(record)
        return expired

    def enforce_retention(
        self,
        org_id: str = "default",
        archive_dir: Path | str | None = None,
        dry_run: bool = False,
    ) -> EnforcementReport:
        """Run retention enforcement: archive or delete expired artifacts."""
        report = EnforcementReport(org_id=org_id)
        expired = self.check_expired(org_id)
        report.total_artifacts = len(self._records)
        report.expired = len(expired)

        archive_path = Path(archive_dir) if archive_dir else self.base_path / org_id / "_archive"

        for record in expired:
            if record.legal_holds:
                report.held += 1
                continue
            if dry_run:
                report.archived += 1
                continue
            try:
                src = Path(record.file_path) if record.file_path else None
                if src and src.exists():
                    dest = archive_path / record.artifact_type.value / src.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dest))
                    record.archived = True
                    report.archived += 1
                    logger.info("Archived %s -> %s", src, dest)
                else:
                    record.deleted = True
                    report.deleted += 1
            except Exception as exc:
                report.errors.append(f"Failed to process {record.bundle_id}/{record.artifact_type.value}: {exc}")

        return report

    def summary(self, org_id: str = "default") -> dict[str, Any]:
        """Return a summary of retention status."""
        now = datetime.now(timezone.utc)
        records = [r for r in self._records.values() if r.org_id == org_id]
        active = [r for r in records if not r.deleted and not r.archived]
        held = [r for r in active if r.legal_holds]
        return {
            "org_id": org_id,
            "total_artifacts": len(records),
            "active": len(active),
            "archived": sum(1 for r in records if r.archived),
            "deleted": sum(1 for r in records if r.deleted),
            "legal_holds_active": len([h for h in self._holds.values() if h.org_id == org_id]),
            "held_artifacts": len(held),
            "next_expiry": min((r.expires_at for r in active), default=now).isoformat(),
        }
