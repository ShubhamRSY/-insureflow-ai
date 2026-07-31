from __future__ import annotations

from insureflow.ingestion.mortgage.loader import MortgageDocumentParser
from insureflow.mortgage.privacy import mask_ssn_value, sanitize_document, sanitize_extracted_fields
from insureflow.models.mortgage import ExtractedMortgageField, MortgageDocument, MortgageDocumentType, ProductLine
from insureflow.redaction.detector import PIICategory, PIIDetector
from insureflow.redaction.pipeline import RedactedLLMClient
from insureflow.redaction.redactor import PIIRedactor


def test_mask_ssn_last4() -> None:
    assert mask_ssn_value("312-55-8891") == "***-**-8891"
    assert "***-**-8891" in mask_ssn_value("SSN: 312-55-8891")


def test_sanitize_extracted_ssn_field() -> None:
    fields = {
        "ssn": [ExtractedMortgageField(field_name="ssn", value="312-55-8891", confidence=0.9)],
        "full_name": [ExtractedMortgageField(field_name="full_name", value="Marcus Johnson", confidence=0.9)],
    }
    out = sanitize_extracted_fields(fields)
    assert out["ssn"][0].value == "***-**-8891"
    assert "312-55-8891" not in out["ssn"][0].value


def test_sanitize_document_redacts_raw_text() -> None:
    doc = MortgageDocument(
        document_id="d1",
        document_type=MortgageDocumentType.SSN_CARD,
        product_line=ProductLine.RESIDENTIAL_MORTGAGE,
        raw_text="SOCIAL SECURITY CARD\nSSN: 312-55-8891\nFull Name: Marcus",
        extracted_fields={
            "ssn": [ExtractedMortgageField(field_name="ssn", value="312-55-8891")],
        },
    )
    sanitize_document(doc)
    assert "312-55-8891" not in doc.raw_text
    assert doc.extracted_fields["ssn"][0].value == "***-**-8891"
    assert any(f.value == "pii_sanitized" for f in doc.extracted_fields.get("privacy", []))


def test_parser_applies_privacy_by_default() -> None:
    parser = MortgageDocumentParser(use_llm=False)
    doc = parser.parse(
        "SOCIAL SECURITY CARD\nFull Name: Marcus D. Johnson\nSSN: 312-55-8891\n",
        "doc-ssn",
        source_path="identity/ssn_card_marcus.txt",
    )
    assert doc.document_type == MortgageDocumentType.SSN_CARD
    assert "312-55-8891" not in doc.raw_text
    ssn_vals = [f.value for f in doc.extracted_fields.get("ssn", [])]
    assert ssn_vals
    assert all("312-55" not in v for v in ssn_vals)


def test_detector_passport_and_dl() -> None:
    detector = PIIDetector()
    text = "Passport Number: 550123456\nDocument Number: D1234567\nDate of Birth: 03/14/1988"
    cats = {s.category for s in detector.detect(text)}
    assert PIICategory.PASSPORT in cats or PIICategory.DRIVERS_LICENSE in cats
    redacted = PIIRedactor(detector).redact(text, mask=True)
    assert "550123456" not in redacted or "[REDACTED" in redacted


def test_mortgage_llm_uses_redacted_client() -> None:
    from insureflow.mortgage.llm_extractor import MortgageLLMExtractor

    extractor = MortgageLLMExtractor()
    assert isinstance(extractor.llm, RedactedLLMClient)
