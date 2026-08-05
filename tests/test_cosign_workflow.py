"""Co-sign workflow — request, approve, enforce on bind."""

from __future__ import annotations

import pytest

from insureflow.underwriting.authority import AuthorityMatrix, AuthorityTier, AuthorityVerdict
from insureflow.underwriting.cosign import (
    CoSignStatus,
    cosign_allows_bind,
    create_cosign_request,
    resolve_cosign,
)
from insureflow.workflow.models import SignOffAction, WorkflowState
from insureflow.workflow.service import WorkflowService
from insureflow.workflow.store import WorkflowStore


@pytest.fixture()
def wf(tmp_path, monkeypatch) -> WorkflowService:
    store = WorkflowStore(base_path=tmp_path / "wf")
    return WorkflowService(store=store)


def _seed_approved(wf: WorkflowService, bundle_id: str = "b-cosign-1") -> str:
    wf.start(bundle_id, "default", ai_decision="accept")
    wf.submit_for_review(bundle_id, "default", ai_decision="accept")
    wf.sign_off(bundle_id, "default", SignOffAction.APPROVE, signed_by="sfields", license_number="UW-1")
    return bundle_id


class TestCoSignWorkflow:
    def test_request_moves_to_pending_co_sign(self, wf: WorkflowService) -> None:
        bid = _seed_approved(wf)
        record = wf.request_cosign(
            bid, "default", requested_by="sfields", premium=200_000, tiv=8_000_000, reason="over threshold"
        )
        assert record.state == WorkflowState.PENDING_CO_SIGN
        assert record.metadata["co_sign"]["status"] == "pending"
        assert record.metadata["co_sign"]["required_tier"] == "cuo"

    def test_peer_cannot_cosign(self, wf: WorkflowService) -> None:
        bid = _seed_approved(wf)
        wf.request_cosign(bid, "default", requested_by="sfields", premium=200_000, tiv=8_000_000)
        with pytest.raises(ValueError, match="below required|different"):
            # Another senior cannot clear a senior's co-sign (needs CUO)
            juniors = AuthorityMatrix().list_by_tier(AuthorityTier.JUNIOR)
            assert juniors
            wf.resolve_cosign_request(
                bid, "default", signer_username=juniors[0].username, approve=True
            )

    def test_cuo_approve_then_bind(self, wf: WorkflowService) -> None:
        bid = _seed_approved(wf)
        wf.request_cosign(bid, "default", requested_by="sfields", premium=200_000, tiv=8_000_000)
        cuos = AuthorityMatrix().list_by_tier(AuthorityTier.CUO)
        assert cuos
        record = wf.resolve_cosign_request(
            bid, "default", signer_username=cuos[0].username, approve=True, notes="ok"
        )
        assert record.state == WorkflowState.APPROVED
        assert record.metadata["co_sign"]["status"] == "approved"
        ok, reason = cosign_allows_bind(record.metadata, binder_username="sfields")
        assert ok is True
        bound = wf.mark_bound(bid, "default", "POL-1", binder_username="sfields")
        assert bound.state == WorkflowState.BOUND

    def test_binder_cannot_be_cosigner(self, wf: WorkflowService) -> None:
        bid = _seed_approved(wf)
        wf.request_cosign(bid, "default", requested_by="sfields", premium=200_000, tiv=8_000_000)
        cuos = AuthorityMatrix().list_by_tier(AuthorityTier.CUO)
        assert cuos
        cuo = cuos[0].username
        wf.resolve_cosign_request(bid, "default", signer_username=cuo, approve=True)
        with pytest.raises(ValueError, match="same person"):
            wf.mark_bound(bid, "default", "POL-2", binder_username=cuo)

    def test_pending_blocks_bind(self, wf: WorkflowService) -> None:
        bid = _seed_approved(wf)
        wf.request_cosign(bid, "default", requested_by="sfields", premium=200_000, tiv=8_000_000)
        with pytest.raises(ValueError, match="Co-sign|PENDING_CO_SIGN|only be bound"):
            wf.mark_bound(bid, "default", "POL-3", binder_username="sfields")


class TestCoSignUnit:
    def test_create_and_resolve(self) -> None:
        req = create_cosign_request(
            bundle_id="b1",
            org_id="default",
            requested_by="sfields",
            premium=200_000,
            tiv=8_000_000,
        )
        assert req.status == CoSignStatus.PENDING
        cuos = AuthorityMatrix().list_by_tier(AuthorityTier.CUO)
        assert cuos
        done = resolve_cosign(req, signer_username=cuos[0].username, approve=True)
        assert done.status == CoSignStatus.APPROVED

    def test_evaluate_verdicts(self) -> None:
        matrix = AuthorityMatrix()
        v, _ = matrix.evaluate_binding_authority(username="sfields", premium=100_000, tiv=5_000_000)
        assert v == AuthorityVerdict.APPROVED
        v, _ = matrix.evaluate_binding_authority(username="sfields", premium=200_000, tiv=8_000_000)
        assert v == AuthorityVerdict.NEEDS_CO_SIGN
