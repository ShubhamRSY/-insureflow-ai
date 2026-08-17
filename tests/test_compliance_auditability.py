"""Tests for compliance/auditability — verbatim source attribution.

Covers:
  - VerbatimCitation model and ProvenanceNode citation propagation
  - provenance/citation.py — quote extraction
  - provenance/chain.py — statement-level provenance chain
  - verification/citation_verifier.py — citation accuracy verification
  - audit/retention.py — retention policy engine with legal holds
  - audit/examiner_export.py — DOI/NAIC examination export
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from insureflow.models.provenance import (
    DataSource,
    ProvenanceNode,
    ProvenanceRecord,
    SourceType,
    TrustLevel,
    VerbatimCitation,
    VerificationStatus,
)
from insureflow.models.submissions import (
    ExtractedField,
    SubmissionBundle,
    UnstructuredSubmission,
)

# ── Helper builders ───────────────────────────────────────────────────────────


def _make_citation(**overrides: Any) -> VerbatimCitation:
    return VerbatimCitation(
        document_id=overrides.get("document_id", "doc-1"),
        document_type=overrides.get("document_type", "inspection_report"),
        page_number=overrides.get("page_number", 2),
        bbox=overrides.get("bbox", [0.1, 0.2, 0.5, 0.35]),
        start_char=overrides.get("start_char", 100),
        end_char=overrides.get("end_char", 250),
        source_text=overrides.get("source_text", "The building was constructed in 1995 with steel_frame."),
        confidence=overrides.get("confidence", 0.92),
        extraction_method=overrides.get("extraction_method", "ocr"),
    )


def _make_node(**overrides: Any) -> ProvenanceNode:
    source = overrides.pop(
        "source",
        DataSource(
            source_id="src-1",
            source_type=SourceType.UNSTRUCTURED,
            source_name="inspection_report",
            received_at=datetime.now(tz=timezone.utc),
            trust_level=TrustLevel.MEDIUM,
        ),
    )
    citation = overrides.pop("citation", _make_citation())
    defaults = {
        "node_id": "node-1",
        "field_path": "risk_profile.construction_type",
        "value": "steel_frame",
        "source": source,
        "citation": citation,
        "confidence": 0.85,
        "verification_status": VerificationStatus.UNVERIFIED,
    }
    defaults.update(overrides)
    return ProvenanceNode(**defaults)


def _make_record(
    record_id: str = "rec-1",
    bundle_id: str = "bundle-1",
    nodes: dict[str, list[ProvenanceNode]] | None = None,
) -> ProvenanceRecord:
    if nodes is None:
        nodes = {"risk_profile.construction_type": [_make_node()]}
    return ProvenanceRecord(
        record_id=record_id,
        bundle_id=bundle_id,
        nodes=nodes,
    )


def _make_bundle() -> SubmissionBundle:
    ef = ExtractedField(
        field_name="construction_type",
        value="steel_frame",
        confidence=0.85,
        context="The building was constructed in 1995 with steel_frame.",
        page_number=2,
        bbox=[0.1, 0.2, 0.5, 0.35],
        source_ref="page 2, region 0.10,0.20..0.50,0.35",
    )
    unstructured = UnstructuredSubmission(
        submission_id="un-1",
        source="inspection_report",
        document_type="inspection_report",
        raw_text="This is an inspection report. The building was constructed in 1995 with steel_frame. It has 3 stories.",
        extracted_fields={"construction_type": [ef]},
    )
    return SubmissionBundle(
        bundle_id="bundle-1",
        unstructured=[unstructured],
    )


# ── VerbatimCitation model tests ─────────────────────────────────────────────


class TestVerbatimCitation:
    def test_default_values(self):
        cit = VerbatimCitation()
        assert cit.document_id == ""
        assert cit.page_number is None
        assert cit.bbox is None
        assert cit.source_text == ""

    def test_full_citation(self):
        cit = _make_citation()
        assert cit.page_number == 2
        assert cit.bbox == [0.1, 0.2, 0.5, 0.35]
        assert "steel_frame" in cit.source_text
        assert cit.start_char == 100
        assert cit.end_char == 250

    def test_citation_on_node(self):
        node = _make_node()
        assert node.citation is not None
        assert node.citation.source_text != ""

    def test_node_without_citation(self):
        node = _make_node(citation=None)
        assert node.citation is None


# ── ProvenanceEngine citation propagation ─────────────────────────────────────


class TestProvenanceEngineCitationPropagation:
    def test_unstructured_fields_carry_citations(self):
        from insureflow.provenance.hierarchy import ProvenanceEngine

        bundle = _make_bundle()
        engine = ProvenanceEngine(deduplicate=False)
        record = engine.build_provenance(bundle)

        node = record.nodes["risk_profile.construction_type"][0]
        assert node.citation is not None
        assert node.citation.document_id == "un-1"
        assert node.citation.page_number == 2
        assert node.citation.bbox == [0.1, 0.2, 0.5, 0.35]
        assert "steel_frame" in node.citation.source_text

    def test_mapped_fields_get_citations(self):
        from insureflow.provenance.hierarchy import ProvenanceEngine

        ef = ExtractedField(
            field_name="year_built",
            value="1995",
            confidence=0.9,
            context="Constructed in 1995.",
            page_number=1,
            bbox=[0.2, 0.1, 0.4, 0.15],
        )
        unstructured = UnstructuredSubmission(
            submission_id="un-2",
            source="inspection_report",
            extracted_fields={"year_built": [ef]},
        )
        bundle = SubmissionBundle(bundle_id="b-2", unstructured=[unstructured])
        engine = ProvenanceEngine(deduplicate=False)
        record = engine.build_provenance(bundle)

        node = record.nodes["extracted.year_built"][0]
        assert node.citation is not None
        assert node.citation.page_number == 1


# ── Quote extraction ─────────────────────────────────────────────────────────


class TestQuoteExtraction:
    def test_extract_source_quote_exact_match(self):
        from insureflow.provenance.citation import extract_source_quote

        raw = "The property is a 3-story building constructed in 1995."
        result = extract_source_quote(raw, "1995")
        assert "1995" in result.text
        assert result.confidence >= 0.9

    def test_extract_source_quote_partial_match(self):
        from insureflow.provenance.citation import extract_source_quote

        raw = "The PROPERTY is located at 123 Main St."
        result = extract_source_quote(raw, "property")
        assert result.text != "" or result.confidence < 1.0

    def test_extract_source_quote_not_found(self):
        from insureflow.provenance.citation import extract_source_quote

        result = extract_source_quote("No match here.", "xyz_missing")
        assert result.text == ""
        assert result.confidence == 0.0

    def test_sentence_window_expands_to_boundaries(self):
        from insureflow.provenance.citation import _sentence_window

        text = "First sentence. The value is 42. Final sentence here."
        result = _sentence_window(text, "42", window_chars=5)
        assert "42" in result

    def test_quote_for_field(self):
        from insureflow.provenance.citation import quote_for_field

        result = quote_for_field(
            "construction_type",
            "steel_frame",
            "The building uses a steel_frame structure.",
            page_number=3,
            bbox=[0.1, 0.2, 0.3, 0.4],
        )
        assert "steel_frame" in result.text
        assert result.page_number == 3

    def test_quote_for_field_empty_value(self):
        from insureflow.provenance.citation import quote_for_field

        result = quote_for_field("field", "", "Some text.")
        assert result.text == ""

    def test_quote_for_field_empty_text(self):
        from insureflow.provenance.citation import quote_for_field

        result = quote_for_field("field", "value", "")
        assert result.text == ""


# ── Citation enrichment ──────────────────────────────────────────────────────


class TestCitationEnrichment:
    def test_enrich_fills_missing_source_text(self):
        from insureflow.provenance.citation import enrich_citations

        node = _make_node(citation=_make_citation(source_text=""))
        record = _make_record(nodes={"risk_profile.construction_type": [node]})
        raw_map = {"src-1": "The building uses a steel_frame structure."}

        enriched = enrich_citations(record, raw_map)
        n = enriched.nodes["risk_profile.construction_type"][0]
        assert n.citation is not None
        assert "steel_frame" in n.citation.source_text

    def test_enrich_skips_already_populated(self):
        from insureflow.provenance.citation import enrich_citations

        node = _make_node()
        assert node.citation is not None
        original_text = node.citation.source_text
        record = _make_record(nodes={"risk_profile.construction_type": [node]})

        enriched = enrich_citations(record, {"src-1": "Different text entirely."})
        n = enriched.nodes["risk_profile.construction_type"][0]
        assert n.citation is not None
        assert n.citation.source_text == original_text


# ── Statement provenance chain ───────────────────────────────────────────────


class TestStatementProvenanceChain:
    def test_build_chain(self):
        from insureflow.provenance.chain import StatementProvenanceChain

        record = _make_record()
        chain = StatementProvenanceChain()
        result = chain.build_chain(record)

        assert "risk_profile.construction_type" in result
        citations = result["risk_profile.construction_type"]
        assert len(citations) == 1
        assert citations[0].extracted_value == "steel_frame"
        assert citations[0].citation is not None

    def test_get_citations_for_field(self):
        from insureflow.provenance.chain import StatementProvenanceChain

        record = _make_record()
        chain = StatementProvenanceChain()
        chain.build_chain(record)

        cits = chain.get_citations_for_field("risk_profile.construction_type")
        assert len(cits) == 1

    def test_get_citations_for_statement(self):
        from insureflow.provenance.chain import StatementProvenanceChain

        record = _make_record()
        chain = StatementProvenanceChain()
        chain.build_chain(record)

        cits = chain.get_citations_for_statement("steel_frame")
        assert len(cits) == 1

    def test_export_for_examiner(self):
        from insureflow.provenance.chain import StatementProvenanceChain

        record = _make_record()
        chain = StatementProvenanceChain()
        chain.build_chain(record)

        examiner = chain.export_for_examiner()
        assert len(examiner) == 1
        assert examiner[0].field_name == "risk_profile.construction_type"
        assert examiner[0].verbatim_quote != ""
        assert examiner[0].source_page == 2

    def test_export_single_field(self):
        from insureflow.provenance.chain import StatementProvenanceChain

        record = _make_record()
        chain = StatementProvenanceChain()
        chain.build_chain(record)

        examiner = chain.export_for_examiner("risk_profile.construction_type")
        assert len(examiner) == 1

    def test_total_citations(self):
        from insureflow.provenance.chain import StatementProvenanceChain

        record = _make_record()
        chain = StatementProvenanceChain()
        chain.build_chain(record)
        assert chain.total_citations() == 1

    def test_fields_with_contradictions(self):
        from insureflow.provenance.chain import StatementProvenanceChain

        node_verified = _make_node()
        node_contradicted = _make_node(
            node_id="node-2",
            citation=_make_citation(document_id="doc-2", source_text="Different value."),
        )
        node_contradicted.verification_status = VerificationStatus.CONTRADICTED
        record = _make_record(nodes={"risk_profile.construction_type": [node_verified, node_contradicted]})
        chain = StatementProvenanceChain()
        chain.build_chain(record)

        contradicted_fields = chain.fields_with_contradictions()
        assert "risk_profile.construction_type" in contradicted_fields


# ── Citation verifier ────────────────────────────────────────────────────────


class TestCitationVerifier:
    def test_verify_text_found_exact(self):
        from insureflow.verification.citation_verifier import verify_text_found

        cit = _make_citation(source_text="steel frame")
        ok, conf = verify_text_found(cit, "The building uses a steel frame structure.")
        assert ok is True
        assert conf >= 0.9

    def test_verify_text_not_found(self):
        from insureflow.verification.citation_verifier import verify_text_found

        cit = _make_citation(source_text="completely absent text")
        ok, conf = verify_text_found(cit, "No match here.")
        assert ok is False

    def test_verify_text_case_insensitive(self):
        from insureflow.verification.citation_verifier import verify_text_found

        cit = _make_citation(source_text="STEEL FRAME")
        ok, conf = verify_text_found(cit, "The building uses a steel frame structure.")
        assert ok is True
        assert conf >= 0.7

    def test_verify_page_in_range(self):
        from insureflow.verification.citation_verifier import verify_page_number

        cit = _make_citation(page_number=2)
        assert verify_page_number(cit, 10) is True

    def test_verify_page_out_of_range(self):
        from insureflow.verification.citation_verifier import verify_page_number

        cit = _make_citation(page_number=99)
        assert verify_page_number(cit, 10) is False

    def test_verify_page_none_ok(self):
        from insureflow.verification.citation_verifier import verify_page_number

        cit = _make_citation(page_number=None)
        assert verify_page_number(cit, 10) is True

    def test_verify_bbox_valid(self):
        from insureflow.verification.citation_verifier import verify_bbox_in_bounds

        cit = _make_citation(bbox=[0.1, 0.2, 0.5, 0.35])
        assert verify_bbox_in_bounds(cit) is True

    def test_verify_bbox_out_of_range(self):
        from insureflow.verification.citation_verifier import verify_bbox_in_bounds

        cit = _make_citation(bbox=[0.1, 0.2, 1.5, 0.35])
        assert verify_bbox_in_bounds(cit) is False

    def test_verify_bbox_reversed(self):
        from insureflow.verification.citation_verifier import verify_bbox_in_bounds

        cit = _make_citation(bbox=[0.5, 0.2, 0.1, 0.35])
        assert verify_bbox_in_bounds(cit) is False

    def test_verify_char_offsets_valid(self):
        from insureflow.verification.citation_verifier import verify_char_offsets

        raw = "The building was constructed in 1995 with steel frame."
        cit = _make_citation(start_char=4, end_char=12, source_text="building")
        ok, msg = verify_char_offsets(cit, raw)
        assert ok is True

    def test_verify_char_offsets_beyond_text(self):
        from insureflow.verification.citation_verifier import verify_char_offsets

        cit = _make_citation(start_char=0, end_char=9999)
        ok, msg = verify_char_offsets(cit, "short text")
        assert ok is False

    def test_verify_single_citation_full(self):
        from insureflow.verification.citation_verifier import verify_single_citation

        raw = "The building was constructed in 1995 with steel_frame."
        # steel_frame starts at index 42, ends at 53
        node = _make_node(
            citation=_make_citation(
                source_text="steel_frame",
                start_char=42,
                end_char=53,
            ),
        )
        result = verify_single_citation(node, raw, page_count=10)
        assert result.text_found is True
        assert result.page_match is True
        assert result.bbox_in_bounds is True
        assert result.char_offsets_valid is True
        assert result.verified is True

    def test_verify_all_citations_report(self):
        from insureflow.verification.citation_verifier import verify_all_citations

        raw = "The building was constructed in 1995 with steel_frame."
        node = _make_node(
            citation=_make_citation(
                source_text="steel_frame",
                start_char=42,
                end_char=53,
            ),
        )
        record = _make_record(nodes={"risk_profile.construction_type": [node]})
        raw_map = {"src-1": raw}
        report = verify_all_citations(record, raw_map)
        assert report.total_citations == 1
        assert report.verified_count >= 1
        assert report.pass_rate > 0

    def test_verify_all_citations_no_citations(self):
        from insureflow.verification.citation_verifier import verify_all_citations

        record = _make_record(nodes={})
        report = verify_all_citations(record, {})
        assert report.total_citations == 0
        assert report.pass_rate == 0.0


# ── Retention engine ─────────────────────────────────────────────────────────


class TestRetentionEngine:
    def test_default_policies_loaded(self):
        from insureflow.audit.retention import ArtifactType, RetentionEngine

        engine = RetentionEngine()
        policy = engine.get_policy(ArtifactType.SUBMISSION_BUNDLE)
        assert policy.retention_days == 2555

    def test_register_and_check_expired(self, tmp_path: Path):
        from insureflow.audit.retention import ArtifactType, RetentionEngine

        engine = RetentionEngine(base_path=tmp_path)
        record = engine.register_artifact(
            ArtifactType.SUBMISSION_BUNDLE,
            "b-1",
            created_at=datetime.now(tz=timezone.utc) - timedelta(days=3000),
        )
        assert record.expires_at < datetime.now(tz=timezone.utc)
        expired = engine.check_expired()
        assert len(expired) == 1

    def test_not_expired_within_window(self, tmp_path: Path):
        from insureflow.audit.retention import ArtifactType, RetentionEngine

        engine = RetentionEngine(base_path=tmp_path)
        engine.register_artifact(ArtifactType.SUBMISSION_BUNDLE, "b-1")
        expired = engine.check_expired()
        assert len(expired) == 0

    def test_legal_hold_blocks_deletion(self, tmp_path: Path):
        from insureflow.audit.retention import ArtifactType, RetentionEngine

        engine = RetentionEngine(base_path=tmp_path)
        engine.apply_legal_hold("b-1", "Pending litigation")
        assert engine.is_held("b-1") is True

        engine.register_artifact(
            ArtifactType.SUBMISSION_BUNDLE,
            "b-1",
            created_at=datetime.now(tz=timezone.utc) - timedelta(days=3000),
        )
        report = engine.enforce_retention(dry_run=True)
        assert report.held == 1

    def test_remove_hold(self, tmp_path: Path):
        from insureflow.audit.retention import RetentionEngine

        engine = RetentionEngine(base_path=tmp_path)
        hold = engine.apply_legal_hold("b-1", "Reason")
        assert engine.remove_hold(hold.hold_id) is True
        assert engine.is_held("b-1") is False

    def test_remove_nonexistent_hold(self, tmp_path: Path):
        from insureflow.audit.retention import RetentionEngine

        engine = RetentionEngine(base_path=tmp_path)
        assert engine.remove_hold("nonexistent") is False

    def test_active_holds(self, tmp_path: Path):
        from insureflow.audit.retention import RetentionEngine

        engine = RetentionEngine(base_path=tmp_path)
        engine.apply_legal_hold("b-1", "Reason 1")
        engine.apply_legal_hold("b-2", "Reason 2")
        holds = engine.active_holds()
        assert len(holds) == 2

    def test_hold_with_expiry(self, tmp_path: Path):
        from insureflow.audit.retention import RetentionEngine

        engine = RetentionEngine(base_path=tmp_path)
        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        engine.apply_legal_hold("b-1", "Expired hold", expires_at=past)
        assert engine.is_held("b-1") is False

    def test_enforce_retention_dry_run(self, tmp_path: Path):
        from insureflow.audit.retention import ArtifactType, RetentionEngine

        engine = RetentionEngine(base_path=tmp_path)
        engine.register_artifact(
            ArtifactType.SUBMISSION_BUNDLE,
            "b-1",
            created_at=datetime.now(tz=timezone.utc) - timedelta(days=3000),
        )
        report = engine.enforce_retention(dry_run=True)
        assert report.expired == 1
        assert report.archived == 1

    def test_enforce_retention_with_hold_blocks(self, tmp_path: Path):
        from insureflow.audit.retention import ArtifactType, RetentionEngine

        engine = RetentionEngine(base_path=tmp_path)
        engine.apply_legal_hold("b-1", "Investigation")
        engine.register_artifact(
            ArtifactType.AUDIT_TRAIL,
            "b-1",
            created_at=datetime.now(tz=timezone.utc) - timedelta(days=4000),
        )
        report = engine.enforce_retention(dry_run=True)
        assert report.held == 1
        assert report.archived == 0

    def test_summary(self, tmp_path: Path):
        from insureflow.audit.retention import ArtifactType, RetentionEngine

        engine = RetentionEngine(base_path=tmp_path)
        engine.register_artifact(ArtifactType.SUBMISSION_BUNDLE, "b-1")
        engine.register_artifact(ArtifactType.AUDIT_TRAIL, "b-1")
        s = engine.summary()
        assert s["total_artifacts"] == 2
        assert s["active"] == 2


# ── Examiner export ──────────────────────────────────────────────────────────


class TestExaminerExport:
    def test_field_citation_report(self):
        from insureflow.audit.examiner_export import ExaminerExportEngine

        record = _make_record()
        engine = ExaminerExportEngine()
        reports = engine.export_field_citation_report(record)
        assert len(reports) == 1
        r = reports[0]
        assert r.field_name == "risk_profile.construction_type"
        assert r.extracted_value == "steel_frame"
        assert r.source_page == 2
        assert r.verbatim_quote != ""

    def test_decision_defense_package(self):
        from insureflow.audit.examiner_export import ExaminerExportEngine

        record = _make_record()
        engine = ExaminerExportEngine()
        pkg = engine.export_decision_defense_package(
            record,
            decision="approve",
            confidence=0.92,
        )
        assert pkg.decision == "approve"
        assert pkg.overall_confidence == 0.92
        assert len(pkg.field_citations) == 1

    def test_naic_workpapers(self):
        from insureflow.audit.examiner_export import ExaminerExportEngine

        record = _make_record()
        engine = ExaminerExportEngine()
        workpapers = engine.export_naic_workpapers(record)
        assert len(workpapers) >= 1
        assert workpapers[0].workpaper_id.startswith("WP-")

    def test_rate_filing_justification(self):
        from insureflow.audit.examiner_export import ExaminerExportEngine

        components = [
            {"name": "base_rate", "amount": 1000.0, "source": "actuarial_study", "regulatory_basis": "adequate"},
            {"name": "expense_load", "amount": 250.0, "source": "budget", "regulatory_basis": "not_excessive"},
        ]
        record = _make_record()
        engine = ExaminerExportEngine()
        results = engine.export_rate_filing_justification(components, record)
        assert len(results) == 2
        assert results[0].rate_component == "base_rate"
        assert results[0].amount == 1000.0

    def test_defense_package_with_findings(self):
        from insureflow.audit.examiner_export import ExaminerExportEngine

        record = _make_record()
        finding = MagicMock()
        finding.title = "High variance"
        finding.description = "Construction type mismatch"
        finding.severity = "warning"
        finding.field_path = "risk_profile.construction_type"

        engine = ExaminerExportEngine()
        pkg = engine.export_decision_defense_package(
            record,
            findings=[finding],
        )
        assert len(pkg.findings) == 1
        assert pkg.findings[0]["title"] == "High variance"

    def test_naic_workpaper_risk_rating(self):
        from insureflow.audit.examiner_export import ExaminerExportEngine

        # Build a record with a low-confidence node
        node = _make_node(confidence=0.3)
        record = _make_record(nodes={"risk_profile.construction_type": [node]})

        engine = ExaminerExportEngine()
        workpapers = engine.export_naic_workpapers(record)
        # Low confidence fields should be medium risk
        assert any(wp.risk_rating == "medium" for wp in workpapers)
