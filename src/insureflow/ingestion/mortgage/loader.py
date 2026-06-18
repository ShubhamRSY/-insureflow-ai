from __future__ import annotations

import base64
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from insureflow.ingestion.base import BaseParser
from insureflow.ingestion.mortgage.classifier import MortgageDocumentClassifier
from insureflow.ingestion.mortgage.extractors import extract_fields
from insureflow.ingestion.ocr import OCRProcessor
from insureflow.models.mortgage import ExtractedMortgageField, MortgageDocument, MortgageDocumentType, ProductLine
from insureflow.mortgage.llm_extractor import MortgageLLMExtractor

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}


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
            regex_fields.setdefault("ocr_engine", []).append(
                ExtractedMortgageField(field_name="ocr_engine", value=ocr_engine, confidence=1.0)
            )

        if self.use_llm and self.llm_extractor and self.llm_extractor.needs_llm(
            resolved_type, regex_fields, raw_text
        ):
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
        return doc

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

        return self.parse(
            raw, submission_id, source_path=path, product_line=product_line, ocr_engine=ocr_engine
        )

    def parse_bytes(
        self,
        data: bytes,
        filename: str,
        submission_id: str,
        product_line: ProductLine | None = None,
    ) -> MortgageDocument:
        ext = Path(filename).suffix.lower()
        ocr_engine = ""

        if ext in {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}:
            ocr_sub = self.ocr.extract_text_from_bytes(data, filename, submission_id)
            raw = ocr_sub.raw_text
            ocr_engine = "pdfminer+tesseract" if ext == ".pdf" else "tesseract"
        else:
            raw = data.decode("utf-8", errors="replace")

        return self.parse(
            raw, submission_id, source_path=filename, product_line=product_line, ocr_engine=ocr_engine
        )


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
        for i, item in enumerate(documents):
            filename = item.get("filename", f"doc-{i}.txt")
            content = item.get("content", "")
            encoding = item.get("encoding", "utf-8")

            if encoding == "base64":
                data = base64.b64decode(content)
                doc = self.parser.parse_bytes(data, filename, f"{bid}-doc-{i}", product_line=product_line)
            else:
                doc = self.parser.parse(content, f"{bid}-doc-{i}", source_path=filename, product_line=product_line)
            results.append(doc)
        return results
