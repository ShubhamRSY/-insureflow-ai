from __future__ import annotations

import re

from insureflow.ingestion.insurance.value_normalizers import normalize_field
from insureflow.models.submissions import ExtractedField


def _field(name: str, value: str, confidence: float = 0.85) -> list[ExtractedField]:
    if not value or not str(value).strip():
        return []
    return [ExtractedField(field_name=name, value=normalize_field(name, str(value).strip()), confidence=confidence)]


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


def extract_sov(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    tiv_match = re.search(r"(?:TOTAL|TOTAL INSURABLE VALUE|Total Insurable Value)[^$]*?\$([\d,]+)", text, re.IGNORECASE)
    if tiv_match and tiv_match.group(1):
        fields["total_insurable_value"] = _field("total_insurable_value", tiv_match.group(1))
    building_match = re.search(r"Buildings?[^$]*?\$([\d,]+)", text, re.IGNORECASE)
    if building_match and building_match.group(1):
        fields["building_value"] = _field("building_value", building_match.group(1))
    bpp_match = re.search(r"(?:Business Personal Property|BPP)[^$]*?\$([\d,]+)", text, re.IGNORECASE)
    if bpp_match and bpp_match.group(1):
        fields["bpp_value"] = _field("bpp_value", bpp_match.group(1))
    return fields


# ── Life insurance structured extraction ────────────────────────────────
_AMOUNT = r"([\d,]+(?:\.\d{2})?)"
_PERSON = r"([A-Za-z][A-Za-z .'-]+)"
_YN = r"([Yy]es|[Nn]o|[Nn]one|Non-?\s?smoker|Smoker|Light|Heavy)"
_LABEL_VALUE = r"^{}(?:\s*:\s*|\s{2,}|\s\-\s|\s)\s*(.+)$"


def _label_value(text: str, label: str) -> str | None:
    for pattern in (label, label.lower(), label.upper()):
        m = re.search(_LABEL_VALUE.format(re.escape(pattern)), text, re.MULTILINE)
        if m and m.group(1).strip():
            return m.group(1).strip().rstrip(".")
    return None


def extract_life_application(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "insured_name": r"(?:Proposed Insured|Primary Insured|Proposed Insured Name|Insured Name|Insured|Applicant|Owner)[:\s]+" + _PERSON,
        "dob": r"(?:Date of Birth|DOB|Birth Date|Birthdate)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        "insured_sex": r"(?:Sex|Gender)[:\s]+([MFmf]|[Mm]ale|[Ff]emale)",
        "smoker_status": r"(?:Smoker|Tobacco Use|Tobacco|Cigarette Use)[:\s]+" + _YN,
        "face_amount": r"(?:Face Amount|Death Benefit|Amount of Insurance|Coverage Amount|Amount Requested)[:\s$]+" + _AMOUNT,
        "premium": r"(?:Annual Premium|Annualized Premium|Mode Premium|Monthly Premium|Total Premium|Premium)[:\s$]+" + _AMOUNT,
        "beneficiary": r"(?:Primary Beneficiary|Contingent Beneficiary|Beneficiary)[:\s]+" + _PERSON,
        "beneficiary_relationship": r"(?:Relationship to Insured|Relationship)[:\s]+" + _PERSON,
        "premium_mode": r"(?:Premium Mode|Mode of Premium|Billing Mode)[:\s]+([A-Za-z-]+)",
        "policy_number": r"(?:Policy Number|Policy No\.?|Policy#)[:\s]+([A-Z0-9-]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1))
    return fields


def extract_beneficiary_form(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "beneficiary_name": r"(?:Primary Beneficiary|Contingent Beneficiary|Beneficiary Name|Beneficiary)[:\s]+([A-Z][a-zA-Z']+(?:[ \t]+[A-Z][a-zA-Z']+)+)",
        "beneficiary_relationship": r"(?:Relationship|Relationship to Insured)[:\s]+" + _PERSON,
        "allocation_percent": r"(?:Allocation|Share|Percentage|Percent|Interest)[:\s]*([\d.]+)\s*%",
        "insured_name": r"(?:Insured|Policy Owner|Owner)[:\s]+" + _PERSON,
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1))
    return fields


def extract_health_questionnaire(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "height": r"Height[:\s]*([^,\n;]{2,25})",
        "weight": r"Weight[:\s]*([\d]{2,4})\s*(?:lbs?\.?|pounds?|kg|kgs)?",
        "smoker_status": r"(?:Smoker|Tobacco Use|Tobacco|Cigarette Use)[:\s]+" + _YN,
        "blood_pressure": r"Blood\s*Pressure[:\s]*(\d{2,3}\s*/\s*\d{2,3})",
        "existing_conditions": r"(?:Health Conditions?|Medical Conditions?|Existing Conditions?|Conditions?)[:\s]+([^\n]{3,120})",
        "medications": r"(?:Current Medications?|Medications?|Prescription Medications?)[:\s]+([^\n]{3,120})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1).strip())
    return fields


def extract_medical_exam(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "height": r"Height[:\s]*([^,\n;]{2,25})",
        "weight": r"Weight[:\s]*([\d]{2,4})\s*(?:lbs?\.?|pounds?|kg|kgs)?",
        "blood_pressure": r"Blood\s*Pressure[:\s]*(\d{2,3}\s*/\s*\d{2,3})",
        "pulse": r"(?:Pulse|Resting Pulse|Heart Rate)[:\s]*([\d]{2,3})",
        "smoker_status": r"(?:Smoker|Tobacco Use|Tobacco)[:\s]+" + _YN,
        "insured_name": r"(?:Examinee|Insured|Patient|Applicant)[:\s]+" + _PERSON,
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1).strip())
    return fields


def extract_income_proof(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "income_amount": r"(?:Annual Income|Gross Income|Net Income|Total Income|Income|Salary)[:\s$]+" + _AMOUNT,
        "income_frequency": r"(?:per year|per annum|annual|yearly|monthly|bi-weekly|weekly)",
        "employer": r"(?:Employer|Company|Employed by|Current Employer)[:\s]+([^\n]{2,80})",
        "insured_name": r"(?:Employee|Applicant|Insured)[:\s]+" + _PERSON,
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if key == "income_frequency" and match:
            fields[key] = _field(key, match.group(0))
        elif match and match.group(1):
            fields[key] = _field(key, match.group(1))
    return fields


def extract_identity_doc(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "full_name": r"(?:Name|Full Name|Legal Name|Applicant Name|Insured Name)[:\s]+" + _PERSON,
        "dob": r"(?:Date of Birth|DOB|Birth Date)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1))
    address = re.search(r"(?:Address|Current Address)[:\s]+([^\n]{3,80})", text, re.IGNORECASE)
    if address:
        fields["address"] = _field("address", address.group(1))
    return fields


def extract_source_of_funds(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "funding_amount": r"(?:Source of Funds Amount|Lump Sum|Funding Amount|Premium Amount|Deposit)[:\s$]+" + _AMOUNT,
        "funding_source": r"(?:Source of Funds|Funding Source|Source|Proceeds From)[:\s]+([^\n]{2,80})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1))
    return fields


def extract_mortgage_statement(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "outstanding_balance": r"(?:Outstanding Balance|Principal Balance|Loan Balance|Balance Due)[:\s$]+" + _AMOUNT,
        "lender": r"(?:Lender|Mortgage Company|Servicer|Mortgagee)[:\s]+([^\n]{2,80})",
        "account_number": r"(?:Loan Number|Account Number|Account#)[:\s]*([A-Z0-9-]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1))
    return fields


def extract_retirement_account_statement(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "account_value": r"(?:Account Value|Total Value|Balance|Market Value)[:\s$]+" + _AMOUNT,
        "custodian": r"(?:Custodian|Institution|Financial Institution|Company)[:\s]+([^\n]{2,80})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1))
    return fields


def extract_premium_waiver_rider(text: str) -> dict[str, list[ExtractedField]]:
    fields: dict[str, list[ExtractedField]] = {}
    patterns = {
        "rider_benefit": r"(?:Rider Benefit|Waiver Amount|Benefit Amount|Monthly Benefit)[:\s$]+" + _AMOUNT,
        "rider_type": r"(?:Rider Type|Type of Rider)[:\s]+([^\n]{2,60})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            fields[key] = _field(key, match.group(1))
    return fields


EXTRACTORS = {
    "broker_slip": extract_broker_slip,
    "dec_page": extract_dec_page,
    "loss_run": extract_loss_run_pdf,
    "schedule_of_values": extract_sov,
    # Life
    "life_application": extract_life_application,
    "beneficiary_form": extract_beneficiary_form,
    "health_questionnaire": extract_health_questionnaire,
    "income_proof": extract_income_proof,
    "medical_exam": extract_medical_exam,
    "photo_id": extract_identity_doc,
    "proof_of_address": extract_identity_doc,
    "social_security_number": extract_identity_doc,
    "source_of_funds": extract_source_of_funds,
    "mortgage_statement": extract_mortgage_statement,
    "retirement_account_statement": extract_retirement_account_statement,
    "premium_waiver_rider": extract_premium_waiver_rider,
}


def extract_fields(doc_type: str, text: str) -> dict[str, list[ExtractedField]]:
    fn = EXTRACTORS.get(doc_type)
    return fn(text) if fn else {}
