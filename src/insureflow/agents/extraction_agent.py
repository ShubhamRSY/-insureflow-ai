from __future__ import annotations

from typing import Optional

from insureflow.ingestion.acord_parser import ACORDParser
from insureflow.ingestion.report_extractor import InspectionReportExtractor
from insureflow.llm.client import LLMClient
from insureflow.llm.prompts import EXTRACTION_PROMPT
from insureflow.models.submissions import (
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)
from insureflow.redaction.pipeline import RedactedLLMClient
from insureflow.redaction.redactor import PIIRedactor


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

    def extract_unstructured(
        self, raw_text: str, bundle_id: str, doc_index: int = 0
    ) -> UnstructuredSubmission:
        regex_based = self.report_extractor.parse(raw_text, bundle_id)

        if self.llm.api_key:
            text_for_llm = (
                self.redactor.redact(raw_text[:8000]) if self.redactor else raw_text[:8000]
            )
            llm_result = self.llm.complete(EXTRACTION_PROMPT, text_for_llm)
            try:
                import json

                parsed = json.loads(llm_result)
                self._merge_llm_results(regex_based, parsed)
            except (json.JSONDecodeError, TypeError):
                pass

        return regex_based

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
            redacted_fields: dict[str, list] = {}
            for key, field_list in doc.extracted_fields.items():
                redacted_fields[key] = [
                    type(f)(**{**f.model_dump(), "value": self.redactor.redact(str(f.value))})
                    for f in field_list
                ]
            doc.extracted_fields = redacted_fields

        for doc in bundle.supplemental:
            doc.raw_text = self.redactor.redact(doc.raw_text)

        return bundle

    def _merge_llm_results(self, submission: UnstructuredSubmission, llm_fields: dict) -> None:
        from insureflow.models.submissions import ExtractedField

        for key, value in llm_fields.items():
            if value is not None:
                str_val = str(value)
                if key not in submission.extracted_fields:
                    submission.extracted_fields[key] = []
                submission.extracted_fields[key].append(
                    ExtractedField(
                        field_name=key,
                        value=str_val,
                        confidence=0.85,
                        context="llm_extraction",
                    )
                )

    def process_bundle(self, bundle: SubmissionBundle) -> SubmissionBundle:
        self.redact_bundle(bundle)
        return bundle
