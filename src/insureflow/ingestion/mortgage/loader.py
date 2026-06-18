from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from insureflow.ingestion.base import BaseParser
from insureflow.ingestion.mortgage.classifier import MortgageDocumentClassifier
from insureflow.ingestion.mortgage.extractors import extract_fields
from insureflow.models.mortgage import ExtractedMortgageField, MortgageDocument, MortgageDocumentType, ProductLine
from insureflow.mortgage.llm_extractor import MortgageLLMExtractor


class MortgageDocumentParser(BaseParser):
    def __init__(self, use_llm: bool = True) -> None:
        self.use_llm = use_llm
        self.llm_extractor = MortgageLLMExtractor() if use_llm else None

    def parse(
        self,
        raw_text: str,
        submission_id: str,
        *,
        source_path: str = "",
        doc_type: MortgageDocumentType | None = None,
        product_line: ProductLine | None = None,
    ) -> MortgageDocument:
        resolved_type = doc_type or MortgageDocumentClassifier.classify(raw_text, source_path)
        resolved_product = product_line or MortgageDocumentClassifier.infer_product_line(source_path)

        regex_fields = extract_fields(resolved_type, raw_text)
        llm_used = False

        if self.use_llm and self.llm_extractor and self.llm_extractor.needs_llm(
            resolved_type, regex_fields, raw_text
        ):
            llm_result = self.llm_extractor.extract(raw_text, resolved_type, source_path)
            if llm_result:
                regex_fields = self.llm_extractor.merge_fields(regex_fields, llm_result)
                llm_used = True
                if llm_result.document_type_guess and resolved_type == MortgageDocumentType.UNKNOWN:
                    for dt in MortgageDocumentType:
                        if dt.value in llm_result.document_type_guess.lower().replace(" ", "_"):
                            resolved_type = dt
                            break

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
                    value="regex+llm",
                    confidence=1.0,
                    context="LLM supplemented regex extraction",
                )
            )
        return doc


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
            with open(path, encoding="utf-8", errors="replace") as f:
                raw = f.read()
            inferred_line = product_line or MortgageDocumentClassifier.infer_product_line(path)
            doc = self.parser.parse(
                raw,
                f"{bid}-doc-{i}",
                source_path=path,
                product_line=inferred_line,
            )
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
        from pathlib import Path

        root = Path(directory)
        pattern = "**/*.txt" if recursive else "*.txt"
        paths = sorted(str(p) for p in root.glob(pattern) if p.is_file())
        return self.load_from_paths(paths, bundle_id=bundle_id, product_line=product_line)

    def load_from_texts(
        self,
        documents: list[dict[str, str]],
        bundle_id: str | None = None,
        product_line: ProductLine = ProductLine.RESIDENTIAL_MORTGAGE,
    ) -> list[MortgageDocument]:
        """Load from API payloads: [{\"filename\": \"w2.txt\", \"content\": \"...\"}]"""
        bid = bundle_id or f"mortgage-{uuid4().hex[:12]}"
        results: list[MortgageDocument] = []
        for i, item in enumerate(documents):
            filename = item.get("filename", f"doc-{i}.txt")
            content = item.get("content", "")
            doc = self.parser.parse(
                content,
                f"{bid}-doc-{i}",
                source_path=filename,
                product_line=product_line,
            )
            results.append(doc)
        return results
