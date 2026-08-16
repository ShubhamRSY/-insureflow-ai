from __future__ import annotations

import base64
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from insureflow.ingestion.acord_parser import ACORDParser
from insureflow.ingestion.agentic_extraction import AgenticExtractionLoop, agentic_enabled
from insureflow.ingestion.chunker import DocumentChunker
from insureflow.ingestion.classifier import DocumentClassifier
from insureflow.ingestion.entity_extraction import extract_named_entities
from insureflow.ingestion.financial_parser import FinancialStatementParser
from insureflow.ingestion.insurance.classifier import InsuranceDocumentClassifier, InsuranceDocumentType
from insureflow.ingestion.insurance.extractors import extract_fields
from insureflow.ingestion.insurance.normalizers import get_normalizer
from insureflow.ingestion.json_parser import JSONBrokerParser
from insureflow.ingestion.loss_run_parser import LossRunParser
from insureflow.ingestion.ocr import OCRProcessor
from insureflow.ingestion.report_extractor import InspectionReportExtractor
from insureflow.ingestion.router import RouteKind, profile_document, route_document, router_enabled
from insureflow.ingestion.sov_parser import SOVParser
from insureflow.ingestion.spatial import SpatialRef, attach_spatial_ref
from insureflow.ingestion.structured_docs import parse_structured_document
from insureflow.ingestion.vlm_parser import vlm_enabled, vlm_parse_document
from insureflow.models.submissions import ExtractedChunk, ExtractedField, SubmissionBundle, SubmissionStatus, UnstructuredSubmission

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp",
    ".tif",
    ".xml",
    ".json",
    ".csv",
    ".xlsx",
    ".xls",
    ".xlsm",
    ".docx",
    ".eml",
    ".msg",
    ".html",
    ".htm",
}
_PDF_IMAGE_EXTS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"})
_TEXT_EXTS = frozenset({".txt", ".md", ".csv", ".xml", ".json", ".html", ".htm", ".eml"})


def _code_exec_fallback_enabled() -> bool:
    from insureflow.agents.code_execution_agent import code_exec_enabled

    return code_exec_enabled()


class InsuranceDocumentLoader:
    """Load insurance broker submissions including OCR on PDF/image uploads."""

    def __init__(self, ocr_engine: str = "auto") -> None:
        self.ocr = OCRProcessor(engine=ocr_engine)
        self.classifier = InsuranceDocumentClassifier()
        self.legacy_classifier = DocumentClassifier()
        self.acord_parser = ACORDParser()
        self.json_parser = JSONBrokerParser()
        self.report_extractor = InspectionReportExtractor()
        self.loss_run_parser = LossRunParser()
        self.sov_parser = SOVParser()
        self.financial_parser = FinancialStatementParser()
        self.chunker = DocumentChunker()
        self._agentic: AgenticExtractionLoop | None = None
        self._code_agent: Any = None

    def _agentic_loop(self) -> AgenticExtractionLoop:
        if self._agentic is None:
            from insureflow.llm.client import LLMClient

            self._agentic = AgenticExtractionLoop(llm=LLMClient())
        return self._agentic

    def load_from_documents(
        self,
        documents: list[dict[str, str]],
        bundle_id: str | None = None,
    ) -> SubmissionBundle:
        bid = bundle_id or f"bundle-{uuid4().hex[:12]}"
        bundle = SubmissionBundle(bundle_id=bid, status=SubmissionStatus.RECEIVED)

        for i, doc in enumerate(documents):
            filename = doc.get("filename", f"doc-{i}.txt")
            content = doc.get("content", "")
            encoding = doc.get("encoding", "utf-8")

            raw_text, engine, extra_fields, spatial_lines, raw_bytes = self._resolve_content(content, filename, encoding)
            doc_type = self.classifier.classify(raw_text, filename)

            if doc_type == InsuranceDocumentType.ACORD_XML:
                bundle.structured = self.acord_parser.parse(raw_text, bid)
                bundle.status = SubmissionStatus.PARSED
                continue

            if filename.endswith(".json") or doc_type == InsuranceDocumentType.BROKER_SLIP and raw_text.strip().startswith("{"):
                try:
                    bundle.structured = self.json_parser.parse(raw_text, bid)
                    bundle.status = SubmissionStatus.PARSED
                    continue
                except Exception:
                    pass

            sub = self._build_unstructured(raw_text, filename, doc_type, bid, i, engine, extra_fields, spatial_lines, raw_bytes)
            bundle.unstructured.append(sub)

        if bundle.unstructured or bundle.structured:
            bundle.status = SubmissionStatus.PARSED
        return bundle

    def load_from_paths(self, paths: list[str], bundle_id: str | None = None) -> SubmissionBundle:
        docs = []
        for path in paths:
            p = Path(path)
            raw = p.read_bytes()
            if p.suffix.lower() in _TEXT_EXTS:
                docs.append(
                    {
                        "filename": p.name,
                        "content": raw.decode("utf-8", errors="replace"),
                        "encoding": "utf-8",
                    }
                )
            else:
                docs.append({"filename": p.name, "content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"})
        return self.load_from_documents(docs, bundle_id=bundle_id)

    def load_from_source(
        self,
        source_id: str,
        raw_data: dict[str, Any],
        bundle_id: str | None = None,
    ) -> SubmissionBundle:
        """Normalize raw data from a specific enterprise source into a SubmissionBundle.

        Uses the source-specific normalizer to transform proprietary field names
        and structures into the common StructuredSubmission schema.
        """
        normalizer = get_normalizer(source_id)
        if normalizer is None:
            raise ValueError(f"No normalizer registered for source '{source_id}'. Use supported_sources() to see available sources.")
        bid = bundle_id or f"bundle-{uuid4().hex[:12]}"
        structured = normalizer.normalize(raw_data, submission_id=f"{bid}-src")
        bundle = SubmissionBundle(
            bundle_id=bid,
            status=SubmissionStatus.RECEIVED,
            structured=structured,
        )
        if structured:
            bundle.status = SubmissionStatus.PARSED
        return bundle

    def _resolve_content(
        self, content: str, filename: str, encoding: str
    ) -> tuple[str, str, dict[str, list[ExtractedField]], dict[int, dict[str, list[float]]], bytes | None]:
        ext = Path(filename).suffix.lower()
        if encoding == "base64":
            data = base64.b64decode(content)

            if ext in _PDF_IMAGE_EXTS and router_enabled():
                decision = route_document(profile_document(filename, data))
                if decision.route == RouteKind.VLM and vlm_enabled():
                    parsed_vlm = vlm_parse_document(data, filename)
                    if parsed_vlm is not None:
                        markdown, vlm_engine = parsed_vlm
                        return markdown, vlm_engine, {}, {}, data

            try:
                structured = parse_structured_document(data, filename)
            except Exception:
                structured = None
            if structured is not None:
                return structured[0], structured[1], structured[2], {}, data
            if ext in _PDF_IMAGE_EXTS:
                sub_id = f"ocr-{uuid4().hex[:8]}"
                parsed = self.ocr.extract_text_from_bytes(data, filename, sub_id)
                engine = "tesseract" if parsed.raw_text and not parsed.raw_text.startswith("[OCR:") else "pdfminer"
                return parsed.raw_text, engine, parsed.extracted_fields or {}, parsed.spatial_lines, data

            if _code_exec_fallback_enabled():
                result = self._code_parse(data, filename)
                if result is not None:
                    return result
            return data.decode("utf-8", errors="replace"), "", {}, {}, data

        if ext == ".pdf" and encoding == "utf-8":
            raw_bytes = content.encode("utf-8", errors="surrogateescape") if isinstance(content, str) else content
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name
            try:
                parsed = self.ocr.extract_text(tmp_path, f"ocr-{uuid4().hex[:8]}")
                return parsed.raw_text, "pdfminer", parsed.extracted_fields or {}, parsed.spatial_lines, raw_bytes
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        return content, "", {}, {}, None

    def _code_parse(self, data: bytes, filename: str) -> tuple[str, str, dict[str, list[ExtractedField]], dict[int, dict[str, list[float]]], bytes] | None:
        """Programmatic-generative fallback for binary blobs the generic parsers miss."""
        if self._code_agent is None:
            from insureflow.agents.code_execution_agent import CodeExecutionAgent
            from insureflow.llm.client import LLMClient

            self._code_agent = CodeExecutionAgent(llm=LLMClient())
        result = self._code_agent.parse_document(data, filename)
        if result is None or result.error or not result.fields:
            return None
        fields: dict[str, list[ExtractedField]] = {
            key: [ExtractedField(field_name=key, value=value, confidence=0.8, context="code_execution")] for key, value in result.fields.items()
        }
        raw = "\n".join(f"{k}: {v}" for k, v in result.fields.items())
        return raw, "code_execution", fields, {}, data

    def _build_unstructured(
        self,
        raw_text: str,
        filename: str,
        doc_type: InsuranceDocumentType,
        bundle_id: str,
        index: int,
        engine: str,
        extra_fields: dict[str, list[ExtractedField]] | None = None,
        spatial_lines: dict[int, dict[str, list[float]]] | None = None,
        raw_bytes: bytes | None = None,
    ) -> UnstructuredSubmission:
        sub_id = f"{bundle_id}-{doc_type.value}-{index}"
        dtype = doc_type.value
        extra_fields = extra_fields or {}
        spatial_lines = spatial_lines or {}

        if doc_type == InsuranceDocumentType.INSPECTION_REPORT:
            sub = self.report_extractor.parse(raw_text, sub_id)
        elif doc_type == InsuranceDocumentType.LOSS_RUN:
            sub = self.loss_run_parser.parse(raw_text, sub_id)
        elif doc_type == InsuranceDocumentType.SCHEDULE_OF_VALUES:
            sub = self.sov_parser.parse(raw_text, sub_id)
        elif doc_type == InsuranceDocumentType.FINANCIAL_STATEMENT:
            sub = self.financial_parser.parse(raw_text, sub_id)
        else:
            extracted = extract_fields(dtype, raw_text)
            chunks = [ExtractedChunk(chunk_index=idx, text=chunk, start_char=0, end_char=len(chunk)) for idx, chunk in enumerate(self.chunker.chunk_text(raw_text))]
            sub = UnstructuredSubmission(
                submission_id=sub_id,
                source=f"broker_{dtype}",
                document_type=dtype,
                raw_text=raw_text,
                extracted_fields=extracted,
                chunks=chunks,
                processed_at=datetime.now(timezone.utc),
            )

        for key, fields in extra_fields.items():
            sub.extracted_fields.setdefault(key, []).extend(fields)
        if engine:
            sub.extracted_fields.setdefault("ocr_engine", []).append(ExtractedField(field_name="ocr_engine", value=engine, confidence=1.0))
        for key, fields in extract_named_entities(raw_text).items():
            sub.extracted_fields.setdefault(key, []).extend(fields)

        sub.spatial_lines = spatial_lines

        if agentic_enabled():
            fields, report = self._agentic_loop().run(raw_text, sub.extracted_fields, dtype)
            sub.extracted_fields = fields
            sub.extracted_fields.setdefault("agentic_report", []).append(
                ExtractedField(field_name="agentic_report", value="; ".join(report), confidence=1.0)
            )

        self._ground_fields(sub.extracted_fields, spatial_lines)
        self._apply_structural_chunks(sub)
        sub.verification = self._verify(sub.extracted_fields, raw_text, dtype, spatial_lines, raw_bytes)
        return sub

    def _verify(
        self,
        fields: dict[str, list[ExtractedField]],
        raw_text: str,
        dtype: str,
        spatial_lines: dict[int, dict[str, list[float]]],
        raw_bytes: bytes | None,
    ) -> Any:
        """Layered defense: deterministic checks + opt-in agentic critic."""
        from insureflow.verification.critic import critic_enabled
        from insureflow.verification.engine import VerificationEngine

        engine = VerificationEngine()
        if critic_enabled():
            from insureflow.llm.client import LLMClient

            engine.llm = LLMClient()
        markdown = None
        if os.getenv("USE_MARKDOWN_CHUNKING", "1").strip().lower() not in {"0", "false", "off", "no", "none"} and "|" in raw_text:
            from insureflow.ingestion.markdown_chunker import normalize_to_markdown

            markdown = normalize_to_markdown(raw_text)
        return engine.run(
            fields,
            raw_text=raw_text,
            document_type=dtype,
            spatial_lines=spatial_lines,
            pdf_bytes=raw_bytes,
            markdown=markdown,
        )

    def _apply_structural_chunks(self, sub: UnstructuredSubmission) -> None:
        """Technique #3: structure-aware chunks replace token windows when enabled."""
        from insureflow.ingestion.markdown_chunker import MarkdownHierarchicalChunker

        raw = os.getenv("USE_MARKDOWN_CHUNKING", "1").strip().lower()
        if raw in {"0", "false", "off", "no", "none"}:
            return
        if not sub.chunks:
            return
        structure_chunks = MarkdownHierarchicalChunker(max_chars=self.chunker.chunk_size).chunk_text(sub.raw_text or "")
        if structure_chunks:
            sub.chunks = [ExtractedChunk(chunk_index=i, text=chunk, start_char=0, end_char=len(chunk)) for i, chunk in enumerate(structure_chunks)]

    @staticmethod
    def _ground_fields(
        fields: dict[str, list[ExtractedField]],
        spatial_lines: dict[int, dict[str, list[float]]],
    ) -> None:
        """Technique #4: box every extracted value against the spatial line map."""
        if not spatial_lines:
            return
        for field_list in fields.values():
            for field in field_list:
                if field.page_number is not None:
                    continue
                value = field.value.strip()
                if not value:
                    continue
                for page, lines in spatial_lines.items():
                    if not lines:
                        continue
                    exact = lines.get(value)
                    if exact is not None:
                        attach_spatial_ref(field, SpatialRef(page_number=page, bbox=exact))
                        break
                    for line_text, bbox in lines.items():
                        if value in line_text:
                            attach_spatial_ref(field, SpatialRef(page_number=page, bbox=bbox))
                            break
                    if field.page_number is not None:
                        break
