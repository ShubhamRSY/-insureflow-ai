"""LOB-aware insurance package completeness (commercial property, D&O, personal lines)."""

from __future__ import annotations

from typing import Any, Iterable

from insureflow.ingestion.insurance.classifier import InsuranceDocumentType

PROPERTY_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("ACORD application", (InsuranceDocumentType.ACORD_XML,)),
    ("Loss run", (InsuranceDocumentType.LOSS_RUN,)),
    ("Schedule of values", (InsuranceDocumentType.SCHEDULE_OF_VALUES,)),
    ("Inspection report", (InsuranceDocumentType.INSPECTION_REPORT,)),
    ("Broker slip / submission", (InsuranceDocumentType.BROKER_SLIP,)),
    ("Financial statement", (InsuranceDocumentType.FINANCIAL_STATEMENT,)),
]

DO_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("D&O application", (InsuranceDocumentType.DO_APPLICATION, InsuranceDocumentType.ACORD_XML)),
    ("D&O questionnaire", (InsuranceDocumentType.DO_QUESTIONNAIRE,)),
    ("Financial statements / 10-K", (InsuranceDocumentType.FINANCIAL_STATEMENT, InsuranceDocumentType.DO_FINANCIALS_10K)),
    ("Bylaws / charter", (InsuranceDocumentType.DO_BYLAWS_CHARTER,)),
    ("Board / D&O roster", (InsuranceDocumentType.DO_BOARD_ROSTER,)),
    ("Ownership chart", (InsuranceDocumentType.DO_OWNERSHIP_CHART,)),
    ("Claims history (D&O)", (InsuranceDocumentType.DO_CLAIMS_HISTORY, InsuranceDocumentType.LOSS_RUN)),
    ("Prior acts warranty", (InsuranceDocumentType.DO_PRIOR_ACTS_WARRANTY,)),
]

HOME_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("Homeowners application", (InsuranceDocumentType.HOMEOWNERS_APPLICATION, InsuranceDocumentType.ACORD_XML)),
    ("Dwelling inspection", (InsuranceDocumentType.DWELLING_INSPECTION, InsuranceDocumentType.INSPECTION_REPORT)),
    ("Claims history / CLUE", (InsuranceDocumentType.HOME_CLAIMS_HISTORY, InsuranceDocumentType.LOSS_RUN)),
    ("Declarations / prior policy", (InsuranceDocumentType.DEC_PAGE,)),
]

AUTO_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("Auto application", (InsuranceDocumentType.AUTO_APPLICATION, InsuranceDocumentType.ACORD_XML)),
    ("MVR / driving record", (InsuranceDocumentType.MVR_REPORT,)),
    ("Vehicle declarations", (InsuranceDocumentType.VEHICLE_DECLARATIONS, InsuranceDocumentType.DEC_PAGE)),
    ("Claims / loss history", (InsuranceDocumentType.LOSS_RUN, InsuranceDocumentType.HOME_CLAIMS_HISTORY)),
]

LIFE_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("Life application", (InsuranceDocumentType.LIFE_APPLICATION,)),
    ("Medical / paramedical exam", (InsuranceDocumentType.MEDICAL_EXAM,)),
    ("APS / medical records", (InsuranceDocumentType.APS_RECORDS,)),
    ("Beneficiary designation", (InsuranceDocumentType.BENEFICIARY_FORM,)),
]

CATALOGS: dict[str, list[tuple[str, tuple[InsuranceDocumentType, ...]]]] = {
    "property": PROPERTY_CATALOG,
    "do": DO_CATALOG,
    "homeowners": HOME_CATALOG,
    "auto": AUTO_CATALOG,
    "life": LIFE_CATALOG,
}


def _has_any(present: set[str], types: Iterable[InsuranceDocumentType]) -> bool:
    return any(t.value in present for t in types)


def detect_lob(text_blob: str = "", product_hint: str = "") -> str:
    blob = f"{product_hint}\n{text_blob}".lower()
    if any(k in blob for k in ("d&o", "d and o", "directors and officers", "directors & officers", "management liability")):
        return "do"
    if any(k in blob for k in ("life insurance", "term life", "face amount", "beneficiary", "paramedical")):
        return "life"
    if any(k in blob for k in ("personal auto", "mvr", "motor vehicle", "vin:", "rideshare", "drivers license")):
        return "auto"
    if any(k in blob for k in ("homeowners", "dwelling coverage", "ho-3", "personal homeowners", "clue report")):
        return "homeowners"
    return "property"


def package_checklist(
    document_types: list[str],
    *,
    lob: str = "property",
) -> dict[str, Any]:
    present_types = {str(t).lower() for t in document_types}
    catalog = CATALOGS.get(lob, PROPERTY_CATALOG)
    present: list[str] = []
    missing: list[str] = []
    for label, types in catalog:
        if _has_any(present_types, types):
            present.append(label)
        else:
            missing.append(label)
    total = len(catalog) or 1
    return {
        "lob": lob,
        "present": present,
        "missing": missing,
        "completeness_pct": round(100.0 * len(present) / total, 1),
        "can_request_from_broker": len(missing) > 0,
    }
