from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.ingestion.mortgage.classifier import MortgageDocumentClassifier
from insureflow.ingestion.mortgage.loader import MortgageSubmissionLoader
from insureflow.models.mortgage import MortgageDocumentType, ProductLine
from insureflow.mortgage.audit import MortgageAuditLogger
from insureflow.mortgage.bundler import discover_borrower_packages
from insureflow.mortgage.llm_extractor import MortgageLLMExtractor
from insureflow.mortgage.pipeline import MortgagePipeline
from insureflow.audit.store import AuditStore

SIM = Path(__file__).resolve().parent.parent / "simulated_documents"
HOME = SIM / "home_mortgage"
COMMERCIAL = SIM / "commercial_mortgage"


@pytest.fixture
def loader() -> MortgageSubmissionLoader:
    return MortgageSubmissionLoader(use_llm=False)


@pytest.fixture
def audit_store(tmp_path: Path) -> AuditStore:
    return AuditStore(base_path=tmp_path / "audit_logs")


class TestMortgageClassifier:
    def test_classify_w2_by_filename(self) -> None:
        path = str(HOME / "income" / "w2_2024_john_thompson.txt")
        content = Path(path).read_text()
        assert MortgageDocumentClassifier.classify(content, path) == MortgageDocumentType.W2

    def test_classify_credit_report(self) -> None:
        path = str(HOME / "credit_debt" / "credit_report_john_thompson.txt")
        content = Path(path).read_text()
        assert MortgageDocumentClassifier.classify(content, path) == MortgageDocumentType.CREDIT_REPORT

    def test_classify_commercial_rent_roll(self) -> None:
        path = str(COMMERCIAL / "property_performance" / "current_rent_roll.txt")
        content = Path(path).read_text()
        assert MortgageDocumentClassifier.classify(content, path) == MortgageDocumentType.RENT_ROLL

    def test_infer_product_line(self) -> None:
        assert MortgageDocumentClassifier.infer_product_line(str(HOME)) == ProductLine.RESIDENTIAL_MORTGAGE
        assert MortgageDocumentClassifier.infer_product_line(str(COMMERCIAL)) == ProductLine.COMMERCIAL_MORTGAGE


class TestMortgageBundler:
    def test_discovers_per_borrower_packages(self) -> None:
        packages = discover_borrower_packages(str(HOME))
        ids = {p.borrower_id for p in packages}
        assert "chen_david_karen" in ids
        assert "rodriguez_maria" in ids
        assert "johnson_marcus_imani" in ids
        assert "thompson_john_sarah" in ids

    def test_borrower_packages_have_documents(self) -> None:
        packages = discover_borrower_packages(str(HOME))
        chen = next(p for p in packages if p.borrower_id == "chen_david_karen")
        assert chen.document_count >= 5

    def test_commercial_borrower_packages(self) -> None:
        packages = discover_borrower_packages(str(COMMERCIAL))
        ids = {p.borrower_id for p in packages}
        assert "midwest_medical_plaza" in ids or "thompson_commercial_properties" in ids


class TestMortgageLLMExtractor:
    def test_needs_llm_for_messy_document(self) -> None:
        extractor = MortgageLLMExtractor()
        text = "Some doc\n[HANDWRITTEN NOTE] corrected value $50,000"
        assert extractor.needs_llm(MortgageDocumentType.UNKNOWN, {}, text)

    def test_needs_llm_for_sparse_extraction(self) -> None:
        extractor = MortgageLLMExtractor()
        assert extractor.needs_llm(MortgageDocumentType.W2, {"employee_name": []}, "plain text")

    def test_merge_fields_combines_llm_and_regex(self) -> None:
        from insureflow.models.mortgage import ExtractedMortgageField
        from insureflow.mortgage.llm_extractor import LLMExtractionResult, LLMExtractedField

        extractor = MortgageLLMExtractor()
        regex = {"wages_box1": [ExtractedMortgageField(field_name="wages_box1", value="100000", confidence=0.9)]}
        llm = LLMExtractionResult(
            fields=[LLMExtractedField(field_name="credit_score", value="720", confidence=0.85)],
            borrower_name="John Smith",
        )
        merged = extractor.merge_fields(regex, llm)
        assert merged["wages_box1"][0].value == "100000"
        assert merged["credit_score"][0].value == "720"
        assert merged["borrower_name"][0].value == "John Smith"


class TestMortgageAudit:
    def test_audit_persist_writes_files(self, audit_store: AuditStore) -> None:
        from insureflow.agents.mortgage.supervisor import MortgageSupervisorAgent
        from insureflow.models.mortgage import MortgageBundle, MortgageBundleStatus

        paths = [
            str(HOME / "income" / "w2_2024_john_thompson.txt"),
            str(HOME / "credit_debt" / "credit_report_john_thompson.txt"),
        ]
        loader = MortgageSubmissionLoader(use_llm=False)
        docs = loader.load_from_paths(paths, bundle_id="audit-test")
        bundle = MortgageBundle(
            bundle_id="audit-test",
            product_line=ProductLine.RESIDENTIAL_MORTGAGE,
            documents=docs,
            status=MortgageBundleStatus.PARSED,
        )
        pipeline = MortgagePipeline(use_llm=False, audit_store=audit_store)
        pipeline.reconciliation.build_summaries(bundle)
        pipeline.reconciliation.reconcile(bundle)
        pipeline.compliance.evaluate(bundle)
        memo = MortgageSupervisorAgent().analyze(bundle)

        logger = MortgageAuditLogger(audit_store)
        logger.start("audit-test")
        paths_written = logger.persist(bundle, memo, extra={"test": True})

        assert Path(paths_written["audit_trail"]).exists()
        assert Path(paths_written["memo"]).exists()
        assert Path(paths_written["bundle"]).exists()
        trail = audit_store.load_json("audit-test", "audit_trail.json")
        assert trail is not None
        assert len(trail["entries"]) >= 1


class TestMortgageExtractors:
    def test_w2_extracts_wages(self, loader: MortgageSubmissionLoader) -> None:
        path = str(HOME / "income" / "w2_2024_john_thompson.txt")
        doc = loader.load_from_paths([path])[0]
        assert doc.document_type == MortgageDocumentType.W2
        wages = doc.get_float("wages_box1")
        assert wages == 112500.0
        assert "John" in doc.get_field("employee_name")

    def test_credit_report_extracts_score(self, loader: MortgageSubmissionLoader) -> None:
        path = str(HOME / "credit_debt" / "credit_report_john_thompson.txt")
        doc = loader.load_from_paths([path])[0]
        assert doc.get_float("credit_score") == 762

    def test_tax_return_extracts_agi(self, loader: MortgageSubmissionLoader) -> None:
        path = str(HOME / "income" / "federal_tax_return_2024_joint.txt")
        doc = loader.load_from_paths([path])[0]
        assert doc.document_type == MortgageDocumentType.TAX_RETURN_1040
        assert doc.get_float("adjusted_gross_income") > 0

    def test_bank_statement_extracts_balance(self, loader: MortgageSubmissionLoader) -> None:
        path = str(HOME / "assets" / "bank_statement_checking_april_2026.txt")
        doc = loader.load_from_paths([path])[0]
        assert doc.get_float("ending_balance") > 0


class TestMortgagePipeline:
    def test_home_mortgage_core_package(self, audit_store: AuditStore) -> None:
        paths = [
            str(HOME / "income" / "w2_2024_john_thompson.txt"),
            str(HOME / "income" / "federal_tax_return_2024_joint.txt"),
            str(HOME / "credit_debt" / "credit_report_john_thompson.txt"),
            str(HOME / "assets" / "bank_statement_checking_april_2026.txt"),
            str(HOME / "property" / "home_appraisal_report.txt"),
            str(HOME / "property" / "signed_purchase_agreement.txt"),
        ]
        results = MortgagePipeline(use_llm=False, audit_store=audit_store).run_from_paths(
            paths, bundle_id="test-home-core"
        )
        assert results["status"] == "completed"
        assert results["document_count"] == 6
        assert results["borrower"]
        assert results["decision"] in ("approve", "refer", "suspend", "deny")
        assert results["audit_trail_entries"] >= 1
        assert "audit_paths" in results

    def test_per_borrower_processing(self, audit_store: AuditStore) -> None:
        results = MortgagePipeline(use_llm=False, audit_store=audit_store).run_per_borrower(str(HOME))
        assert results["status"] == "completed"
        assert results["borrower_count"] >= 5
        for pkg in results["packages"]:
            assert pkg["document_count"] >= 1
            assert pkg["borrower_id"]
            assert pkg["decision"] in ("approve", "refer", "suspend", "deny")

    def test_commercial_mortgage_directory(self, audit_store: AuditStore) -> None:
        if not COMMERCIAL.exists():
            pytest.skip("commercial mortgage fixtures not present")
        results = MortgagePipeline(use_llm=False, audit_store=audit_store).run_from_directory(
            str(COMMERCIAL), bundle_id="test-commercial"
        )
        assert results["status"] == "completed"
        assert results["document_count"] >= 20
        assert results["product_line"] == "commercial_mortgage"

    def test_compliance_rules_fire(self, audit_store: AuditStore) -> None:
        paths = [str(HOME / "credit_debt" / "credit_report_john_thompson.txt")]
        results = MortgagePipeline(use_llm=False, audit_store=audit_store).run_from_paths(
            paths, bundle_id="test-compliance"
        )
        violations = results.get("compliance_violations", [])
        rule_ids = {v["rule_id"] for v in violations}
        assert "INCOME-001" in rule_ids

    def test_api_text_submission(self, audit_store: AuditStore, monkeypatch: pytest.MonkeyPatch) -> None:
        w2 = (HOME / "income" / "w2_2024_john_thompson.txt").read_text()
        credit = (HOME / "credit_debt" / "credit_report_john_thompson.txt").read_text()
        result = MortgagePipeline(use_llm=False, audit_store=audit_store).run_from_texts(
            [
                {"filename": "w2_2024_john_thompson.txt", "content": w2},
                {"filename": "credit_report_john_thompson.txt", "content": credit},
            ],
            bundle_id="api-text-test",
            borrower_id="thompson_john_sarah",
        )
        assert result["status"] == "completed"
        assert result["borrower_id"] == "thompson_john_sarah"


class TestMortgageAPI:
    def test_mortgage_health_and_jobs_require_auth(self) -> None:
        client = TestClient(app)
        assert client.get("/health").status_code == 200
        assert client.get("/mortgage/pipeline/jobs").status_code == 401
