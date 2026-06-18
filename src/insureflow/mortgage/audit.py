from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from insureflow.audit.store import AuditStore
from insureflow.models.audit import AuditEntry, AuditTrail, EventSeverity, PipelineEvent
from insureflow.models.mortgage import MortgageBundle, MortgageMemo


class MortgageAuditLogger:
    """Audit trail for mortgage pipeline runs — wired to AuditStore."""

    def __init__(self, store: AuditStore | None = None) -> None:
        self.store = store or AuditStore()
        self._trail: AuditTrail | None = None

    def start(self, bundle_id: str) -> AuditTrail:
        self._trail = AuditTrail(
            trail_id=f"trail-{uuid4().hex[:12]}",
            bundle_id=bundle_id,
        )
        self.log(PipelineEvent.SUBMISSION_RECEIVED, f"Mortgage submission received: {bundle_id}")
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
                metadata=metadata or {},
            )
        )

    def persist(
        self,
        bundle: MortgageBundle,
        memo: MortgageMemo,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        if self._trail is None:
            self.start(bundle.bundle_id)

        self.log(PipelineEvent.PIPELINE_COMPLETE, f"Decision: {memo.decision.value.upper()}")

        if memo.human_review_required:
            self.log(
                PipelineEvent.HUMAN_REVIEW_REQUIRED,
                "Human review required before final decision",
                severity=EventSeverity.WARNING,
            )

        for issue in bundle.reconciliation_issues:
            self.log(
                PipelineEvent.DISCREPANCY_DETECTED,
                f"{issue.field_path}: {issue.value_a} vs {issue.value_b}",
                severity=EventSeverity.WARNING if issue.severity == "warning" else EventSeverity.ERROR,
                metadata={"rule_id": issue.rule_id},
            )

        for violation in bundle.compliance_violations:
            sev = EventSeverity.CRITICAL if violation.severity == "critical" else EventSeverity.WARNING
            self.log(
                PipelineEvent.DISCREPANCY_DETECTED,
                f"[{violation.rule_id}] {violation.message}",
                severity=sev,
                metadata={"rule_id": violation.rule_id, "compliance": True},
            )

        assert self._trail is not None
        self._trail.completed_at = datetime.now(tz=timezone.utc)

        bundle_dir = self.store.base_path / bundle.bundle_id
        bundle_dir.mkdir(parents=True, exist_ok=True)

        paths: dict[str, str] = {}

        bundle_path = bundle_dir / "mortgage_bundle.json"
        bundle_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
        paths["bundle"] = str(bundle_path)

        memo_path = bundle_dir / "mortgage_memo.json"
        memo_path.write_text(memo.model_dump_json(indent=2), encoding="utf-8")
        paths["memo"] = str(memo_path)

        trail_path = bundle_dir / "audit_trail.json"
        trail_path.write_text(self._trail.model_dump_json(indent=2), encoding="utf-8")
        paths["audit_trail"] = str(trail_path)

        if extra:
            summary_path = bundle_dir / "pipeline_summary.json"
            import json
            summary_path.write_text(json.dumps(extra, indent=2, default=str), encoding="utf-8")
            paths["summary"] = str(summary_path)

        return paths

    @property
    def trail(self) -> AuditTrail | None:
        return self._trail
