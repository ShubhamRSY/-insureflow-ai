"""ML / cloud document-feature tests: spaCy NER, Instructor, Chroma, cloud OCR, vision ML."""

from __future__ import annotations

import sys

import pytest

from insureflow.rag.vector_store import (
    ChromaVectorStore,
    InMemoryVectorStore,
    WeaviateVectorStore,
    get_vector_store,
)

try:
    import spacy  # noqa: F401

    HAS_SPACY = True
except ImportError:
    HAS_SPACY = False

try:
    import chromadb  # noqa: F401

    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False


def _has_spacy_model() -> bool:
    """True when a usable spaCy pipeline (model) is available on this machine."""
    if not HAS_SPACY:
        return False
    try:
        from insureflow.ingestion.entity_extraction import _get_nlp

        return _get_nlp() is not None
    except Exception:
        return False


HAS_SPACY_MODEL = _has_spacy_model()


# ── spaCy NER enrichment ────────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_SPACY_MODEL, reason="spacy model not installed (download with: python -m spacy download en_core_web_sm)")
def test_spacy_extract_named_entities(monkeypatch):
    monkeypatch.delenv("USE_SPACY_NER", raising=False)
    from insureflow.ingestion.entity_extraction import extract_named_entities

    text = "Named Insured: Pacific Coast Manufacturing located in Austin, Texas. TIV $4,350,000 on March 14, 2026."
    fields = extract_named_entities(text)
    assert fields, "expected spaCy to find entities"
    insured = [f.value for f in fields.get("spacy.insured_name", [])]
    assert any("Pacific Coast Manufacturing" in v for v in insured)
    dates = [f.value for f in fields.get("spacy.date", [])]
    assert any(d.startswith("2026-03-14") for d in dates)


@pytest.mark.skipif(not HAS_SPACY, reason="spacy not installed")
def test_spacy_empty_text_returns_no_fields(monkeypatch):
    monkeypatch.delenv("USE_SPACY_NER", raising=False)
    from insureflow.ingestion.entity_extraction import extract_named_entities

    assert extract_named_entities("") == {}
    assert extract_named_entities("   \n ") == {}


@pytest.mark.skipif(not HAS_SPACY_MODEL, reason="spacy model not installed (download with: python -m spacy download en_core_web_sm)")
def test_loader_enriches_with_spacy_fields():
    from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader

    bundle = InsuranceDocumentLoader().load_from_documents(
        [
            {
                "filename": "note.txt",
                "content": "Named Insured: Pacific Coast Manufacturing. Located in Austin, Texas.",
                "encoding": "utf-8",
            }
        ],
        bundle_id="ner-bundle",
    )
    sub = bundle.unstructured[0]
    assert any(f.value.startswith("Pacific Coast Manufacturing") for f in sub.extracted_fields.get("spacy.insured_name", []))


# ── Instructor / structured extraction ──────────────────────────────────────


def test_instructor_available_reflects_install():
    from insureflow.llm.structured import instructor_available

    assert instructor_available() is True  # instructor is installed in the dev env


def test_extract_structured_falls_back_to_client(monkeypatch):
    from insureflow.llm.structured import extract_structured

    class FakeModel:
        pass

    class FakeClient:
        provider = "claude"

        def extract_structured(self, system, user, response_model):
            return response_model()

    result = extract_structured(FakeClient(), "sys", "user", FakeModel)
    assert isinstance(result, FakeModel)


def test_extract_structured_instructor_path(monkeypatch):
    from insureflow.llm.structured import _extract_with_instructor

    class FakeModel:
        pass

    captured = {}

    class FakeOpenAI:
        provider = "openai"
        model = "gpt-4o"
        max_tokens = 512
        temperature = 0.0

        def _get_client(self):
            return "raw"

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            captured["model"] = kwargs["model"]
            return FakeModel()

    class FakeChat:
        completions = FakeCompletions()

    class FakePatched:
        chat = FakeChat()

    import instructor

    real_from_openai = instructor.from_openai

    def fake_from_openai(raw_client, mode=None):
        captured["mode"] = mode
        return FakePatched()

    monkeypatch.setattr(instructor, "from_openai", fake_from_openai)
    try:
        result = _extract_with_instructor(FakeOpenAI(), "sys", "user", FakeModel)
    finally:
        monkeypatch.setattr(instructor, "from_openai", real_from_openai)
    assert isinstance(result, FakeModel)
    assert captured["model"] == "gpt-4o"


def test_client_extract_structured_passes_response_format(monkeypatch):
    from insureflow.llm.client import LLMClient

    called = {}

    class FakeModel:
        @classmethod
        def model_validate_json(cls, raw):
            return cls()

    client = object.__new__(LLMClient)
    client.api_key = "sk-test"
    client.provider = "openai"
    client.model = "gpt-4o"
    client.temperature = 0.0
    client.max_tokens = 512
    client.redact_pii = False
    client.model_tier = "cheap"
    client.agent = "underwriter"
    client.fallback = None  # type: ignore[attr-defined]

    def fake_complete(self, system, user, response_format=None):
        called["response_format"] = response_format
        return '{"ok": true}'

    monkeypatch.setattr(LLMClient, "complete", fake_complete)
    result = LLMClient.extract_structured(client, "sys", "user", FakeModel)
    assert called["response_format"] is FakeModel
    assert isinstance(result, FakeModel)


# ── Chroma vector store ─────────────────────────────────────────────────────


def _sample_guidelines():
    from insureflow.rag.guidelines import Guideline, GuidelineCategory, GuidelineSource

    return [
        Guideline(
            id="G-fire",
            category=GuidelineCategory.PROTECTION,
            source=GuidelineSource.ISO,
            title="Fire Protection",
            content="Sprinklered buildings qualify for protection credits.",
            keywords=["sprinkler", "fire"],
        ),
        Guideline(
            id="G-frame",
            category=GuidelineCategory.CONSTRUCTION,
            source=GuidelineSource.COMPANY,
            title="Frame Construction",
            content="Frame construction over 25,000 sqft requires a carrier appetitite check.",
            keywords=["frame", "construction"],
        ),
    ]


@pytest.mark.skipif(not HAS_CHROMA, reason="chromadb not installed")
def test_chroma_store_roundtrip(monkeypatch):
    import tempfile

    monkeypatch.setenv("EMBEDDING_BACKEND", "hash")

    from insureflow.rag.vector_store import ChromaVectorStore

    with tempfile.TemporaryDirectory() as tmp:
        store = ChromaVectorStore(tmp, collection_name="guideline_embeddings")
        store.index_guidelines(_sample_guidelines())
        results = store.search("sprinklered building", top_k=2)
        assert results
        best = max(results, key=lambda x: x[1])
        assert best[0].id == "G-fire"


@pytest.mark.skipif(not HAS_CHROMA, reason="chromadb not installed")
def test_chroma_store_clear(monkeypatch):
    import tempfile

    monkeypatch.setenv("EMBEDDING_BACKEND", "hash")

    with tempfile.TemporaryDirectory() as tmp:
        store = ChromaVectorStore(tmp, collection_name="guideline_embeddings")
        store.index_guidelines(_sample_guidelines())
        store.clear()
        assert store.search("sprinkler", top_k=1) == []


def test_vector_store_selection_defaults_to_memory(monkeypatch):
    for key in ("CHROMA_PERSIST_DIR", "WEAVIATE_URL", "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)
    store = get_vector_store()
    assert isinstance(store, InMemoryVectorStore)


def test_vector_store_selection_chroma_when_configured(monkeypatch):
    import tempfile

    monkeypatch.delenv("WEAVIATE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("CHROMA_PERSIST_DIR", tmp)
        store = get_vector_store()
        assert isinstance(store, ChromaVectorStore)


def test_vector_store_selection_pg_when_database_url(monkeypatch):
    monkeypatch.delenv("CHROMA_PERSIST_DIR", raising=False)
    monkeypatch.delenv("WEAVIATE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:5432/nope")
    store = get_vector_store()
    # Connection fails (no server) → in-memory fallback; never raises.
    assert isinstance(store, InMemoryVectorStore)


def test_weaviate_store_is_constructible(monkeypatch):
    monkeypatch.setenv("WEAVIATE_URL", "http://localhost:8080")
    store = WeaviateVectorStore("http://localhost:8080", collection_name="guideline_embeddings")
    assert store._url == "http://localhost:8080"


# ── Cloud OCR ───────────────────────────────────────────────────────────────


def test_configured_providers_default_off(monkeypatch):
    monkeypatch.delenv("USE_CLOUD_OCR", raising=False)
    from insureflow.ingestion.cloud_ocr import configured_providers

    assert configured_providers() == []


def test_configured_providers_parses_list(monkeypatch):
    monkeypatch.setenv("USE_CLOUD_OCR", "textract, documentai")
    from insureflow.ingestion.cloud_ocr import configured_providers

    assert configured_providers() == ["textract", "documentai"]


def test_cloud_extract_none_when_unconfigured(monkeypatch):
    monkeypatch.delenv("USE_CLOUD_OCR", raising=False)
    from insureflow.ingestion.cloud_ocr import cloud_extract

    assert cloud_extract(b"bytes", "file.pdf") is None


def test_textract_extract_with_mocked_boto(monkeypatch):
    monkeypatch.setenv("USE_CLOUD_OCR", "textract")
    monkeypatch.delenv("TEXTRACT_REGION", raising=False)
    from insureflow.ingestion.cloud_ocr import textract_extract

    blocks = [
        {"BlockType": "TABLE", "Id": "t1", "Relationships": [{"Type": "CHILD", "Ids": ["c1"]}]},
        {"BlockType": "CELL", "Id": "c1", "RowIndex": 1, "ColumnIndex": 1, "Relationships": [{"Type": "CHILD", "Ids": ["w1"]}]},
        {"BlockType": "WORD", "Id": "w1", "Text": "Sprinklered"},
        {"BlockType": "LINE", "Id": "l1", "Text": "Sprinklered building"},
    ]
    response = {"Blocks": blocks}

    class FakeAnalyze:
        def analyze_document(self, **kwargs):
            return response

    class FakeBoto:
        def __init__(self):
            self.calls = {}

        def client(self, service, region_name=None):
            self.calls["region"] = region_name
            return FakeAnalyze()

    import sys as _sys
    from typing import Any as _Any

    real_boto = _sys.modules.get("boto3")
    fake_module: _Any = type(sys)("boto3")
    fake_module.client = FakeBoto().client
    _sys.modules["boto3"] = fake_module
    try:
        result = textract_extract(b"x" * 100, "scan.pdf")
    finally:
        if real_boto is None:
            _sys.modules.pop("boto3", None)
        else:
            _sys.modules["boto3"] = real_boto

    assert result is not None
    assert result.provider == "textract"
    assert "Sprinklered building" in result.text
    assert "Sprinklered" in result.tables


def test_documentai_requires_credentials(monkeypatch):
    monkeypatch.setenv("USE_CLOUD_OCR", "documentai")
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GCP_PROCESSOR_ID", raising=False)
    from insureflow.ingestion.cloud_ocr import documentai_extract

    assert documentai_extract(b"pdf", "file.pdf") is None


# ── Vision ML ───────────────────────────────────────────────────────────────


def test_vision_ml_disabled_by_default(monkeypatch):
    monkeypatch.delenv("USE_VISION_ML", raising=False)
    from insureflow.ingestion.vision_ml import enabled_features

    assert enabled_features() == set()


def test_vision_ml_returns_none_when_disabled(monkeypatch):
    monkeypatch.delenv("USE_VISION_ML", raising=False)
    from insureflow.ingestion.vision_ml import paddleocr_extract_image, vision_extract_image

    assert paddleocr_extract_image("img.png") is None
    assert vision_extract_image("img.png") == ""


def test_vision_ml_enabled_but_sdk_missing(monkeypatch):
    monkeypatch.setenv("USE_VISION_ML", "paddleocr,hf_ocr,hf_tables")
    from insureflow.ingestion import vision_ml

    # No paddle OCR / transformers → returns None without raising.
    assert vision_ml.paddleocr_extract_image("img.png") is None
    assert vision_ml.hf_ocr_extract_image("img.png") is None


# ── OCR processor degradation ───────────────────────────────────────────────


def test_ocr_cloud_step_none_when_unconfigured(monkeypatch):
    monkeypatch.delenv("USE_CLOUD_OCR", raising=False)
    monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)
    from insureflow.ingestion.ocr import OCRProcessor

    assert OCRProcessor()._cloud_or_ml_pdf("nonexistent.pdf") is None


def test_ocr_image_engine_labels_unchanged(monkeypatch, tmp_path):
    monkeypatch.delenv("USE_CLOUD_OCR", raising=False)
    monkeypatch.delenv("USE_VISION_ML", raising=False)
    from insureflow.ingestion.ocr import OCRProcessor

    img = tmp_path / "scan.png"
    img.write_bytes(b"not an image")
    text, engine, lines = OCRProcessor(engine="auto")._extract_image_text(str(img))
    # Falls through all engines without raising; engine is always set.
    assert isinstance(text, str)
    assert engine in {"tesseract", "pdfminer", "raw", "vision_ml"}
    assert isinstance(lines, dict)


# ── LlamaParse wrapper ──────────────────────────────────────────────────────


def test_llamaparse_disabled_without_key(monkeypatch):
    monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)
    from insureflow.ingestion.llamaparse import llamaparse_available, parse_pdf_with_llamaparse

    assert llamaparse_available() is False
    assert parse_pdf_with_llamaparse("file.pdf") is None
