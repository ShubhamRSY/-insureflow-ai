"""Per-leaf general / non-life underwriting. No invented premium."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.personal_lines import _blob, _int_field, _money


@dataclass
class GeneralUWDecision:
    decision: UWDecision
    product_id: str
    coverage_id: str
    category_id: str
    product_family: str
    reasons: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    gates: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "product_id": self.product_id,
            "coverage_id": self.coverage_id,
            "category_id": self.category_id,
            "product_family": self.product_family,
            "reasons": list(self.reasons),
            "conditions": list(self.conditions),
            "gates": dict(self.gates),
            **dict(self.metadata or {}),
        }


@dataclass
class _Ctx:
    bundle: SubmissionBundle
    blob: str
    types: set[str]
    product_id: str
    coverage_id: str
    category_id: str
    age: int | None
    sum_insured: float
    skip_retail_kyc: bool = False


def _types(bundle: SubmissionBundle) -> set[str]:
    out: set[str] = set()
    for doc in bundle.unstructured or []:
        dt = str(getattr(doc, "document_type", "") or "").strip().lower()
        if dt:
            out.add(dt)
    return out


def _has(ctx: _Ctx, *needles: str, types: tuple[str, ...] = ()) -> bool:
    if types and any(t in ctx.types for t in types):
        return True
    blob = ctx.blob
    return any(n.lower() in blob for n in needles if n)


def _finding(title: str, msg: str, sev: RiskSeverity, family: str) -> Finding:
    return Finding(title=title, description=msg, severity=sev, category=f"general_{family}")


def _finalize(
    ctx: _Ctx,
    *,
    family: str,
    extra: list[tuple[str, bool, str, RiskSeverity]],
    conditions: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    retail_kyc: bool = True,
) -> GeneralUWDecision:
    findings: list[Finding] = []
    reasons: list[str] = []
    conds = list(conditions or [])
    gates: dict[str, str] = {}
    decline = refer = conditional = False

    if retail_kyc and not ctx.skip_retail_kyc:
        id_ok = _has(ctx, "identity", "aadhaar", "id + address", "id proof", "photo id", types=("photo_id",))
        addr_ok = _has(ctx, "address proof", "id + address", "proof of address", types=("proof_of_address",))
        for gid, ok, msg in (
            ("kyc_identity", id_ok, "Identity proof of proposer / owner required"),
            ("kyc_address", addr_ok, "Address proof of proposer / owner required"),
        ):
            gates[gid] = "pass" if ok else "fail"
            if not ok:
                refer = True
                reasons.append(msg)
                findings.append(_finding("KYC incomplete", msg, RiskSeverity.HIGH, family))

    for gid, ok, msg, sev in extra:
        gates[gid] = "pass" if ok else "fail"
        if ok:
            continue
        reasons.append(msg)
        findings.append(_finding(gid.replace("_", " ").title(), msg, sev, family))
        if sev == RiskSeverity.CRITICAL:
            decline = True
        elif sev == RiskSeverity.HIGH:
            refer = True
        else:
            conditional = True

    if decline:
        decision = UWDecision.DECLINE
    elif refer:
        decision = UWDecision.REFER
    elif conditional:
        decision = UWDecision.CONDITIONAL_ACCEPT
    else:
        decision = UWDecision.ACCEPT
        conds.append("Eligibility clear — premium remains catalog-only until a filed general rate manual is imported")

    terms = general_product_terms(ctx.product_id, ctx.coverage_id)
    return GeneralUWDecision(
        decision=decision,
        product_id=ctx.product_id,
        coverage_id=ctx.coverage_id,
        category_id=ctx.category_id,
        product_family=family,
        reasons=reasons,
        conditions=conds,
        findings=findings,
        gates=gates,
        metadata={"age": ctx.age, "sum_insured": ctx.sum_insured, **terms, **(metadata or {})},
    )


def _new_vehicle(blob: str) -> bool:
    return bool(re.search(r"\b(new vehicle|brand new|ex-showroom|zero km|0 km)\b", blob, re.I))


def _used_or_lapse(blob: str) -> bool:
    return bool(re.search(r"\b(pre-owned|used vehicle|lapse|lapsed|break in cover|expired policy)\b", blob, re.I))


def _renewal(blob: str) -> bool:
    return "renewal" in blob or "previous policy" in blob or "prior policy" in blob or "ncb" in blob


# ── Motor ───────────────────────────────────────────────────────────────────


def _uw_car_tp(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        (
            "vehicle_rc",
            _has(ctx, "registration certificate", " rc ", "vehicle rc", types=("vehicle_rc", "vehicle_declarations")),
            "RC (registration certificate) of vehicle required",
            RiskSeverity.HIGH,
        ),
        ("driving_license", _has(ctx, "driving license", "driving licence", "dl copy", types=("driving_license",)), "Driving license required", RiskSeverity.HIGH),
        ("chassis_engine", _has(ctx, "chassis", "engine number", "engine no"), "Vehicle chassis / engine number details required", RiskSeverity.HIGH),
        (
            "prior_if_renewal",
            _has(ctx, "previous policy", "prior policy", "renewal policy", types=("dec_page",)) or not _renewal(ctx.blob),
            "Previous insurance policy copy required on renewal",
            RiskSeverity.HIGH,
        ),
    ]
    return _finalize(ctx, family="car_tp", extra=extra, conditions=["Statutory TP only — no own-damage"], metadata={"cover_type": "third_party"})


def _uw_car_comp(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("vehicle_rc", _has(ctx, "registration certificate", " rc ", "vehicle rc", types=("vehicle_rc", "vehicle_declarations")), "RC of vehicle required", RiskSeverity.HIGH),
        ("driving_license", _has(ctx, "driving license", "driving licence", types=("driving_license",)), "Driving license required", RiskSeverity.HIGH),
        (
            "ncb_prior",
            _has(ctx, "previous policy", "ncb", "no-claim", "no claim bonus", types=("dec_page",)) or not _renewal(ctx.blob),
            "Previous policy copy required for NCB transfer",
            RiskSeverity.HIGH,
        ),
        (
            "inspection_if_used",
            _has(ctx, "inspection", "vehicle photo", types=("inspection_report", "property_photos")) or not _used_or_lapse(ctx.blob),
            "Vehicle inspection / photos required for pre-owned or lapsed renewal",
            RiskSeverity.HIGH,
        ),
        ("invoice_if_new", _has(ctx, "invoice", "ex-showroom", types=("vehicle_invoice",)) or not _new_vehicle(ctx.blob), "Invoice copy required for a new vehicle", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="car_comprehensive", extra=extra, conditions=["OD + TP; NCB only with prior policy"], metadata={"cover_type": "comprehensive"})


def _uw_tw_tp(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("vehicle_rc", _has(ctx, "registration certificate", " rc ", types=("vehicle_rc",)), "RC of vehicle required", RiskSeverity.HIGH),
        ("driving_license", _has(ctx, "driving license", "driving licence", types=("driving_license",)), "Driving license required", RiskSeverity.HIGH),
        ("prior_if_renewal", _has(ctx, "previous policy", types=("dec_page",)) or not _renewal(ctx.blob), "Previous policy copy required on renewal", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="tw_tp", extra=extra, metadata={"cover_type": "third_party", "vehicle_class": "two_wheeler"})


def _uw_tw_comp(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("vehicle_rc", _has(ctx, "registration certificate", " rc ", types=("vehicle_rc",)), "RC of vehicle required", RiskSeverity.HIGH),
        ("driving_license", _has(ctx, "driving license", "driving licence", types=("driving_license",)), "Driving license required", RiskSeverity.HIGH),
        ("ncb_prior", _has(ctx, "previous policy", "ncb", types=("dec_page",)) or not _renewal(ctx.blob), "Previous policy copy required for NCB transfer", RiskSeverity.HIGH),
        (
            "photos_if_used",
            _has(ctx, "vehicle photo", "inspection", types=("property_photos", "inspection_report")) or not _used_or_lapse(ctx.blob),
            "Vehicle photos / inspection if applicable (used)",
            RiskSeverity.MODERATE,
        ),
        ("invoice_if_new", _has(ctx, "invoice", types=("vehicle_invoice",)) or not _new_vehicle(ctx.blob), "Invoice copy required for a new two-wheeler", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="tw_comprehensive", extra=extra, metadata={"cover_type": "comprehensive", "vehicle_class": "two_wheeler"})


def _uw_cv_tp(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("vehicle_rc", _has(ctx, "registration certificate", " rc ", types=("vehicle_rc",)), "RC of vehicle required", RiskSeverity.HIGH),
        ("fitness", _has(ctx, "fitness certificate", "fitness cert", types=("fitness_certificate",)), "Fitness certificate mandatory for commercial vehicle", RiskSeverity.HIGH),
        ("permit", _has(ctx, "permit", "national permit", "state permit", types=("vehicle_permit",)), "National / state permit copy required", RiskSeverity.HIGH),
        ("puc", _has(ctx, "puc", "pollution under control", types=("puc_certificate",)), "PUC certificate required", RiskSeverity.HIGH),
        ("driving_license", _has(ctx, "driving license", "driving licence", types=("driving_license",)), "Driving license of driver required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="cv_tp", extra=extra, conditions=["Do not rate CV TP as private car"], metadata={"cover_type": "third_party", "vehicle_class": "commercial"})


def _uw_cv_comp(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("vehicle_rc", _has(ctx, "registration certificate", " rc ", types=("vehicle_rc",)), "RC of vehicle required", RiskSeverity.HIGH),
        ("fitness", _has(ctx, "fitness certificate", types=("fitness_certificate",)), "Fitness certificate mandatory", RiskSeverity.HIGH),
        ("permit", _has(ctx, "permit", types=("vehicle_permit",)), "Permit copy required", RiskSeverity.HIGH),
        ("puc", _has(ctx, "puc", "pollution", types=("puc_certificate",)), "PUC certificate required", RiskSeverity.HIGH),
        ("driving_license", _has(ctx, "driving license", "driving licence", types=("driving_license",)), "Driving license required", RiskSeverity.HIGH),
        ("ncb_prior", _has(ctx, "previous policy", "ncb", types=("dec_page",)) or not _renewal(ctx.blob), "Previous policy copy required for NCB transfer", RiskSeverity.HIGH),
        ("inspection", _has(ctx, "inspection", types=("inspection_report",)), "Vehicle inspection report required for CV comprehensive", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="cv_comprehensive", extra=extra, metadata={"cover_type": "comprehensive", "vehicle_class": "commercial"})


# ── Home / fire / travel ────────────────────────────────────────────────────


def _uw_home_structure(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("ownership", _has(ctx, "sale deed", "registry", "ownership proof", "title deed", types=("property_deed",)), "Property ownership proof (sale deed / registry) required", RiskSeverity.HIGH),
        ("valuation", _has(ctx, "valuation", "construction cost", types=("valuation_report",)), "Property valuation / construction cost estimate required", RiskSeverity.HIGH),
        ("property_tax", _has(ctx, "property tax", types=("property_tax",)), "Property tax receipt required", RiskSeverity.HIGH),
        ("photos", _has(ctx, "photograph", "property photo", types=("property_photos", "passport_photo")), "Photographs of property required", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="home_structure", extra=extra, conditions=["Structure only — no contents schedule on this leaf"], metadata={"subject": "building"})


def _uw_home_contents(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("inventory", _has(ctx, "list of insured", "contents schedule", "item list", "jewelry", types=("contents_schedule",)), "List of insured items with values required", RiskSeverity.HIGH),
        ("invoices", _has(ctx, "invoice", "purchase bill", types=("vehicle_invoice",)), "Purchase invoices of high-value items required", RiskSeverity.HIGH),
        ("photos", _has(ctx, "photograph", "contents photo", types=("property_photos",)), "Photographs of contents required", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="home_contents", extra=extra, conditions=["Contents only — sale deed not required"], metadata={"subject": "contents", "requires_deed": False})


def _uw_home_comp(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("ownership", _has(ctx, "sale deed", "ownership", "registry", types=("property_deed",)), "Property ownership proof required", RiskSeverity.HIGH),
        ("valuation", _has(ctx, "valuation", types=("valuation_report",)), "Property valuation report required", RiskSeverity.HIGH),
        ("inventory", _has(ctx, "list of insured", "contents", "invoices of insured", types=("contents_schedule",)), "List + invoices of insured contents required", RiskSeverity.HIGH),
        ("property_tax", _has(ctx, "property tax", types=("property_tax",)), "Property tax receipt required", RiskSeverity.HIGH),
        ("photos", _has(ctx, "interior", "exterior", "photograph", types=("property_photos",)), "Interior + exterior photographs required", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="home_comprehensive", extra=extra, metadata={"subject": "building_and_contents"})


def _uw_travel_domestic(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("age_proof", _has(ctx, "age proof", "date of birth", types=("age_proof",)) or ctx.age is not None, "Age proof required", RiskSeverity.HIGH),
        ("itinerary", _has(ctx, "itinerary", "ticket", "pnr", types=("travel_documents",)), "Travel itinerary / ticket required", RiskSeverity.HIGH),
        ("photo", _has(ctx, "photograph", types=("passport_photo",)), "Photograph required", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="travel_domestic", extra=extra, conditions=["Passport / visa not required for domestic travel"], metadata={"territory": "domestic", "requires_passport": False})


def _uw_travel_intl(ctx: _Ctx) -> GeneralUWDecision:
    blob_wo_photo = re.sub(r"passport[-\s]?size", " ", ctx.blob)
    passport = "travel_documents" in ctx.types or bool(re.search(r"\bpassport\b", blob_wo_photo, re.I))
    extra = [
        ("passport", passport, "Passport is mandatory for international travel", RiskSeverity.CRITICAL),
        ("visa", _has(ctx, "visa", types=("travel_documents",)), "Visa copy required", RiskSeverity.HIGH),
        ("itinerary", _has(ctx, "itinerary", "flight", "ticket", types=("travel_documents",)), "Travel itinerary / flight ticket required", RiskSeverity.HIGH),
        ("age_proof", _has(ctx, "age proof", types=("age_proof",)) or ctx.age is not None, "Age proof required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="travel_international", extra=extra, metadata={"territory": "international", "requires_passport": True})


# ── Marine / fire / liability / cyber ───────────────────────────────────────


def _uw_marine_cargo(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("invoice", _has(ctx, "invoice of goods", "commercial invoice", "invoice", types=("vehicle_invoice",)), "Invoice of goods being shipped required", RiskSeverity.HIGH),
        ("bl_awb", _has(ctx, "bill of lading", "airway bill", "air waybill", "bl copy", types=("bill_of_lading",)), "Bill of lading / airway bill required", RiskSeverity.HIGH),
        ("packing_list", _has(ctx, "packing list", types=("packing_list",)), "Packing list required", RiskSeverity.HIGH),
        ("iec", _has(ctx, "iec", "importer exporter", types=("iec_certificate",)), "IEC certificate required", RiskSeverity.HIGH),
        ("gst", _has(ctx, "gst", "company registration", types=("company_registration",)), "Company registration / GST required", RiskSeverity.HIGH),
        (
            "lc_if_used",
            _has(ctx, "letter of credit", " l/c ", " lc ", types=("letter_of_credit",)) or "letter of credit" not in ctx.blob,
            "Letter of credit required when LC is used",
            RiskSeverity.MODERATE,
        ),
    ]
    return _finalize(ctx, family="marine_cargo", extra=extra, retail_kyc=False, metadata={"subject": "cargo"})


def _uw_marine_hull(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("vessel_reg", _has(ctx, "vessel registration", "ship registration", types=("vessel_registration",)), "Ship / vessel registration certificate required", RiskSeverity.HIGH),
        ("valuation", _has(ctx, "vessel valuation", "hull valuation", types=("valuation_report",)), "Vessel valuation report required", RiskSeverity.HIGH),
        (
            "class_cert",
            _has(ctx, "classification society", "seaworthiness", "class certificate", types=("classification_certificate",)),
            "Classification society / seaworthiness certificate required",
            RiskSeverity.HIGH,
        ),
        ("ownership", _has(ctx, "ownership proof of vessel", "vessel ownership"), "Ownership proof of vessel required", RiskSeverity.HIGH),
        ("crew", _has(ctx, "crew list", "crew certification", types=("crew_list",)), "Crew list & certification required", RiskSeverity.HIGH),
        ("company", _has(ctx, "gst", "company registration", types=("company_registration",)), "Ship-owner company registration required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="marine_hull", extra=extra, retail_kyc=False, metadata={"subject": "hull"})


def _uw_fire_res(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("ownership", _has(ctx, "ownership", "sale deed", types=("property_deed",)), "Property ownership proof required", RiskSeverity.HIGH),
        ("valuation", _has(ctx, "valuation", types=("valuation_report",)), "Property valuation report required", RiskSeverity.HIGH),
        ("photos", _has(ctx, "photograph", types=("property_photos",)), "Photographs of property required", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="fire_residential", extra=extra, conditions=["Residential SFSP — not industrial occupancy"], metadata={"occupancy": "residential"})


def _uw_fire_comm(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("ownership_lease", _has(ctx, "ownership", "lease", "factory", types=("property_deed",)), "Ownership or lease documents required", RiskSeverity.HIGH),
        ("gst", _has(ctx, "gst", "company registration", types=("company_registration",)), "Company registration / GST required", RiskSeverity.HIGH),
        ("asset_valuation", _has(ctx, "asset valuation", "machinery", "valuation", types=("valuation_report",)), "Asset valuation (building + machinery + stock) required", RiskSeverity.HIGH),
        ("fire_safety", _has(ctx, "fire safety", "fire noc", types=("fire_safety_certificate",)), "Fire safety compliance certificate required", RiskSeverity.HIGH),
        ("stock", _has(ctx, "stock", "inventory statement", types=("contents_schedule", "schedule_of_values")), "Stock / inventory statement required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="fire_commercial", extra=extra, retail_kyc=False, metadata={"occupancy": "commercial_industrial"})


def _uw_pi(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        (
            "license",
            _has(ctx, "professional license", "medical council", "bar council", "ca license", "icai", types=("professional_license",)),
            "Professional license / registration is mandatory",
            RiskSeverity.HIGH,
        ),
        ("practice_reg", _has(ctx, "practice registration", "business registration", "gst", types=("company_registration",)), "Business / practice registration proof required", RiskSeverity.HIGH),
        ("services", _has(ctx, "services offered", "nature of practice", "scope of services"), "Details of services offered required", RiskSeverity.HIGH),
        (
            "claims_hist",
            _has(ctx, "claims history", "no prior claims", "loss run", types=("loss_run",)) or "no claim" in ctx.blob,
            "Past claims history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]
    return _finalize(ctx, family="professional_indemnity", extra=extra)


def _uw_public_liab(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("gst", _has(ctx, "gst", "company registration", types=("company_registration",)), "Company registration / GST required", RiskSeverity.HIGH),
        ("premises", _has(ctx, "lease", "premises", "ownership", types=("property_deed",)), "Business premises ownership / lease proof required", RiskSeverity.HIGH),
        ("nature", _has(ctx, "nature of business", "operations", "description of business"), "Nature of business declaration required", RiskSeverity.HIGH),
        ("claims_hist", _has(ctx, "claims history", "loss run", types=("loss_run",)) or "no claim" in ctx.blob, "Past claims history required (or explicit nil)", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="public_liability", extra=extra, retail_kyc=False)


def _uw_prod_liab(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("gst", _has(ctx, "gst", "company registration", types=("company_registration",)), "Company registration / GST required", RiskSeverity.HIGH),
        ("catalog", _has(ctx, "product details", "product catalog", "sku"), "Product details / catalog required", RiskSeverity.HIGH),
        ("mfg_license", _has(ctx, "manufacturing license", "factory license", types=("manufacturing_license",)), "Manufacturing license required", RiskSeverity.HIGH),
        ("quality", _has(ctx, "iso", "bis", "quality cert", types=("quality_certification",)) or True, "Quality certification (ISO/BIS) if applicable", RiskSeverity.MODERATE),
        ("recall", "recall" not in ctx.blob or _has(ctx, "recall history", "claims history", types=("loss_run",)), "Product recall / claims history must be declared", RiskSeverity.HIGH),
    ]
    if "recall" in ctx.blob and "no recall" not in ctx.blob:
        extra.append(("open_recall", False, "Open / prior product recall — refer or decline product liability", RiskSeverity.HIGH))
    return _finalize(ctx, family="product_liability", extra=extra, retail_kyc=False)


def _uw_cyber_breach(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("gst", _has(ctx, "gst", "company registration", types=("company_registration",)), "Company registration / GST required", RiskSeverity.HIGH),
        ("security_policy", _has(ctx, "security policy", "data security", "it infrastructure", types=("cyber_questionnaire",)), "IT / data security policy required", RiskSeverity.HIGH),
        ("data_volume", _has(ctx, "data volume", "records", "customer data", "employee data", "pii"), "Details of data handled (volume) required", RiskSeverity.HIGH),
        (
            "incident_hist",
            _has(ctx, "incident history", "no prior breach", "cyber incident", types=("loss_run",)) or "no incident" in ctx.blob or "no breach" in ctx.blob,
            "Past cyber incident history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]
    return _finalize(ctx, family="cyber_data_breach", extra=extra, retail_kyc=False, metadata={"cyber_cover": "data_breach"})


def _uw_cyber_ransom(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("gst", _has(ctx, "gst", "company registration", types=("company_registration",)), "Company registration / GST required", RiskSeverity.HIGH),
        ("network", _has(ctx, "network", "it infrastructure", types=("cyber_questionnaire",)), "IT infrastructure & network details required", RiskSeverity.HIGH),
        ("controls", _has(ctx, "cybersecurity measures", "mfa", "backup", "edr", "controls"), "Existing cybersecurity measures declaration required", RiskSeverity.HIGH),
        (
            "incident_hist",
            _has(ctx, "incident", "breach history", "ransomware", types=("loss_run",)) or "no incident" in ctx.blob,
            "Past incident / breach history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]
    return _finalize(ctx, family="cyber_ransomware", extra=extra, retail_kyc=False, metadata={"cyber_cover": "ransomware"})


# ── Crop / animal / event / title / mortgage / provider ─────────────────────


def _uw_crop_yield(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("land", _has(ctx, "khasra", "khatauni", "7-12", "land ownership", "tenancy", types=("land_record",)), "Land ownership / tenancy proof required", RiskSeverity.HIGH),
        ("aadhaar", _has(ctx, "aadhaar", "identity", types=("photo_id",)), "Aadhaar / ID proof mandatory for most yield schemes", RiskSeverity.HIGH),
        ("bank", _has(ctx, "bank account", "ifsc", types=("bank_ach_form",)), "Bank account details required for subsidy / payout", RiskSeverity.HIGH),
        ("sowing", _has(ctx, "sowing certificate", "crop sown", types=("sowing_certificate",)), "Sowing certificate required", RiskSeverity.HIGH),
        ("acreage", _has(ctx, "survey number", "acreage", "hectare", "land area"), "Land area details (survey number, acreage) required", RiskSeverity.HIGH),
        (
            "loan_if_any",
            _has(ctx, "loan account", "kcc", "crop loan", types=("loan_agreement",)) or "crop loan" not in ctx.blob,
            "Loan account details required when farmer has a crop loan",
            RiskSeverity.MODERATE,
        ),
    ]
    return _finalize(ctx, family="crop_yield", extra=extra, retail_kyc=False, metadata={"index": "yield"})


def _uw_crop_weather(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("land", _has(ctx, "khasra", "khatauni", "land ownership", "tenancy", types=("land_record",)), "Land ownership / tenancy proof required", RiskSeverity.HIGH),
        ("id", _has(ctx, "aadhaar", "identity", "id + address", types=("photo_id",)), "ID + address proof required", RiskSeverity.HIGH),
        ("bank", _has(ctx, "bank account", "ifsc", types=("bank_ach_form",)), "Bank account details required", RiskSeverity.HIGH),
        ("sowing", _has(ctx, "sowing", types=("sowing_certificate",)), "Sowing certificate required", RiskSeverity.HIGH),
        ("weather_station", _has(ctx, "weather station", "imd", "index station"), "Nearest weather station reference required for indexed payout", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="crop_weather", extra=extra, retail_kyc=False, metadata={"index": "weather"})


def _uw_livestock(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("vet_health", _has(ctx, "animal health", "veterinar", types=("animal_health_cert", "doctor_certificate")), "Animal health certificate from veterinarian required", RiskSeverity.HIGH),
        ("animal_id", _has(ctx, "tag number", "microchip", "animal identification"), "Animal identification (tag / photo / microchip) required", RiskSeverity.HIGH),
        ("ownership", _has(ctx, "purchase receipt", "ownership proof of animal"), "Ownership proof of animal required", RiskSeverity.HIGH),
        ("valuation", _has(ctx, "valuation certificate", "valuer", types=("valuation_report",)), "Valuation certificate required", RiskSeverity.HIGH),
        ("photos", _has(ctx, "photograph", "photo of animal", types=("property_photos",)), "Photographs of animal required", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="livestock_cattle", extra=extra, metadata={"subject": "livestock"})


def _uw_pet(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("vaccination", _has(ctx, "vaccination", types=("pet_vaccination",)), "Pet vaccination record required", RiskSeverity.HIGH),
        ("medical_hist", _has(ctx, "medical history", "health certificate", types=("doctor_certificate",)), "Pet medical history / health certificate required", RiskSeverity.HIGH),
        ("breed_age", _has(ctx, "breed", "adoption", "age proof", types=("age_proof",)), "Breed & age proof required", RiskSeverity.HIGH),
        ("photo", _has(ctx, "photograph", "photo of pet", types=("property_photos", "passport_photo")), "Photograph of pet required", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="pet_insurance", extra=extra, conditions=["Companion pet — not livestock tag/valuation wording"], metadata={"subject": "pet"})


def _uw_wedding(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("event_details", _has(ctx, "venue", "event date", "budget", "wedding date"), "Event details (date, venue, budget) required", RiskSeverity.HIGH),
        ("vendors", _has(ctx, "vendor contract", "caterer", "decorator", "venue contract", types=("vendor_contract",)), "Vendor contracts required", RiskSeverity.HIGH),
        ("advances", _has(ctx, "advance", "booking amount", "receipt") or "cancellation" not in ctx.blob, "Advance payment receipts required for cancellation cover", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="wedding_insurance", extra=extra, metadata={"event_type": "wedding"})


def _uw_concert(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("gst", _has(ctx, "gst", "business registration", types=("company_registration",)), "Organizer business registration / GST required", RiskSeverity.HIGH),
        ("venue", _has(ctx, "venue booking", "venue agreement", types=("vendor_contract",)), "Venue booking agreement required", RiskSeverity.HIGH),
        ("permit", _has(ctx, "event license", "event permit", "local authority", types=("event_permit",)), "Event license / permit from local authority required", RiskSeverity.HIGH),
        ("contracts", _has(ctx, "artist", "vendor contract", types=("vendor_contract",)), "Artist / vendor contracts required", RiskSeverity.HIGH),
        ("budget", _has(ctx, "ticket sales", "budget", "projection"), "Estimated budget & ticket sales projection required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="concert_event", extra=extra, retail_kyc=False, metadata={"event_type": "public_concert"})


def _uw_title(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("deed", _has(ctx, "sale deed", "title deed", types=("property_deed",)), "Property sale deed / title deed required", RiskSeverity.HIGH),
        ("chain", _has(ctx, "ownership chain", "12 year", "30 year", "mother deed"), "Ownership chain documents (12–30 years) required", RiskSeverity.HIGH),
        ("encumbrance", _has(ctx, "encumbrance", types=("encumbrance_certificate",)), "Encumbrance certificate required", RiskSeverity.HIGH),
        ("tax", _has(ctx, "property tax", types=("property_tax",)), "Property tax receipts required", RiskSeverity.HIGH),
        ("survey", _has(ctx, "survey", "site plan", types=("inspection_report",)), "Survey / site plan required", RiskSeverity.HIGH),
        ("title_search", _has(ctx, "title search", types=("title_search", "attorney_documentation")), "Legal title search report required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="title_insurance", extra=extra, conditions=["Title is legal-history UW — not a motor/health KYC pattern"], metadata={"subject": "title"})


def _uw_mortgage_gi(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("sanction", _has(ctx, "sanction letter", "loan sanction", types=("loan_agreement", "lender_information")), "Loan sanction letter required", RiskSeverity.HIGH),
        (
            "property_docs",
            _has(ctx, "property document", "sale deed", "mortgage", types=("property_deed", "mortgage_statement")),
            "Property documents linked to the mortgage required",
            RiskSeverity.HIGH,
        ),
        ("income", _has(ctx, "income proof", "salary", "itr", types=("income_proof",)), "Income proof required", RiskSeverity.HIGH),
        ("age_proof", _has(ctx, "age proof", types=("age_proof",)) or ctx.age is not None, "Age proof required", RiskSeverity.HIGH),
        ("loan_stmt", _has(ctx, "loan account", "loan statement", types=("mortgage_statement",)), "Loan account statement required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="mortgage_insurance_gi", extra=extra, metadata={"linked_to": "housing_loan"})


def _uw_psu(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("age_proof", _has(ctx, "age proof", types=("age_proof",)) or ctx.age is not None, "Age proof required", RiskSeverity.HIGH),
        ("photo", _has(ctx, "photograph", types=("passport_photo",)), "Photograph required", RiskSeverity.MODERATE),
        ("aadhaar_link", _has(ctx, "aadhaar", "e-kyc", "ekyc", types=("photo_id", "ekyc")), "Aadhaar-linked verification often mandatory for PSU / subsidy schemes", RiskSeverity.HIGH),
        (
            "category_if_subsidy",
            _has(ctx, "category certificate", "caste", "income certificate", types=("category_certificate",)) or "subsidy" not in ctx.blob,
            "Category certificate required when scheme has caste/income subsidy",
            RiskSeverity.MODERATE,
        ),
    ]
    return _finalize(ctx, family="insurer_psu", extra=extra, metadata={"channel": "psu"})


def _uw_private(ctx: _Ctx) -> GeneralUWDecision:
    high_si = ctx.sum_insured >= 500_000 or "high sum insured" in ctx.blob or "higher sum" in ctx.blob
    extra = [
        ("age_proof", _has(ctx, "age proof", types=("age_proof",)) or ctx.age is not None, "Age proof required", RiskSeverity.HIGH),
        ("photo", _has(ctx, "photograph", types=("passport_photo",)), "Photograph required", RiskSeverity.MODERATE),
        ("income_if_high_si", _has(ctx, "income proof", "salary", "itr", types=("income_proof",)) or not high_si, "Income proof required for higher sum insured products", RiskSeverity.HIGH),
        ("ekyc", _has(ctx, "e-kyc", "ekyc", "digital kyc", "aadhaar", "pan", types=("ekyc", "photo_id")), "Digital e-KYC (Aadhaar/PAN) increasingly standard", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="insurer_private", extra=extra, metadata={"channel": "private"})


def _uw_reinsurance(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        (
            "ceding_license",
            _has(ctx, "ceding", "insurer registration", "irdai license", "license details", types=("company_registration",)),
            "Ceding insurer registration & license details required",
            RiskSeverity.HIGH,
        ),
        ("treaty", _has(ctx, "treaty", "facultative", "reinsurance agreement", types=("treaty_agreement",)), "Treaty / facultative reinsurance agreement required", RiskSeverity.HIGH),
        ("portfolio", _has(ctx, "portfolio", "policies being reinsured", "risk portfolio"), "Risk portfolio details of ceding insurer required", RiskSeverity.HIGH),
        ("loss_hist", _has(ctx, "loss history", "claims data", types=("loss_run",)), "Loss history / claims data of ceding insurer required", RiskSeverity.HIGH),
        (
            "solvency",
            _has(ctx, "solvency", "financial statements", types=("financial_statement", "solvency_statement")),
            "Solvency & financial statements of ceding insurer required",
            RiskSeverity.HIGH,
        ),
        ("regulator", _has(ctx, "irdai", "regulatory approval", "regulator clearance"), "Regulatory approval documents required", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="reinsurance_treaty",
        extra=extra,
        retail_kyc=False,
        conditions=["B2B reinsurance — not individual KYC"],
        metadata={"channel": "reinsurance_b2b"},
    )


_PRODUCT_HANDLERS: dict[str, Callable[[_Ctx], GeneralUWDecision]] = {
    "car_tp": _uw_car_tp,
    "car_comprehensive": _uw_car_comp,
    "tw_tp": _uw_tw_tp,
    "tw_comprehensive": _uw_tw_comp,
    "cv_tp": _uw_cv_tp,
    "cv_comprehensive": _uw_cv_comp,
    "home_structure": _uw_home_structure,
    "home_contents": _uw_home_contents,
    "home_comprehensive": _uw_home_comp,
    "travel_domestic": _uw_travel_domestic,
    "travel_international": _uw_travel_intl,
    "marine_cargo": _uw_marine_cargo,
    "marine_hull": _uw_marine_hull,
    "fire_residential": _uw_fire_res,
    "fire_commercial": _uw_fire_comm,
    "professional_indemnity_gi": _uw_pi,
    "public_liability_gi": _uw_public_liab,
    "product_liability_gi": _uw_prod_liab,
    "cyber_data_breach": _uw_cyber_breach,
    "cyber_ransomware": _uw_cyber_ransom,
    "crop_yield": _uw_crop_yield,
    "crop_weather": _uw_crop_weather,
    "livestock_cattle": _uw_livestock,
    "pet_insurance": _uw_pet,
    "wedding_insurance": _uw_wedding,
    "concert_event_insurance": _uw_concert,
    "title_insurance_gi": _uw_title,
    "mortgage_insurance_gi": _uw_mortgage_gi,
    "insurer_psu": _uw_psu,
    "insurer_private": _uw_private,
    "reinsurance_treaty": _uw_reinsurance,
}

_PRODUCT_TERMS: dict[str, dict[str, Any]] = {
    "car_tp": {"benefit_type": "motor_third_party", "vehicle_class": "car"},
    "car_comprehensive": {"benefit_type": "motor_comprehensive", "vehicle_class": "car"},
    "tw_tp": {"benefit_type": "motor_third_party", "vehicle_class": "two_wheeler"},
    "tw_comprehensive": {"benefit_type": "motor_comprehensive", "vehicle_class": "two_wheeler"},
    "cv_tp": {"benefit_type": "motor_third_party", "vehicle_class": "commercial"},
    "cv_comprehensive": {"benefit_type": "motor_comprehensive", "vehicle_class": "commercial"},
    "home_structure": {"benefit_type": "home_structure", "subject": "building"},
    "home_contents": {"benefit_type": "home_contents", "subject": "contents"},
    "home_comprehensive": {"benefit_type": "home_comprehensive", "subject": "building_and_contents"},
    "travel_domestic": {"benefit_type": "travel_domestic", "requires_passport": False},
    "travel_international": {"benefit_type": "travel_international", "requires_passport": True},
    "marine_cargo": {"benefit_type": "marine_cargo"},
    "marine_hull": {"benefit_type": "marine_hull"},
    "fire_residential": {"benefit_type": "fire_sfsp_residential"},
    "fire_commercial": {"benefit_type": "fire_commercial_industrial"},
    "professional_indemnity_gi": {"benefit_type": "professional_indemnity"},
    "public_liability_gi": {"benefit_type": "public_liability"},
    "product_liability_gi": {"benefit_type": "product_liability"},
    "cyber_data_breach": {"benefit_type": "cyber_data_breach"},
    "cyber_ransomware": {"benefit_type": "cyber_ransomware"},
    "crop_yield": {"benefit_type": "crop_yield_index"},
    "crop_weather": {"benefit_type": "crop_weather_index"},
    "livestock_cattle": {"benefit_type": "livestock"},
    "pet_insurance": {"benefit_type": "pet"},
    "wedding_insurance": {"benefit_type": "wedding_event"},
    "concert_event_insurance": {"benefit_type": "public_event"},
    "title_insurance_gi": {"benefit_type": "title"},
    "mortgage_insurance_gi": {"benefit_type": "mortgage_gi"},
    "insurer_psu": {"benefit_type": "channel_kyc_psu"},
    "insurer_private": {"benefit_type": "channel_kyc_private"},
    "reinsurance_treaty": {"benefit_type": "reinsurance_b2b"},
}


def general_product_terms(product_id: str | None = None, coverage_id: str | None = None) -> dict[str, Any]:
    pid = str(product_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    cid = str(coverage_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    out = dict(_PRODUCT_TERMS.get(pid) or {"benefit_type": "general_non_life"})
    out["product_id"] = pid
    out["coverage_id"] = cid
    return out


def registered_general_uw_products() -> frozenset[str]:
    return frozenset(_PRODUCT_HANDLERS)


def _resolve_ids(product_id: str | None, coverage_id: str | None) -> tuple[str, str, str]:
    from insureflow.insurance.general_lobs import get_general_coverage, resolve_general_checklist_lob

    pid = str(product_id or "").strip()
    cid = str(coverage_id or "").strip()
    line, cov = get_general_coverage(pid or None, cid or None)
    if line:
        pid = str(line.get("id") or pid)
        category = str(line.get("category_id") or "")
        if cov and not cid:
            cid = str(cov.get("id") or "")
        return pid, cid, category
    resolved = resolve_general_checklist_lob(pid) or resolve_general_checklist_lob(cid) or pid.replace("-", "_")
    return resolved, cid, ""


def underwrite_general(
    bundle: SubmissionBundle,
    *,
    product_id: str | None = None,
    coverage_id: str | None = None,
) -> GeneralUWDecision:
    pid, cid, category = _resolve_ids(product_id, coverage_id)
    blob = _blob(bundle)
    ctx = _Ctx(
        bundle=bundle,
        blob=blob,
        types=_types(bundle),
        product_id=pid.replace("-", "_"),
        coverage_id=cid.replace("-", "_"),
        category_id=category,
        age=_int_field(blob, "age", "proposer age", "insured age"),
        sum_insured=float(_money(blob, "sum insured", "si", "sum_insured") or 0.0),
        skip_retail_kyc=pid.replace("-", "_")
        in {
            "marine_cargo",
            "marine_hull",
            "fire_commercial",
            "public_liability_gi",
            "product_liability_gi",
            "cyber_data_breach",
            "cyber_ransomware",
            "crop_yield",
            "crop_weather",
            "concert_event_insurance",
            "reinsurance_treaty",
        },
    )
    handler = _PRODUCT_HANDLERS.get(ctx.product_id)
    if handler is None:
        return _finalize(ctx, family="general_generic", extra=[], conditions=["Unknown general leaf — KYC only"])
    return handler(ctx)
