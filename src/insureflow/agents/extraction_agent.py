from __future__ import annotations

from typing import Any, Optional

from insureflow.ingestion.acord_parser import ACORDParser
from insureflow.ingestion.insurance.classifier import LIFE_DOCUMENT_TYPES
from insureflow.ingestion.report_extractor import InspectionReportExtractor
from insureflow.llm.client import LLMClient
from insureflow.llm.prompts import EXTRACTION_PROMPT, LIFE_EXTRACTION_PROMPT
from insureflow.models.submissions import StructuredSubmission, SubmissionBundle, UnstructuredSubmission
from insureflow.redaction.pipeline import RedactedLLMClient
from insureflow.redaction.redactor import PIIRedactor

# The LLM prompt requests canonical snake_case keys, but keep a small alias map
# for the common variants a model may drift toward.
LLM_FIELD_ALIASES: dict[str, str] = {
    "stories": "number_of_stories",
    "construction": "construction_type",
    "sqft": "square_footage",
    "square_feet": "square_footage",
    "protection": "protection_class",
    "occupancy": "occupancy_type",
    "sprinkler": "sprinklered",
    "year_built_in": "year_built",
    "total_premium": "premium",
}

# Deterministic regex extraction is authoritative over the LLM's guess, which
# runs on truncated, redacted text and is inherently non-deterministic.
LLM_MERGE_CONFIDENCE = 0.85


class ExtractionAgent:
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        redact_pii: bool = True,
    ) -> None:
        self.acord_parser = ACORDParser()
        self.report_extractor = InspectionReportExtractor()
        self.redactor = PIIRedactor() if redact_pii else None
        self.llm = llm_client or (RedactedLLMClient() if redact_pii else LLMClient())

    def extract_structured(self, xml_content: str, bundle_id: str) -> StructuredSubmission:
        return self.acord_parser.parse(xml_content, bundle_id)

    def extract_unstructured(self, raw_text: str, bundle_id: str, doc_index: int = 0) -> UnstructuredSubmission:
        regex_based = self.report_extractor.parse(raw_text, bundle_id)
        return self.enhance_unstructured(regex_based)

    def enhance_unstructured(self, submission: UnstructuredSubmission) -> UnstructuredSubmission:
        """LLM-enhance a single unstructured submission (ZTA LLM path).

        Deterministic regex extraction always runs first; the LLM only merges
        additional fields in when the router decided this document genuinely
        needs it.
        """
        if not self.llm.api_key:
            return submission
        raw_text = submission.raw_text or ""
        text_for_llm = self.redactor.redact(raw_text[:8000]) if self.redactor else raw_text[:8000]
        prompt = LIFE_EXTRACTION_PROMPT if submission.document_type in LIFE_DOCUMENT_TYPES else EXTRACTION_PROMPT
        try:
            llm_result = self.llm.complete(prompt, text_for_llm)
        except Exception:
            return submission

        try:
            import json

            parsed = json.loads(llm_result)
            self._merge_llm_results(submission, parsed)
        except (json.JSONDecodeError, TypeError):
            pass
        return submission

    def redact_bundle(self, bundle: SubmissionBundle) -> SubmissionBundle:
        if not self.redactor:
            return bundle

        if bundle.structured:
            if bundle.structured.raw_xml:
                bundle.structured.raw_xml = self.redactor.redact(bundle.structured.raw_xml)
            if bundle.structured.raw_json:
                bundle.structured.raw_json = self.redactor.redact(bundle.structured.raw_json)

        for doc in bundle.unstructured:
            doc.raw_text = self.redactor.redact(doc.raw_text)
            redacted_fields: dict[str, list[Any]] = {}
            for key, field_list in doc.extracted_fields.items():
                redacted_fields[key] = [type(f)(**{**f.model_dump(), "value": self.redactor.redact(str(f.value))}) for f in field_list]
            doc.extracted_fields = redacted_fields

        for doc in bundle.supplemental:
            doc.raw_text = self.redactor.redact(doc.raw_text)

        return bundle

    def _merge_llm_results(self, submission: UnstructuredSubmission, llm_fields: dict[str, Any]) -> None:
        from insureflow.models.submissions import ExtractedField

        for raw_key, value in llm_fields.items():
            if value is None:
                continue
            key = LLM_FIELD_ALIASES.get(raw_key, raw_key)
            str_val = str(value).strip()
            if not str_val or str_val.lower() in {"null", "none", "unknown", "n/a"}:
                continue

            existing = submission.extracted_fields.get(key, [])
            if existing:
                # Deterministic regex extraction already covered this field.
                # Never duplicate it or let the lower-confidence LLM guess
                # override the regex value: a second node on the same canonical
                # path would surface a false reconciliation conflict.
                continue

            submission.extracted_fields[key] = existing
            submission.extracted_fields[key].append(
                ExtractedField(
                    field_name=key,
                    value=str_val,
                    confidence=LLM_MERGE_CONFIDENCE,
                    context="llm_extraction",
                )
            )

    def process_bundle(self, bundle: SubmissionBundle) -> SubmissionBundle:
        self.redact_bundle(bundle)
        return bundle
