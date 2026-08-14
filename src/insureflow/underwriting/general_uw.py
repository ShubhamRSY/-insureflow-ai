"""Per-leaf general / non-life underwriting. No invented premium."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Callable

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.general_product import is_filed_general_product
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
        if is_filed_general_product(ctx.product_id):
            conds.append("Eligibility clear — filed general rate manual applies; premium computed by the rating engine")
        else:
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

_CAR_TP_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    (
        "high",
        1.4,
        ("taxi", "cab", "commercial use", "rental", "ride share", "uber", "ola", "high performance", "sports car"),
    ),
    ("medium", 1.15, ("family car", "sedan", "suv", "company car", "long distance")),
    ("low", 1.0, ("hatchback", "small car", "city car", "weekend use", "personal use")),
)

_CAR_COMP_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.8, ("luxury", "imported", "premium", "expensive", "high value", "sports car")),
    ("medium", 1.3, ("sedan", "mid-size", "suv", "family car")),
    ("low", 1.0, ("hatchback", "economy", "value car", "small car", "city car")),
)

_TW_TP_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.5, ("high cc", "350cc", "500cc", "650cc", "superbike", "sport bike", "above 350 cc")),
    ("medium", 1.15, ("motorcycle", "150cc", "200cc", "250cc", "commuter bike")),
    ("low", 1.0, ("scooter", "gearless", "electric", "100cc", "moped")),
)

_TW_COMP_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.7, ("premium motorcycle", "superbike", "expensive bike", "high value", "sport bike")),
    ("medium", 1.25, ("motorcycle", "commuter bike", "150cc", "200cc")),
    ("low", 1.0, ("scooter", "gearless", "electric", "moped")),
)

_CV_TP_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    (
        "high",
        1.6,
        ("passenger transport", "bus", "tanker", "hazardous goods", "chemicals transport", "school bus", "interstate"),
    ),
    ("medium", 1.2, ("goods truck", "mini truck", "container", "tempo")),
    ("low", 1.0, ("light commercial", "van", "pickup", "private use", "small lcv")),
)

_CV_COMP_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.85, ("fleet", "heavy goods", "tanker", "hazardous", "container", "multi-axle")),
    ("medium", 1.3, ("goods truck", "mini truck", "single vehicle")),
    ("low", 1.0, ("light commercial", "van", "pickup", "small lcv")),
)


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


# ── Home ─────────────────────────────────────────────────────────────────────


def _home_years(ctx: _Ctx) -> int | None:
    m = re.search(r"(?:built|constructed|construction year|year built|built in)\s*(?:in\s*)?(?:the\s*)?year\s*(\d{4})", ctx.blob, re.I)
    if m:
        return 2026 - int(m.group(1))
    return None


_HOME_STRUCTURE_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    (
        "high",
        1.7,
        ("coastal", "flood-prone", "flood zone", "wooden", "thatched", "kutcha", "cyclone", "seismic zone", "earthquake zone", "heritage building"),
    ),
    ("medium", 1.2, ("semi-pucca", "brick", "mixed construction", "stone", "old building")),
    ("low", 1.0, ("rcc", "reinforced concrete", "concrete", "fire-resistant", "modern", "new construction")),
)

_HOME_CONTENTS_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    (
        "high",
        1.8,
        ("jewelry", "jewellery", "gold", "silver", "artwork", "luxury", "cash", "high-value electronics", "designer items"),
    ),
    ("medium", 1.25, ("electronics", "television", "refrigerator", "washing machine", "laptop", "furniture", "appliances")),
    ("low", 1.0, ("general household", "household goods", "books", "clothing", "kitchenware")),
)

_HOME_COMP_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.7, ("coastal", "flood-prone", "wooden structure", "heritage", "jewelry", "antique")),
    ("medium", 1.2, ("brick", "semi-pucca", "electronics", "moderate contents")),
    ("low", 1.0, ("rcc", "concrete", "alarm", "security system", "standard contents")),
)


def _uw_home_structure(ctx: _Ctx) -> GeneralUWDecision:
    year_built = _home_years(ctx)
    cls, _ = _risk_class(ctx.blob, _HOME_STRUCTURE_RISK_TABLE)
    cat_exp = bool(re.search(r"\b(coastal|flood-prone|flood zone|cyclone|seismic zone|earthquake zone)\b", ctx.blob, re.I))
    extra = [
        ("ownership", _has(ctx, "sale deed", "registry", "ownership proof", "title deed", types=("property_deed",)), "Property ownership proof (sale deed / registry) required", RiskSeverity.HIGH),
        ("valuation", _has(ctx, "valuation", "construction cost", types=("valuation_report",)), "Property valuation / construction cost estimate required", RiskSeverity.HIGH),
        ("property_tax", _has(ctx, "property tax", types=("property_tax",)), "Property tax receipt required", RiskSeverity.HIGH),
        ("photos", _has(ctx, "photograph", "property photo", "photos", types=("property_photos", "passport_photo")), "Photographs of property required", RiskSeverity.MODERATE),
        (
            "construction_type",
            _has(ctx, "rcc", "concrete", "wooden", "brick", "semi-pucca", "thatched", "kutcha"),
            "Construction type (RCC / brick / wooden) declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "building_age",
            year_built is not None,
            "Year of construction required to assess building age",
            RiskSeverity.MODERATE,
        ),
        (
            "prior_claims",
            _has(ctx, "claims history", "no claims", "no prior claim", types=("loss_run",))
            or "no claims" in ctx.blob
            or "no prior fire claims" in ctx.blob
            or "no previous claims" in ctx.blob,
            "Prior property claims history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]
    if cat_exp:
        extra.append(
            (
                "catastrophe_exposure",
                False,
                "Coastal / flood / seismic exposure detected — cover subject to catastrophe sub-limits and terms",
                RiskSeverity.MODERATE,
            )
        )
    return _finalize(
        ctx,
        family="home_structure",
        extra=extra,
        conditions=["Structure only — building and fixtures, contents excluded", "Allied perils as per schedule"],
        metadata={
            "subject": "building",
            "construction": cls,
            "building_age": year_built,
            "coastal": cat_exp,
            "prior_claims": _claims_severity(ctx.blob),
        },
    )


def _uw_home_contents(ctx: _Ctx) -> GeneralUWDecision:
    extra = [
        ("inventory", _has(ctx, "list of insured", "contents schedule", "item list", "jewelry", types=("contents_schedule",)), "List of insured items with values required", RiskSeverity.HIGH),
        ("invoices", _has(ctx, "invoice", "purchase bill", types=("vehicle_invoice",)), "Purchase invoices of high-value items required", RiskSeverity.HIGH),
        ("photos", _has(ctx, "photograph", "contents photo", "photos", types=("property_photos",)), "Photographs of contents required", RiskSeverity.MODERATE),
        (
            "declared_value",
            _has(ctx, "declared value", "total contents value", "contents value", "insured value", "inventory value"),
            "Declared value of insured contents required",
            RiskSeverity.MODERATE,
        ),
        (
            "security_measures",
            _has(ctx, "locks", "alarm", "security system", "burglary", "safe"),
            "Declared security measures (locks / alarm / safe) required for theft cover",
            RiskSeverity.MODERATE,
        ),
        (
            "prior_claims",
            _has(ctx, "claims history", "no claims", "no prior claim", types=("loss_run",))
            or "no claims" in ctx.blob
            or "no prior contents claims" in ctx.blob
            or "no theft claims" in ctx.blob,
            "Prior contents / theft claims history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]
    return _finalize(
        ctx,
        family="home_contents",
        extra=extra,
        conditions=["Contents only — sale deed not required", "Burglary and theft cover requires declared security measures"],
        metadata={
            "subject": "contents",
            "requires_deed": False,
            "declared_value": ctx.blob,
            "high_value_items": _risk_class(ctx.blob, _HOME_CONTENTS_RISK_TABLE)[0],
        },
    )


def _uw_home_comp(ctx: _Ctx) -> GeneralUWDecision:
    year_built = _home_years(ctx)
    cat_exp = bool(re.search(r"\b(coastal|flood-prone|flood zone|cyclone|seismic zone|earthquake zone)\b", ctx.blob, re.I))
    extra = [
        ("ownership", _has(ctx, "sale deed", "ownership", "registry", types=("property_deed",)), "Property ownership proof required", RiskSeverity.HIGH),
        ("valuation", _has(ctx, "valuation", types=("valuation_report",)), "Property valuation report required", RiskSeverity.HIGH),
        ("inventory", _has(ctx, "list of insured", "contents", "invoices of insured", types=("contents_schedule",)), "List + invoices of insured contents required", RiskSeverity.HIGH),
        ("property_tax", _has(ctx, "property tax", types=("property_tax",)), "Property tax receipt required", RiskSeverity.HIGH),
        ("photos", _has(ctx, "interior", "exterior", "photograph", "photos", types=("property_photos",)), "Interior + exterior photographs required", RiskSeverity.MODERATE),
        (
            "building_age",
            year_built is not None,
            "Year of construction required to assess building age",
            RiskSeverity.MODERATE,
        ),
        (
            "security_measures",
            _has(ctx, "locks", "alarm", "security system", "burglary", "safe"),
            "Declared security measures required for contents schedule",
            RiskSeverity.MODERATE,
        ),
        (
            "prior_claims",
            _has(ctx, "claims history", "no claims", "no prior claim", types=("loss_run",))
            or "no claims" in ctx.blob
            or "no prior fire claims" in ctx.blob
            or "no previous claims" in ctx.blob,
            "Prior claims history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]
    if cat_exp:
        extra.append(
            (
                "catastrophe_exposure",
                False,
                "Coastal / flood / seismic exposure detected — cover subject to catastrophe sub-limits and terms",
                RiskSeverity.MODERATE,
            )
        )
    return _finalize(
        ctx,
        family="home_comprehensive",
        extra=extra,
        conditions=["Comprehensive — building and contents on one policy", "Interior + exterior photographs required"],
        metadata={"subject": "building_and_contents", "building_age": year_built, "coastal": cat_exp},
    )


# ── Travel: domestic ─────────────────────────────────────────────────────────
# Domain: in-country medical emergency, trip cancellation and baggage. Risk
# drivers are trip duration, destination remoteness (hill / adventure vs metro),
# adventure activities and pre-existing health conditions. No passport / visa /
# destination-medical-cost concerns — those belong to international cover.

_TRAVEL_DOM_RISK_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "high",
        0.8,
        (
            "trekking",
            "mountaineering",
            "rafting",
            "scuba",
            "paragliding",
            "adventure",
            "high altitude",
            "himalaya",
            "remote",
            "northeast",
        ),
    ),
    ("medium", 0.5, ("hill station", "pilgrimage", "tier-2", "business travel", "jaipur", "udaipur")),
    ("low", 0.3, ("metro", "delhi", "mumbai", "bangalore", "chennai", "short trip", "city")),
]


def _uw_travel_domestic(ctx: _Ctx) -> GeneralUWDecision:
    cls, cls_factor = _risk_class(ctx.blob, _TRAVEL_DOM_RISK_TABLE)
    duration = _int_field(ctx.blob, "trip duration", "duration days", "trip days", "number of days", "duration")
    adventure = bool(re.search(r"\b(trekking|mountaineering|rafting|scuba|paragliding|adventure sport|adventure)\b", ctx.blob, re.I))
    destination = bool(re.search(r"\b(destination|traveling to|travelling to|visiting|staying at)\b", ctx.blob, re.I))

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        (
            "age_proof",
            _has(ctx, "age proof", "date of birth", types=("age_proof",)) or ctx.age is not None,
            "Age proof required",
            RiskSeverity.HIGH,
        ),
        (
            "itinerary",
            _has(ctx, "itinerary", "ticket", "pnr", types=("travel_documents",)),
            "Travel itinerary / ticket required",
            RiskSeverity.HIGH,
        ),
        (
            "trip_duration",
            duration is not None,
            "Trip duration (dates / days) required",
            RiskSeverity.MODERATE,
        ),
        (
            "destination",
            destination or _has(ctx, "destination", "traveling to", "visiting", "itinerary"),
            "Travel destination declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "pre_existing_conditions",
            _has(ctx, "health declaration", "pre-existing", "medical condition", "health condition", "no pre-existing", "medical history"),
            "Pre-existing condition health declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "photo",
            _has(ctx, "photograph", types=("passport_photo",)),
            "Photograph required",
            RiskSeverity.MODERATE,
        ),
    ]
    if adventure:
        extra.append(
            (
                "adventure_activities",
                False,
                "Adventure / high-altitude activities detected — cover only by adventure endorsement with loadings",
                RiskSeverity.MODERATE,
            )
        )

    return _finalize(
        ctx,
        family="travel_domestic",
        extra=extra,
        conditions=[
            "In-country medical emergency, trip cancellation and baggage cover",
            "Adventure sports covered by endorsement only",
        ],
        metadata={
            "territory": "domestic",
            "requires_passport": False,
            "travel_risk_class": cls,
            "duration_days": duration,
            "adventure_activities": adventure,
            "domain_risk_score": cls_factor,
        },
    )


# ── Travel: international ────────────────────────────────────────────────────
# Domain: out-of-country cover. Risk drivers are passport validity, visa, the
# destination's medical cost band (USA / Canada / Europe high), trip duration
# and pre-existing conditions. No adventure / hill-station classification and no
# in-country-only framing — those belong to domestic cover.

_TRAVEL_INTL_RISK_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "high",
        0.9,
        (
            "usa",
            "united states",
            "canada",
            "europe",
            "uk",
            "united kingdom",
            "switzerland",
            "australia",
            "new zealand",
            "scandinavia",
        ),
    ),
    (
        "medium",
        0.5,
        ("uae", "dubai", "singapore", "japan", "qatar", "saudi", "hong kong", "middle east", "gulf"),
    ),
    ("low", 0.3, ("thailand", "bali", "nepal", "sri lanka", "malaysia", "vietnam", "south asia", "indonesia")),
]


def _uw_travel_intl(ctx: _Ctx) -> GeneralUWDecision:
    blob_wo_photo = re.sub(r"passport[-\s]?size", " ", ctx.blob)
    passport = "travel_documents" in ctx.types or bool(re.search(r"\bpassport\b", blob_wo_photo, re.I))
    cls, cls_factor = _risk_class(ctx.blob, _TRAVEL_INTL_RISK_TABLE)
    duration = _int_field(ctx.blob, "trip duration", "duration days", "trip days", "number of days", "duration")
    validity = bool(re.search(r"\b(passport valid|valid until|validity|valid for 6 months|valid 10)\b", ctx.blob, re.I))

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        ("passport", passport, "Passport is mandatory for international travel", RiskSeverity.CRITICAL),
        ("visa", _has(ctx, "visa", types=("travel_documents",)), "Visa copy required", RiskSeverity.HIGH),
        ("itinerary", _has(ctx, "itinerary", "flight", "ticket", types=("travel_documents",)), "Travel itinerary / flight ticket required", RiskSeverity.HIGH),
        ("age_proof", _has(ctx, "age proof", "date of birth", types=("age_proof",)) or ctx.age is not None, "Age proof required", RiskSeverity.HIGH),
        (
            "destination_risk",
            _has(ctx, "destination", "visiting", "traveling to", "country", "flying to", "usa", "europe", "uae", "thailand"),
            "Destination country declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "passport_validity",
            validity or cls == "low",
            "Passport validity at least 6 months beyond the return date required",
            RiskSeverity.MODERATE,
        ),
        (
            "pre_existing_conditions",
            _has(ctx, "health declaration", "pre-existing", "medical condition", "medical history", "no pre-existing", "fit to travel"),
            "Pre-existing condition health declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "trip_duration",
            duration is not None,
            "Trip duration (dates / days) required",
            RiskSeverity.MODERATE,
        ),
        (
            "photo",
            _has(ctx, "photograph", types=("passport_photo",)),
            "Photograph required",
            RiskSeverity.MODERATE,
        ),
    ]
    if cls == "high":
        extra.append(
            (
                "high_cost_destination",
                False,
                "High medical-cost destination (USA / Canada / Europe) — medical limit and deductible to be set per destination band",
                RiskSeverity.MODERATE,
            )
        )

    return _finalize(
        ctx,
        family="travel_international",
        extra=extra,
        conditions=[
            "Worldwide cover excluding home country",
            "Medical limit banded by destination medical-cost class",
        ],
        metadata={
            "territory": "international",
            "requires_passport": True,
            "destination_cost_class": cls,
            "duration_days": duration,
            "domain_risk_score": cls_factor,
        },
    )


# ── Marine: cargo ────────────────────────────────────────────────────────────
# Domain: goods in transit. Risk drivers are the nature of the cargo (perishable
# / hazardous / fragile), mode and route of transit, declared cargo value and the
# shipping documents (invoice, bill of lading / airway bill, packing list).
# No concern with the vessel itself, its classification or crew — those belong
# to hull cover.

_MARINE_CARGO_RISK_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "high",
        0.9,
        (
            "perishable",
            "seafood",
            "frozen",
            "refrigerated",
            "pharmaceuticals",
            "electronics",
            "hazardous",
            "dangerous goods",
            "chemicals",
            "explosive",
            "flammable",
            "toxic",
            "fragile",
            "glass",
            "ceramic",
            "artwork",
            "jewelry",
            "tobacco",
        ),
    ),
    ("medium", 0.5, ("machinery", "garments", "textiles", "food grains", "leather", "paper", "spices", "beverages")),
    ("low", 0.3, ("general merchandise", "steel", "iron", "raw materials", "stationery", "cement", "fertilizer")),
]


def _uw_marine_cargo(ctx: _Ctx) -> GeneralUWDecision:
    cls, cls_factor = _risk_class(ctx.blob, _MARINE_CARGO_RISK_TABLE)
    cargo_value = _scaled_money(ctx.blob, "cargo value", "invoice value", "goods value", "declared cargo value")
    hazardous = bool(re.search(r"\b(hazardous|dangerous goods|explosive|chemical|flammable|toxic)\b", ctx.blob, re.I))
    perishable = bool(re.search(r"\b(perishable|frozen|refrigerated|fresh produce|meat|seafood|flowers)\b", ctx.blob, re.I))
    mode = bool(re.search(r"\b(mode of transit|sea freight|air freight|road|rail|vessel|flight|truck|container)\b", ctx.blob, re.I))
    route = bool(re.search(r"\b(port of loading|port of discharge|destination|transshipment|transit route|route)\b", ctx.blob, re.I))

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        (
            "invoice",
            _has(ctx, "invoice of goods", "commercial invoice", "invoice", "proforma invoice", types=("vehicle_invoice",)),
            "Invoice of goods being shipped required",
            RiskSeverity.HIGH,
        ),
        (
            "bl_awb",
            _has(ctx, "bill of lading", "airway bill", "air waybill", "bl copy", types=("bill_of_lading",)),
            "Bill of lading / airway bill required",
            RiskSeverity.HIGH,
        ),
        (
            "packing_list",
            _has(ctx, "packing list", "packing standard", types=("packing_list",)),
            "Packing list / packing standard required",
            RiskSeverity.HIGH,
        ),
        (
            "cargo_declared",
            _has(ctx, "cargo", "goods", "nature of goods", "shipment", "commodity"),
            "Nature / description of cargo required",
            RiskSeverity.HIGH,
        ),
        (
            "transit_mode",
            mode or _has(ctx, "mode of transit", "sea", "air", "road", "rail"),
            "Mode of transit (sea / air / road / rail) required",
            RiskSeverity.HIGH,
        ),
        (
            "cargo_value",
            cargo_value > 0 or _has(ctx, "cargo value", "invoice value", "sum insured"),
            "Declared cargo value / sum insured required",
            RiskSeverity.HIGH,
        ),
        (
            "iec",
            _has(ctx, "iec", "importer exporter", types=("iec_certificate",)),
            "IEC certificate required for cross-border shipments",
            RiskSeverity.MODERATE,
        ),
        (
            "transit_route",
            route or _has(ctx, "port of loading", "port of discharge", "destination", "route"),
            "Transit route / ports of loading & discharge required",
            RiskSeverity.MODERATE,
        ),
        (
            "lc_if_used",
            _has(ctx, "letter of credit", " l/c ", " lc ", types=("letter_of_credit",)) or "letter of credit" not in ctx.blob,
            "Letter of credit required when LC is used",
            RiskSeverity.MODERATE,
        ),
    ]
    if hazardous:
        extra.append(
            (
                "hazardous_cargo",
                False,
                "Hazardous / dangerous cargo requires carrier acceptance and IMDG compliance confirmation",
                RiskSeverity.HIGH,
            )
        )
    if perishable:
        extra.append(
            (
                "perishable_cargo",
                False,
                "Perishable / fragile cargo requires refrigerated or shock-protected packing declaration",
                RiskSeverity.MODERATE,
            )
        )

    return _finalize(
        ctx,
        family="marine_cargo",
        extra=extra,
        conditions=[
            "Coverage attaches from loading until discharge; inland transit extension as per schedule",
            "Institute Cargo Clauses (A / B / C) as selected",
        ],
        retail_kyc=False,
        metadata={
            "subject": "cargo",
            "cargo_risk_class": cls,
            "cargo_value": cargo_value,
            "hazardous": hazardous,
            "perishable": perishable,
            "mode_declared": mode,
            "domain_risk_score": cls_factor,
        },
    )


# ── Marine: hull ─────────────────────────────────────────────────────────────
# Domain: the vessel itself (hull & machinery). Risk drivers are the vessel's
# classification / seaworthiness, age, trading area, crew certification and prior
# losses, plus any laid-up period. No concern with the goods carried, their
# packing or the shipping documents — those belong to cargo cover.

_MARINE_HULL_RISK_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "high",
        0.9,
        ("fishing vessel", "wooden hull", "inland waterways", "river barge", "country craft", "old coaster", "unclassed"),
    ),
    (
        "medium",
        0.5,
        ("general cargo vessel", "bulk carrier", "coastal tanker", "offshore supply", "tug", "dredger"),
    ),
    ("low", 0.3, ("container vessel", "modern tanker", "passenger ferry", "well-classed", "classed")),
]


def _uw_marine_hull(ctx: _Ctx) -> GeneralUWDecision:
    cls, cls_factor = _risk_class(ctx.blob, _MARINE_HULL_RISK_TABLE)
    hull_value = _scaled_money(ctx.blob, "hull value", "vessel value", "insured value", "sum insured", "vessel valuation")
    year_built = _int_field(ctx.blob, "year built", "built year", "build year", "vessel year")
    vessel_age = (2026 - year_built) if year_built else None
    laid_up = bool(re.search(r"\b(laid up|lay-up|mooring|laid-up)\b", ctx.blob, re.I))

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        (
            "vessel_reg",
            _has(ctx, "vessel registration", "ship registration", "imo number", types=("vessel_registration",)),
            "Ship / vessel registration certificate required",
            RiskSeverity.HIGH,
        ),
        (
            "valuation",
            _has(ctx, "hull valuation", "vessel valuation", "insured value", "hull value", types=("valuation_report",)),
            "Hull / vessel valuation report required",
            RiskSeverity.HIGH,
        ),
        (
            "class_cert",
            _has(ctx, "classification society", "seaworthiness", "class certificate", "survey certificate", types=("classification_certificate",)),
            "Classification society / seaworthiness certificate required",
            RiskSeverity.HIGH,
        ),
        (
            "ownership",
            _has(ctx, "ownership proof of vessel", "vessel ownership", "bill of sale"),
            "Ownership proof of vessel required",
            RiskSeverity.HIGH,
        ),
        (
            "crew",
            _has(ctx, "crew list", "crew certification", "manning", "master certificate", types=("crew_list",)),
            "Crew list & certification required",
            RiskSeverity.MODERATE,
        ),
        (
            "company",
            _has(ctx, "gst", "company registration", types=("company_registration",)),
            "Ship-owner company registration required",
            RiskSeverity.HIGH,
        ),
        (
            "vessel_age",
            vessel_age is not None,
            "Vessel build year required to assess age-related deterioration",
            RiskSeverity.MODERATE,
        ),
        (
            "trading_area",
            _has(ctx, "trading area", "voyage", "coastal", "overseas", "international waters", "port risk", "inland", "river"),
            "Trading area / voyage limits declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "hull_history",
            _has(ctx, "claims history", "loss record", "no claims", "no losses", "clean record", types=("loss_run",))
            or "no claims" in ctx.blob
            or "no losses" in ctx.blob
            or "no prior claim" in ctx.blob,
            "Prior claims / loss history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]
    if laid_up:
        extra.append(
            (
                "laid_up_warranty",
                False,
                "Laid-up vessel — confirm lay-up warranty and reduced laid-up valuation",
                RiskSeverity.MODERATE,
            )
        )

    return _finalize(
        ctx,
        family="marine_hull",
        extra=extra,
        conditions=[
            "Hull & machinery — Institute Time Clauses / Voyage Clauses as selected",
            "Trading limits warranty applies as per schedule",
        ],
        retail_kyc=False,
        metadata={
            "subject": "hull",
            "hull_risk_class": cls,
            "hull_value": hull_value,
            "vessel_age": vessel_age,
            "year_built": year_built,
            "laid_up": laid_up,
            "domain_risk_score": cls_factor,
        },
    )


# ── Fire: residential ────────────────────────────────────────────────────────
# Domain: Standard Fire & Allied Perils on a dwelling. Risk drivers are
# construction type, building age, owner-occupied vs tenant, cooking fuel and
# basic protection (extinguisher / smoke alarm). Owner KYC (ID + address)
# applies per the residential checklist. No concern with factory stock,
# fire-safety NOCs or manufacturing processes — those belong to commercial cover.

_FIRE_RES_RISK_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    ("high", 0.9, ("wooden construction", "thatched", "kutcha", "temporary construction", "firecracker", "lpg cylinder heavy use", "old heritage building")),
    ("medium", 0.5, ("semi-pucca", "mixed construction", "brick mortar")),
    ("low", 0.3, ("rcc", "reinforced concrete", "concrete", "fire-resistant", "fire resistant", "new construction")),
]


def _uw_fire_res(ctx: _Ctx) -> GeneralUWDecision:
    cls, cls_factor = _risk_class(ctx.blob, _FIRE_RES_RISK_TABLE)
    year_built = _int_field(ctx.blob, "year built", "built year", "building year", "constructed")
    building_age = (2026 - year_built) if year_built else None

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        (
            "ownership",
            _has(ctx, "ownership", "sale deed", "property deed", types=("property_deed",)),
            "Property ownership proof required",
            RiskSeverity.HIGH,
        ),
        (
            "valuation",
            _has(ctx, "valuation", "property value", "replacement cost", types=("valuation_report",)),
            "Property valuation report required",
            RiskSeverity.HIGH,
        ),
        (
            "construction_type",
            _has(ctx, "construction", "rcc", "concrete", "wooden", "brick", "thatched"),
            "Construction type declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "occupancy_declared",
            _has(ctx, "owner occupied", "owner-occupied", "self occupied", "tenant", "rented", "tenanted", "residential"),
            "Owner-occupied / tenancy declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "building_age",
            year_built is not None,
            "Year of construction required to assess building age",
            RiskSeverity.MODERATE,
        ),
        (
            "protection_measures",
            _has(ctx, "fire extinguisher", "smoke alarm", "smoke detector", "fire alarm", "fire extinguishers"),
            "Basic fire protection (extinguisher / smoke alarm) declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "prior_fire_claims",
            _has(ctx, "claims history", "no claims", "no fire claims", "no prior claim", types=("loss_run",))
            or "no claims" in ctx.blob
            or "no fire losses" in ctx.blob
            or "no prior fire claims" in ctx.blob
            or "no previous claims" in ctx.blob,
            "Prior fire claims history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
        (
            "photos",
            _has(ctx, "photograph", "photos", types=("property_photos",)),
            "Photographs of property required",
            RiskSeverity.MODERATE,
        ),
    ]

    return _finalize(
        ctx,
        family="fire_residential",
        extra=extra,
        conditions=[
            "Residential SFSP — not industrial occupancy",
            "Cover: fire, lightning, explosion and allied perils as per schedule",
        ],
        metadata={
            "occupancy": "residential",
            "fire_risk_class": cls,
            "building_age": building_age,
            "year_built": year_built,
            "domain_risk_score": cls_factor,
        },
    )


# ── Fire: commercial / industrial ────────────────────────────────────────────
# Domain: SFSP on factory / warehouse / office property. Risk drivers are the
# occupancy class, storage of combustible stock, fire-safety compliance (NOC),
# suppression systems and prior fire losses. No concern with residential
# construction details or owner KYC — those belong to residential cover.

_FIRE_COMM_RISK_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "high",
        0.9,
        (
            "fireworks",
            "chemicals",
            "textiles",
            "paper",
            "plastic",
            "petroleum",
            "paint",
            "solvent",
            "match",
            "wood",
            "timber",
            "polythene",
            "rubber",
        ),
    ),
    ("medium", 0.5, ("pharma", "food processing", "warehouse", "electronics", "packaging", "garments")),
    ("low", 0.3, ("office", "software", "general services", "banking", "retail")),
]


def _uw_fire_comm(ctx: _Ctx) -> GeneralUWDecision:
    cls, cls_factor = _risk_class(ctx.blob, _FIRE_COMM_RISK_TABLE)
    combustible = bool(re.search(r"\b(combustible|flammable|chemicals|paper|textiles|plastic|wood|solvent)\b", ctx.blob, re.I))
    protected_text = re.sub(
        r"\bno\s+(fire\s+safety|sprinklers?|hydrant|fire\s+suppression|fire\s+system|extinguishers?)\w*\b",
        "",
        ctx.blob,
        flags=re.I,
    )
    protected = any(kw in protected_text for kw in ("sprinkler", "hydrant", "fire suppression", "fire system", "fire safety", "extinguisher"))

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        (
            "ownership_lease",
            _has(ctx, "ownership", "lease", "factory", "rent agreement", types=("property_deed",)),
            "Property / factory ownership or lease documents required",
            RiskSeverity.HIGH,
        ),
        (
            "gst",
            _has(ctx, "gst", "company registration", types=("company_registration",)),
            "Company registration / GST certificate required",
            RiskSeverity.HIGH,
        ),
        (
            "asset_valuation",
            _has(ctx, "asset valuation", "machinery", "valuation", "building stock", types=("valuation_report",)),
            "Asset valuation (building + machinery + stock) required",
            RiskSeverity.HIGH,
        ),
        (
            "fire_safety",
            _has(ctx, "fire safety", "fire noc", "fire compliance", types=("fire_safety_certificate",)),
            "Fire safety compliance certificate (NOC) required",
            RiskSeverity.HIGH,
        ),
        (
            "stock",
            _has(ctx, "stock", "inventory statement", "raw material", types=("contents_schedule", "schedule_of_values")),
            "Stock / inventory statement required",
            RiskSeverity.HIGH,
        ),
        (
            "occupancy_class",
            _has(ctx, "factory", "warehouse", "office", "industrial", "occupancy", "manufacturing", "godown"),
            "Occupancy class declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "suppression_system",
            _has(ctx, "sprinkler", "hydrant", "fire extinguishers", "fire suppression", "fire system"),
            "Fire suppression / protection system declaration required",
            RiskSeverity.MODERATE,
        ),
        (
            "electrical_safety",
            _has(ctx, "electrical audit", "electrical safety", "earthing", "electrical installation"),
            "Electrical safety declaration required for industrial occupancies",
            RiskSeverity.MODERATE,
        ),
        (
            "prior_fire_losses",
            _has(ctx, "claims history", "fire losses", "no fire loss", "no claims", types=("loss_run",))
            or "no claims" in ctx.blob
            or "no fire loss" in ctx.blob,
            "Prior fire loss history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]
    if combustible and not protected:
        extra.append(
            (
                "combustible_storage",
                False,
                "Combustible stock detected without declared suppression — require sprinklers and storage segregation",
                RiskSeverity.HIGH,
            )
        )

    return _finalize(
        ctx,
        family="fire_commercial",
        extra=extra,
        conditions=[
            "Standard Fire & Allied Perils — commercial / industrial occupancy",
            "Stock on declaration basis; extensions as per schedule",
        ],
        retail_kyc=False,
        metadata={
            "occupancy": "commercial_industrial",
            "fire_risk_class": cls,
            "combustible_storage": combustible,
            "domain_risk_score": cls_factor,
        },
    )


def _scaled_money(blob: str, *labels: str) -> float:
    """Parse an amount with an optional crore/lakh/million/k suffix (Indian filings)."""
    for label in labels:
        m = re.search(
            rf"{re.escape(label)}\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(crore|crs?|lakh|lacs?|k|million|mn)?",
            blob,
            re.I,
        )
        if not m:
            continue
        try:
            value = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        suffix = (m.group(2) or "").strip().lower()
        if suffix in {"crore", "cr", "crs"}:
            value *= 10_000_000
        elif suffix in {"lakh", "lac", "lacs"}:
            value *= 100_000
        elif suffix == "k":
            value *= 1_000
        elif suffix in {"million", "mn"}:
            value *= 1_000_000
        return value
    return 0.0


def _risk_class(blob: str, table: Sequence[tuple[str, float, tuple[str, ...]]]) -> tuple[str, float]:
    """Highest-factor class whose keywords appear in the blob; else the table's lowest."""
    lowest = min(table, key=lambda row: row[1])
    best_id, best_factor = lowest[0], lowest[1]
    for cid, factor, keywords in table:
        if factor > best_factor and any(kw in blob for kw in keywords):
            best_id, best_factor = cid, factor
    return best_id, best_factor


def _claims_severity(blob: str) -> str | None:
    """Classify declared claims history by severity; None when nothing declared."""
    if not re.search(r"claim|loss run|incident", blob, re.I):
        return None
    if re.search(r"\b(death|fatal|paralysis|permanent disability|catastrophic)\b", blob, re.I):
        return "critical"
    if re.search(r"\b(bodily injury|injury|malpractice|negligence|lawsuit|sued|settled claim|defective)\b", blob, re.I):
        return "high"
    return "medium"


# ── Liability: professional indemnity ────────────────────────────────────────
# Domain: negligence in a professional's services. Risk drivers are the
# profession's inherent claim severity, capacity (limit vs gross fees),
# retroactive coverage continuity, and supervision of staff professionals.

_PI_RISK_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "high",
        0.85,
        (
            "surgery",
            "surgeon",
            "obstetric",
            "anaesthes",
            "neuro",
            "cardiolog",
            "lawyer",
            "advocate",
            "litigation",
            "chartered accountant",
            "auditor",
            "architect",
            "structural",
            "investment advisor",
            "stock broker",
            "sebi",
            "fund manager",
            "financial adviser",
        ),
    ),
    (
        "medium",
        0.5,
        ("consultant", "consulting", "accountant", "tax adviser", "it services", "software", "technology", "designer", "engineer", "media", "advertising", "real estate", "realtor"),
    ),
    ("low", 0.3, ("trainer", "coach", "recruitment", "marketing", "hr", "general consulting")),
]


def _uw_pi(ctx: _Ctx) -> GeneralUWDecision:
    cls, cls_factor = _risk_class(ctx.blob, _PI_RISK_TABLE)
    fees = _scaled_money(ctx.blob, "gross fees", "gross receipts", "annual fees", "fees income", "turnover")
    limit = _scaled_money(ctx.blob, "indemnity limit", "limit of indemnity", "sum insured", "cover limit")
    severity = _claims_severity(ctx.blob)
    staff = bool(re.search(r"\b(associates|paralegal|nurses|staff|employees|juniors)\b", ctx.blob, re.I))
    supervision = bool(re.search(r"\b(supervision|peer review|qa|quality control|oversight|check and balance)\b", ctx.blob, re.I))

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        (
            "license",
            _has(ctx, "professional license", "medical council", "bar council", "ca license", "icai", "license number", types=("professional_license",)),
            "Professional license / registration is mandatory",
            RiskSeverity.HIGH,
        ),
        (
            "practice_registration",
            _has(ctx, "practice registration", "business registration", "firm registration", "gst", types=("company_registration",)),
            "Business / practice registration proof required",
            RiskSeverity.HIGH,
        ),
        (
            "fees_declared",
            fees > 0 or _has(ctx, "gross fees", "gross receipts", "annual fees", "fees income", "turnover"),
            "Gross fees / revenue must be declared for the limit-capacity check",
            RiskSeverity.HIGH,
        ),
        (
            "claims_declared",
            _has(ctx, "claims history", "no claims", "no prior claims", "nil claims", "loss run", types=("loss_run",)) or "no claim" in ctx.blob,
            "Claims history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]

    if cls == "high":
        extra.append(("profession_risk_class", False, "High-risk profession class detected — specialist PI terms required", RiskSeverity.HIGH))
    fees_ratio: float | None = None
    if fees > 0 and limit > 0:
        fees_ratio = limit / fees
        if fees_ratio > 5.0:
            extra.append(("limit_vs_fees", False, f"Indemnity limit {fees_ratio:.1f}x gross fees — beyond the 5x capacity band", RiskSeverity.HIGH))
    if staff and not supervision:
        extra.append(("staff_supervision", False, "Supervising / QA controls for staff professionals not declared", RiskSeverity.MODERATE))
    if severity in {"high", "critical"}:
        extra.append(("claims_severity", False, f"Prior claim with '{severity}' severity — refer for specialist assessment", RiskSeverity.HIGH))

    ratio = round(fees_ratio, 2) if fees_ratio is not None else None
    score = round(
        min(1.0, 0.4 * cls_factor + 0.3 * (0.9 if severity in {"high", "critical"} else 0.1) + 0.2 * (0.8 if ratio and ratio > 5 else 0.1) + 0.1 * (0.8 if staff and not supervision else 0.1)),
        3,
    )
    return _finalize(
        ctx,
        family="professional_indemnity",
        extra=extra,
        conditions=[
            "Claims-made basis — report circumstances that may give rise to a claim promptly",
            "Retroactive date must predate the start of continuous professional practice",
        ],
        metadata={
            "profession_risk_class": cls,
            "gross_fees": fees,
            "indemnity_limit": limit,
            "limit_fees_ratio": ratio,
            "domain_risk_score": score,
        },
    )


# ── Liability: public liability ──────────────────────────────────────────────
# Domain: third-party bodily injury / property damage from operations. Risk
# drivers are the occupancy hazard class, crowd or public-footfall exposure,
# limit vs turnover, safety controls, and prior third-party claim severity.

_PUBLIC_HAZARD_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "high",
        0.85,
        (
            "fireworks",
            "petrochemical",
            "flammable",
            "explosive",
            "demolition",
            "amusement park",
            "chemical plant",
            "fuel station",
            "petrol",
            "lpg",
            "cng",
            "event",
            "festival",
            "concert",
            "exhibition",
            "fair",
            "crowd",
        ),
    ),
    (
        "medium",
        0.5,
        (
            "restaurant",
            "hotel",
            "retail",
            "supermarket",
            "warehouse",
            "logistics",
            "factory",
            "manufacturing",
            "food",
            "bakery",
            "gym",
            "cinema",
            "school",
            "hospital",
            "clinic",
            "cafe",
            "showroom",
            "store",
        ),
    ),
    ("low", 0.25, ("office", "consulting", "software", "it", "administration", "call center", "trading", "import", "export")),
]


def _uw_public_liab(ctx: _Ctx) -> GeneralUWDecision:
    cls, cls_factor = _risk_class(ctx.blob, _PUBLIC_HAZARD_TABLE)
    turnover = _scaled_money(ctx.blob, "turnover", "annual turnover", "gross turnover", "projected turnover")
    limit = _scaled_money(ctx.blob, "indemnity limit", "limit of indemnity", "sum insured", "any one accident", "aggregate")
    severity = _claims_severity(ctx.blob)
    open_to_public = bool(re.search(r"\b(open to public|retail|showroom|restaurant|cafe|customers|walk-in|footfall|visitors)\b", ctx.blob, re.I))
    crowd = bool(re.search(r"\b(event|festival|concert|exhibition|fair|large gathering|temporary structure)\b", ctx.blob, re.I))
    safety = bool(re.search(r"\b(safety|fire noc|first aid|safety audit|trained staff|insurance of contractors|barricade)\b", ctx.blob, re.I))

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        (
            "company_registration",
            _has(ctx, "gst", "company registration", "business registration", types=("company_registration",)),
            "Company registration / GST required",
            RiskSeverity.HIGH,
        ),
        (
            "premises_proof",
            _has(ctx, "lease", "rent agreement", "premises", "ownership", "property tax", types=("property_deed",)),
            "Business premises ownership / lease proof required",
            RiskSeverity.HIGH,
        ),
        (
            "operations_declared",
            _has(ctx, "nature of business", "operations", "description of business", "business activity"),
            "Nature of business declaration required",
            RiskSeverity.HIGH,
        ),
        (
            "third_party_claims_declared",
            _has(ctx, "claims history", "no claims", "nil claims", "loss run", "third party", types=("loss_run",)) or "no claim" in ctx.blob,
            "Third-party claims history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]

    if cls == "high":
        extra.append(("occupancy_hazard_class", False, "High-hazard operations detected — public liability exposure warrants referral", RiskSeverity.HIGH))
    if crowd:
        extra.append(("crowd_operations", False, "Crowd / event exposure detected — separate public-event terms required", RiskSeverity.HIGH))
    elif open_to_public:
        extra.append(("public_access_exposure", False, "Premises open to the public — third-party footfall exposure", RiskSeverity.MODERATE))
    if turnover > 0 and limit > 0 and limit > turnover:
        extra.append(("limit_vs_turnover", False, f"Indemnity limit {limit:,.0f} exceeds declared turnover {turnover:,.0f}", RiskSeverity.MODERATE))
    if cls == "medium" and not safety:
        extra.append(("safety_controls", False, "Safety controls / fire NOC not declared for operational premises", RiskSeverity.MODERATE))
    if severity in {"high", "critical"}:
        extra.append(("third_party_claims_severity", False, f"Prior third-party claim severity '{severity}' — refer", RiskSeverity.HIGH))

    ratio = round(limit / turnover, 2) if turnover > 0 and limit > 0 else None
    score = round(
        min(
            1.0,
            0.4 * cls_factor + 0.25 * (0.9 if severity in {"high", "critical"} else 0.1) + 0.2 * (0.9 if crowd else 0.6 if open_to_public else 0.1) + 0.15 * (0.8 if ratio and ratio > 1 else 0.1),
        ),
        3,
    )
    return _finalize(
        ctx,
        family="public_liability",
        extra=extra,
        retail_kyc=False,
        conditions=[
            "Cross-liability and non-owned premises coverage included",
            "Indemnity limit applies per event and in the aggregate for the policy period",
        ],
        metadata={
            "occupancy_hazard_class": cls,
            "turnover": turnover,
            "indemnity_limit": limit,
            "limit_turnover_ratio": ratio,
            "domain_risk_score": score,
        },
    )


# ── Liability: product liability ─────────────────────────────────────────────
# Domain: liability for defective products. Risk drivers are the product class
# (food/pharma/chemical/electrical/toys are the hardest), open vs resolved
# recalls, retail vs business distribution reach, and prior claim severity.

_PRODUCT_RISK_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "high",
        0.85,
        (
            "pharma",
            "drug",
            "medicine",
            "vaccine",
            "food",
            "beverage",
            "chemical",
            "pesticide",
            "fertilizer",
            "electrical",
            "electronics",
            "appliance",
            "toy",
            "medical device",
            "syringe",
            "alcohol",
            "auto part",
            "tyre",
            "battery",
            "pressure vessel",
            "gas cylinder",
        ),
    ),
    (
        "medium",
        0.5,
        ("cosmetic", "personal care", "machinery", "equipment", "paint", "building material", "cement", "furniture", "textile", "garment"),
    ),
    ("low", 0.25, ("stationery", "packaging", "paper", "office supply", "book")),
]


def _uw_prod_liab(ctx: _Ctx) -> GeneralUWDecision:
    cls, cls_factor = _risk_class(ctx.blob, _PRODUCT_RISK_TABLE)
    severity = _claims_severity(ctx.blob)
    open_recall = "recall" in ctx.blob and not re.search(r"\b(no recall|nil recall|resolved|closed|remediated)\b", ctx.blob, re.I)
    prior_recall = bool(re.search(r"\b(prior recall|recall history|previous recall|recalled)\b", ctx.blob, re.I))
    retail = bool(re.search(r"\b(retail|supermarket|e-commerce|online sale|public sale|consumers|b2c|household)\b", ctx.blob, re.I))
    imported = bool(re.search(r"\bimport(ed|s)?\b", ctx.blob, re.I))
    import_qc = bool(re.search(r"\b(inspection|qc|quality control|batch test)\b", ctx.blob, re.I))

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        (
            "business_entity",
            _has(ctx, "gst", "company registration", "business registration", types=("company_registration",)),
            "Company registration / GST required",
            RiskSeverity.HIGH,
        ),
        (
            "product_specs",
            _has(ctx, "product details", "product catalog", "sku", "product specification", "specification"),
            "Product details / catalog required",
            RiskSeverity.HIGH,
        ),
        (
            "manufacturing_license",
            _has(ctx, "manufacturing license", "factory license", "fssai", "gmp", "cdsco", types=("manufacturing_license",)),
            "Manufacturing license required for manufacturer / branded distributor",
            RiskSeverity.HIGH,
        ),
        (
            "quality_certification",
            _has(ctx, "iso", "bis", "quality cert", "fssai", "gmp", "ce ", "halal", types=("quality_certification",)) or True,
            "Quality certification (ISO/BIS/FSSAI/GMP) if applicable",
            RiskSeverity.MODERATE,
        ),
        (
            "recall_declared",
            _has(ctx, "recall history", "no recall", "nil recall", "claims history", types=("loss_run",)) or "no recall" in ctx.blob,
            "Product recall / claims history must be declared",
            RiskSeverity.HIGH,
        ),
    ]

    if open_recall:
        extra.append(("open_recall", False, "Open / active product recall — decline until remediation is verified", RiskSeverity.CRITICAL))
    if prior_recall:
        extra.append(("prior_recall", False, "Prior recall history — require recall-management plan and enhanced QC", RiskSeverity.HIGH))
    if cls == "high":
        extra.append(("product_risk_class", False, "High-risk product class detected — specialist product liability terms required", RiskSeverity.HIGH))
    if retail:
        extra.append(("distribution_channel", False, "Products sold to the public / retail — broad consumer exposure", RiskSeverity.MODERATE))
    if imported and not import_qc:
        extra.append(("import_controls", False, "Imported products without declared inspection / QC of imported batches", RiskSeverity.MODERATE))
    if severity in {"high", "critical"}:
        extra.append(("product_claims_severity", False, f"Prior product claim severity '{severity}' — refer", RiskSeverity.HIGH))

    score = round(
        min(1.0, 0.4 * cls_factor + 0.25 * (0.95 if open_recall else 0.7 if prior_recall else 0.1) + 0.2 * (0.9 if severity in {"high", "critical"} else 0.1) + 0.15 * (0.8 if retail else 0.1)),
        3,
    )
    return _finalize(
        ctx,
        family="product_liability",
        extra=extra,
        retail_kyc=False,
        conditions=[
            "Occurrence-based; cover attaches to products sold during the policy period",
            "Territory of sale as declared in the schedule",
        ],
        metadata={
            "product_risk_class": cls,
            "distribution": "retail" if retail else "business",
            "open_recall": open_recall,
            "prior_recall": prior_recall,
            "domain_risk_score": score,
        },
    )


# ── Cyber: data breach cover ────────────────────────────────────────────────
# Domain: first-party breach response + regulatory notification + third-party
# liability for exposed personal data. Risk drivers are the volume and
# sensitivity of data handled, the security policy behind it, and the severity
# of any prior breach. No concern with network topology, remote access, or
# ransomware demand mechanics — those belong to the ransomware cover.

_CYBER_BREACH_RISK_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "high",
        0.9,
        (
            "hospital",
            "healthcare",
            "clinic",
            "pharma",
            "bank",
            "fintech",
            "payment",
            "insurance",
            "government",
            "public sector",
            "telecom",
            "children",
            "edtech",
            "credit card",
            "medical records",
        ),
    ),
    (
        "medium",
        0.5,
        ("saas", "software", "e-commerce", "retail", "hr", "recruitment", "marketing", "college", "university", "travel"),
    ),
    ("low", 0.3, ("manufacturing", "logistics", "construction", "small office", "general consulting")),
]


def _cyber_severity(blob: str) -> str | None:
    """Classify declared cyber incident history; None when nothing (or nothing affirmative) declared."""
    negated = re.sub(
        r"\bno\s+(?:prior\s+|previous\s+|reported\s+)?(?:cyber\s+|data\s+)?(incident|breach|attack|ransomware|ransom|malware|phishing)s?\b",
        "",
        blob,
        flags=re.I,
    )
    if not re.search(r"incident|breach|ransom|attack|malware|phishing", negated, re.I):
        return None
    if re.search(r"\b(ransomware|ransom|extortion|exfiltration|data leaked|critical incident|multiple incidents|repeated incidents)\b", negated, re.I):
        return "critical"
    if re.search(r"\b(phishing|malware|data breach|breach|attack|downtime|outage)\b", negated, re.I):
        return "high"
    return "medium"


def _record_count(blob: str) -> int | None:
    """Parse a declared data volume (records / data subjects / patients)."""
    m = re.search(r"\b(records|data subjects|patients)\b\s*[:=]?\s*([\d,]+)", blob, re.I)
    if m:
        return int(m.group(2).replace(",", ""))
    m = re.search(r"([\d,]+)\s*\b(records|data subjects|patients)\b", blob, re.I)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def _uw_cyber_breach(ctx: _Ctx) -> GeneralUWDecision:
    cls, cls_factor = _risk_class(ctx.blob, _CYBER_BREACH_RISK_TABLE)
    severity = _cyber_severity(ctx.blob)
    records = _record_count(ctx.blob)
    sensitive = bool(
        re.search(
            r"\b(medical records|health data|financial data|credit card|cardholder|minor|children data|salary data|payroll)\b",
            ctx.blob,
            re.I,
        )
    )
    high_volume = bool(records is not None and records >= 100_000)

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        (
            "company_registration",
            _has(ctx, "gst", "company registration", types=("company_registration",)),
            "Company registration / GST certificate required",
            RiskSeverity.HIGH,
        ),
        (
            "data_policy",
            _has(ctx, "data security policy", "data protection policy", "privacy policy", "information security", types=("cyber_questionnaire",)),
            "Data security policy for handled data required",
            RiskSeverity.HIGH,
        ),
        (
            "data_handled",
            _has(ctx, "data handled", "data volume", "records", "data subjects", "customer data", "employee data", "pii"),
            "Details of data handled (customer / employee data volume) required",
            RiskSeverity.HIGH,
        ),
        (
            "data_volume",
            high_volume or (records is not None and records > 0) or _has(ctx, "data volume", "records", "customer data", "employee data", "pii"),
            "Declared data volume (records / data subjects) required",
            RiskSeverity.HIGH,
        ),
        (
            "sensitive_data_controls",
            (not sensitive) or _has(ctx, "encryption", "anonymization", "access control", "consent management", "dpdp", "gdpr", "consent"),
            "Sensitive data (medical / financial / children) requires declared protection controls — encryption, consent, DPDP / GDPR compliance",
            RiskSeverity.HIGH,
        ),
        (
            "breach_history",
            _has(ctx, "incident history", "breach history", "no breach", "no prior incident", types=("loss_run",))
            or "no incident" in ctx.blob
            or "no breach" in ctx.blob
            or "no prior breach" in ctx.blob
            or "no history" in ctx.blob,
            "Past cyber incident / breach history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]
    if severity in {"critical", "high"}:
        extra.append(
            (
                "breach_severity",
                False,
                "Prior breach classified as severe — confirm regulatory notification and remediation before binding",
                RiskSeverity.HIGH,
            )
        )

    return _finalize(
        ctx,
        family="cyber_data_breach",
        extra=extra,
        conditions=[
            "First-party breach response, regulatory notification and third-party liability for exposed personal data",
            "Limit applies per data breach event; annual aggregate sub-limit applies",
        ],
        retail_kyc=False,
        metadata={
            "cyber_cover": "data_breach",
            "breach_exposure_class": cls,
            "data_volume_records": records,
            "sensitive_data": sensitive,
            "breach_severity": severity,
            "domain_risk_score": cls_factor,
        },
    )


# ── Cyber: cyberattack / ransomware cover ───────────────────────────────────
# Domain: first-party extortion + attack-driven business interruption. Risk
# drivers are network visibility, existing security controls (EDR / MFA /
# backups), remote-access exposure (RDP / public-facing systems) and the
# severity of any prior ransomware event. No concern with data-volume counts,
# record sensitivity or regulatory posture — those belong to the breach cover.

_CYBER_RANSOM_RISK_TABLE: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "high",
        0.9,
        (
            "managed service provider",
            "msp",
            "cloud",
            "data center",
            "fintech",
            "bank",
            "hospital",
            "healthcare",
            "logistics",
            "manufacturing",
            "law firm",
            "critical infrastructure",
            "infrastructure",
        ),
    ),
    (
        "medium",
        0.5,
        ("e-commerce", "saas", "software", "retail", "telecom", "media", "pharma", "real estate"),
    ),
    ("low", 0.3, ("small office", "education", "general services", "non-critical it")),
]


def _uw_cyber_ransom(ctx: _Ctx) -> GeneralUWDecision:
    cls, cls_factor = _risk_class(ctx.blob, _CYBER_RANSOM_RISK_TABLE)
    severity = _cyber_severity(ctx.blob)
    remote = bool(re.search(r"\b(rdp|remote access|vpn|public-facing|public facing|exposed port|remote desktop)\b", ctx.blob, re.I))
    backups = bool(re.search(r"\b(offline backups?|immutable backups?|3-2-1 backups?|air-gapped|disaster recovery|backup policy|data restoration)\b", ctx.blob, re.I))

    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        (
            "business_registration",
            _has(ctx, "gst", "company registration", types=("company_registration",)),
            "Company registration / GST certificate required",
            RiskSeverity.HIGH,
        ),
        (
            "network_visibility",
            _has(ctx, "it infrastructure", "network details", "network", "systems inventory", "asset inventory", types=("cyber_questionnaire",)),
            "IT infrastructure & network details required",
            RiskSeverity.HIGH,
        ),
        (
            "controls",
            _has(ctx, "cybersecurity measures", "mfa", "multi-factor", "endpoint", "edr", "antivirus", "firewall", "controls", types=("cyber_questionnaire",)),
            "Existing cybersecurity measures declaration required",
            RiskSeverity.HIGH,
        ),
        (
            "backup_discipline",
            backups or _has(ctx, "backup policy", "backup procedure", "recovery plan", "data restoration"),
            "Offline / immutable backup and recovery plan required for ransomware survival",
            RiskSeverity.MODERATE,
        ),
        (
            "ransom_history",
            _has(ctx, "incident", "breach history", "ransomware", "attack history", types=("loss_run",))
            or "no incident" in ctx.blob
            or "no attack" in ctx.blob
            or "no prior incident" in ctx.blob
            or "no prior attack" in ctx.blob,
            "Past incident / breach history required (or explicit nil)",
            RiskSeverity.MODERATE,
        ),
    ]
    if remote:
        extra.append(
            (
                "remote_access_exposure",
                False,
                "RDP / public-facing remote access detected — require MFA and access restrictions before binding",
                RiskSeverity.HIGH,
            )
        )
    if severity in {"critical", "high"}:
        extra.append(
            (
                "ransom_severity",
                False,
                "Prior ransomware / extortion classified as severe — require IR retainer confirmation before binding",
                RiskSeverity.HIGH,
            )
        )

    return _finalize(
        ctx,
        family="cyber_ransomware",
        extra=extra,
        conditions=[
            "Extortion and first-party ransomware with 48-hour notification of any ransom demand",
            "Sub-limits apply for extortion payment and forensic investigation",
        ],
        retail_kyc=False,
        metadata={
            "cyber_cover": "ransomware",
            "ransom_exposure_class": cls,
            "has_remote_access": remote,
            "backup_discipline": backups,
            "ransom_severity": severity,
            "domain_risk_score": cls_factor,
        },
    )


# ── Crop / animal / event / title / mortgage / provider ─────────────────────

_CROP_YIELD_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    (
        "high",
        1.5,
        ("irrigated", "canal irrigation", "borewell", "mono-crop", "paddy", "cotton", "sugarcane", "horticulture", "high acreage"),
    ),
    ("medium", 1.15, ("maize", "soybean", "groundnut", "semi-irrigated")),
    ("low", 1.0, ("millets", "jowar", "bajra", "drought-resistant", "dry land", "rain-fed hardy")),
)

_CROP_WEATHER_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    (
        "high",
        1.55,
        ("polyhouse", "greenhouse", "grape", "hail", "heatwave", "cold wave", "deficit rainfall", "excess rainfall", "dry spell"),
    ),
    ("medium", 1.15, ("cotton", "maize", "soybean", "open field")),
    ("low", 1.0, ("resistant", "rain-fed hardy", "millets", "tolerant")),
)

_LIVESTOCK_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.6, ("jersey", "holstein", "friesian", "high milk yield", "imported breed", "high value breed")),
    ("medium", 1.2, ("cross-bred", "crossbred", "indigenous improved")),
    ("low", 1.0, ("local breed", "indigenous", "drought breed", "gir", "sahiwal")),
)

_PET_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.7, ("purebred", "pedigree", "imported breed", "exotic", "brachycephalic", "premium breed")),
    ("medium", 1.25, ("cross-breed", "mixed breed", "indian breed")),
    ("low", 1.0, ("mongrel", "indian", "street", "non-pedigree")),
)

_WEDDING_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.5, ("destination wedding", "outdoor", "500 guests", "500+ guests", "large venue", "high budget", "multiday")),
    ("medium", 1.15, ("banquet", "medium budget", "indoor venue")),
    ("low", 1.0, ("small function", "intimate", "home ceremony", "small budget")),
)

_CONCERT_EVENT_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.7, ("outdoor", "large crowd", "10000", "10,000", "open field", "celebrity", "multi-day", "international artist")),
    ("medium", 1.3, ("indoor", "medium capacity", "arena")),
    ("low", 1.0, ("small venue", "intimate", "small ticketed", "club")),
)

_TITLE_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.6, ("litigation", "dispute", "encumbrance", "fraud", "forged", "defective title", "challenged")),
    ("medium", 1.2, ("inherited", "gift deed", "long chain", "partition")),
    ("low", 1.0, ("clean title", "registered sale deed", "clear chain", "marketable title")),
)

_MORTGAGE_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.6, ("high ltv", "subprime", "second loan", "default", "overdue", "prepayment")),
    ("medium", 1.2, ("standard home loan", "lumpy", "long tenure")),
    ("low", 1.0, ("low ltv", "clean repayment", "first loan", "salaried")),
)

_INSURER_PSU_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.3, ("loss-making", "negative solvency", "underwriting losses", "declining market share")),
    ("medium", 1.15, ("moderate solvency", "stable")),
    ("low", 1.0, ("strong solvency", "government backing", "well-capitalized")),
)

_INSURER_PRIVATE_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.5, ("new entrant", "low solvency", "rapid growth", "concentrated book", "startup")),
    ("medium", 1.2, ("established", "moderate solvency")),
    ("low", 1.0, ("well-capitalized", "strong solvency", "diversified", "profitable")),
)

_REINSURANCE_RISK_TABLE: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("high", 1.8, ("catastrophe", "nat cat", "property cat", "high severity", "concentrated", "new cedant")),
    ("medium", 1.25, ("treaty mix", "moderate portfolio", "regional")),
    ("low", 1.0, ("well-diversified", "established cedant", "low exposure", "global")),
)


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
