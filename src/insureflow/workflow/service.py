from __future__ import annotations

from uuid import uuid4

from insureflow.workflow.models import SignOffAction, SignOffRecord, WorkflowRecord, WorkflowState
from insureflow.workflow.store import WorkflowStore


class WorkflowService:
    def __init__(self, store: WorkflowStore | None = None) -> None:
        self.store = store or WorkflowStore()

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

        if record.state not in (WorkflowState.PENDING_REVIEW, WorkflowState.ANALYZING):
            raise ValueError(f"Cannot sign off — workflow state is {record.state.value}")

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
