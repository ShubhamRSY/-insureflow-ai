from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from insureflow.audit.store import AuditStore
from insureflow.models.agents import UnderwritingMemo
from insureflow.models.audit import AuditEntry, AuditTrail, EventSeverity, PipelineEvent
from insureflow.models.provenance import ProvenanceRecord
from insureflow.models.submissions import SubmissionBundle
from insureflow.models.audit import ReconciliationResult
from insureflow.storage.encryption import EnvelopeEncryption


class InsuranceAuditLogger:
    """Encrypted audit persistence for insurance submissions — mirrors MortgageAuditLogger."""

    def __init__(
        self,
        store: AuditStore | None = None,
        encryption: EnvelopeEncryption | None = None,
        org_id: str = "default",
    ) -> None:
        self.store = store or AuditStore()
        self.encryption = encryption or EnvelopeEncryption()
        self.org_id = org_id
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

        return paths

    @property
    def trail(self) -> AuditTrail | None:
        return self._trail
