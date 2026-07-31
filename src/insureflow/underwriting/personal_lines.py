"""Personal lines underwriting: homeowners, auto, and life risk factors."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import PERSONAL_LINES, InsuranceLine


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
    return "\n".join(parts).lower()


def detect_insurance_line(text_blob: str = "", product_hint: str = "") -> InsuranceLine:
    blob = f"{product_hint}\n{text_blob}".lower()
    if any(
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
        )
    ):
        return InsuranceLine.LIFE
    if any(
        k in blob
        for k in (
            "personal auto",
            "auto application",
            "drivers license",
            "mvr",
            "motor vehicle report",
            "vin:",
            "vehicle year",
            "rideshare",
            "insurance_line: personal_auto",
            "line: personal_auto",
        )
    ):
        return InsuranceLine.PERSONAL_AUTO
    if any(
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
        )
    ):
        return InsuranceLine.PERSONAL_HOMEOWNERS
    if any(k in blob for k in ("d&o", "directors and officers", "management liability")):
        return InsuranceLine.COMMERCIAL_PROPERTY  # D&O priced via commercial path + checklist
    return InsuranceLine.COMMERCIAL_PROPERTY


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
    }
    if normalized in aliases:
        return aliases[normalized]
    try:
        return InsuranceLine(normalized)
    except ValueError:
        return None


def _money(blob: str, *labels: str) -> float:
    for label in labels:
        m = re.search(rf"{re.escape(label)}\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d+)?)", blob, re.I)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return 0.0


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
        if self.face_amount and self.income and self.face_amount > self.income * 30:
            mod += 15.0  # financial underwriting stretch
        return mod


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
                source_agent="personal_auto",
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
    blob = _blob(bundle)
    health = "standard"
    if "preferred plus" in blob or "preferred best" in blob or "super preferred" in blob:
        health = "preferred"
    elif "preferred" in blob:
        health = "preferred"
    elif "substandard" in blob or "rated table" in blob or "table rating" in blob:
        health = "substandard"
    f = LifeFactors(
        face_amount=_money(blob, "face amount", "death benefit", "coverage amount", "sum assured"),
        age=_int_field(blob, "applicant age", "insured age", "age:"),
        sex="female" if "female" in blob or " sex: f" in blob else ("male" if "male" in blob or " sex: m" in blob else ""),
        smoker=any(k in blob for k in ("smoker", "tobacco", "nicotine", "cigarettes")),
        health_class=health,
        hazardous_avocation=any(k in blob for k in ("scuba", "skydiving", "hang gliding", "motorsport", "pilot", "aviation")),
        foreign_travel=any(k in blob for k in ("foreign travel", "travel to", "overseas residence")),
        criminal_history=any(k in blob for k in ("felony", "incarceration", "criminal history", "conviction")),
        income=_money(blob, "annual income", "income", "salary", "net worth"),
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
        f = extract_home_factors(bundle)
        return f.schedule_mod_pct, f.exposure, f.findings, f.__dict__
    if line == InsuranceLine.PERSONAL_AUTO:
        f = extract_auto_factors(bundle)
        return f.schedule_mod_pct, f.exposure, f.findings, f.__dict__
    if line == InsuranceLine.LIFE:
        f = extract_life_factors(bundle)
        return f.schedule_mod_pct, f.exposure, f.findings, f.__dict__
    return 0.0, 0.0, [], {}


def personal_appetite_check(bundle: SubmissionBundle, line: InsuranceLine) -> tuple[bool, list[Finding], str, bool]:
    """Return (passed, findings, reason, needs_uw_referral)."""
    findings: list[Finding] = []
    if line not in PERSONAL_LINES:
        return True, findings, "", False

    if line == InsuranceLine.PERSONAL_HOMEOWNERS:
        f = extract_home_factors(bundle)
        findings.extend(f.findings)
        if f.prior_claims >= 4:
            findings.append(
                Finding(
                    title="Excessive homeowners claims history",
                    description="4+ prior claim signals — outside standard appetite",
                    severity=RiskSeverity.CRITICAL,
                    category="personal_homeowners",
                )
            )
        if f.coastal_or_cat and f.dwelling_limit > 2_000_000:
            findings.append(
                Finding(
                    title="High-value coastal dwelling",
                    description="CAT + high TIV requires referral",
                    severity=RiskSeverity.HIGH,
                    category="personal_homeowners",
                )
            )
    elif line == InsuranceLine.PERSONAL_AUTO:
        f = extract_auto_factors(bundle)
        findings.extend(f.findings)
        if f.violations >= 4 or "dui" in _blob(bundle) or "dwi" in _blob(bundle):
            findings.append(
                Finding(
                    title="Unacceptable driving record",
                    description="Multiple violations or DUI/DWI — decline/refer",
                    severity=RiskSeverity.CRITICAL,
                    category="personal_auto",
                )
            )
        if f.driver_age is not None and f.driver_age < 18:
            findings.append(
                Finding(
                    title="Underage primary driver",
                    description="Primary driver under 18 — outside appetite",
                    severity=RiskSeverity.CRITICAL,
                    category="personal_auto",
                )
            )
    elif line == InsuranceLine.LIFE:
        f = extract_life_factors(bundle)
        findings.extend(f.findings)
        if f.criminal_history:
            pass  # already critical finding
        if f.age is not None and f.age > 85:
            findings.append(
                Finding(
                    title="Age outside life appetite",
                    description="Applicant age > 85",
                    severity=RiskSeverity.CRITICAL,
                    category="life",
                )
            )
        if f.face_amount > 10_000_000:
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
