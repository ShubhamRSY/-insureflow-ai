"""LOB-aware insurance package completeness (commercial + personal lines).

Commercial catalogs are generated from `commercial_lobs` (product + coverage docs)
to avoid drift. Personal lines keep explicit catalog entries.
"""

from __future__ import annotations

from typing import Any, Iterable

from insureflow.ingestion.insurance.classifier import InsuranceDocumentType

# ---------------------------------------------------------------------------
# Personal lines catalogs (explicit — not derived from commercial_lobs)
# ---------------------------------------------------------------------------

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

PERSONAL_CATALOGS: dict[str, list[tuple[str, tuple[InsuranceDocumentType, ...]]]] = {
    "homeowners": HOME_CATALOG,
    "auto": AUTO_CATALOG,
    "life": LIFE_CATALOG,
}


def _types_for_label(label: str) -> tuple[InsuranceDocumentType, ...]:
    """Heuristic InsuranceDocumentType matching from document label keywords."""
    text = (label or "").lower()
    types: list[InsuranceDocumentType] = []

    def add(t: InsuranceDocumentType) -> None:
        if t not in types:
            types.append(t)

    if "loss run" in text or "loss history" in text or "claims history" in text or "claims experience" in text:
        add(InsuranceDocumentType.LOSS_RUN)
    if "acord" in text or ("application" in text and "medical" not in text):
        add(InsuranceDocumentType.ACORD_XML)
    if "statement of values" in text or "sov" in text or "schedule of values" in text or "equipment schedule" in text or "vehicle schedule" in text or "location schedule" in text:
        add(InsuranceDocumentType.SCHEDULE_OF_VALUES)
    if "financial" in text or "p&l" in text or "balance sheet" in text or "tax return" in text:
        add(InsuranceDocumentType.FINANCIAL_STATEMENT)
    if "photo" in text:
        add(InsuranceDocumentType.PROPERTY_PHOTOS)
    if "inspection" in text or "survey" in text or "appraisal" in text or "engineering report" in text:
        add(InsuranceDocumentType.INSPECTION_REPORT)
    if "mvr" in text or "driving record" in text:
        add(InsuranceDocumentType.MVR_REPORT)
    if "dec page" in text or "declarations" in text or "prior policy" in text:
        add(InsuranceDocumentType.DEC_PAGE)
    if "broker slip" in text or "description of operations" in text or "description of business" in text:
        add(InsuranceDocumentType.BROKER_SLIP)
    if "10-k" in text or "def 14a" in text or "8-k" in text or "sec filing" in text:
        add(InsuranceDocumentType.DO_FINANCIALS_10K)
        add(InsuranceDocumentType.FINANCIAL_STATEMENT)
    if "bylaw" in text or "articles of incorporation" in text or "certificate of formation" in text:
        add(InsuranceDocumentType.DO_BYLAWS_CHARTER)
    if "board" in text and ("bio" in text or "roster" in text or "officer" in text or "resume" in text):
        add(InsuranceDocumentType.DO_BOARD_ROSTER)
    if "cap table" in text or "ownership" in text or "org chart" in text or "organizational chart" in text:
        add(InsuranceDocumentType.DO_OWNERSHIP_CHART)
    if "d&o" in text or "directors & officers" in text or "directors and officers" in text:
        if "application" in text or "questionnaire" in text:
            add(InsuranceDocumentType.DO_APPLICATION)
            add(InsuranceDocumentType.DO_QUESTIONNAIRE)
    if "engagement letter" in text or "client contract" in text:
        add(InsuranceDocumentType.ENGAGEMENT_LETTER)
    if "e&o" in text or "errors and omissions" in text or "professional liability" in text:
        if "application" in text:
            add(InsuranceDocumentType.EO_APPLICATION)
    if "ar aging" in text or "accounts receivable" in text:
        add(InsuranceDocumentType.AR_AGING_REPORT)
    if "buyer" in text and ("list" in text or "exposure" in text or "customer" in text):
        add(InsuranceDocumentType.BUYER_EXPOSURE_LIST)
    if "trade credit" in text and "application" in text:
        add(InsuranceDocumentType.TRADE_CREDIT_APPLICATION)
    if "key person" in text or "key-person" in text:
        if "application" in text:
            add(InsuranceDocumentType.KEY_PERSON_APPLICATION)
    if "corporate resolution" in text:
        add(InsuranceDocumentType.CORPORATE_RESOLUTION)
    if "beneficiary" in text:
        add(InsuranceDocumentType.BENEFICIARY_FORM)
    if "paramedical" in text or "medical exam" in text or "medical questionnaire" in text:
        add(InsuranceDocumentType.MEDICAL_EXAM)
    if "medical records" in text or "aps" in text:
        add(InsuranceDocumentType.APS_RECORDS)
    if "vehicle declaration" in text:
        add(InsuranceDocumentType.VEHICLE_DECLARATIONS)

    return tuple(types)


def _catalog_from_documents(documents: list[str]) -> list[tuple[str, tuple[InsuranceDocumentType, ...]]]:
    return [(doc, _types_for_label(doc)) for doc in documents if str(doc).strip()]


def _commercial_catalogs() -> dict[str, list[tuple[str, tuple[InsuranceDocumentType, ...]]]]:
    from insureflow.insurance.commercial_lobs import COMMERCIAL_LINES, flatten_line_documents

    catalogs: dict[str, list[tuple[str, tuple[InsuranceDocumentType, ...]]]] = {}
    for line in COMMERCIAL_LINES:
        key = str(line.get("checklist_lob") or "").strip()
        if not key:
            continue
        docs = flatten_line_documents(line)
        # Prefer first product that owns this checklist_lob (stable mapping)
        if key not in catalogs:
            catalogs[key] = _catalog_from_documents(docs)
    return catalogs


def _build_catalogs() -> dict[str, list[tuple[str, tuple[InsuranceDocumentType, ...]]]]:
    catalogs = dict(PERSONAL_CATALOGS)
    catalogs.update(_commercial_catalogs())
    return catalogs


# Lazily-built + refreshable so imports stay light and tests can rebuild if needed
CATALOGS: dict[str, list[tuple[str, tuple[InsuranceDocumentType, ...]]]] = {}


def refresh_catalogs() -> dict[str, list[tuple[str, tuple[InsuranceDocumentType, ...]]]]:
    global CATALOGS
    CATALOGS = _build_catalogs()
    return CATALOGS


refresh_catalogs()

# Thin wrappers kept for callers that imported specific catalog constants
PROPERTY_CATALOG = CATALOGS.get("property", [])
DO_CATALOG = CATALOGS.get("do", [])
WORKERS_COMP_CATALOG = CATALOGS.get("workers_comp", [])
TRADE_CREDIT_CATALOG = CATALOGS.get("trade_credit", [])
EO_CATALOG = CATALOGS.get("eo", [])
KEY_PERSON_CATALOG = CATALOGS.get("key_person", [])

# Aliases → canonical checklist keys
CHECKLIST_ALIASES: dict[str, str] = {
    "property_bi": "property",
    "commercial_property": "property",
    "errors_and_omissions": "eo",
    "directors_and_officers": "do",
    "directors_officers": "do",
    "workers-comp": "workers_comp",
    "trade-credit": "trade_credit",
    "key-person": "key_person",
    "business_owners_policy": "bop",
    "commercial_package": "cpp",
    "cyber_liability": "cyber",
    "pollution_liability": "pollution",
    "liquor_liability": "liquor",
    "media_liability": "media",
    "fiduciary_liability": "fiduciary",
    "garage_liability": "garage",
    "surety_bonds": "surety",
    "event_insurance": "event",
    "flood_commercial": "flood",
    "earthquake_commercial": "earthquake",
    "business_overhead_expense": "business_overhead",
    "architects_engineers": "architects_engineers",
    "ae_professional": "architects_engineers",
    "mpl": "miscellaneous_professional",
    "miscellaneous_professional_liability": "miscellaneous_professional",
    "rw": "representations_warranties",
    "r_and_w": "representations_warranties",
    "representations_and_warranties": "representations_warranties",
    "litigation_insurance": "legal_expense",
    "legal_expense_insurance": "legal_expense",
    "bobtail": "non_trucking_liability",
    "non_trucking": "non_trucking_liability",
    "dic": "dic_excess_flood",
    "excess_flood": "dic_excess_flood",
    "loss_of_rents": "rent_loss_of_rents",
    "ordinance_law": "ordinance_or_law",
    "captive": "captive_insurance",
    "sir": "sir_fronting",
    "fronting": "sir_fronting",
    "crop": "crop_insurance",
    "livestock": "livestock_bloodstock",
    "bloodstock": "livestock_bloodstock",
}


def _has_any(present: set[str], types: Iterable[InsuranceDocumentType]) -> bool:
    if not types:
        return False
    return any(t.value in present for t in types)


def normalize_checklist_lob(lob: str) -> str:
    if not CATALOGS:
        refresh_catalogs()
    raw = (lob or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not raw:
        return "property"
    if raw in CATALOGS:
        return raw
    aliased = CHECKLIST_ALIASES.get(raw)
    if aliased:
        return aliased
    try:
        from insureflow.insurance.commercial_lobs import resolve_checklist_lob

        return resolve_checklist_lob(raw, default="property")
    except Exception:
        return "property"


def detect_lob(text_blob: str = "", product_hint: str = "") -> str:
    blob = f"{product_hint}\n{text_blob}".lower()
    hint = (product_hint or "").strip().lower()

    from insureflow.underwriting.personal_lines import _has_strong_commercial_signals

    commercial = _has_strong_commercial_signals(blob)

    if hint:
        normalized_hint = normalize_checklist_lob(hint)
        if commercial and normalized_hint in {"life", "auto", "homeowners"}:
            return "property"
        if normalized_hint in CATALOGS:
            return normalized_hint

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

    # Keyword → checklist lob (order matters; more specific first)
    keyword_rules: list[tuple[tuple[str, ...], str]] = [
        (("cyber liability", "ransomware", "data breach response", "security questionnaire"), "cyber"),
        (("employment practices", "epli", "wrongful termination", "eeoc charge"), "epli"),
        (("fiduciary liability", "form 5500", "erisa fiduciary"), "fiduciary"),
        (("architects and engineers", "architects & engineers", "a&e professional", "design professional liability"), "architects_engineers"),
        (("miscellaneous professional", "mpl application", "mpl insurance"), "miscellaneous_professional"),
        (("representations and warranties", "representations & warranties", "r&w insurance", "r&w policy"), "representations_warranties"),
        (("legal expense", "litigation insurance", "after the event", "ate insurance"), "legal_expense"),
        (("ordinance or law", "ordinance and law", "increased cost of construction"), "ordinance_or_law"),
        (("loss of rents", "rent insurance", "rental income insurance"), "rent_loss_of_rents"),
        (("difference in conditions", "dic insurance", "excess flood"), "dic_excess_flood"),
        (("non-trucking", "non trucking", "bobtail"), "non_trucking_liability"),
        (("crop insurance", "acreage report", "aph yield"), "crop_insurance"),
        (("livestock insurance", "bloodstock", "herd mortality"), "livestock_bloodstock"),
        (("captive insurance", "captive feasibility", "single-parent captive"), "captive_insurance"),
        (("self-insured retention", "sir program", "fronting arrangement", "large deductible program"), "sir_fronting"),
        (("builders risk", "builder's risk", "course of construction"), "builders_risk"),
        (("inland marine", "contractors equipment floater", "installation floater"), "inland_marine"),
        (("ocean marine", "hull insurance", "protection & indemnity", "p&i"), "ocean_marine"),
        (("equipment breakdown", "boiler and machinery", "boiler & machinery"), "equipment_breakdown"),
        (("flood insurance", "elevation certificate", "nfip"), "flood"),
        (("earthquake insurance", "seismic pml"), "earthquake"),
        (("crime insurance", "employee dishonesty", "fidelity coverage", "funds transfer fraud"), "crime"),
        (("product liability", "products liability"), "product_liability"),
        (("liquor liability", "dram shop"), "liquor"),
        (("pollution liability", "contractor's pollution", "site pollution", "ust liability"), "pollution"),
        (("media liability", "defamation coverage"), "media"),
        (("umbrella", "excess liability", "acord 131"), "umbrella"),
        (("commercial general liability", "cgl", "acord 126", "premises/operations"), "general_liability"),
        (("motor truck cargo", "cargo insurance"), "motor_truck_cargo"),
        (("hired and non-owned", "hired & non-owned", "hnoa"), "hnoa"),
        (("garage liability", "garagekeepers"), "garage"),
        (("fleet insurance", "fleet schedule", "telematics fleet"), "fleet"),
        (("commercial auto", "business auto", "acord 127"), "commercial_auto"),
        (("surety bond", "performance bond", "payment bond", "bid bond"), "surety"),
        (("political risk", "expropriation", "inconvertibility"), "political_risk"),
        (("kidnap", "ransom", "k&r"), "kidnap_ransom"),
        (("product recall", "contamination insurance"), "product_recall"),
        (("business interruption", "business income worksheet", "extra expense coverage", "contingent business interruption"), "business_interruption"),
        (("supply chain insurance", "non-damage supply chain"), "supply_chain"),
        (("business owners policy", "bop application"), "bop"),
        (("commercial package", "cpp "), "cpp"),
        (("technology e&o", "tech e&o", "saas professional liability"), "tech_eo_cyber"),
        (("wrap-up", "ocip", "ccip", "contractor's insurance"), "construction"),
        (("aviation insurance", "aircraft hull"), "aviation"),
        (("event cancellation", "event liability"), "event"),
        (("intellectual property insurance", "patent infringement insurance"), "intellectual_property"),
        (("terrorism insurance", "tripra"), "terrorism"),
        (("group health", "self-funded plan", "stop-loss"), "group_health"),
        (("group life", "group term life"), "group_life"),
        (("short-term disability", "long-term disability", "group disability"), "group_disability"),
        (("business overhead expense", "boe insurance"), "business_overhead"),
        (("voluntary benefits", "critical illness", "group dental"), "voluntary_benefits"),
        (("employer's liability", "employers liability"), "employers_liability"),
        (("workers compensation", "workers' compensation", "workers_comp", "acord 130", "experience mod", "ncci"), "workers_comp"),
        (("trade credit", "accounts receivable aging", "buyer credit", "credit insurance"), "trade_credit"),
        (("errors and omissions", "errors & omissions", "e&o application", "professional liability", "acord 126"), "eo"),
        (("key person", "key-person", "keyman insurance", "key man insurance"), "key_person"),
    ]

    if not property_heavy:
        for keys, lob in keyword_rules:
            if any(k in blob for k in keys):
                return lob

    return "property"


def package_checklist(
    document_types: list[str],
    *,
    lob: str = "property",
) -> dict[str, Any]:
    if not CATALOGS:
        refresh_catalogs()
    present_types = {str(t).lower() for t in document_types}
    resolved = normalize_checklist_lob(lob)
    catalog = CATALOGS.get(resolved) or CATALOGS.get("property") or PROPERTY_CATALOG
    present: list[str] = []
    missing: list[str] = []
    for label, types in catalog:
        if _has_any(present_types, types):
            present.append(label)
        else:
            missing.append(label)
    total = len(catalog) or 1
    return {
        "lob": resolved,
        "present": present,
        "missing": missing,
        "completeness_pct": round(100.0 * len(present) / total, 1),
        "can_request_from_broker": len(missing) > 0,
    }
