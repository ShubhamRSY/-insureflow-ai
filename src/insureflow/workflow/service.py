from __future__ import annotations

from uuid import uuid4

from insureflow.workflow.models import SignOffAction, SignOffRecord, WorkflowRecord, WorkflowState
from insureflow.workflow.store import WorkflowStore


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
        except Exception:
            pass

    def start(self, bundle_id: str, org_id: str, ai_decision: str) -> WorkflowRecord:
        record = WorkflowRecord(
            bundle_id=bundle_id,
            org_id=org_id,
            state=WorkflowState.ANALYZING,
            ai_decision=ai_decision,
        )
        self.store.save(record)
        return record

    def submit_for_review(self, bundle_id: str, org_id: str, ai_decision: str) -> WorkflowRecord:
        record = self.store.get(bundle_id, org_id) or WorkflowRecord(bundle_id=bundle_id, org_id=org_id)
        if record.state in (WorkflowState.APPROVED, WorkflowState.BOUND):
            raise ValueError(f"Cannot reopen workflow in {record.state.value} state")
        record.state = WorkflowState.PENDING_REVIEW
        record.ai_decision = ai_decision
        self.store.save(record)
        return record

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

        if record.state not in (WorkflowState.PENDING_REVIEW,):
            raise ValueError(f"Cannot sign off — workflow state is {record.state.value}. Must be PENDING_REVIEW.")

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
            record.final_decision = "approve"
        elif action == SignOffAction.DECLINE:
            record.state = WorkflowState.DECLINED
            record.final_decision = "decline"
        else:
            record.state = WorkflowState.PENDING_REVIEW
            record.final_decision = action.value

        self.store.save(record)
        return record

    def mark_bound(self, bundle_id: str, org_id: str, policy_number: str) -> WorkflowRecord:
        record = self.store.get(bundle_id, org_id)
        if not record:
            raise ValueError(f"No workflow found for bundle {bundle_id}")
        if record.state != WorkflowState.APPROVED:
            raise ValueError("Policy can only be bound after UW approval")
        record.state = WorkflowState.BOUND
        record.metadata["policy_number"] = policy_number
        self.store.save(record)
        return record
