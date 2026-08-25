"""Personal lines underwriting: homeowners, auto, and life risk factors."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import PERSONAL_LINES, InsuranceLine

_DOC_SEP = "\n#\n"


def _blob(bundle: SubmissionBundle) -> str:
    parts: list[str] = []
    if bundle.structured:
        parts.append(str(bundle.structured.model_dump() if hasattr(bundle.structured, "model_dump") else bundle.structured))
    for doc in bundle.unstructured or []:
        parts.append(getattr(doc, "raw_text", "") or "")
        parts.append(getattr(doc, "filename", "") or getattr(doc, "source", "") or "")
        ef = getattr(doc, "extracted_fields", None) or {}
        if isinstance(ef, dict):
            parts.append(str(ef))
    return _DOC_SEP.join(parts).lower()


_NEGATION_STARTERS = (
    "no",
    "not",
    "non ",
    "none",
    "never",
    "without",
    "denies",
    "denied",
    "deny",
    "negative",
    "free of",
    "ruled out",
    "r/o",
)

_NEGATION_SEGMENT_RE = re.compile(
    r"(?:^|(?<=[.;!?\n#]))\s*(" + "|".join(re.escape(s) for s in _NEGATION_STARTERS) + r")\b[^\n.;!?#]*",
    re.I,
)


def strip_negated_clauses(text: str) -> str:
    """Remove self-negated segments ('no prior X', 'denies Y') from a blob.

    Underwriting knockouts/referrals must fire on AFFIRMATIVE disclosures only;
    negated histories are the classic false-decline source. Segment boundaries
    are sentence punctuation and newlines so a negation never reaches across
    documents or fields.
    """
    return _NEGATION_SEGMENT_RE.sub("", text)


_MONEY_SUFFIX_MULT = {"k": 1_000.0, "m": 1_000_000.0, "mm": 1_000_000.0, "bn": 1_000_000_000.0, "b": 1_000_000_000.0}
_MONEY_WORD_MULT = {"thousand": 1_000.0, "million": 1_000_000.0, "billion": 1_000_000_000.0}


def _money(blob: str, *labels: str) -> float:
    for label in labels:
        m = re.search(
            rf"{re.escape(label)}\s*[:=]?\s*(?:usd|eur|gbp|cad)?\s*\$?\s*"
            rf"([\d,]+(?:\.\d+)?)"
            rf"(?:\s*(?P<sym>k|mm|bn|b|m)(?![a-z])|\s*(?P<word>thousand|million|billion)\b)?",
            blob,
            re.I,
        )
        if m:
            try:
                value = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            mult = _MONEY_SUFFIX_MULT.get((m.group("sym") or "").lower())
            if mult is None:
                mult = _MONEY_WORD_MULT.get((m.group("word") or "").lower(), 1.0)
            return value * mult
    return 0.0


def _has_strong_commercial_signals(blob: str) -> bool:
    """True when the package is clearly a commercial (not personal) submission."""
    commercial_markers = (
        "commercial lines",
        "commercial property",
        "commercial general liability",
        "general liability",
        "workers compensation",
        "workers' compensation",
        "schedule of values",
        "schedule of value",
        "named insured",
        "grossvehicleweight",
        "gross vehicle weight",
        "commercial auto",
        "businessowners",
        "bop ",
        "naics",
        "fein",
        "tax id",
        "warehouse",
        "total insurable value",
        "acord commercial",
        "certificate of insurance",
        "loss run",
        "inc.",
        "llc",
        "corp.",
        "corporation",
    )
    hits = sum(1 for k in commercial_markers if k in blob)
    # Fleet / heavy equipment also screams commercial even with VINs present
    fleet_markers = ("kenworth", "peterbilt", "freightliner", "reefer", "tractor", "trailer", "fleet count", "vehicle schedule")
    fleet_hits = sum(1 for k in fleet_markers if k in blob)
    return hits >= 2 or fleet_hits >= 2 or ("commercial" in blob and hits >= 1)


def _detect_line_from_content(blob: str) -> InsuranceLine:
    """Content-only LOB inference (blob already lowercased)."""
    commercial = _has_strong_commercial_signals(blob)

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

    # Key person before life — "face amount" appears on both
    if (
        any(
            k in blob
            for k in (
                "key person",
                "key-person",
                "keyman insurance",
                "key man insurance",
                "insurance_line: key_person",
                "insurance_line=key_person",
            )
        )
        and not property_heavy
    ):
        return InsuranceLine.KEY_PERSON

    if (
        any(
            k in blob
            for k in (
                "health insurance",
                "mediclaim",
                "family floater",
                "critical illness",
                "personal accident",
                "hospital cash",
                "insurance_line: health",
                "insurance_line=health",
                "disability income",
            )
        )
        and not commercial
    ):
        return InsuranceLine.HEALTH

    if (
        any(
            k in blob
            for k in (
                "third-party only",
                "third party only",
                "two-wheeler insurance",
                "commercial vehicle insurance",
                "domestic travel insurance",
                "international travel insurance",
                "marine cargo",
                "marine hull",
                "title insurance",
                "wedding insurance",
                "pet insurance",
                "yield-based crop",
                "weather-based crop",
                "insurance_line: general",
                "insurance_line=general",
            )
        )
        and not commercial
    ):
        return InsuranceLine.GENERAL

    if (
        any(
            k in blob
            for k in (
                "life insurance application",
                "term life",
                "whole life",
                "face amount",
                "mortality",
                "beneficiary designation",
                "paramedical exam",
                "insurance_line: life",
                "line: life",
                "insurance_line=life",
            )
        )
        and not commercial
    ):
        return InsuranceLine.LIFE

    # Personal auto: require explicit personal-auto language — never VIN alone
    personal_auto_explicit = any(
        k in blob
        for k in (
            "personal auto",
            "personal_auto",
            "auto application",
            "insurance_line: personal_auto",
            "line: personal_auto",
            "insurance_line=personal_auto",
            "pleasure use",
            "commute to work",
        )
    )
    personal_auto_soft = any(
        k in blob
        for k in (
            "drivers license",
            "driver's license",
            "motor vehicle report",
            "mvr /",
            "mvr report",
            "rideshare",
            "vehicle year",
        )
    )
    if personal_auto_explicit and not commercial:
        return InsuranceLine.PERSONAL_AUTO
    if personal_auto_soft and not commercial and ("vin:" in blob or "vin " in blob):
        return InsuranceLine.PERSONAL_AUTO

    if (
        any(
            k in blob
            for k in (
                "homeowners application",
                "homeowners policy",
                "dwelling coverage",
                "ho-3",
                "ho3",
                "residential dwelling",
                "personal homeowners",
                "insurance_line: personal_homeowners",
                "line: personal_homeowners",
                "insurance_line=personal_homeowners",
            )
        )
        and not commercial
    ):
        return InsuranceLine.PERSONAL_HOMEOWNERS

    # True D&O — avoid matching "and observed" via naive "d and o"
    if (
        any(
            k in blob
            for k in (
                "d&o",
                "directors and officers",
                "directors & officers",
                "management liability",
                "d and o liability",
                "d and o application",
                "insurance_line: directors_and_officers",
                "insurance_line=directors_and_officers",
            )
        )
        and not property_heavy
    ):
        return InsuranceLine.DIRECTORS_AND_OFFICERS

    if (
        any(
            k in blob
            for k in (
                "trade credit",
                "accounts receivable aging",
                "buyer credit",
                "credit insurance",
                "insurance_line: trade_credit",
                "insurance_line=trade_credit",
            )
        )
        and not property_heavy
    ):
        return InsuranceLine.TRADE_CREDIT

    if (
        any(
            k in blob
            for k in (
                "errors and omissions",
                "errors & omissions",
                "e&o application",
                "professional liability",
                "acord 126",
                "insurance_line: errors_and_omissions",
                "insurance_line=errors_and_omissions",
            )
        )
        and not property_heavy
    ):
        return InsuranceLine.ERRORS_AND_OMISSIONS

    if commercial:
        # Multi-line commercial packages often mention WC in passing — prefer
        # property/SOV/CGL as the primary rating line when those dominate.
        gl_heavy = "general liability" in blob or "commercial general liability" in blob
        wc_only = ("workers comp" in blob or "workers' compensation" in blob or "workers compensation" in blob) and not property_heavy and not gl_heavy
        if wc_only:
            return InsuranceLine.WORKERS_COMP
        if "businessowners" in blob or " bop " in blob or "bop policy" in blob:
            return InsuranceLine.BOP
        if gl_heavy and not property_heavy:
            return InsuranceLine.GENERAL_LIABILITY
        return InsuranceLine.COMMERCIAL_PROPERTY

    return InsuranceLine.COMMERCIAL_PROPERTY


def detect_insurance_line(text_blob: str = "", product_hint: str = "") -> InsuranceLine:
    """Infer LOB from package text.

    Package content wins over a conflicting product hint. Commercial fleets
    with VIN / vehicle schedules are never priced as personal_auto — for every
    submission (uploads and demos), not Pacific Coast only.
    """
    from insureflow.rating.models import COMMERCIAL_SPECIALTY_LINES

    hint = (product_hint or "").strip().lower().replace("-", "_").replace(" ", "_")
    hinted = parse_insurance_line(hint) if hint else None
    # Detect from document text only so the hint cannot seed false keywords
    blob = (text_blob or "").lower()
    content = _detect_line_from_content(blob)
    commercial = _has_strong_commercial_signals(blob)

    if hinted is None:
        return content

    # Conflicting hint: trust the package
    if commercial and hinted in PERSONAL_LINES:
        return content
    if content in PERSONAL_LINES and hinted not in PERSONAL_LINES:
        return content

    # Specialty hub tags (Trade Credit, E&O, D&O, Key Person) win unless the
    # package is clearly a property/SOV submission.
    if hinted in COMMERCIAL_SPECIALTY_LINES:
        property_heavy = any(
            k in blob
            for k in (
                "schedule of values",
                "commercial property",
                "building value",
                "total insurable value",
                "acord 140",
            )
        )
        if property_heavy and content == InsuranceLine.COMMERCIAL_PROPERTY:
            return content
        return hinted

    return hinted


def parse_insurance_line(value: str | None) -> InsuranceLine | None:
    if not value:
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "home": InsuranceLine.PERSONAL_HOMEOWNERS,
        "homeowners": InsuranceLine.PERSONAL_HOMEOWNERS,
        "personal_home": InsuranceLine.PERSONAL_HOMEOWNERS,
        "ho": InsuranceLine.PERSONAL_HOMEOWNERS,
        "auto": InsuranceLine.PERSONAL_AUTO,
        "personal_auto": InsuranceLine.PERSONAL_AUTO,
        "car": InsuranceLine.PERSONAL_AUTO,
        "life": InsuranceLine.LIFE,
        "term_life": InsuranceLine.LIFE,
        "health": InsuranceLine.HEALTH,
        "mediclaim": InsuranceLine.HEALTH,
        "family_floater": InsuranceLine.HEALTH,
        "critical_illness": InsuranceLine.HEALTH,
        "personal_accident": InsuranceLine.HEALTH,
        "hospital_cash": InsuranceLine.HEALTH,
        "general": InsuranceLine.GENERAL,
        "motor": InsuranceLine.GENERAL,
        "travel": InsuranceLine.GENERAL,
        "title_insurance": InsuranceLine.GENERAL,
        # Commercial specialty hub aliases
        "do": InsuranceLine.DIRECTORS_AND_OFFICERS,
        "d&o": InsuranceLine.DIRECTORS_AND_OFFICERS,
        "d_and_o": InsuranceLine.DIRECTORS_AND_OFFICERS,
        "directors_officers": InsuranceLine.DIRECTORS_AND_OFFICERS,
        "management_liability": InsuranceLine.DIRECTORS_AND_OFFICERS,
        "eo": InsuranceLine.ERRORS_AND_OMISSIONS,
        "e&o": InsuranceLine.ERRORS_AND_OMISSIONS,
        "e_and_o": InsuranceLine.ERRORS_AND_OMISSIONS,
        "professional_liability": InsuranceLine.ERRORS_AND_OMISSIONS,
        "errors_omissions": InsuranceLine.ERRORS_AND_OMISSIONS,
        "keyman": InsuranceLine.KEY_PERSON,
        "key_man": InsuranceLine.KEY_PERSON,
        "workerscompensation": InsuranceLine.WORKERS_COMP,
        "workers_compensation": InsuranceLine.WORKERS_COMP,
        "property": InsuranceLine.COMMERCIAL_PROPERTY,
        "property_bi": InsuranceLine.COMMERCIAL_PROPERTY,
        "commercial": InsuranceLine.COMMERCIAL_PROPERTY,
        "cyber": InsuranceLine.CYBER,
        "cyber_liability": InsuranceLine.CYBER,
        "tech_eo_cyber": InsuranceLine.CYBER,
        "commercial_auto": InsuranceLine.COMMERCIAL_AUTO,
        "fleet": InsuranceLine.COMMERCIAL_AUTO,
        "hnoa": InsuranceLine.COMMERCIAL_AUTO,
        "garage_liability": InsuranceLine.COMMERCIAL_AUTO,
        "non_trucking_liability": InsuranceLine.COMMERCIAL_AUTO,
        "inland_marine": InsuranceLine.INLAND_MARINE,
        "motor_truck_cargo": InsuranceLine.INLAND_MARINE,
        "ocean_marine": InsuranceLine.INLAND_MARINE,
        "crime": InsuranceLine.CRIME,
        "builders_risk": InsuranceLine.BUILDERS_RISK,
        "surety": InsuranceLine.SURETY,
        "surety_bonds": InsuranceLine.SURETY,
        "bop": InsuranceLine.BOP,
        "business_owners_policy": InsuranceLine.BOP,
        "cpp": InsuranceLine.COMMERCIAL_PACKAGE,
        "commercial_package": InsuranceLine.COMMERCIAL_PACKAGE,
        "package": InsuranceLine.COMMERCIAL_PACKAGE,
        "pollution": InsuranceLine.POLLUTION,
        "flood": InsuranceLine.FLOOD,
        "earthquake": InsuranceLine.EARTHQUAKE,
        "k_and_r": InsuranceLine.KIDNAP_RANSOM,
        "knr": InsuranceLine.KIDNAP_RANSOM,
        "legal_expenses": InsuranceLine.LEGAL_EXPENSE,
    }
    if normalized in aliases:
        return aliases[normalized]
    try:
        return InsuranceLine(normalized)
    except ValueError:
        return None


def _int_field(blob: str, *labels: str) -> int | None:
    for label in labels:
        m = re.search(rf"{re.escape(label)}\s*[:=]?\s*(\d{{1,4}})", blob, re.I)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


@dataclass
class PersonalHomeFactors:
    dwelling_limit: float = 0.0
    year_built: int | None = None
    construction: str = ""
    protection_class: int | None = None
    has_pool: bool = False
    has_wood_stove: bool = False
    renovations_recent: bool = False
    high_crime_area: bool = False
    coastal_or_cat: bool = False
    prior_claims: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def exposure(self) -> float:
        return self.dwelling_limit

    @property
    def schedule_mod_pct(self) -> float:
        mod = 0.0
        if self.year_built and self.year_built < 1970:
            mod += 12.0
        elif self.year_built and self.year_built < 1990:
            mod += 5.0
        if self.has_pool:
            mod += 8.0
        if self.has_wood_stove:
            mod += 10.0
        if self.renovations_recent:
            mod -= 5.0
        if self.high_crime_area:
            mod += 10.0
        if self.coastal_or_cat:
            mod += 15.0
        if self.protection_class and self.protection_class >= 8:
            mod += 8.0
        elif self.protection_class and self.protection_class <= 3:
            mod -= 5.0
        if "frame" in self.construction:
            mod += 3.0
        if "masonry" in self.construction or "brick" in self.construction:
            mod -= 4.0
        mod += min(self.prior_claims * 7.0, 28.0)
        return mod


@dataclass
class PersonalAutoFactors:
    vehicle_year: int | None = None
    make_model: str = ""
    vehicle_value: float = 0.0
    annual_mileage: int | None = None
    intended_use: str = "personal"
    driver_age: int | None = None
    years_licensed: int | None = None
    violations: int = 0
    at_fault_accidents: int = 0
    high_performance: bool = False
    rideshare: bool = False
    findings: list[Finding] = field(default_factory=list)

    @property
    def exposure(self) -> float:
        return self.vehicle_value or 25_000.0

    @property
    def schedule_mod_pct(self) -> float:
        mod = 0.0
        if self.high_performance:
            mod += 25.0
        if self.rideshare or "rideshare" in self.intended_use:
            mod += 35.0
        if self.annual_mileage and self.annual_mileage > 15_000:
            mod += 8.0
        elif self.annual_mileage and self.annual_mileage < 7_500:
            mod -= 5.0
        if self.driver_age is not None:
            if self.driver_age < 21:
                mod += 40.0
            elif self.driver_age < 25:
                mod += 20.0
            elif self.driver_age >= 70:
                mod += 10.0
        if self.years_licensed is not None and self.years_licensed < 3:
            mod += 15.0
        mod += min(self.violations * 8.0, 32.0)
        mod += min(self.at_fault_accidents * 12.0, 36.0)
        if self.vehicle_year and self.vehicle_year >= 2022:
            mod += 5.0  # newer cars: higher physical damage
        return mod


@dataclass
class LifeFactors:
    face_amount: float = 0.0
    age: int | None = None
    sex: str = ""
    smoker: bool = False
    health_class: str = "standard"  # preferred | standard | substandard
    hazardous_avocation: bool = False
    foreign_travel: bool = False
    criminal_history: bool = False
    income: float = 0.0
    net_worth: float = 0.0
    in_force_face: float = 0.0
    beneficiary_relationship: str = ""
    state: str = ""
    findings: list[Finding] = field(default_factory=list)

    @property
    def exposure(self) -> float:
        return self.face_amount

    @property
    def schedule_mod_pct(self) -> float:
        mod = 0.0
        if self.age is not None:
            if self.age >= 70:
                mod += 40.0
            elif self.age >= 60:
                mod += 20.0
            elif self.age >= 50:
                mod += 8.0
            elif self.age < 30:
                mod -= 5.0
        if self.smoker:
            mod += 50.0
        if self.health_class == "preferred":
            mod -= 15.0
        elif self.health_class == "substandard":
            mod += 35.0
        if self.hazardous_avocation:
            mod += 25.0
        if self.foreign_travel:
            mod += 10.0
        if self.criminal_history:
            mod += 20.0
        if self.face_amount and self.income:
            from insureflow.underwriting.life_financial import income_multiple_for_age

            if self.face_amount > self.income * income_multiple_for_age(self.age):
                mod += 15.0  # financial underwriting stretch
        return mod


def _state_from_blob(blob: str) -> str:
    m = re.search(r"\bstate\s*[:=]\s*([a-z]{2})\b", blob, re.I)
    if m:
        return m.group(1).upper()
    # City, ST ZIP
    m = re.search(r",\s*([a-z]{2})\s+\d{5}", blob, re.I)
    if m:
        return m.group(1).upper()
    return ""


def extract_home_factors(bundle: SubmissionBundle) -> PersonalHomeFactors:
    blob = _blob(bundle)
    f = PersonalHomeFactors(
        dwelling_limit=_money(blob, "dwelling coverage", "dwelling limit", "coverage a", "replacement cost"),
        year_built=_int_field(blob, "year built", "year_built"),
        construction=next((c for c in ("masonry", "brick", "frame", "steel") if c in blob), ""),
        protection_class=_int_field(blob, "protection class", "ppc", "iso ppc"),
        has_pool=any(k in blob for k in ("swimming pool", "has pool", "in-ground pool")),
        has_wood_stove=any(k in blob for k in ("wood stove", "woodstove", "solid fuel")),
        renovations_recent=any(k in blob for k in ("renovation", "upgraded electrical", "new roof", "rewired")),
        high_crime_area=any(k in blob for k in ("high crime", "crime score", "theft prone")),
        coastal_or_cat=any(k in blob for k in ("coastal", "hurricane", "flood zone", "wildfire zone", "cat exposure")),
        prior_claims=len(re.findall(r"prior claim|date of loss|claim #", blob)),
    )
    if f.has_pool:
        f.findings.append(
            Finding(
                title="Swimming pool / special feature",
                description="Pool increases liability and property exposure",
                severity=RiskSeverity.MODERATE,
                category="personal_homeowners",
            )
        )
    if f.coastal_or_cat:
        f.findings.append(
            Finding(
                title="CAT / coastal exposure",
                description="Location has elevated weather or catastrophe risk",
                severity=RiskSeverity.HIGH,
                category="personal_homeowners",
            )
        )
    return f


def extract_auto_factors(bundle: SubmissionBundle) -> PersonalAutoFactors:
    blob = _blob(bundle)
    use = "personal"
    if "rideshare" in blob or "uber" in blob or "lyft" in blob:
        use = "rideshare"
    elif "commercial" in blob and "delivery" in blob:
        use = "delivery"
    f = PersonalAutoFactors(
        vehicle_year=_int_field(blob, "vehicle year", "model year", "year:"),
        make_model="",
        vehicle_value=_money(blob, "vehicle value", "actual cash value", "acv", "msrp"),
        annual_mileage=_int_field(blob, "annual mileage", "miles per year", "odometer annual"),
        intended_use=use,
        driver_age=_int_field(blob, "driver age", "applicant age", "age:"),
        years_licensed=_int_field(blob, "years licensed", "driving experience", "years driving"),
        violations=len(re.findall(r"speeding|violation|ticket|dui|dwi", blob)),
        at_fault_accidents=len(re.findall(r"at-fault|at fault accident", blob)),
        high_performance=any(k in blob for k in ("high-performance", "high performance", "sports car", "turbo", "mustang gt", "corvette")),
        rideshare=use == "rideshare",
    )
    mm = re.search(r"(?:make/?model|vehicle)\s*[:=]\s*([^\n|]{3,60})", blob, re.I)
    if mm:
        f.make_model = mm.group(1).strip()[:80]
    if f.violations or f.at_fault_accidents:
        f.findings.append(
            Finding(
                title="Driving record adverse activity",
                description=f"{f.violations} violation signal(s), {f.at_fault_accidents} at-fault signal(s)",
                severity=RiskSeverity.HIGH if (f.violations + f.at_fault_accidents) >= 2 else RiskSeverity.MODERATE,
                category="personal_auto",
            )
        )
    if f.rideshare:
        f.findings.append(
            Finding(
                title="Rideshare / commercial use",
                description="Intended use elevates liability exposure vs personal pleasure",
                severity=RiskSeverity.HIGH,
                category="personal_auto",
            )
        )
    return f


def extract_life_factors(bundle: SubmissionBundle) -> LifeFactors:
    blob = strip_negated_clauses(_blob(bundle))
    health = "standard"
    if "preferred plus" in blob or "preferred best" in blob or "super preferred" in blob:
        health = "preferred"
    elif "preferred" in blob:
        health = "preferred"
    elif "substandard" in blob or "rated table" in blob or "table rating" in blob:
        health = "substandard"
    beneficiary_match = re.search(r"beneficiary(?:\s+relationship)?\s*[:=]\s*([A-Za-z][A-Za-z /-]{1,40})", blob, re.I)
    f = LifeFactors(
        face_amount=_money(blob, "face amount", "death benefit", "coverage amount", "sum assured"),
        age=_int_field(blob, "applicant age", "insured age", "age:"),
        sex="female" if "female" in blob or " sex: f" in blob else ("male" if "male" in blob or " sex: m" in blob else ""),
        smoker=bool(
            re.search(
                r"(?:current smoker|nicotine\s*:\s*positive|tobacco\s*:\s*(?!none\b|no\b|non-)\w+|cigarettes\s*:\s*(?!none\b|no\b|0)\w+)",
                blob,
                re.I,
            )
        ),
        health_class=health,
        hazardous_avocation=any(k in blob for k in ("scuba", "skydiving", "hang gliding", "motorsport", "pilot", "aviation")),
        foreign_travel=any(k in blob for k in ("foreign travel", "travel to", "overseas residence")),
        criminal_history=bool(
            re.search(
                r"(?:felony conviction|currently incarcerated|criminal history\s*:\s*(?!none\b|no\b|n/a\b)\w+)",
                blob,
                re.I,
            )
        ),
        income=_money(blob, "annual income", "earned income", "salary", "w-2 income"),
        net_worth=_money(blob, "net worth", "networth", "liquid net worth"),
        in_force_face=_money(blob, "in-force face", "in force coverage", "existing life insurance", "inforce face"),
        beneficiary_relationship=beneficiary_match.group(1).strip() if beneficiary_match else "",
        state=_state_from_blob(blob),
    )
    if f.smoker:
        f.findings.append(
            Finding(
                title="Tobacco / nicotine use",
                description="Smoker rates apply — mortality loading",
                severity=RiskSeverity.HIGH,
                category="life",
            )
        )
    if f.criminal_history:
        f.findings.append(
            Finding(
                title="Criminal history disclosed",
                description="May require referral or decline per life guidelines",
                severity=RiskSeverity.CRITICAL,
                category="life",
            )
        )
    if f.hazardous_avocation:
        f.findings.append(
            Finding(
                title="Hazardous avocation",
                description="Avocation activity may require flat extra or exclusion",
                severity=RiskSeverity.HIGH,
                category="life",
            )
        )
    return f


def personal_schedule_and_exposure(
    bundle: SubmissionBundle,
    line: InsuranceLine,
) -> tuple[float, float, list[Finding], dict[str, Any]]:
    """Return (schedule_mod_pct, exposure_base, findings, factor_dict)."""
    if line == InsuranceLine.PERSONAL_HOMEOWNERS:
        home = extract_home_factors(bundle)
        return home.schedule_mod_pct, home.exposure, home.findings, home.__dict__
    if line == InsuranceLine.PERSONAL_AUTO:
        auto = extract_auto_factors(bundle)
        return auto.schedule_mod_pct, auto.exposure, auto.findings, auto.__dict__
    if line == InsuranceLine.LIFE:
        life = extract_life_factors(bundle)
        return life.schedule_mod_pct, life.exposure, life.findings, life.__dict__
    return 0.0, 0.0, [], {}


def personal_appetite_check(bundle: SubmissionBundle, line: InsuranceLine) -> tuple[bool, list[Finding], str, bool]:
    """Return (passed, findings, reason, needs_uw_referral)."""
    findings: list[Finding] = []
    if line not in PERSONAL_LINES:
        return True, findings, "", False

    if line == InsuranceLine.PERSONAL_HOMEOWNERS:
        home = extract_home_factors(bundle)
        findings.extend(home.findings)
        if home.prior_claims >= 4:
            findings.append(
                Finding(
                    title="Excessive homeowners claims history",
                    description="4+ prior claim signals — outside standard appetite",
                    severity=RiskSeverity.CRITICAL,
                    category="personal_homeowners",
                )
            )
        if home.coastal_or_cat and home.dwelling_limit > 2_000_000:
            findings.append(
                Finding(
                    title="High-value coastal dwelling",
                    description="CAT + high TIV requires referral",
                    severity=RiskSeverity.HIGH,
                    category="personal_homeowners",
                )
            )
    elif line == InsuranceLine.PERSONAL_AUTO:
        auto = extract_auto_factors(bundle)
        findings.extend(auto.findings)
        if auto.violations >= 4 or "dui" in _blob(bundle) or "dwi" in _blob(bundle):
            findings.append(
                Finding(
                    title="Unacceptable driving record",
                    description="Multiple violations or DUI/DWI — decline/refer",
                    severity=RiskSeverity.CRITICAL,
                    category="personal_auto",
                )
            )
        if auto.driver_age is not None and auto.driver_age < 18:
            findings.append(
                Finding(
                    title="Underage primary driver",
                    description="Primary driver under 18 — outside appetite",
                    severity=RiskSeverity.CRITICAL,
                    category="personal_auto",
                )
            )
    elif line == InsuranceLine.LIFE:
        life = extract_life_factors(bundle)
        findings.extend(life.findings)
        if life.criminal_history:
            pass  # already critical finding
        if life.age is not None and life.age > 85:
            findings.append(
                Finding(
                    title="Age outside life appetite",
                    description="Applicant age > 85",
                    severity=RiskSeverity.CRITICAL,
                    category="life",
                )
            )
        if life.face_amount > 10_000_000:
            findings.append(
                Finding(
                    title="Jumbo face amount",
                    description="Face amount > $10M requires facultative referral",
                    severity=RiskSeverity.HIGH,
                    category="life",
                )
            )

    critical = [x for x in findings if x.severity == RiskSeverity.CRITICAL]
    high = [x for x in findings if x.severity == RiskSeverity.HIGH]
    if critical:
        return False, findings, "; ".join(x.title for x in critical), False
    if high:
        return False, findings, "; ".join(x.title for x in high), True
    return True, findings, "Personal lines appetite passed", False
