from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.audit.insurance_audit import InsuranceAuditLogger
from insureflow.audit.package import RegulatoryPackageBuilder
from insureflow.audit.store import AuditStore
from insureflow.auth import Role
from insureflow.auth.dependencies import _USER_STORE
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.ingestion.insurance.classifier import InsuranceDocumentClassifier, InsuranceDocumentType
from insureflow.ingestion.insurance.extractors import extract_broker_slip
from insureflow.insurance.pipeline import InsurancePipeline
from insureflow.models.agents import UnderwritingMemo, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.outcomes.feedback import FeedbackEngine
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.storage.encryption import EnvelopeEncryption
from insureflow.workflow.models import SignOffAction, WorkflowState
from insureflow.workflow.service import WorkflowService

SIM = Path(__file__).resolve().parent.parent / "simulated_documents"
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class TestInsuranceOCR:
    def test_classify_broker_slip(self) -> None:
        text = "UNDERWRITING SUBMISSION\nNamed Insured: Pacific Coast Distributors\nTIV: $4,350,000"
        assert InsuranceDocumentClassifier.classify(text, "broker_slip.pdf") == InsuranceDocumentType.BROKER_SLIP

    def test_extract_broker_slip_fields(self) -> None:
        text = "Named Insured: Pacific Coast Distributors, Inc.\nTIV: $4,350,000\nNAICS: 493120"
        fields = extract_broker_slip(text)
        assert "named_insured" in fields
        assert "493120" in fields["naics_code"][0].value


class TestInsuranceRating:
    def test_quote_from_bundle(self) -> None:
        bundle = SubmissionBundle(bundle_id="rate-test")
        memo = UnderwritingMemo(bundle_id="rate-test", decision=UWDecision.ACCEPT, insured_name="Test Co")
        quote = InsuranceRatingEngine().quote(bundle, memo)
        assert quote.adjusted_premium > 0
        assert quote.policy_admin_reference.startswith("PA-")


class TestWorkflowSignOff:
    def test_sign_off_flow(self, tmp_path: Path) -> None:
        from insureflow.workflow.store import WorkflowStore

        store = WorkflowStore(base_path=tmp_path / "workflows")
        svc = WorkflowService(store=store)
        svc.submit_for_review("bundle-1", "test-org", "refer")
        record = svc.sign_off(
            "bundle-1", "test-org", SignOffAction.APPROVE,
            signed_by="jane.uw", license_number="UW-CA-12345",
        )
        assert record.state == WorkflowState.APPROVED
        assert record.sign_offs[0].license_number == "UW-CA-12345"


class TestFeedbackLoop:
    def test_calibration_after_loss_experience(self, tmp_path: Path) -> None:
        from insureflow.outcomes.store import OutcomeStore

        store = OutcomeStore(base_path=tmp_path / "outcomes")
        fb = FeedbackEngine(store=store)
        fb.record_loss_experience("POL-001", "test-org", 2024, 100_000, 25_000, 20_000, 2)
        summary = fb.calibration_summary("test-org")
        assert summary["sample_size"] == 1
        assert summary["avg_loss_ratio"] == 0.25


class TestRegulatoryAudit:
    def test_encrypted_audit_and_package(self, tmp_path: Path) -> None:
        key = EnvelopeEncryption.generate_key()
        enc = EnvelopeEncryption(key)
        audit_store = AuditStore(base_path=tmp_path / "audit")
        logger = InsuranceAuditLogger(audit_store, enc, org_id="test-org")

        bundle = SubmissionBundle(bundle_id="audit-test")
        memo = UnderwritingMemo(bundle_id="audit-test", decision=UWDecision.REFER, insured_name="Audit Co")
        logger.start("audit-test")
        paths = logger.persist(bundle, memo, extra={"status": "completed"})
        assert paths["underwriting_memo"]

        pkg = RegulatoryPackageBuilder(audit_store, enc).build("audit-test", org_id="test-org")
        assert pkg["artifact_count"] >= 2
        assert Path(pkg["package_path"]).exists()


class TestInsurancePipelineIntegration:
    @pytest.fixture
    def audit_store(self, tmp_path: Path) -> AuditStore:
        return AuditStore(base_path=tmp_path / "audit")

    def test_pipeline_produces_memo_and_workflow(self, audit_store: AuditStore) -> None:
        acord_path = EXAMPLES / "pacific_coast_acord.xml"
        inspection = EXAMPLES / "pacific_coast_inspection_report.md"
        if not acord_path.exists() or not inspection.exists():
            pytest.skip("Pacific Coast examples not present")

        acord = acord_path.read_text()

        result = InsurancePipeline(org_id="test", use_llm=False, audit_store=audit_store).run(
            acord_xml=acord,
            inspection_reports=[inspection.read_text()],
            bundle_id="integration-test",
        )
        assert result["status"] == "completed"
        assert result["ai_decision"] in ("accept", "refer", "decline")
        assert result["workflow_state"] == "pending_review"
        assert "quote" in result
        assert result["audit_trail_entries"] >= 1


class TestInsuranceAPIProduction:
    @pytest.fixture(autouse=True)
    def reset_users(self) -> None:
        _USER_STORE.clear()

    def _headers(self, role: Role = Role.LICENSED_UW, org_id: str = "acme") -> dict[str, str]:
        _USER_STORE["uw"] = User(username="uw", hashed_password="x", role=role, org_id=org_id)
        token = create_access_token({"sub": "uw", "role": role.value, "org_id": org_id})
        return {"Authorization": f"Bearer {token}"}

    def test_rating_products_endpoint(self) -> None:
        client = TestClient(app)
        resp = client.get("/pipeline/rating/products", headers=self._headers(Role.VIEWER))
        assert resp.status_code == 200
        assert len(resp.json()["lines"]) >= 4
