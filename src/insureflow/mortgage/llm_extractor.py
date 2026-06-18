from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from insureflow.config import settings
from insureflow.llm.client import LLMClient
from insureflow.models.mortgage import ExtractedMortgageField, MortgageDocumentType

logger = logging.getLogger(__name__)

MESSY_DOC_MARKERS = re.compile(
    r"(?i)\[handwritten|\[smudged|\[illegible|margin note|\?\?\?|"
    r"draft|smudged|illegible|partially obscured|water damage|"
    r"faded|unclear handwriting|corrected by hand"
)

LLM_EXTRACTION_PROMPT = """\
You are a bank mortgage document extraction specialist. Extract structured \
fields from the document text below.

Document type hint: {doc_type}
Source file: {source_path}

Return ONLY valid JSON with this shape:
{{
  "document_type_guess": "string",
  "borrower_name": "string or empty",
  "fields": [
    {{"field_name": "snake_case_key", "value": "string", "confidence": 0.0-1.0, "context": "brief note"}}
  ],
  "handwritten_notes_detected": ["note1", "note2"],
  "extraction_warnings": ["warning1"]
}}

Focus on: wages, income, credit score, balances, property value, purchase price, \
employer, account numbers (masked ok), dates, DTI-relevant monthly payments.
For handwritten or smudged sections, extract best-effort values and lower confidence.
"""


class LLMExtractedField(BaseModel):
    field_name: str
    value: str
    confidence: float = 0.75
    context: str = ""


class LLMExtractionResult(BaseModel):
    document_type_guess: str = ""
    borrower_name: str = ""
    fields: list[LLMExtractedField] = Field(default_factory=list)
    handwritten_notes_detected: list[str] = Field(default_factory=list)
    extraction_warnings: list[str] = Field(default_factory=list)
    raw: str = ""


class MortgageLLMExtractor:
    """LLM-assisted extraction for messy, handwritten, or non-standard documents."""

    MIN_REGEX_FIELDS = 3

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient(model_tier="cheap")

    @property
    def is_available(self) -> bool:
        return bool(settings.llm_api_key or settings.llm_cheap_api_key or settings.claude_api_key)

    def needs_llm(
        self,
        doc_type: MortgageDocumentType,
        extracted_fields: dict[str, list[ExtractedMortgageField]],
        raw_text: str,
    ) -> bool:
        if doc_type == MortgageDocumentType.UNKNOWN:
            return True
        populated = sum(1 for v in extracted_fields.values() if v)
        if populated < self.MIN_REGEX_FIELDS:
            return True
        if MESSY_DOC_MARKERS.search(raw_text):
            return True
        return False

    def extract(
        self,
        raw_text: str,
        doc_type: MortgageDocumentType,
        source_path: str = "",
    ) -> LLMExtractionResult | None:
        if not self.is_available:
            return None
        try:
            truncated = raw_text[:12000]
            user_prompt = LLM_EXTRACTION_PROMPT.format(
                doc_type=doc_type.value,
                source_path=source_path or "unknown",
            ) + f"\n\n--- DOCUMENT TEXT ---\n{truncated}"

            result = self.llm.extract_structured(
                system_prompt="You extract mortgage underwriting fields. Respond with JSON only.",
                user_prompt=user_prompt,
                response_model=LLMExtractionResult,
            )
            if isinstance(result, LLMExtractionResult):
                return result
            return None
        except Exception as exc:
            logger.warning("LLM extraction failed for %s: %s", source_path, exc)
            return None

    def merge_fields(
        self,
        regex_fields: dict[str, list[ExtractedMortgageField]],
        llm_result: LLMExtractionResult | None,
    ) -> dict[str, list[ExtractedMortgageField]]:
        if not llm_result:
            return regex_fields

        merged = {k: list(v) for k, v in regex_fields.items()}

        for lf in llm_result.fields:
            if not lf.value.strip():
                continue
            existing = merged.get(lf.field_name, [])
            if not existing:
                merged[lf.field_name] = [
                    ExtractedMortgageField(
                        field_name=lf.field_name,
                        value=lf.value,
                        confidence=lf.confidence,
                        context=f"LLM: {lf.context}" if lf.context else "LLM extraction",
                    )
                ]
            elif existing[0].confidence < lf.confidence:
                merged[lf.field_name] = [
                    ExtractedMortgageField(
                        field_name=lf.field_name,
                        value=lf.value,
                        confidence=lf.confidence,
                        context=f"LLM override: {lf.context}",
                    )
                ]

        if llm_result.borrower_name and "borrower_name" not in merged:
            merged["borrower_name"] = [
                ExtractedMortgageField(
                    field_name="borrower_name",
                    value=llm_result.borrower_name,
                    confidence=0.8,
                    context="LLM borrower identification",
                )
            ]

        for note in llm_result.handwritten_notes_detected:
            merged.setdefault("handwritten_notes", []).append(
                ExtractedMortgageField(
                    field_name="handwritten_notes",
                    value=note,
                    confidence=0.7,
                    context="LLM detected annotation",
                )
            )

        return merged
