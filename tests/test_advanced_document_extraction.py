"""Advanced extraction techniques: VLM parsing, agentic self-correction,
markdown/hierarchical chunking, bounding-box grounding, ensemble routing,
and programmatic-generative (code-exec) execution."""

from __future__ import annotations

import base64

import pytest

try:
    import pymupdf  # noqa: F401

    HAS_PYMUPDF = True
except ImportError:
    try:
        import fitz  # noqa: F401

        HAS_PYMUPDF = True
    except ImportError:
        HAS_PYMUPDF = False


# ── 1. VLM native parsing ───────────────────────────────────────────────────


def test_vlm_disabled_by_default(monkeypatch):
    monkeypatch.delenv("USE_VLM_PARSING", raising=False)
    monkeypatch.delenv("VLM_PROVIDER", raising=False)
    from insureflow.ingestion.vlm_parser import vlm_enabled, vlm_parse_document

    assert vlm_enabled() is False
    assert vlm_parse_document(b"pdf", "doc.pdf") is None


def test_vlm_provider_forced(monkeypatch):
    monkeypatch.setenv("USE_VLM_PARSING", "1")
    monkeypatch.setenv("VLM_PROVIDER", "openai")
    monkeypatch.delenv("VLM_MODEL", raising=False)
    from insureflow.ingestion.vlm_parser import selected_provider

    assert selected_provider() == "openai"


def test_vlm_parse_document_uses_configured_provider(monkeypatch):
    monkeypatch.setenv("USE_VLM_PARSING", "1")
    monkeypatch.setenv("VLM_PROVIDER", "openai")
    from insureflow.ingestion import vlm_parser

    monkeypatch.setattr(vlm_parser, "render_pdf_to_images", lambda path, dpi=200: [b"fake-png"])
    monkeypatch.setattr(vlm_parser, "_openai_vision", lambda images: "# Parsed\n\n| A | B |\n|---|---|")
    markdown, provider = vlm_parser.vlm_parse_document(b"not really a pdf", "doc.pdf")
    assert markdown.startswith("# Parsed")
    assert provider == "vlm:openai"


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf not installed")
def test_render_pdf_to_images(tmp_path):
    import pymupdf

    pdf_path = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Hello underwriter")
    doc.save(str(pdf_path))
    doc.close()

    from insureflow.ingestion.vlm_parser import render_pdf_to_images

    images = render_pdf_to_images(str(pdf_path))
    assert images
    assert all(img.startswith(b"\x89PNG") for img in images)


# ── 2. Agentic self-correction ──────────────────────────────────────────────


def test_agentic_disabled_by_default(monkeypatch):
    monkeypatch.delenv("USE_AGENTIC_EXTRACTION", raising=False)
    from insureflow.ingestion.agentic_extraction import agentic_enabled

    assert agentic_enabled() is False


def _ef(name: str, value: str, confidence: float = 1.0):
    from insureflow.models.submissions import ExtractedField

    return ExtractedField(field_name=name, value=value, confidence=confidence)


def test_consistency_issues_arithmetic_mismatch():
    from insureflow.ingestion.agentic_extraction import consistency_issues

    fields = {
        "claim_1": [_ef("claim_1", "1000")],
        "claim_2": [_ef("claim_2", "2000")],
        "total_incurred": [_ef("total_incurred", "5000")],
    }
    issues = consistency_issues(fields, document_type="")
    assert any("arithmetic mismatch" in issue for issue in issues)


def test_consistency_issues_missing_required():
    from insureflow.ingestion.agentic_extraction import consistency_issues

    issues = consistency_issues({}, document_type="loss_run")
    assert any("missing required field: total_incurred" in issue for issue in issues)


def test_consistency_issues_low_confidence():
    from insureflow.ingestion.agentic_extraction import consistency_issues

    fields = {"occupancy_type": [_ef("occupancy_type", "warehouse", confidence=0.4)]}
    issues = consistency_issues(fields, document_type="inspection_report", min_confidence=0.6)
    assert any("low confidence (0.40)" in issue for issue in issues)


class _FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.api_key = "test-key"
        self.calls = 0

    def complete(self, prompt, **kwargs):
        self.calls += 1
        return self.responses[min(self.calls, len(self.responses)) - 1]


def test_agentic_loop_refines_and_records_report(monkeypatch):
    monkeypatch.setenv("USE_AGENTIC_EXTRACTION", "1")
    monkeypatch.setenv("AGENTIC_MAX_LOOPS", "2")
    from insureflow.ingestion.agentic_extraction import AgenticExtractionLoop

    llm = _FakeLLM(['{"total_incurred": "500000"}'])
    loop = AgenticExtractionLoop(llm=llm, max_loops=2, min_confidence=0.6)
    seed = {"total_claims": [_ef("total_claims", "3")]}
    fields, report = loop.run("Total incurred 500000.", seed, document_type="loss_run")
    assert fields["total_incurred"][0].value == "500000"
    assert fields["total_incurred"][0].context == "agentic_refinement_pass_1"
    assert fields["agentic"][0].value
    assert any("merged 1 refined fields" in line for line in report)


def test_agentic_loop_keeps_high_confidence_seed(monkeypatch):
    monkeypatch.setenv("USE_AGENTIC_EXTRACTION", "1")
    from insureflow.ingestion.agentic_extraction import AgenticExtractionLoop

    llm = _FakeLLM(['{"occupancy_type": "office"}'])
    loop = AgenticExtractionLoop(llm=llm, max_loops=1, min_confidence=0.6)
    seed = {"occupancy_type": [_ef("occupancy_type", "warehouse", confidence=0.95)]}
    fields, _ = loop.run("", seed, document_type="")
    assert fields["occupancy_type"][0].value == "warehouse"  # seed wins


def test_agentic_loop_skips_without_llm(monkeypatch):
    monkeypatch.setenv("USE_AGENTIC_EXTRACTION", "1")
    from insureflow.ingestion.agentic_extraction import AgenticExtractionLoop

    fields, report = AgenticExtractionLoop(llm=None).run("", {}, "loss_run")
    assert fields == {}
    assert report[0] == "agentic disabled or no LLM available"


# ── 3. Markdown normalization + hierarchical chunking ───────────────────────


def test_normalize_to_markdown_keeps_structure():
    from insureflow.ingestion.markdown_chunker import normalize_to_markdown

    md = normalize_to_markdown("# Title\n- item one\n- item two\n\nplain prose here")
    assert "# Title" in md
    assert "- item one" in md
    assert "plain prose here" in md


def test_normalize_to_markdown_promotes_layout_rows():
    from insureflow.ingestion.markdown_chunker import normalize_to_markdown

    md = normalize_to_markdown("Building  4,000,000  2020\nEquipment   350,000  2021")
    assert "| Building | 4,000,000 | 2020 |" in md
    assert "| Equipment | 350,000 | 2021 |" in md


def test_hierarchical_chunker_splits_on_headings():
    from insureflow.ingestion.markdown_chunker import MarkdownHierarchicalChunker

    md = (
        "# Policy Summary\n\nNamed Insured: Pacific Coast\n\n"
        "## Loss History\n\nOne claim in 2024.\n\n"
        "## Assets\n\n| Item | Value |\n| --- | --- |\n| Building | 4,000,000 |"
    )
    chunks = MarkdownHierarchicalChunker().chunk_text(md)
    assert any(chunk.startswith("## Policy Summary") for chunk in chunks)
    assert any("## Loss History" in chunk for chunk in chunks)
    assert any("## Assets" in chunk for chunk in chunks)


def test_hierarchical_chunks_helper_empty():
    from insureflow.ingestion.markdown_chunker import hierarchical_chunks

    assert hierarchical_chunks("") == []


# ── 4. Bounding-box grounding ───────────────────────────────────────────────


def test_spatial_ref_citation():
    from insureflow.ingestion.spatial import SpatialRef

    ref = SpatialRef(page_number=2, bbox=[0.1, 0.2, 0.5, 0.35])
    assert "page 2" in ref.citation()
    assert "0.100,0.200..0.500,0.350" in ref.citation()


def test_attach_citation_sets_field_attrs():
    from insureflow.ingestion.spatial import attach_citation, grounding_citations

    field = _ef("total_assets", "4000000")
    attach_citation(field, page_number=1, bbox=[0.1, 0.2, 0.5, 0.3])
    assert field.page_number == 1
    assert field.bbox == [0.1, 0.2, 0.5, 0.3]
    assert "page 1" in field.source_ref
    citations = grounding_citations([field])
    assert citations and "total_assets: 4000000" in citations[0]


def test_textract_result_carries_spatial_lines(monkeypatch):
    monkeypatch.setenv("USE_CLOUD_OCR", "textract")
    from insureflow.ingestion.cloud_ocr import _textract_blocks_to_result

    response = {
        "Blocks": [
            {
                "BlockType": "LINE",
                "Id": "l1",
                "Page": 1,
                "Text": "Named Insured: Acme Corp",
                "Geometry": {"BoundingBox": {"Left": 0.1, "Top": 0.2, "Width": 0.4, "Height": 0.03}},
            }
        ]
    }
    result = _textract_blocks_to_result(response)
    assert result.lines
    bbox = result.lines[1]["Named Insured: Acme Corp"]
    assert bbox == pytest.approx([0.1, 0.2, 0.5, 0.23])


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf not installed")
def test_loader_grounds_spacy_fields_to_bbox(tmp_path):
    import pymupdf

    pdf_path = tmp_path / "grounding.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Named Insured: Pacific Coast Manufacturing")
    doc.save(str(pdf_path))
    doc.close()

    from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader

    bundle = InsuranceDocumentLoader().load_from_paths([str(pdf_path)], bundle_id="ground")
    sub = bundle.unstructured[0]
    grounded = [f for fields in sub.extracted_fields.values() for f in fields if f.source_ref]
    assert grounded
    assert any("page 1" in f.source_ref for f in grounded)


# ── 5. Dynamic ensemble routing ─────────────────────────────────────────────


def test_router_enabled_by_default(monkeypatch):
    monkeypatch.delenv("USE_DOCUMENT_ROUTER", raising=False)
    from insureflow.ingestion.router import router_enabled

    assert router_enabled() is True


def test_route_structured_extension():
    from insureflow.ingestion.router import DocumentProfile, RouteKind, route_document

    decision = route_document(DocumentProfile(filename="sov.xlsx", extension=".xlsx"))
    assert decision.route == RouteKind.STRUCTURED


def test_route_plain_text():
    from insureflow.ingestion.router import DocumentProfile, RouteKind, route_document

    decision = route_document(DocumentProfile(filename="note.txt", extension=".txt"))
    assert decision.route == RouteKind.STANDARD


def test_route_scanned_low_density():
    from insureflow.ingestion.router import DocumentProfile, RouteKind, route_document

    profile = DocumentProfile(
        filename="scan.pdf", extension=".pdf", page_count=5, image_count=8, text_chars=40, text_density=0.004
    )
    assert route_document(profile).route == RouteKind.SCANNED


def test_route_vlm_multi_column():
    from insureflow.ingestion.router import DocumentProfile, RouteKind, route_document

    profile = DocumentProfile(
        filename="report.pdf", extension=".pdf", page_count=10, text_chars=8800, text_density=0.4, column_span=0.8
    )
    assert route_document(profile).route == RouteKind.VLM


def test_route_force_override(monkeypatch):
    monkeypatch.setenv("ROUTER_FORCE", "code")
    from insureflow.ingestion.router import DocumentProfile, RouteKind, route_document

    decision = route_document(DocumentProfile(filename="note.txt", extension=".txt"))
    assert decision.route == RouteKind.CODE


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf not installed")
def test_profile_document_text_pdf(tmp_path):
    import pymupdf

    pdf_path = tmp_path / "text.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Loss run for Pacific Coast. Claims total 3. Incurred 500000.")
    doc.save(str(pdf_path))
    doc.close()

    from insureflow.ingestion.router import RouteKind, profile_document, route_document

    profile = profile_document(str(pdf_path))
    assert profile.page_count == 1
    assert profile.text_chars > 0
    assert profile.text_density > 0
    assert route_document(profile).route == RouteKind.STANDARD


def test_loader_vlm_route(monkeypatch):
    monkeypatch.setenv("ROUTER_FORCE", "vlm")
    monkeypatch.setenv("USE_VLM_PARSING", "1")
    from insureflow.ingestion.insurance import loader as loader_mod

    monkeypatch.setattr(
        loader_mod, "vlm_parse_document", lambda data, filename: ("# VLM Parsed\nNamed Insured: Acme Corp", "vlm:fake")
    )
    bundle = loader_mod.InsuranceDocumentLoader().load_from_documents(
        [{"filename": "bus.pdf", "content": base64.b64encode(b"pdf").decode("ascii"), "encoding": "base64"}],
        bundle_id="vlm-route",
    )
    sub = bundle.unstructured[0]
    assert sub.raw_text.startswith("# VLM Parsed")
    assert any(f.value == "vlm:fake" for f in sub.extracted_fields.get("ocr_engine", []))


# ── 6. Programmatic-generative execution ────────────────────────────────────


def test_code_exec_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_CODE_EXECUTION", raising=False)
    from insureflow.agents.code_execution_agent import code_exec_enabled

    assert code_exec_enabled() is False


def test_code_exec_scan_denies_dangerous_constructs():
    from insureflow.agents.code_execution_agent import _scan_script

    assert _scan_script("import os\nos.system('rm -rf /')") is not None
    assert _scan_script("import subprocess") is not None
    assert _scan_script("import json\nprint('ok')") is None


def test_code_exec_parse_output():
    from insureflow.agents.code_execution_agent import _parse_output

    assert _parse_output('{"a": "1"}') == {"a": "1"}
    assert _parse_output('prefix ```json\n{"a": "1"}\n``` suffix') == {"a": "1"}
    assert _parse_output("not json") is None


def test_code_exec_agent_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("ALLOW_CODE_EXECUTION", "false")
    from insureflow.agents.code_execution_agent import CodeExecutionAgent

    assert CodeExecutionAgent(llm=_FakeLLM(['print("x")'])).parse_document(b"data", "f.dat") is None


class _FakeGenLLM:
    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.api_key = "test-key"
        self.calls = 0

    def complete(self, prompt, **kwargs):
        self.calls += 1
        return self.scripts[min(self.calls, len(self.scripts)) - 1]


def test_code_exec_agent_runs_script_and_parses(monkeypatch):
    monkeypatch.setenv("ALLOW_CODE_EXECUTION", "true")
    from insureflow.agents.code_execution_agent import CodeExecutionAgent

    good = 'import json, sys\nprint(json.dumps({"total_claims": "3"}))'
    agent = CodeExecutionAgent(llm=_FakeGenLLM([good]), max_attempts=2)
    result = agent.parse_document(b"data", "loss.dat")
    assert result is not None and not result.error
    assert result.fields == {"total_claims": "3"}
    assert result.attempts == 1
    assert "total_claims" in result.script


def test_code_exec_agent_self_debugs(monkeypatch):
    monkeypatch.setenv("ALLOW_CODE_EXECUTION", "true")
    from insureflow.agents.code_execution_agent import CodeExecutionAgent

    bad = 'print("not json at all")'
    good = 'import json, sys\nprint(json.dumps({"total": "100"}))'
    agent = CodeExecutionAgent(llm=_FakeGenLLM([bad, good]), max_attempts=2)
    result = agent.parse_document(b"data", "f.dat")
    assert result is not None and not result.error
    assert result.fields == {"total": "100"}
    assert result.attempts == 2  # first pass failed, second fixed


def test_loader_code_exec_fallback(monkeypatch):
    from insureflow.agents.code_execution_agent import CodeExecResult
    from insureflow.ingestion.insurance import loader as loader_mod

    class _FakeAgent:
        def parse_document(self, file_bytes, filename):
            return CodeExecResult(fields={"total_claims": "12", "incurred": "34000"}, attempts=1)

    loader = loader_mod.InsuranceDocumentLoader()
    loader._code_agent = _FakeAgent()
    monkeypatch.setenv("ALLOW_CODE_EXECUTION", "true")
    bundle = loader.load_from_documents(
        [{"filename": "weird.dat", "content": base64.b64encode(b"\x00\x01\x02").decode("ascii"), "encoding": "base64"}],
        bundle_id="code-route",
    )
    sub = bundle.unstructured[0]
    assert sub.extracted_fields["total_claims"][0].value == "12"
    assert any(f.value == "code_execution" for f in sub.extracted_fields.get("ocr_engine", []))
