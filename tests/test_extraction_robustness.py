"""Tests for the extraction robustness features:

- value normalization (canonical number/date/yes-no forms)
- structured-output LLM extraction schemas
- extraction validation pass (allocations, ranges, conflicts, DOB sanity)
"""

from __future__ import annotations

from insureflow.agents.extraction_agent import (
    CommercialExtractionSchema,
    ExtractionAgent,
    LifeExtractionSchema,
)
from insureflow.ingestion.insurance.validation import severity_counts, validate_extraction
from insureflow.ingestion.insurance.value_normalizers import (
    normalize_amount,
    normalize_date,
    normalize_field,
    normalize_percent,
    normalize_yesno,
)
from insureflow.models.submissions import ExtractedField, SubmissionBundle, UnstructuredSubmission

# ── value normalization ──────────────────────────────────────────────────────


def test_normalize_amount_collapses_common_forms() -> None:
    assert normalize_amount("750,000") == "750000"
    assert normalize_amount("$4,350") == "4350"
    assert normalize_amount("1.2M") == "1200000"
    assert normalize_amount("$1.2M") == "1200000"
    assert normalize_amount("4.35 million") == "4350000"
    assert normalize_amount("2bn") == "2000000000"
    assert normalize_amount("100") == "100"
    assert normalize_amount("1,234.50") == "1234.5"


def test_normalize_amount_preserves_unparseable_text() -> None:
    assert normalize_amount("per year") == "per year"
    assert normalize_amount("Lump sum rollover") == "Lump sum rollover"
    assert normalize_amount("") == ""


def test_normalize_percent_and_yesno_and_date() -> None:
    assert normalize_percent("100%") == "100"
    assert normalize_percent("85.5 %") == "85.5"
    assert normalize_yesno("No") == "no"
    assert normalize_yesno("Y") == "yes"
    assert normalize_yesno("Non-smoker") == "non-smoker"
    assert normalize_date("03/14/1985") == "1985-03-14"
    assert normalize_date("Mar 14, 1985") == "1985-03-14"
    assert normalize_date("1985-03-14") == "1985-03-14"


def test_normalize_field_dispatches_by_field_name() -> None:
    assert normalize_field("face_amount", "$750K") == "750000"
    assert normalize_field("premium", "4,350") == "4350"
    assert normalize_field("dob", "03/14/1985") == "1985-03-14"
    assert normalize_field("allocation_percent", "100%") == "100"
    assert normalize_field("smoker_status", "No") == "no"
    assert normalize_field("pulse", "68") == "68"
    assert normalize_field("naics_code", "493120") == "493120"
    assert normalize_field("insured_name", " John Q. Public ") == "John Q. Public"


# ── structured-output schemas ────────────────────────────────────────────────


def test_life_extraction_schema_coerces_loose_json() -> None:
    instance = LifeExtractionSchema.model_validate(
        {
            "insured_name": "John Q. Public",
            "dob": "03/14/1985",
            "face_amount": "750000",
            "smoker_status": "No",
            "existing_conditions": ["hypertension"],
            "medications": ["Lisinopril"],
        }
    )
    assert instance.face_amount == 750000.0
    assert instance.dob == "03/14/1985"
    assert instance.existing_conditions == ["hypertension"]


def test_commercial_extraction_schema_rejects_wrong_types() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CommercialExtractionSchema.model_validate({"year_built": "not-a-number", "sprinklered": "maybe"})

    instance = CommercialExtractionSchema.model_validate({"year_built": "1999", "sprinklered": "true", "square_footage": "125000"})
    assert instance.year_built == 1999
    assert instance.sprinklered is True
    assert instance.square_footage == 125000.0


def test_schema_to_llm_fields_joins_lists_and_bools() -> None:
    agent = ExtractionAgent()
    instance = LifeExtractionSchema.model_validate({"face_amount": 750000, "smoker_status": "no", "existing_conditions": ["a", "b"], "medications": []})
    fields = agent._schema_to_llm_fields(instance)
    assert fields["face_amount"] == 750000.0
    assert fields["smoker_status"] == "no"
    assert fields["existing_conditions"] == "a; b"
    assert "medications" not in fields


def test_parse_json_response_tolerates_fences() -> None:
    agent = ExtractionAgent()
    assert agent._parse_json_response('```json\n{"face_amount": 750000}\n```') == {"face_amount": 750000}
    assert agent._parse_json_response('{"face_amount": 750000}') == {"face_amount": 750000}
    assert agent._parse_json_response("not json at all") is None


# ── extraction validation pass ───────────────────────────────────────────────


def _bundle_with(*docs: tuple[str, dict[str, list[ExtractedField]]]) -> SubmissionBundle:
    unstructured = [
        UnstructuredSubmission(
            submission_id=f"doc-{i}",
            source="test_loader",
            document_type=doc_type,
            raw_text="",
            extracted_fields=fields,
        )
        for i, (doc_type, fields) in enumerate(docs)
    ]
    return SubmissionBundle(bundle_id="validate-test", unstructured=unstructured)


def _ef(name: str, value: str) -> dict[str, list[ExtractedField]]:
    return {name: [ExtractedField(field_name=name, value=value, confidence=0.9)]}


def test_validate_allocation_sum_over_100_is_error() -> None:
    bundle = _bundle_with(
        ("beneficiary_form", _ef("allocation_percent", "60")),
        ("beneficiary_form", _ef("allocation_percent", "50")),
    )
    issues = validate_extraction(bundle)
    assert any(i["issue"] == "allocation_sum_exceeds_100" and i["severity"] == "error" for i in issues)


def test_validate_negative_face_amount_is_error() -> None:
    bundle = _bundle_with(("life_application", _ef("face_amount", "-1000")))
    issues = validate_extraction(bundle)
    assert any(i["issue"] == "non_positive_value" and i["field"] == "face_amount" for i in issues)


def test_validate_conflicting_insured_name_is_warning() -> None:
    bundle = _bundle_with(
        ("life_application", _ef("insured_name", "John Q. Public")),
        ("medical_exam", _ef("insured_name", "Jane Public")),
    )
    issues = validate_extraction(bundle)
    assert any(i["issue"] == "conflicting_values" and i["field"] == "insured_name" for i in issues)


def test_validate_future_dob_is_error() -> None:
    bundle = _bundle_with(("life_application", _ef("dob", "01/01/2099")))
    issues = validate_extraction(bundle)
    assert any(i["issue"] == "future_date" and i["field"] == "dob" for i in issues)


def test_validate_clean_bundle_produces_no_errors() -> None:
    bundle = _bundle_with(
        ("life_application", {**_ef("insured_name", "John Q. Public"), **_ef("face_amount", "750000"), **_ef("dob", "1985-03-14")}),
        ("beneficiary_form", _ef("allocation_percent", "100")),
    )
    issues = validate_extraction(bundle)
    counts = severity_counts(issues)
    assert counts["error"] == 0
    assert not any(i["field"] == "insured_name" and i["issue"] == "conflicting_values" for i in issues)


def test_severity_counts_buckets_by_severity() -> None:
    bundle = _bundle_with(
        ("life_application", _ef("face_amount", "-100")),
        ("beneficiary_form", _ef("allocation_percent", "45")),
        ("beneficiary_form", _ef("allocation_percent", "45")),
    )
    counts = severity_counts(validate_extraction(bundle))
    assert counts["error"] == 1
    assert counts["warning"] >= 1
