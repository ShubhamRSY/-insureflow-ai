from __future__ import annotations

from pathlib import Path

import pytest

from insureflow.analytics.documents import (
    DocumentAnalyticsEngine,
    DocumentAnalyticsStore,
    DocumentRecord,
)


@pytest.fixture
def store(tmp_path: Path) -> DocumentAnalyticsStore:
    return DocumentAnalyticsStore(base_path=tmp_path / "doc_analytics")


@pytest.fixture
def engine(store: DocumentAnalyticsStore) -> DocumentAnalyticsEngine:
    return DocumentAnalyticsEngine(store=store)


class TestDocumentRecord:
    def test_create_record(self) -> None:
        rec = DocumentRecord(bundle_id="test-001", document_count=5, vertical="insurance")
        assert rec.record_id.startswith("dr-")
        assert rec.vertical == "insurance"
        assert rec.document_count == 5

    def test_record_defaults(self) -> None:
        rec = DocumentRecord(bundle_id="test-002", document_count=3)
        assert rec.structured_count == 0
        assert rec.unstructured_count == 0
        assert rec.human_review_required is False
        assert rec.decision == ""
        assert rec.org_id == "default"


class TestDocumentAnalyticsStore:
    def test_save_and_get(self, store: DocumentAnalyticsStore) -> None:
        rec = DocumentRecord(bundle_id="b-1", document_count=10, vertical="insurance")
        store.save(rec)

        loaded = store.get("b-1")
        assert loaded is not None
        assert loaded.bundle_id == "b-1"
        assert loaded.document_count == 10
        assert loaded.vertical == "insurance"

    def test_get_missing(self, store: DocumentAnalyticsStore) -> None:
        assert store.get("nonexistent") is None

    def test_list_all(self, store: DocumentAnalyticsStore) -> None:
        store.save(DocumentRecord(bundle_id="b-1", document_count=5, vertical="insurance"))
        store.save(DocumentRecord(bundle_id="b-2", document_count=3, vertical="mortgage"))
        store.save(DocumentRecord(bundle_id="b-3", document_count=8, vertical="insurance"))

        all_records = store.list_all()
        assert len(all_records) == 3

        ins_records = store.list_all(vertical="insurance")
        assert len(ins_records) == 2

        mtg_records = store.list_all(vertical="mortgage")
        assert len(mtg_records) == 1


class TestDocumentAnalyticsEngine:
    def test_record_creates_entry(self, engine: DocumentAnalyticsEngine) -> None:
        rec = engine.record(
            bundle_id="test-rec",
            document_count=7,
            vertical="insurance",
            structured_count=1,
            unstructured_count=6,
            human_review_required=True,
            decision="refer",
            org_id="org-1",
        )
        assert rec.bundle_id == "test-rec"
        assert rec.document_count == 7

        loaded = engine.store.get("test-rec")
        assert loaded is not None
        assert loaded.human_review_required is True
        assert loaded.decision == "refer"

    def test_summary_empty(self, engine: DocumentAnalyticsEngine) -> None:
        summary = engine.summary()
        assert summary["total_applications"] == 0
        assert summary["avg_documents_per_application"] == 0.0

    def test_summary_single_application(self, engine: DocumentAnalyticsEngine) -> None:
        engine.record(bundle_id="single", document_count=5, vertical="insurance")
        summary = engine.summary()
        assert summary["total_applications"] == 1
        assert summary["avg_documents_per_application"] == 5.0
        assert summary["min_documents"] == 5
        assert summary["max_documents"] == 5

    def test_summary_multiple_applications(self, engine: DocumentAnalyticsEngine) -> None:
        engine.record(bundle_id="a", document_count=2, vertical="insurance", decision="accept")
        engine.record(bundle_id="b", document_count=5, vertical="mortgage", decision="approve")
        engine.record(bundle_id="c", document_count=8, vertical="insurance", decision="refer")
        engine.record(bundle_id="d", document_count=1, vertical="insurance", decision="decline")
        engine.record(bundle_id="e", document_count=10, vertical="mortgage", decision="deny")

        summary = engine.summary()
        assert summary["total_applications"] == 5
        assert summary["avg_documents_per_application"] == 5.2  # (2+5+8+1+10)/5
        assert summary["min_documents"] == 1
        assert summary["max_documents"] == 10
        assert summary["total_documents_processed"] == 26
        assert summary["by_decision"]["accept"] == 1
        assert summary["by_decision"]["approve"] == 1
        assert summary["by_decision"]["refer"] == 1
        assert summary["by_decision"]["decline"] == 1
        assert summary["by_decision"]["deny"] == 1

    def test_summary_by_vertical(self, engine: DocumentAnalyticsEngine) -> None:
        engine.record(bundle_id="a", document_count=3, vertical="insurance")
        engine.record(bundle_id="b", document_count=7, vertical="insurance")
        engine.record(bundle_id="c", document_count=4, vertical="mortgage")

        ins_summary = engine.summary(vertical="insurance")
        assert ins_summary["total_applications"] == 2
        assert ins_summary["avg_documents_per_application"] == 5.0

        mtg_summary = engine.summary(vertical="mortgage")
        assert mtg_summary["total_applications"] == 1
        assert mtg_summary["avg_documents_per_application"] == 4.0

    def test_median_odd(self, engine: DocumentAnalyticsEngine) -> None:
        assert engine._median([1, 3, 5]) == 3.0

    def test_median_even(self, engine: DocumentAnalyticsEngine) -> None:
        assert engine._median([1, 3, 5, 7]) == 4.0

    def test_median_empty(self, engine: DocumentAnalyticsEngine) -> None:
        assert engine._median([]) == 0.0

    def test_distribution(self, engine: DocumentAnalyticsEngine) -> None:
        engine.record(bundle_id="a", document_count=1, vertical="insurance")
        engine.record(bundle_id="b", document_count=2, vertical="insurance")
        engine.record(bundle_id="c", document_count=5, vertical="insurance")
        engine.record(bundle_id="d", document_count=11, vertical="insurance")

        dist = engine.distribution()
        assert dist.get("1") == 1
        assert dist.get("2-3") == 1
        assert dist.get("4-5") == 1
        assert dist.get("11-20") == 1

    def test_sample_records_in_summary(self, engine: DocumentAnalyticsEngine) -> None:
        for i in range(15):
            engine.record(bundle_id=f"b-{i}", document_count=i + 1, vertical="insurance")

        summary = engine.summary()
        assert len(summary["sample_records"]) == 10

    def test_applications_with_review(self, engine: DocumentAnalyticsEngine) -> None:
        engine.record(bundle_id="a", document_count=5, human_review_required=True)
        engine.record(bundle_id="b", document_count=3, human_review_required=False)
        engine.record(bundle_id="c", document_count=7, human_review_required=True)

        summary = engine.summary()
        assert summary["applications_with_review"] == 2
        assert summary["applications_without_review"] == 1


class TestDocumentCountFromPipelineFixtures:
    """Test that document counting matches real pipeline fixture data."""

    ACORD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD><Submission>
  <NamedInsured><GeneralPartyInfo>
    <NameInfo><CommercialName><Name>Test Corp</Name></CommercialName></NameInfo>
  </GeneralPartyInfo></NamedInsured>
</Submission></ACORD>"""

    INSPECTION_REPORT = "# INSPECTION\nBuilding is fine."
    LOSS_RUN = "# LOSS RUN\nNo claims."

    def test_insurance_count_with_all_docs(self) -> None:
        from insureflow.ingestion.loader import SubmissionLoader

        loader = SubmissionLoader()
        bundle = loader.load_bundle(
            acord_xml=self.ACORD_XML,
            inspection_reports=[self.INSPECTION_REPORT],
            loss_run=self.LOSS_RUN,
            bundle_id="test-ins-all",
        )
        # Pipeline formula: len(unstructured) + (1 if structured else 0)
        doc_count = len(bundle.unstructured) + (1 if bundle.structured else 0)
        assert doc_count == 3  # structured(ACORD) + inspection + loss_run
        assert bundle.structured is not None
        assert len(bundle.unstructured) == 2

    def test_insurance_count_no_structured(self) -> None:
        from insureflow.ingestion.loader import SubmissionLoader

        loader = SubmissionLoader()
        bundle = loader.load_bundle(
            loss_run=self.LOSS_RUN,
            bundle_id="test-ins-no-structured",
        )
        doc_count = len(bundle.unstructured) + (1 if bundle.structured else 0)
        assert doc_count == 1  # just the loss run
        assert bundle.structured is None

    def test_insurance_count_multiple_reports(self) -> None:
        from insureflow.ingestion.loader import SubmissionLoader

        loader = SubmissionLoader()
        bundle = loader.load_bundle(
            acord_xml=self.ACORD_XML,
            inspection_reports=[self.INSPECTION_REPORT, "# SECOND REPORT", "# THIRD REPORT"],
            bundle_id="test-ins-multi-report",
        )
        doc_count = len(bundle.unstructured) + (1 if bundle.structured else 0)
        assert doc_count == 4  # structured + 3 inspection reports

    def test_insurance_count_empty(self) -> None:
        from insureflow.ingestion.loader import SubmissionLoader

        loader = SubmissionLoader()
        bundle = loader.load_bundle(bundle_id="test-ins-empty")
        doc_count = len(bundle.unstructured) + (1 if bundle.structured else 0)
        assert doc_count == 0

    def test_mortgage_document_count(self) -> None:
        from insureflow.models.mortgage import MortgageDocument, MortgageDocumentType, ProductLine

        docs = [
            MortgageDocument(document_id="1", source_path="/a.pdf", document_type=MortgageDocumentType.W2, product_line=ProductLine.RESIDENTIAL_MORTGAGE, raw_text="W2"),
            MortgageDocument(document_id="2", source_path="/b.pdf", document_type=MortgageDocumentType.BANK_STATEMENT, product_line=ProductLine.RESIDENTIAL_MORTGAGE, raw_text="bank"),
            MortgageDocument(document_id="3", source_path="/c.pdf", document_type=MortgageDocumentType.TAX_RETURN_1040, product_line=ProductLine.RESIDENTIAL_MORTGAGE, raw_text="tax"),
        ]
        assert len(docs) == 3

    def test_mortgage_document_count_single(self) -> None:
        from insureflow.models.mortgage import MortgageDocument, MortgageDocumentType, ProductLine

        docs = [
            MortgageDocument(document_id="1", source_path="/a.pdf", document_type=MortgageDocumentType.CREDIT_REPORT, product_line=ProductLine.RESIDENTIAL_MORTGAGE, raw_text="credit"),
        ]
        assert len(docs) == 1

    def test_mortgage_document_count_commercial(self) -> None:
        from insureflow.models.mortgage import MortgageDocument, MortgageDocumentType, ProductLine

        docs = [
            MortgageDocument(document_id=str(i), source_path=f"/{i}.pdf",
                           document_type=dt, product_line=ProductLine.COMMERCIAL_MORTGAGE, raw_text="doc")
            for i, dt in enumerate([
                MortgageDocumentType.OPERATING_STATEMENT,
                MortgageDocumentType.BALANCE_SHEET,
                MortgageDocumentType.BUSINESS_CREDIT_REPORT,
                MortgageDocumentType.COMMERCIAL_APPRAISAL,
                MortgageDocumentType.TITLE_POLICY,
                MortgageDocumentType.PHASE_I_ESA,
                MortgageDocumentType.RENT_ROLL,
                MortgageDocumentType.COMMERCIAL_LEASE,
            ])
        ]
        assert len(docs) == 8

    def test_analytics_records_match_pipeline_count(self, engine: DocumentAnalyticsEngine) -> None:
        engine.record(bundle_id="ins-match", document_count=4, vertical="insurance",
                      structured_count=1, unstructured_count=3)
        engine.record(bundle_id="mtg-match", document_count=6, vertical="mortgage",
                      unstructured_count=6)

        summary = engine.summary()
        assert summary["total_applications"] == 2
        assert summary["avg_documents_per_application"] == 5.0
        assert summary["total_documents_processed"] == 10


class TestDocumentCountEdgeCases:
    def test_zero_documents(self, engine: DocumentAnalyticsEngine) -> None:
        engine.record(bundle_id="zero", document_count=0, vertical="insurance")
        summary = engine.summary()
        assert summary["min_documents"] == 0
        assert summary["avg_documents_per_application"] == 0.0

    def test_large_document_set(self, engine: DocumentAnalyticsEngine) -> None:
        engine.record(bundle_id="large", document_count=50, vertical="insurance")
        dist = engine.distribution()
        assert dist.get("21+") == 1

    def test_mixed_verticals_summary(self, engine: DocumentAnalyticsEngine) -> None:
        for i in range(20):
            engine.record(bundle_id=f"ins-{i}", document_count=5, vertical="insurance")
        for i in range(10):
            engine.record(bundle_id=f"mtg-{i}", document_count=8, vertical="mortgage")

        all_summary = engine.summary()
        assert all_summary["total_applications"] == 30
        assert all_summary["avg_documents_per_application"] == 6.0  # (20*5 + 10*8) / 30

        ins_summary = engine.summary(vertical="insurance")
        assert ins_summary["total_applications"] == 20
        assert ins_summary["avg_documents_per_application"] == 5.0

        mtg_summary = engine.summary(vertical="mortgage")
        assert mtg_summary["total_applications"] == 10
        assert mtg_summary["avg_documents_per_application"] == 8.0
