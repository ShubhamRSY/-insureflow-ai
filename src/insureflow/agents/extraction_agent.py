from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional, cast

from pydantic import BaseModel, Field

from insureflow.ingestion.acord_parser import ACORDParser
from insureflow.ingestion.insurance.classifier import LIFE_DOCUMENT_TYPES
from insureflow.ingestion.insurance.value_normalizers import normalize_field
from insureflow.ingestion.report_extractor import InspectionReportExtractor
from insureflow.llm.client import LLMClient
from insureflow.llm.prompts import EXTRACTION_PROMPT, LIFE_EXTRACTION_PROMPT
from insureflow.models.submissions import StructuredSubmission, SubmissionBundle, UnstructuredSubmission
from insureflow.redaction.pipeline import RedactedLLMClient
from insureflow.redaction.redactor import PIIRedactor

logger = logging.getLogger(__name__)

# Process-local cache: identical (schema, prompt, document text) always yields
# the same extracted fields, so re-processing the same document within one
# server process doesn't take a fresh, potentially different sample from the
# model each time. Unbounded is fine here — keyed by content hash, so it only
# grows with the number of *distinct* documents seen, not the number of runs.
_EXTRACTION_CACHE: dict[str, dict[str, Any]] = {}


def _extraction_cache_key(schema_name: str, prompt: str, text: str) -> str:
    digest = hashlib.sha256(f"{schema_name}\x00{prompt}\x00{text}".encode("utf-8")).hexdigest()
    return digest


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


class LifeExtractionSchema(BaseModel):
    """Structured-output schema for the LLM extraction of life documents."""

    insured_name: Optional[str] = None
    dob: Optional[str] = None
    insured_sex: Optional[str] = None
    smoker_status: Optional[str] = None
    face_amount: Optional[float] = None
    premium: Optional[float] = None
    premium_mode: Optional[str] = None
    policy_number: Optional[str] = None
    beneficiary_name: Optional[str] = None
    beneficiary_relationship: Optional[str] = None
    allocation_percent: Optional[float] = None
    height: Optional[str] = None
    weight: Optional[float] = None
    blood_pressure: Optional[str] = None
    pulse: Optional[int] = None
    existing_conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    income_amount: Optional[float] = None
    income_frequency: Optional[str] = None
    employer: Optional[str] = None
    occupation: Optional[str] = None
    full_name: Optional[str] = None
    address: Optional[str] = None
    funding_amount: Optional[float] = None
    funding_source: Optional[str] = None
    outstanding_balance: Optional[float] = None
    account_value: Optional[float] = None
    rider_benefit: Optional[float] = None
    rider_type: Optional[str] = None


class CommercialExtractionSchema(BaseModel):
    """Structured-output schema for the LLM extraction of commercial documents."""

    construction_type: Optional[str] = None
    year_built: Optional[int] = None
    square_footage: Optional[float] = None
    number_of_stories: Optional[int] = None
    occupancy_type: Optional[str] = None
    sprinklered: Optional[bool] = None
    protection_class: Optional[int] = None
    roof_type: Optional[str] = None
    security_features: Optional[str] = None
    overall_condition: Optional[str] = None
    prior_claims: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


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
        needs it. The completion is coerced through a Pydantic schema so the
        model's free-form answer is parsed into canonical, type-safe keys.

        Results are cached by (schema, prompt, document text) hash so that
        re-processing the same document — e.g. re-running a demo preset, or
        two documents in the bundle with identical text — returns the exact
        same extracted fields instead of a fresh, potentially different
        sample from the model.
        """
        if not self.llm.api_key:
            return submission
        raw_text = submission.raw_text or ""
        text_for_llm = self.redactor.redact(raw_text[:8000]) if self.redactor else raw_text[:8000]
        is_life = submission.document_type in LIFE_DOCUMENT_TYPES
        prompt = LIFE_EXTRACTION_PROMPT if is_life else EXTRACTION_PROMPT
        schema = LifeExtractionSchema if is_life else CommercialExtractionSchema

        cache_key = _extraction_cache_key(schema.__name__, prompt, text_for_llm)
        cached = _EXTRACTION_CACHE.get(cache_key)
        if cached is not None:
            self._merge_llm_results(submission, cached)
            return submission

        try:
            llm_result = self.llm.complete(prompt, text_for_llm, response_format=schema)
        except Exception as exc:
            logger.warning(
                "LLM extraction failed for document_type=%s (%s: %s) — falling back to deterministic regex extraction only",
                submission.document_type,
                type(exc).__name__,
                exc,
            )
            return submission

        parsed = self._parse_json_response(llm_result)
        if parsed is None:
            logger.warning("LLM extraction returned unparseable JSON for document_type=%s", submission.document_type)
            return submission

        try:
            instance = cast(Any, schema).model_validate(parsed)
        except Exception as exc:
            logger.warning("LLM extraction result failed schema validation for document_type=%s: %s", submission.document_type, exc)
            return submission

        llm_fields = self._schema_to_llm_fields(instance)
        _EXTRACTION_CACHE[cache_key] = llm_fields
        self._merge_llm_results(submission, llm_fields)
        return submission

    @staticmethod
    def _parse_json_response(raw: str) -> Any:
        """Parse an LLM JSON answer, tolerating markdown code fences."""
        import json

        clean_raw = raw.strip()
        if clean_raw.startswith("```json"):
            clean_raw = clean_raw[7:]
        if clean_raw.startswith("```"):
            clean_raw = clean_raw[3:]
        if clean_raw.endswith("```"):
            clean_raw = clean_raw[:-3]
        try:
            return json.loads(clean_raw.strip())
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def _schema_to_llm_fields(instance: BaseModel) -> dict[str, Any]:
        """Flatten a schema instance into canonical extracted field values."""
        out: dict[str, Any] = {}
        for name, value in instance.model_dump().items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                if not value:
                    continue
                value = "; ".join(str(v) for v in value)
            elif isinstance(value, bool):
                value = "yes" if value else "no"
            out[name] = value
        return out

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
                    value=normalize_field(key, str_val),
                    confidence=LLM_MERGE_CONFIDENCE,
                    context="llm_extraction",
                )
            )

    def process_bundle(self, bundle: SubmissionBundle) -> SubmissionBundle:
        self.redact_bundle(bundle)
        return bundle
