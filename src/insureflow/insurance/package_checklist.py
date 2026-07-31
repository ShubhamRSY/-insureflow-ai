"""LOB-aware insurance package completeness (property + D&O)."""

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


def _has_any(present: set[str], types: Iterable[InsuranceDocumentType]) -> bool:
    return any(t.value in present for t in types)


def detect_lob(text_blob: str = "", product_hint: str = "") -> str:
    blob = f"{product_hint}\n{text_blob}".lower()
    if any(k in blob for k in ("d&o", "d and o", "directors and officers", "directors & officers", "management liability")):
        return "do"
    return "property"


def package_checklist(
    document_types: list[str],
    *,
    lob: str = "property",
) -> dict[str, Any]:
    present_types = {str(t).lower() for t in document_types}
    catalog = DO_CATALOG if lob == "do" else PROPERTY_CATALOG
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
