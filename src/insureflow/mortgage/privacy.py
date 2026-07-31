"""Mortgage PII controls: redact before LLM egress; mask sensitive stored fields."""

from __future__ import annotations

import re

from insureflow.models.mortgage import ExtractedMortgageField, MortgageBundle, MortgageDocument
from insureflow.redaction.redactor import PIIRedactor

_SSN_RE = re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b")
_SENSITIVE_FIELD_KEYS = {
    "ssn",
    "social_security",
    "social_security_number",
    "document_number",
    "passport_number",
    "alien_number",
    "account_number",
    "routing_number",
    "bank_account",
    "card_number",
}


def mask_ssn_value(value: str) -> str:
    """Keep last-4 only for SSN-shaped values."""
    m = _SSN_RE.fullmatch(value.strip())
    if m:
        return f"***-**-{m.group(3)}"
    m = _SSN_RE.search(value)
    if m:
        return _SSN_RE.sub(lambda match: f"***-**-{match.group(3)}", value)
    digits = re.sub(r"\D", "", value)
    if len(digits) == 9:
        return f"***-**-{digits[-4:]}"
    return value


def sanitize_field_value(field_name: str, value: str, redactor: PIIRedactor | None = None) -> str:
    key = field_name.lower().replace(" ", "_")
    redactor = redactor or PIIRedactor()
    if key in _SENSITIVE_FIELD_KEYS or key.endswith("_ssn") or "ssn" in key:
        masked = mask_ssn_value(value)
        if masked != value:
            return masked
        # Non-SSN ID numbers → keep last 4 only when long enough
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 6:
            return f"***{digits[-4:]}"
        return redactor.redact(value, mask=True)
    return redactor.redact(value, mask=True)


def sanitize_extracted_fields(
    fields: dict[str, list[ExtractedMortgageField]],
    redactor: PIIRedactor | None = None,
) -> dict[str, list[ExtractedMortgageField]]:
    redactor = redactor or PIIRedactor()
    out: dict[str, list[ExtractedMortgageField]] = {}
    for key, items in fields.items():
        sanitized: list[ExtractedMortgageField] = []
        for item in items:
            sanitized.append(
                item.model_copy(
                    update={
                        "value": sanitize_field_value(item.field_name or key, item.value, redactor),
                        "context": redactor.redact(item.context, mask=True) if item.context else item.context,
                    }
                )
            )
        out[key] = sanitized
    return out


def sanitize_document(doc: MortgageDocument, *, redact_raw_text: bool = True) -> MortgageDocument:
    """Mask sensitive extracted fields and optionally redact raw_text for storage/LLM follow-ups."""
    redactor = PIIRedactor()
    doc.extracted_fields = sanitize_extracted_fields(doc.extracted_fields, redactor)
    if redact_raw_text and doc.raw_text:
        doc.raw_text = redactor.redact(doc.raw_text, mask=True)
    doc.extracted_fields.setdefault("privacy", []).append(
        ExtractedMortgageField(
            field_name="privacy",
            value="pii_sanitized",
            confidence=1.0,
            context="SSN/account/ID masked; raw_text redacted for storage",
        )
    )
    return doc


def sanitize_bundle(bundle: MortgageBundle, *, redact_raw_text: bool = True) -> MortgageBundle:
    for doc in bundle.documents:
        sanitize_document(doc, redact_raw_text=redact_raw_text)
    if bundle.borrowers:
        for b in bundle.borrowers:
            if b.ssn_last4 and len(b.ssn_last4) > 4:
                b.ssn_last4 = b.ssn_last4[-4:]
    return bundle
