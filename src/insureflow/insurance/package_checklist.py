"""LOB-aware insurance package completeness (commercial property, D&O, personal lines)."""

from __future__ import annotations

from typing import Any, Iterable

from insureflow.ingestion.insurance.classifier import InsuranceDocumentType

PROPERTY_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("ACORD application (125 / 140)", (InsuranceDocumentType.ACORD_XML,)),
    ("Loss run (3–5 years)", (InsuranceDocumentType.LOSS_RUN,)),
    ("Schedule of values / COPE", (InsuranceDocumentType.SCHEDULE_OF_VALUES,)),
    ("Inspection / valuation report", (InsuranceDocumentType.INSPECTION_REPORT,)),
    ("Property photos", (InsuranceDocumentType.PROPERTY_PHOTOS,)),
    ("Broker slip / submission", (InsuranceDocumentType.BROKER_SLIP,)),
    ("Financial statements (2–3 years)", (InsuranceDocumentType.FINANCIAL_STATEMENT,)),
    ("Business interruption worksheet", ()),
    ("Equipment / machinery schedule", ()),
    ("Lease or title deed", ()),
    ("Flood / quake exposure cert", ()),
    ("Business continuity / DR plan", ()),
]

DO_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("D&O application", (InsuranceDocumentType.DO_APPLICATION, InsuranceDocumentType.ACORD_XML)),
    ("D&O questionnaire", (InsuranceDocumentType.DO_QUESTIONNAIRE,)),
    ("Financial statements / 10-K", (InsuranceDocumentType.FINANCIAL_STATEMENT, InsuranceDocumentType.DO_FINANCIALS_10K)),
    ("Bylaws / charter / operating agreement", (InsuranceDocumentType.DO_BYLAWS_CHARTER,)),
    ("Board / officer roster & bios", (InsuranceDocumentType.DO_BOARD_ROSTER,)),
    ("Org chart / cap table", (InsuranceDocumentType.DO_OWNERSHIP_CHART,)),
    ("Claims history / loss runs (D&O)", (InsuranceDocumentType.DO_CLAIMS_HISTORY, InsuranceDocumentType.LOSS_RUN)),
    ("Prior acts / prior policy dec page", (InsuranceDocumentType.DO_PRIOR_ACTS_WARRANTY, InsuranceDocumentType.DEC_PAGE)),
    ("Litigation / regulatory disclosures", ()),
    ("M&A / funding disclosures", ()),
]

WORKERS_COMP_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("ACORD 130 application", (InsuranceDocumentType.ACORD_XML,)),
    ("Loss run (3–5 years)", (InsuranceDocumentType.LOSS_RUN,)),
    ("Financial statements", (InsuranceDocumentType.FINANCIAL_STATEMENT,)),
    ("Payroll by NCCI class code", ()),
    ("Employee census (titles / states)", ()),
    ("Experience mod (e-mod) worksheet", ()),
    ("OSHA 300 / 300A logs", ()),
    ("Safety manual / written program", ()),
    ("Prior policy declarations", (InsuranceDocumentType.DEC_PAGE,)),
    ("Subcontractor usage + COIs", ()),
    ("Return-to-work program", ()),
]

TRADE_CREDIT_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("Trade credit application", (InsuranceDocumentType.TRADE_CREDIT_APPLICATION, InsuranceDocumentType.ACORD_XML)),
    ("AR aging report", (InsuranceDocumentType.AR_AGING_REPORT,)),
    ("Buyer / customer exposure list", (InsuranceDocumentType.BUYER_EXPOSURE_LIST,)),
    ("Bad debt / write-off history (3–5 years)", (InsuranceDocumentType.LOSS_RUN,)),
    ("Audited financial statements", (InsuranceDocumentType.FINANCIAL_STATEMENT,)),
    ("Credit management policy", ()),
    ("Domestic vs export sales split", ()),
    ("Top customer concentration report", ()),
    ("Prior credit policy + claims", (InsuranceDocumentType.DEC_PAGE,)),
    ("Terms of sale / payment terms", ()),
]

EO_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("E&O application (ACORD 126 / carrier)", (InsuranceDocumentType.EO_APPLICATION, InsuranceDocumentType.ACORD_XML)),
    ("Services / scope of operations", (InsuranceDocumentType.BROKER_SLIP,)),
    ("Revenue by service line", (InsuranceDocumentType.FINANCIAL_STATEMENT,)),
    ("Sample contracts / engagement letters", (InsuranceDocumentType.ENGAGEMENT_LETTER,)),
    ("Loss runs (3–5 years)", (InsuranceDocumentType.LOSS_RUN,)),
    ("Professional licenses / certifications", ()),
    ("QC / risk management procedures", ()),
    ("Subcontractor / vendor agreements", ()),
    ("Complaint / grievance history", ()),
    ("Prior E&O declarations", (InsuranceDocumentType.DEC_PAGE,)),
]

KEY_PERSON_CATALOG: list[tuple[str, tuple[InsuranceDocumentType, ...]]] = [
    ("Application + medical questionnaire", (InsuranceDocumentType.KEY_PERSON_APPLICATION, InsuranceDocumentType.LIFE_APPLICATION, InsuranceDocumentType.ACORD_XML)),
    ("Paramedical exam / medical records", (InsuranceDocumentType.MEDICAL_EXAM, InsuranceDocumentType.APS_RECORDS)),
    ("Financials attributable to key person", (InsuranceDocumentType.FINANCIAL_STATEMENT,)),
    ("Job description / coverage justification", ()),
    ("Corporate resolution authorizing purchase", (InsuranceDocumentType.CORPORATE_RESOLUTION,)),
    ("Buy-sell agreement (if applicable)", ()),
    ("Loan / collateral documents (if any)", ()),
    ("Beneficiary designation (usually company)", (InsuranceDocumentType.BENEFICIARY_FORM,)),
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
    "workers_comp": WORKERS_COMP_CATALOG,
    "trade_credit": TRADE_CREDIT_CATALOG,
    "eo": EO_CATALOG,
    "key_person": KEY_PERSON_CATALOG,
    "homeowners": HOME_CATALOG,
    "auto": AUTO_CATALOG,
    "life": LIFE_CATALOG,
}


def _has_any(present: set[str], types: Iterable[InsuranceDocumentType]) -> bool:
    if not types:
        return False
    return any(t.value in present for t in types)


def detect_lob(text_blob: str = "", product_hint: str = "") -> str:
    blob = f"{product_hint}\n{text_blob}".lower()
    hint = (product_hint or "").strip().lower()

    # Commercial packages (warehouse / SOV / CGL / fleet) → property checklist
    from insureflow.underwriting.personal_lines import _has_strong_commercial_signals

    commercial = _has_strong_commercial_signals(blob)

    # Exact / short LOB tokens — but never trust personal checklist hints
    # on a commercial package (wrong UI default / stale job metadata).
    if hint in {
        "life",
        "auto",
        "homeowners",
        "property",
        "do",
        "workers_comp",
        "trade_credit",
        "eo",
        "key_person",
        "property_bi",
        "errors_and_omissions",
        "directors_and_officers",
        "workers-comp",
        "trade-credit",
        "key-person",
    }:
        normalized = {
            "property_bi": "property",
            "errors_and_omissions": "eo",
            "directors_and_officers": "do",
            "workers-comp": "workers_comp",
            "trade-credit": "trade_credit",
            "key-person": "key_person",
        }.get(hint, hint)
        if commercial and normalized in {"life", "auto", "homeowners"}:
            return "property"
        return normalized

    # True D&O only — do NOT match "and observed" via "d and o"
    if any(
        k in blob
        for k in (
            "d&o",
            "directors and officers",
            "directors & officers",
            "management liability",
            "d and o liability",
            "d and o application",
        )
    ):
        return "do"

    if (
        any(
            k in blob
            for k in (
                "life insurance",
                "term life",
                "face amount",
                "beneficiary designation",
                "paramedical",
                "insurance_line: life",
                "insurance_line=life",
            )
        )
        and not commercial
    ):
        return "life"

    personal_auto = any(
        k in blob
        for k in (
            "personal auto",
            "auto application",
            "insurance_line: personal_auto",
            "insurance_line=personal_auto",
            "drivers license",
            "driver's license",
            "motor vehicle report",
            "mvr report",
            "rideshare",
        )
    )
    if personal_auto and not commercial:
        return "auto"

    if (
        any(
            k in blob
            for k in (
                "homeowners",
                "dwelling coverage",
                "ho-3",
                "personal homeowners",
                "clue report",
            )
        )
        and not commercial
    ):
        return "homeowners"

    property_heavy = any(
        k in blob
        for k in (
            "schedule of values",
            "commercial property",
            "building value",
            "warehouse",
            "total insurable value",
            "protection class",
            "acord 140",
        )
    )

    # Specialty checklist LOBs — never override a property/SOV package
    if not property_heavy:
        if any(k in blob for k in ("workers compensation", "workers' compensation", "workers_comp", "acord 130", "experience mod", "ncci")):
            return "workers_comp"
        if any(k in blob for k in ("trade credit", "accounts receivable aging", "buyer credit", "credit insurance")):
            return "trade_credit"
        if any(k in blob for k in ("errors and omissions", "errors & omissions", "e&o application", "professional liability", "acord 126")):
            return "eo"
        if any(k in blob for k in ("key person", "key-person", "keyman insurance", "key man insurance")):
            return "key_person"

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
