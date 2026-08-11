from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.audit.insurance_audit import InsuranceAuditLogger
from insureflow.audit.package import RegulatoryPackageBuilder
from insureflow.audit.store import AuditStore
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import clear_user_store, get_user_store
from insureflow.ingestion.insurance.classifier import InsuranceDocumentClassifier, InsuranceDocumentType
from insureflow.ingestion.insurance.extractors import extract_broker_slip
from insureflow.insurance.pipeline import InsurancePipeline
from insureflow.models.agents import AgentResult, AgentType, Finding, Recommendation, RiskSeverity, UnderwritingMemo, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.outcomes.feedback import FeedbackEngine
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.rating.models import InsuranceLine
from insureflow.storage.encryption import EnvelopeEncryption
from insureflow.workflow.models import SignOffAction, WorkflowState
from insureflow.workflow.service import WorkflowService

SIM = Path(__file__).resolve().parent.parent / "simulated_documents"
EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "insurance"


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
        from insureflow.models.submissions import CoverageDetail, LocationData, NamedInsured, StructuredSubmission

        bundle = SubmissionBundle(
            bundle_id="rate-test",
            structured=StructuredSubmission(
                submission_id="rate-test",
                named_insured=NamedInsured(legal_name="Test Co"),
                locations=[
                    LocationData(
                        address="1 Main",
                        city="Austin",
                        state="TX",
                        zip_code="78701",
                        building_value=2_500_000,
                        contents_value=500_000,
                    )
                ],
                coverages=[CoverageDetail(coverage_type="Property", limit_amount=3_000_000, deductible=10_000, premium=0)],
            ),
        )
        memo = UnderwritingMemo(bundle_id="rate-test", decision=UWDecision.ACCEPT, insured_name="Test Co")
        quote = InsuranceRatingEngine().quote(bundle, memo)
        assert quote.adjusted_premium > 0
        assert quote.eligible is True
        assert quote.policy_admin_reference.startswith(("PA-", "ISO-"))

    def test_quote_without_tiv_is_ineligible(self) -> None:
        bundle = SubmissionBundle(bundle_id="rate-empty")
        memo = UnderwritingMemo(bundle_id="rate-empty", decision=UWDecision.ACCEPT, insured_name="Empty Co")
        quote = InsuranceRatingEngine().quote(bundle, memo)
        assert quote.adjusted_premium == 0
        assert quote.eligible is False
        assert "TIV could not be determined" in quote.ineligibility_reasons

    def test_substandard_loading_raises_premium(self) -> None:
        from insureflow.models.submissions import CoverageDetail, LocationData, NamedInsured, StructuredSubmission

        bundle = SubmissionBundle(
            bundle_id="rate-loading-test",
            structured=StructuredSubmission(
                submission_id="rate-loading-test",
                named_insured=NamedInsured(legal_name="Test Co"),
                locations=[
                    LocationData(
                        address="1 Main",
                        city="Austin",
                        state="TX",
                        zip_code="78701",
                        building_value=2_500_000,
                        contents_value=500_000,
                    )
                ],
                coverages=[CoverageDetail(coverage_type="Property", limit_amount=3_000_000, deductible=10_000, premium=0)],
            ),
        )
        engine = InsuranceRatingEngine()
        base_memo = UnderwritingMemo(bundle_id="rate-loading-test", decision=UWDecision.ACCEPT, insured_name="Test Co")
        base = engine.quote(bundle, base_memo)
        loaded_memo = UnderwritingMemo(
            bundle_id="rate-loading-test",
            decision=UWDecision.CONDITIONAL_ACCEPT,
            insured_name="Test Co",
            recommendation=Recommendation(
                action="conditional_accept",
                rationale="Substandard class rate loading",
                suggested_premium_modification=25.0,
            ),
        )
        loaded = engine.quote(bundle, loaded_memo)
        assert loaded.adjusted_premium > base.adjusted_premium
        assert loaded.adjusted_premium / base.adjusted_premium > 1.20
        assert any(c.name == "uw_schedule_modification" and c.modifier_pct == 25.0 for c in loaded.schedule_modifications)


class TestWorkflowSignOff:
    def test_sign_off_flow(self, tmp_path: Path) -> None:
        from insureflow.workflow.store import WorkflowStore

        store = WorkflowStore(base_path=tmp_path / "workflows")
        svc = WorkflowService(store=store)
        svc.submit_for_review("bundle-1", "test-org", "refer")
        record = svc.sign_off(
            "bundle-1",
            "test-org",
            SignOffAction.APPROVE,
            signed_by="jane.uw",
            license_number="UW-CA-12345",
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
        assert result["ai_decision"] in ("accept", "conditional_accept", "refer", "decline")
        assert "human_checkpoints" in result
        assert "open_conditions" in result
        assert result["workflow_state"] == "pending_review"
        assert "quote" in result
        assert result["audit_trail_entries"] >= 1
        # Selection standards / book-balance runs on commercial lines.
        selection = result.get("selection_standards") or {}
        assert selection.get("agent_type") == "selection_standards"
        assert selection.get("findings")
        # Experience-rating feedback loop surfaces in the summary even when the
        # store has no reported losses yet (inert, status "unknown").
        assert result.get("selection_experience", {}).get("status") in ("unknown", "better", "expected", "worse")
        # Producer-experience (financial function) runs alongside selection.
        producer = result.get("producer_experience") or {}
        assert producer.get("agent_type") == "producer_experience"
        # Adverse-selection (purpose of underwriting) screen runs alongside selection.
        adverse = result.get("adverse_selection") or {}
        assert adverse.get("agent_type") == "adverse_selection"
        # Moral-hazard / character screen (judge of people doctrine) runs on every line.
        moral = result.get("moral_hazard") or {}
        assert moral.get("agent_type") == "moral_hazard"

    def test_critical_moral_hazard_forces_decline(self, audit_store: AuditStore, monkeypatch: pytest.MonkeyPatch) -> None:
        """If the applicant's morals are open to question, decline regardless of everything else."""
        acord_path = EXAMPLES / "pacific_coast_acord.xml"
        inspection = EXAMPLES / "pacific_coast_inspection_report.md"
        if not acord_path.exists() or not inspection.exists():
            pytest.skip("Pacific Coast examples not present")

        pipe = InsurancePipeline(org_id="test", use_llm=False, audit_store=audit_store)
        critical = AgentResult(
            agent_type=AgentType.MORAL_HAZARD,
            agent_name="MoralHazardAgent",
            risk_score=1.0,
            risk_severity=RiskSeverity.CRITICAL,
            findings=[
                Finding(
                    title="Moral hazard: applicant's character is open to question — declination indicated",
                    description="intentional non-disclosure detected",
                    severity=RiskSeverity.CRITICAL,
                    category="moral_hazard",
                )
            ],
        )
        monkeypatch.setattr(pipe.moral_hazard, "run", lambda bundle, **kw: critical)

        result = pipe.run(
            acord_xml=acord_path.read_text(),
            inspection_reports=[inspection.read_text()],
            bundle_id="moral-decline-test",
        )
        assert result["status"] == "completed"
        assert result["ai_decision"] == "decline"
        assert result["moral_hazard"]["findings"][0]["severity"] == "critical"

    def test_funnel_deferral_and_deep_dive(self, audit_store: AuditStore) -> None:
        acord_path = EXAMPLES / "pacific_coast_acord.xml"
        inspection = EXAMPLES / "pacific_coast_inspection_report.md"
        if not acord_path.exists() or not inspection.exists():
            pytest.skip("Pacific Coast examples not present")

        acord = acord_path.read_text()
        pipe = InsurancePipeline(org_id="test", use_llm=False, audit_store=audit_store)

        result = pipe.run(
            acord_xml=acord,
            inspection_reports=[inspection.read_text()],
            bundle_id="funnel-test",
            funnel=True,
        )
        assert result["status"] == "completed"
        assert result.get("funnel") is True
        # Funnel defers the expensive analyses but keeps them discoverable.
        assert result["deep_dive_available"] == ["oracles", "portfolio", "selection_standards", "producer_experience", "adverse_selection", "moral_hazard", "reinsurance", "fraud_ml"]
        stage_status = {s["id"]: s["status"] for s in result["pipeline_stages"]}
        assert stage_status.get("verify") == "skipped"
        assert stage_status.get("portfolio") == "skipped"
        assert stage_status.get("reinsurance") == "skipped"
        assert result["ai_decision"] in ("accept", "conditional_accept", "refer", "decline")

        # Deep dive re-runs everything the funnel deferred — nothing is lost.
        dd = pipe.deep_dive("funnel-test", org_id="test")
        assert set(dd["completed"]) == {"oracles", "portfolio", "selection_standards", "producer_experience", "adverse_selection", "moral_hazard", "reinsurance", "fraud_ml", "premium_ml", "churn_ml"}
        for section in ("oracles", "portfolio", "selection_standards", "producer_experience", "adverse_selection", "moral_hazard", "reinsurance", "fraud_ml", "premium_ml", "churn_ml"):
            assert section in dd["findings"]

    def test_funnel_deep_dive_missing_bundle_raises(self, audit_store: AuditStore) -> None:
        pipe = InsurancePipeline(org_id="test", use_llm=False, audit_store=audit_store)
        with pytest.raises(KeyError):
            pipe.deep_dive("does-not-exist", org_id="test")


class TestInsuranceAPIProduction:
    @pytest.fixture(autouse=True)
    def reset_users(self) -> None:
        clear_user_store()

    def _headers(self, role: Role = Role.LICENSED_UW, org_id: str = "acme") -> dict[str, str]:
        get_user_store()["uw"] = User(username="uw", hashed_password="x", role=role, org_id=org_id)
        token = create_access_token({"sub": "uw", "role": role.value, "org_id": org_id})
        return {"Authorization": f"Bearer {token}"}

    def test_rating_products_endpoint(self) -> None:
        client = TestClient(app)
        resp = client.get("/pipeline/rating/products", headers=self._headers(Role.VIEWER))
        assert resp.status_code == 200
        assert len(resp.json()["lines"]) >= 4

    def test_ratemaking_endpoints(self) -> None:
        client = TestClient(app)
        headers = self._headers(Role.VIEWER)
        overview = client.get("/pipeline/rating/ratemaking", headers=headers)
        assert overview.status_code == 200
        data = overview.json()
        assert len(data["line_build_ups"]) == len(list(InsuranceLine))
        assert {"ISO", "AAIS", "NCCI"}.issubset(set(data["advisory_organizations"]))
        assert len(data["regulatory"]) == 3
        assert len(data["characteristics"]) == 5
        assert len(data["investment_income"]) == len(list(InsuranceLine))
        assert data["states_requiring_explicit_investment_income"]
        assert "projections" in data["expense_analysis"]
        assert "allocations" in data["expense_analysis"]

        run = client.post(
            "/pipeline/rating/ratemaking/run",
            headers=headers,
            json={"line": "workers_comp", "incurred_losses": 10_000_000, "exposure_units": 100_000},
        )
        assert run.status_code == 200
        study = run.json()
        assert study["pure_premium_result"]["base_rate"] == 100.0
        assert study["loss_ratio_result"]["rate_change_pct"] == round((0.60 * 1.03 * 1.05 / 0.65 - 1.0) * 100, 2)
        assert "NCCI" in study["advisory_orgs"]

    def test_demo_presets_cover_all_verticals(self) -> None:
        client = TestClient(app)
        presets = client.get("/api/demo/presets").json()
        assert {k for k in presets} == {"insurance", "mortgage", "lending"}
        assert len(presets["insurance"]) >= 5
        assert len(presets["mortgage"]) >= 3
        assert len(presets["lending"]) >= 2
        for preset in presets["mortgage"] + presets["lending"]:
            assert "directory" in preset

    def test_lending_demo_endpoint_runs_sample(self) -> None:
        client = TestClient(app)
        resp = client.post("/api/demo/lending/blue-harbor-bakery")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vertical"] == "lending"
        assert data["preset"] == "blue-harbor-bakery"
        assert data["decision"] in ("approved", "approved_with_conditions", "declined", "referred", "suspended")
        assert data["documents_ingested"] >= 5
        assert data["approved_amount"] > 0

    def test_lending_demo_unknown_preset_404(self) -> None:
        client = TestClient(app)
        assert client.post("/api/demo/lending/does-not-exist").status_code == 404

    def test_mortgage_demo_new_presets(self) -> None:
        client = TestClient(app)
        for preset_id in ("chen-residential", "oak-street-commercial"):
            resp = client.post(f"/api/demo/mortgage/{preset_id}")
            assert resp.status_code == 202, resp.text
            assert resp.json()["status"] == "processing"
