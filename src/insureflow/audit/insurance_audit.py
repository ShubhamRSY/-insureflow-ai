from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from insureflow.audit.retention import ArtifactType, RetentionEngine
from insureflow.audit.store import AuditStore
from insureflow.audit.worm import WormAuditStore
from insureflow.models.agents import UnderwritingMemo
from insureflow.models.audit import AuditEntry, AuditTrail, EventSeverity, PipelineEvent, ReconciliationResult
from insureflow.models.provenance import ProvenanceRecord
from insureflow.models.submissions import SubmissionBundle
from insureflow.storage.encryption import EnvelopeEncryption

logger = logging.getLogger(__name__)


class InsuranceAuditLogger:
    """Encrypted audit persistence for insurance submissions — mirrors MortgageAuditLogger."""

    def __init__(
        self,
        store: AuditStore | None = None,
        encryption: EnvelopeEncryption | None = None,
        org_id: str = "default",
        worm: WormAuditStore | None = None,
        retention: RetentionEngine | None = None,
    ) -> None:
        self.store = store or AuditStore()
        self.encryption = encryption or EnvelopeEncryption()
        self.org_id = org_id
        self.worm = worm or WormAuditStore()
        self.retention = retention or RetentionEngine()
        self._trail: AuditTrail | None = None

    def start(self, bundle_id: str) -> AuditTrail:
        self._trail = AuditTrail(
            trail_id=f"trail-{uuid4().hex[:12]}",
            bundle_id=bundle_id,
        )
        self.log(PipelineEvent.SUBMISSION_RECEIVED, f"Insurance submission received: {bundle_id}")
        return self._trail

    def log(
        self,
        event: PipelineEvent,
        message: str,
        *,
        severity: EventSeverity = EventSeverity.INFO,
        agent_name: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._trail is None:
            return
        self._trail.add_entry(
            AuditEntry(
                entry_id=f"entry-{uuid4().hex[:8]}",
                bundle_id=self._trail.bundle_id,
                event=event,
                severity=severity,
                agent_name=agent_name,
                message=message,
                metadata={**(metadata or {}), "org_id": self.org_id},
            )
        )

    def persist(
        self,
        bundle: SubmissionBundle | None,
        memo: UnderwritingMemo | None,
        provenance: ProvenanceRecord | None = None,
        reconciliation: ReconciliationResult | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        bundle_id = bundle.bundle_id if bundle else (extra or {}).get("bundle_id", "unknown")
        if self._trail is None:
            self.start(bundle_id)

        decision_label = "DECLINED (appetite)"
        if memo is not None:
            decision_label = memo.decision.value.upper()
        self.log(
            PipelineEvent.PIPELINE_COMPLETE,
            f"AI recommendation: {decision_label}",
            agent_name="uw_decision_agent",
        )

        if memo is not None and memo.human_review_required:
            self.log(
                PipelineEvent.HUMAN_REVIEW_REQUIRED,
                "Licensed UW sign-off required",
                severity=EventSeverity.WARNING,
            )

        if reconciliation:
            for disc in reconciliation.discrepancies:
                self.log(
                    PipelineEvent.DISCREPANCY_DETECTED,
                    f"{disc.field_path}: {disc.source_a} vs {disc.source_b}",
                    severity=EventSeverity.WARNING if disc.severity != EventSeverity.CRITICAL else EventSeverity.CRITICAL,
                    metadata={"description": disc.description},
                )

        assert self._trail is not None
        self._trail.completed_at = datetime.now(tz=timezone.utc)

        bundle_dir = self.store.base_path / self.org_id / bundle_id
        bundle_dir.mkdir(parents=True, exist_ok=True)

        paths: dict[str, str] = {}

        artifacts: dict[str, Any] = {
            "audit_trail.json": self._trail.model_dump(),
        }
        if bundle is not None:
            artifacts["submission_bundle.json"] = bundle.model_dump()
        if memo is not None:
            artifacts["underwriting_memo.json"] = memo.model_dump()
        if provenance:
            artifacts["provenance_record.json"] = provenance.model_dump()
        if reconciliation:
            artifacts["reconciliation.json"] = reconciliation.model_dump()
        if extra:
            artifacts["pipeline_summary.json"] = extra

        for filename, data in artifacts.items():
            path = str(bundle_dir / filename)
            self.encryption.write_encrypted_file(path, data)
            paths[filename.replace(".json", "")] = path

        if self.encryption.enabled:
            self.log(
                PipelineEvent.VERIFICATION_COMPLETE,
                "Regulatory audit bundle encrypted at rest",
                metadata={"encrypted": True},
            )

        # ── WORM seal: write-once-read-many for examiner audit ──
        worm_record: dict[str, Any] | None = None
        try:
            worm_record = self.worm.seal(self.org_id, bundle_id, self._trail.model_dump())
        except FileExistsError:
            logger.warning("WORM object already sealed for bundle %s — skipping duplicate", bundle_id)
        except Exception:
            logger.exception("WORM seal failed for bundle %s", bundle_id)

        # ── Retention registration: track lifecycle for each artifact ──
        retention_records: list[dict[str, Any]] = []
        for artifact_name, file_path in paths.items():
            try:
                artifact_type_map = {
                    "audit_trail": ArtifactType.AUDIT_TRAIL,
                    "submission_bundle": ArtifactType.SUBMISSION_BUNDLE,
                    "underwriting_memo": ArtifactType.UNDERWRITING_MEMO,
                    "provenance_record": ArtifactType.PROVENANCE_RECORD,
                    "reconciliation": ArtifactType.RECONCILIATION,
                    "pipeline_summary": ArtifactType.SYNTHESIS_OUTPUT,
                }
                art_type = artifact_type_map.get(artifact_name, ArtifactType.AUDIT_TRAIL)
                rec = self.retention.register_artifact(
                    artifact_type=art_type,
                    bundle_id=bundle_id,
                    org_id=self.org_id,
                    file_path=file_path,
                )
                retention_records.append(rec.model_dump())
            except Exception:
                logger.warning("Retention registration failed for %s", artifact_name, exc_info=True)

        if worm_record:
            paths["worm_seal"] = worm_record.get("path", "")
        if retention_records:
            paths["retention_records"] = str(len(retention_records))

        # ── Incremental audit trail persistence (crash-safe) ──
        try:
            trail_path = self.store.base_path / self.org_id / bundle_id / "audit_trail_incremental.json"
            trail_path.parent.mkdir(parents=True, exist_ok=True)
            trail_path.write_text(self._trail.model_dump_json(indent=2))
        except Exception:
            logger.warning("Incremental audit trail persist failed for bundle %s", bundle_id, exc_info=True)

        return paths

    @property
    def trail(self) -> AuditTrail | None:
        return self._trail
