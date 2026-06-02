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


class ExtractionAgent:
    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.acord_parser = ACORDParser()
        self.report_extractor = InspectionReportExtractor()
        self.llm = llm_client or LLMClient()

    def extract_structured(self, xml_content: str, bundle_id: str) -> StructuredSubmission:
        return self.acord_parser.parse(xml_content, bundle_id)

    def extract_unstructured(
        self, raw_text: str, bundle_id: str, doc_index: int = 0
    ) -> UnstructuredSubmission:
        regex_based = self.report_extractor.parse(raw_text, bundle_id)

        if self.llm.api_key:
            llm_result = self.llm.complete(EXTRACTION_PROMPT, raw_text[:8000])
            try:
                import json
                parsed = json.loads(llm_result)
                self._merge_llm_results(regex_based, parsed)
            except (json.JSONDecodeError, TypeError):
                pass

        return regex_based

    def _merge_llm_results(
        self, submission: UnstructuredSubmission, llm_fields: dict
    ) -> None:
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
        return bundle
