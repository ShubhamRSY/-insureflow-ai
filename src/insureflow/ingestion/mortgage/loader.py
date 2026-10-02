from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from insureflow.ingestion.base import BaseParser
from insureflow.ingestion.intake import ACTIVE_CONTENT_FIELD, BLOCKED_TEXT, IMAGE_EXTS, UNREADABLE_ENGINE, decode_text, intake_documents, is_unreadable, pdf_packet_sections, prepare
from insureflow.ingestion.mortgage.classifier import MortgageDocumentClassifier
from insureflow.ingestion.mortgage.extractors import extract_fields
from insureflow.ingestion.ocr import OCRProcessor
from insureflow.ingestion.structured_docs import parse_structured_document
from insureflow.models.mortgage import ExtractedMortgageField, MortgageDocument, MortgageDocumentType, ProductLine
from insureflow.mortgage.llm_extractor import MortgageLLMExtractor
from insureflow.mortgage.privacy import sanitize_document

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}


def _classify_heading(heading: str) -> MortgageDocumentType:
    # Content scoring guesses at any text; the filename rules ("pay_stub",
    # "closing_disclosure") are precise and match a title written like a filename.
    # A "Schedule ..." page (Schedule C, Schedule B - Exceptions) belongs to the document before it.
    if heading.lower().startswith("schedule"):
        return MortgageDocumentType.UNKNOWN
    return MortgageDocumentClassifier.classify("", re.sub(r"\W+", "_", heading.lower().replace("-", "")))


class MortgageDocumentParser(BaseParser):
    def __init__(self, use_llm: bool = True) -> None:
        self.use_llm = use_llm
        self.llm_extractor = MortgageLLMExtractor() if use_llm else None
        self.ocr = OCRProcessor(engine="auto")

    def parse(
        self,
        raw_text: str,
        submission_id: str,
        *,
        source_path: str = "",
        doc_type: MortgageDocumentType | None = None,
        product_line: ProductLine | None = None,
        ocr_engine: str = "",
    ) -> MortgageDocument:
        resolved_type = doc_type or MortgageDocumentClassifier.classify(raw_text, source_path)
        resolved_product = product_line or MortgageDocumentClassifier.infer_product_line(source_path)

        regex_fields = extract_fields(resolved_type, raw_text)
        llm_used = False
        ocr_used = bool(ocr_engine)

        if ocr_used:
            regex_fields.setdefault("ocr_engine", []).append(ExtractedMortgageField(field_name="ocr_engine", value=ocr_engine, confidence=1.0))

        if self.use_llm and self.llm_extractor and self.llm_extractor.needs_llm(resolved_type, regex_fields, raw_text):
            llm_result = self.llm_extractor.extract(raw_text, resolved_type, source_path)
            if llm_result:
                regex_fields = self.llm_extractor.merge_fields(regex_fields, llm_result)
                llm_used = True

        doc = MortgageDocument(
            document_id=submission_id,
            source_path=source_path,
            document_type=resolved_type,
            product_line=resolved_product,
            raw_text=raw_text,
            extracted_fields=regex_fields,
            parsed_at=datetime.now(tz=timezone.utc),
        )
        if llm_used:
            doc.extracted_fields.setdefault("extraction_method", []).append(
                ExtractedMortgageField(
                    field_name="extraction_method",
                    value="regex+llm+ocr" if ocr_used else "regex+llm",
                    confidence=1.0,
                    context="LLM supplemented extraction",
                )
            )
        elif ocr_used:
            doc.extracted_fields.setdefault("extraction_method", []).append(
                ExtractedMortgageField(
                    field_name="extraction_method",
                    value="ocr+regex",
                    confidence=1.0,
                )
            )
        return sanitize_document(doc, redact_raw_text=True)

    def parse_file(
        self,
        path: str,
        submission_id: str,
        product_line: ProductLine | None = None,
    ) -> MortgageDocument:
        ext = Path(path).suffix.lower()
        ocr_engine = ""

        if ext in {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}:
            ocr_sub = self.ocr.extract_text(path, submission_id)
            raw = ocr_sub.raw_text
            ocr_engine = "pdfminer+tesseract" if ext == ".pdf" else "tesseract"
        else:
            raw = Path(path).read_text(encoding="utf-8", errors="replace")

        return self.parse(raw, submission_id, source_path=path, product_line=product_line, ocr_engine=ocr_engine)

    def parse_upload(
        self,
        data: bytes,
        filename: str,
        submission_id: str,
        product_line: ProductLine | None = None,
    ) -> list[MortgageDocument]:
        """A raw upload becomes one document — or one per section of a
        multi-document PDF packet (e.g. a closing package)."""
        data, filename, blocked, active = prepare(data, filename)
        if blocked:
            return [self.parse(BLOCKED_TEXT[blocked], submission_id, source_path=filename, product_line=product_line, ocr_engine=blocked)]
        raw, engine = self._bytes_to_text(data, filename, submission_id)
        sections = pdf_packet_sections(data, filename, _classify_heading, MortgageDocumentType.UNKNOWN, MortgageDocumentClassifier.classify, ocr_text=raw) if engine not in BLOCKED_TEXT else []
        if sections:
            docs = [
                self.parse(
                    text,
                    f"{submission_id}.{k}",
                    source_path=f"{filename} (pages {first}-{last})",
                    doc_type=kind if kind != MortgageDocumentType.UNKNOWN else None,
                    product_line=product_line,
                    ocr_engine=engine,
                )
                for k, (kind, first, last, text) in enumerate(sections)
            ]
        else:
            docs = [self.parse(raw, submission_id, source_path=filename, product_line=product_line, ocr_engine=engine)]
        if active:
            for doc in docs:
                doc.extracted_fields[ACTIVE_CONTENT_FIELD] = [ExtractedMortgageField(field_name=ACTIVE_CONTENT_FIELD, value=", ".join(active), confidence=1.0)]
        return docs

    def parse_bytes(
        self,
        data: bytes,
        filename: str,
        submission_id: str,
        product_line: ProductLine | None = None,
    ) -> MortgageDocument:
        raw, engine = self._bytes_to_text(data, filename, submission_id)
        return self.parse(raw, submission_id, source_path=filename, product_line=product_line, ocr_engine=engine)

    def _bytes_to_text(self, data: bytes, filename: str, submission_id: str) -> tuple[str, str]:
        """``(text, engine)``: OCR for PDFs and images, the structured parsers
        for Office files and email, else a UTF-8 decode. Text that comes out
        empty or as junk is replaced by the unreadable marker."""
        ext = Path(filename).suffix.lower()
        if ext in {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}:
            raw = self.ocr.extract_text_from_bytes(data, filename, submission_id).raw_text
            engine = "pdfminer+tesseract" if ext == ".pdf" else "tesseract"
        else:
            try:
                structured = parse_structured_document(data, filename)
            except Exception:
                structured = None
            raw, engine = (structured[0], structured[1]) if structured else (decode_text(data), "")
        if ext not in IMAGE_EXTS and is_unreadable(raw):
            return BLOCKED_TEXT[UNREADABLE_ENGINE], UNREADABLE_ENGINE
        return raw, engine


class MortgageSubmissionLoader:
    def __init__(self, use_llm: bool = True) -> None:
        self.parser = MortgageDocumentParser(use_llm=use_llm)
        self.use_llm = use_llm

    def load_from_paths(
        self,
        paths: list[str],
        bundle_id: str | None = None,
        product_line: ProductLine | None = None,
    ) -> list[MortgageDocument]:
        documents: list[MortgageDocument] = []
        bid = bundle_id or f"mortgage-{uuid4().hex[:12]}"
        for i, path in enumerate(paths):
            inferred_line = product_line or MortgageDocumentClassifier.infer_product_line(path)
            ext = Path(path).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS - {".txt"}:
                doc = self.parser.parse_file(path, f"{bid}-doc-{i}", product_line=inferred_line)
            else:
                with open(path, encoding="utf-8", errors="replace") as f:
                    raw = f.read()
                doc = self.parser.parse(raw, f"{bid}-doc-{i}", source_path=path, product_line=inferred_line)
            documents.append(doc)
        return documents

    def load_from_directory(
        self,
        directory: str,
        bundle_id: str | None = None,
        product_line: ProductLine | None = None,
        *,
        recursive: bool = True,
    ) -> list[MortgageDocument]:
        root = Path(directory)
        paths: list[str] = []
        for ext in SUPPORTED_EXTENSIONS:
            pattern = f"**/*{ext}" if recursive else f"*{ext}"
            paths.extend(str(p) for p in root.glob(pattern) if p.is_file())
        return self.load_from_paths(sorted(paths), bundle_id=bundle_id, product_line=product_line)

    def load_from_texts(
        self,
        documents: list[dict[str, str]],
        bundle_id: str | None = None,
        product_line: ProductLine = ProductLine.RESIDENTIAL_MORTGAGE,
    ) -> list[MortgageDocument]:
        bid = bundle_id or f"mortgage-{uuid4().hex[:12]}"
        results: list[MortgageDocument] = []
        for i, item in enumerate(intake_documents(documents)):
            filename = item.get("filename", f"doc-{i}.txt")
            content = item.get("content", "")
            encoding = item.get("encoding", "utf-8")

            if encoding == "s3_ref":
                results.extend(self._load_s3_ref(content, filename, bid, i, product_line))
            elif encoding == "base64":
                data = base64.b64decode(content)
                results.extend(self.parser.parse_upload(data, filename, f"{bid}-doc-{i}", product_line=product_line))
            else:
                results.append(self.parser.parse(content, f"{bid}-doc-{i}", source_path=filename, product_line=product_line))
        return results

    def _load_s3_ref(
        self,
        storage_key: str,
        filename: str,
        bundle_id: str,
        index: int,
        product_line: ProductLine,
    ) -> list[MortgageDocument]:
        """Large-file path mirroring the insurance loader's ``s3_ref`` branch
        (``insurance/loader.py:_resolve_content``) — ``storage_key`` is an S3
        object reference, not inline content. Gated by the same
        ``MAX_PROCESSABLE_BYTES`` ceiling so a multi-GB closing package scan
        is stored/visible but never auto-OCR'd into this process's memory.
        """
        from insureflow.storage.object_storage import MAX_PROCESSABLE_BYTES, download_object_bytes, head_object

        meta = head_object(storage_key)
        size = int((meta or {}).get("size_bytes") or 0)
        if size > MAX_PROCESSABLE_BYTES:
            raw = f"[File too large to auto-process: {size:,} bytes exceeds the {MAX_PROCESSABLE_BYTES // (1024 * 1024)}MB automatic-processing limit — needs manual review]"
            return [self.parser.parse(raw, f"{bundle_id}-doc-{index}", source_path=filename, product_line=product_line, ocr_engine="unprocessed_oversized")]

        data = download_object_bytes(storage_key)
        return self.parser.parse_upload(data, filename, f"{bundle_id}-doc-{index}", product_line=product_line)
