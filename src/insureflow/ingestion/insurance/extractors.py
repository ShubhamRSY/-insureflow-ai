from __future__ import annotations

import re

from insureflow.models.submissions import ExtractedField


def _field(name: str, value: str, confidence: float = 0.85) -> list[ExtractedField]:
    if not value or not str(value).strip():
        return []
    return [ExtractedField(field_name=name, value=str(value).strip(), confidence=confidence)]


def extract_broker_slip(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "named_insured": r"(?:Named Insured|Applicant)[:\s]+([^\n]+)",
        "broker_name": r"(?:Broker|Agency)[:\s]+([^\n]+)",
        "effective_date": r"(?:Effective|Policy Period)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        "tiv": r"(?:TIV|Total Insured Value|Total Values?)[:\s$]+([\d,]+(?:\.\d{2})?)",
        "naics_code": r"NAICS[:\s]+(\d{6})",
        "occupancy": r"(?:Occupancy|Business Description)[:\s]+([^\n]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1))
    return fields


def extract_dec_page(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "policy_number": r"Policy (?:Number|No\.?)[:\s]+([A-Z0-9-]+)",
        "carrier": r"(?:Insurer|Carrier|Company)[:\s]+([^\n]+)",
        "premium": r"(?:Total Premium|Annual Premium)[:\s$]+([\d,]+(?:\.\d{2})?)",
        "effective_date": r"Effective[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        "expiration_date": r"Expir(?:ation|es)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1))
    return fields


def extract_loss_run_pdf(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    total_match = re.search(r"Total Incurred[:\s$]+([\d,]+(?:\.\d{2})?)", text, re.IGNORECASE)
    if total_match and total_match.group(1):
        fields["total_incurred"] = _field("total_incurred", total_match.group(1))
    claims = re.findall(r"Claim\s*#?\s*(\d+)", text, re.IGNORECASE)
    if claims:
        fields["claim_count"] = _field("claim_count", str(len(claims)))
    return fields


EXTRACTORS = {
    "broker_slip": extract_broker_slip,
    "dec_page": extract_dec_page,
    "loss_run": extract_loss_run_pdf,
}


def extract_fields(doc_type: str, text: str) -> dict[str, list[ExtractedField]]:
    fn = EXTRACTORS.get(doc_type)
    return fn(text) if fn else {}
