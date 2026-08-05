from __future__ import annotations

from uuid import uuid4

from insureflow.decisions import DecisionOutcome, is_decline, normalize_decision, to_vertical
from insureflow.underwriting.cosign import (
    CoSignStatus,
    active_cosign,
    cosign_allows_bind,
    create_cosign_request,
    resolve_cosign,
)
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

        if record.state not in (WorkflowState.PENDING_REVIEW, WorkflowState.PENDING_CO_SIGN):
            raise ValueError(f"Cannot sign off — workflow state is {record.state.value}. Must be PENDING_REVIEW (or PENDING_CO_SIGN to cancel back to review).")

        prior_ai = ai_decision or record.ai_decision
        if action == SignOffAction.APPROVE and is_decline(prior_ai):
            if not (override_reason or "").strip():
                raise ValueError("override_reason is required when approving a submission the AI declined")

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
        elif action == SignOffAction.DECLINE:
            record.state = WorkflowState.DECLINED
            record.final_decision = to_vertical(DecisionOutcome.DECLINE, "insurance")
            record.metadata["outcome"] = DecisionOutcome.DECLINE.value
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
        if record.state not in (WorkflowState.APPROVED, WorkflowState.PENDING_CO_SIGN):
            raise ValueError("Co-sign can only be requested after UW approval")
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
        if approve:
            record.state = WorkflowState.APPROVED
        else:
            record.state = WorkflowState.APPROVED  # UW approval stands; bind still blocked until new co-sign
            # Keep rejected record so binder sees rejection; they must re-request
        self.store.save(record)
        return record

    def mark_bound(self, bundle_id: str, org_id: str, policy_number: str, binder_username: str = "") -> WorkflowRecord:
        record = self.store.get(bundle_id, org_id)
        if not record:
            raise ValueError(f"No workflow found for bundle {bundle_id}")
        if record.state not in (WorkflowState.APPROVED,):
            raise ValueError("Policy can only be bound after UW approval (and co-sign if required)")
        if binder_username:
            ok, reason = cosign_allows_bind(record.metadata, binder_username)
            if not ok:
                raise ValueError(reason)
        record.state = WorkflowState.BOUND
        record.metadata["policy_number"] = policy_number
        self.store.save(record)
        return record
