from __future__ import annotations

import base64
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from insureflow.ingestion.acord_parser import ACORDParser
from insureflow.ingestion.chunker import DocumentChunker
from insureflow.ingestion.classifier import DocumentClassifier
from insureflow.ingestion.insurance.classifier import (
    InsuranceDocumentClassifier,
    InsuranceDocumentType,
)
from insureflow.ingestion.insurance.extractors import extract_fields
from insureflow.ingestion.insurance.normalizers import get_normalizer
from insureflow.ingestion.json_parser import JSONBrokerParser
from insureflow.ingestion.loss_run_parser import LossRunParser
from insureflow.ingestion.ocr import OCRProcessor
from insureflow.ingestion.report_extractor import InspectionReportExtractor
from insureflow.ingestion.sov_parser import SOVParser
from insureflow.models.submissions import (
    ExtractedChunk,
    ExtractedField,
    SubmissionBundle,
    SubmissionStatus,
    UnstructuredSubmission,
)

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
}


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
        self.chunker = DocumentChunker()

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

            raw_text, ocr_engine = self._resolve_content(content, filename, encoding)
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

            sub = self._build_unstructured(raw_text, filename, doc_type, bid, i, ocr_engine)
            bundle.unstructured.append(sub)

        if bundle.unstructured or bundle.structured:
            bundle.status = SubmissionStatus.PARSED
        return bundle

    def load_from_paths(self, paths: list[str], bundle_id: str | None = None) -> SubmissionBundle:
        docs = []
        for path in paths:
            p = Path(path)
            docs.append(
                {
                    "filename": p.name,
                    "content": p.read_text(encoding="utf-8", errors="replace"),
                    "encoding": "utf-8",
                }
            )
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

    def _resolve_content(self, content: str, filename: str, encoding: str) -> tuple[str, str]:
        ext = Path(filename).suffix.lower()
        if encoding == "base64":
            data = base64.b64decode(content)
            if ext in {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}:
                sub_id = f"ocr-{uuid4().hex[:8]}"
                parsed = self.ocr.extract_text_from_bytes(data, filename, sub_id)
                engine = "tesseract" if parsed.raw_text and not parsed.raw_text.startswith("[OCR:") else "pdfminer"
                return parsed.raw_text, engine
            return data.decode("utf-8", errors="replace"), ""

        if ext == ".pdf" and encoding == "utf-8":
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(content.encode("utf-8", errors="surrogateescape") if isinstance(content, str) else content)
                tmp_path = tmp.name
            try:
                parsed = self.ocr.extract_text(tmp_path, f"ocr-{uuid4().hex[:8]}")
                return parsed.raw_text, "pdfminer"
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        return content, ""

    def _build_unstructured(
        self,
        raw_text: str,
        filename: str,
        doc_type: InsuranceDocumentType,
        bundle_id: str,
        index: int,
        ocr_engine: str,
    ) -> UnstructuredSubmission:
        sub_id = f"{bundle_id}-{doc_type.value}-{index}"
        dtype = doc_type.value

        if doc_type == InsuranceDocumentType.INSPECTION_REPORT:
            return self.report_extractor.parse(raw_text, sub_id)
        if doc_type == InsuranceDocumentType.LOSS_RUN:
            return self.loss_run_parser.parse(raw_text, sub_id)
        if doc_type == InsuranceDocumentType.SCHEDULE_OF_VALUES:
            return self.sov_parser.parse(raw_text, sub_id)

        extracted = extract_fields(dtype, raw_text)
        if ocr_engine:
            extracted.setdefault("ocr_engine", []).append(ExtractedField(field_name="ocr_engine", value=ocr_engine, confidence=1.0))

        chunks = [ExtractedChunk(chunk_index=idx, text=chunk, start_char=0, end_char=len(chunk)) for idx, chunk in enumerate(self.chunker.chunk_text(raw_text))]

        return UnstructuredSubmission(
            submission_id=sub_id,
            source=f"broker_{dtype}",
            document_type=dtype,
            raw_text=raw_text,
            extracted_fields=extracted,
            chunks=chunks,
            processed_at=datetime.now(timezone.utc),
        )
