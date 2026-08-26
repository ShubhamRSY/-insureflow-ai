from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from insureflow.decisions import DecisionOutcome, is_decline, normalize_decision, to_vertical
from insureflow.underwriting.cosign import CoSignStatus, active_cosign, cosign_allows_bind, create_cosign_request, resolve_cosign
from insureflow.workflow.models import (
    EscalationRecord,
    ReviewPriority,
    SignOffAction,
    SignOffRecord,
    WorkflowRecord,
    WorkflowState,
    allows_bind,
)
from insureflow.workflow.store import WorkflowStore

logger = logging.getLogger(__name__)


class WorkflowService:
    def __init__(self, store: WorkflowStore | None = None) -> None:
        self.store = store or WorkflowStore()

    def _track_override(self, bundle_id: str, ai_decision: str, human_decision: str, signed_by: str, override_reason: str, org_id: str) -> None:
        try:
            from insureflow.analytics.metrics import get_pipeline_metrics

            get_pipeline_metrics().override_rate.record_sign_off(
                bundle_id=bundle_id,
                ai_decision=ai_decision,
                human_decision=human_decision,
                signed_by=signed_by,
                override_reason=override_reason,
                org_id=org_id,
            )
        except Exception as exc:
            import logging as _log

            _log.getLogger(__name__).debug("Override rate tracking failed: %s", exc)

    def start(self, bundle_id: str, org_id: str, ai_decision: str) -> WorkflowRecord:
        record = WorkflowRecord(
            bundle_id=bundle_id,
            org_id=org_id,
            state=WorkflowState.ANALYZING,
            ai_decision=ai_decision,
        )
        self.store.save(record)
        return record

    def submit_for_review(
        self,
        bundle_id: str,
        org_id: str,
        ai_decision: str,
        priority: ReviewPriority = ReviewPriority.NORMAL,
        assigned_to: str = "",
    ) -> WorkflowRecord:
        record = self.store.get(bundle_id, org_id) or WorkflowRecord(bundle_id=bundle_id, org_id=org_id)
        if record.state in (WorkflowState.APPROVED, WorkflowState.QUOTED, WorkflowState.BOUND):
            raise ValueError(f"Cannot reopen workflow in {record.state.value} state")
        record.state = WorkflowState.PENDING_REVIEW
        record.ai_decision = ai_decision
        record.priority = priority
        if assigned_to:
            record.assigned_to = assigned_to
            record.assigned_at = datetime.now(tz=timezone.utc)
        record.compute_sla_deadline()
        self.store.save(record)
        return record

    def assign(self, bundle_id: str, org_id: str, assignee: str) -> WorkflowRecord:
        """Route a case to a specific underwriter. Sets/restarts SLA clock."""
        record = self.store.get(bundle_id, org_id)
        if not record:
            raise ValueError(f"No workflow found for bundle {bundle_id}")
        record.assigned_to = assignee
        record.assigned_at = datetime.now(tz=timezone.utc)
        record.compute_sla_deadline()
        self.store.save(record)
        return record

    def escalate(
        self,
        bundle_id: str,
        org_id: str,
        escalate_to: str,
        reason: str = "",
    ) -> WorkflowRecord:
        """Escalate an overdue or high-priority case to a senior underwriter."""
        record = self.store.get(bundle_id, org_id)
        if not record:
            raise ValueError(f"No workflow found for bundle {bundle_id}")
        overdue_hours = record.hours_overdue()
        escalation = EscalationRecord(
            escalation_id=f"esc-{uuid4().hex[:8]}",
            bundle_id=bundle_id,
            org_id=org_id,
            escalated_from=record.assigned_to,
            escalated_to=escalate_to,
            reason=reason or (f"SLA breached by {overdue_hours:.1f}h" if overdue_hours > 0 else "Manual escalation"),
            sla_breach_hours=overdue_hours,
        )
        record.escalations.append(escalation)
        record.assigned_to = escalate_to
        record.assigned_at = datetime.now(tz=timezone.utc)
        record.state = WorkflowState.ESCALATED
        record.compute_sla_deadline()
        self.store.save(record)
        logger.warning(
            "Bundle %s escalated to %s (overdue %.1fh): %s",
            bundle_id,
            escalate_to,
            overdue_hours,
            escalation.reason,
        )
        return record

    def check_overdue(self, org_id: str = "default") -> list[WorkflowRecord]:
        """Return all cases in PENDING_REVIEW/ESCALATED state that have breached SLA."""
        all_records = self.store.list_by_org(org_id) if hasattr(self.store, "list_by_org") else []
        return [r for r in all_records if r.state in (WorkflowState.PENDING_REVIEW, WorkflowState.ESCALATED) and r.is_overdue()]

    def reassign_if_overdue(self, org_id: str, supervisor: str) -> list[WorkflowRecord]:
        """Auto-escalate overdue cases to a supervisor if no escalation exists yet."""
        overdue = self.check_overdue(org_id)
        reassigned: list[WorkflowRecord] = []
        for record in overdue:
            # Only auto-escalate if not already escalated
            if not record.escalations:
                self.escalate(
                    record.bundle_id,
                    org_id,
                    escalate_to=supervisor,
                    reason=f"Auto-escalation: SLA breached by {record.hours_overdue():.1f}h",
                )
                reassigned.append(record)
        return reassigned

    def sign_off(
        self,
        bundle_id: str,
        org_id: str,
        action: SignOffAction,
        signed_by: str,
        license_number: str = "",
        notes: str = "",
        override_reason: str = "",
        ai_decision: str = "",
    ) -> WorkflowRecord:
        record = self.store.get(bundle_id, org_id)
        if not record:
            raise ValueError(f"No workflow found for bundle {bundle_id}")

        if record.state not in (WorkflowState.PENDING_REVIEW, WorkflowState.PENDING_CO_SIGN):
            raise ValueError(f"Cannot sign off — workflow state is {record.state.value}. Must be PENDING_REVIEW (or PENDING_CO_SIGN to cancel back to review).")

        prior_ai = ai_decision or record.ai_decision
        if action in (SignOffAction.APPROVE, SignOffAction.QUOTE) and is_decline(prior_ai):
            if not (override_reason or "").strip():
                raise ValueError("override_reason is required when quoting or approving a submission the AI declined")
        if action == SignOffAction.NO_QUOTE and not (notes or override_reason).strip():
            raise ValueError("notes or override_reason is required for a no-quote decision")

        sign_off = SignOffRecord(
            sign_off_id=f"so-{uuid4().hex[:10]}",
            bundle_id=bundle_id,
            org_id=org_id,
            action=action,
            signed_by=signed_by,
            license_number=license_number,
            notes=notes,
            ai_decision=ai_decision or record.ai_decision,
            override_reason=override_reason,
        )
        record.sign_offs.append(sign_off)

        self._track_override(
            bundle_id=bundle_id,
            ai_decision=ai_decision or record.ai_decision,
            human_decision=action.value,
            signed_by=signed_by,
            override_reason=override_reason,
            org_id=org_id,
        )

        if action == SignOffAction.APPROVE:
            record.state = WorkflowState.APPROVED
            record.final_decision = to_vertical(DecisionOutcome.ACCEPT, "insurance")
            record.metadata["outcome"] = DecisionOutcome.ACCEPT.value
            record.metadata["quote_intent"] = "quote"
        elif action == SignOffAction.QUOTE:
            record.state = WorkflowState.QUOTED
            record.final_decision = "quote"
            record.metadata["outcome"] = DecisionOutcome.ACCEPT.value
            record.metadata["quote_intent"] = "quote"
        elif action == SignOffAction.NO_QUOTE:
            record.state = WorkflowState.NO_QUOTE
            record.final_decision = "no_quote"
            record.metadata["outcome"] = DecisionOutcome.DECLINE.value
            record.metadata["quote_intent"] = "no_quote"
        elif action == SignOffAction.DECLINE:
            record.state = WorkflowState.DECLINED
            record.final_decision = to_vertical(DecisionOutcome.DECLINE, "insurance")
            record.metadata["outcome"] = DecisionOutcome.DECLINE.value
            record.metadata["quote_intent"] = "no_quote"
        elif action == SignOffAction.REQUEST_INFO:
            record.state = WorkflowState.PENDING_REVIEW
            record.final_decision = "request_info"
            record.metadata["outcome"] = DecisionOutcome.REFER.value
            try:
                from insureflow.insurance.collaboration import get_collaboration_store

                docs: list[str] = []
                if notes:
                    lowered = notes.lower()
                    if "docs:" in lowered:
                        part = notes.split(":", 1)[1]
                        docs = [d.strip() for d in part.split(",") if d.strip()]
                    else:
                        docs = [notes[:240]]
                get_collaboration_store().add_info_request(
                    bundle_id,
                    org_id,
                    docs or ["Additional underwriting information"],
                    notes=notes,
                    requested_by=signed_by,
                    source="uw_signoff",
                )
            except Exception as exc:
                import logging as _log

                _log.getLogger(__name__).debug("Info request persist failed: %s", exc)
        else:
            record.state = WorkflowState.PENDING_REVIEW
            record.final_decision = action.value
            record.metadata["outcome"] = normalize_decision(action.value).value

        self.store.save(record)
        return record

    def request_cosign(
        self,
        bundle_id: str,
        org_id: str,
        requested_by: str,
        premium: float,
        tiv: float,
        reason: str = "",
    ) -> WorkflowRecord:
        record = self.store.get(bundle_id, org_id)
        if not record:
            raise ValueError(f"No workflow found for bundle {bundle_id}")
        if record.state not in (WorkflowState.APPROVED, WorkflowState.QUOTED, WorkflowState.PENDING_CO_SIGN):
            raise ValueError("Co-sign can only be requested after UW quote/approval")
        existing = active_cosign(record.metadata)
        if existing and existing.status == CoSignStatus.APPROVED:
            return record
        req = create_cosign_request(
            bundle_id=bundle_id,
            org_id=org_id,
            requested_by=requested_by,
            premium=premium,
            tiv=tiv,
            reason=reason,
        )
        record.metadata["co_sign"] = req.model_dump(mode="json")
        record.state = WorkflowState.PENDING_CO_SIGN
        self.store.save(record)
        return record

    def resolve_cosign_request(
        self,
        bundle_id: str,
        org_id: str,
        signer_username: str,
        approve: bool,
        notes: str = "",
    ) -> WorkflowRecord:
        record = self.store.get(bundle_id, org_id)
        if not record:
            raise ValueError(f"No workflow found for bundle {bundle_id}")
        pending = active_cosign(record.metadata)
        if not pending or pending.status != CoSignStatus.PENDING:
            raise ValueError("No pending co-sign request for this bundle")
        updated = resolve_cosign(
            pending,
            signer_username=signer_username,
            approve=approve,
            notes=notes,
            org_id=org_id,
        )
        record.metadata["co_sign"] = updated.model_dump(mode="json")
        restored = WorkflowState.QUOTED if record.final_decision == "quote" else WorkflowState.APPROVED
        if approve:
            record.state = restored
        else:
            record.state = restored  # UW quote/approval stands; bind still blocked until new co-sign
            # Keep rejected record so binder sees rejection; they must re-request
        self.store.save(record)
        return record

    def mark_bound(self, bundle_id: str, org_id: str, policy_number: str, binder_username: str = "") -> WorkflowRecord:
        record = self.store.get(bundle_id, org_id)
        if not record:
            raise ValueError(f"No workflow found for bundle {bundle_id}")
        if not allows_bind(record.state):
            raise ValueError("Policy can only be bound after UW quote/approval (and co-sign if required)")
        if binder_username:
            ok, reason = cosign_allows_bind(record.metadata, binder_username)
            if not ok:
                raise ValueError(reason)
        record.state = WorkflowState.BOUND
        record.metadata["policy_number"] = policy_number
        self.store.save(record)
        return record
