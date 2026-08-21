"""Underwriting factor models.

Implements structured assessment of:
  1. Current Health Status & Stability (build, BP, cholesterol, labs)
  2. Medical History & Family Longevity
  3. Lifestyle & Avocation Risks (hazards, tobacco, substances)
  4. Financial Justification & Insurable Interest
  5. Persistency & Longevity of Need
  6. Mortality Table Integration (q_x, risk classification)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .mortality import q_x

# ── Risk Classification ──────────────────────────────────────────────


class UWClass(str, Enum):
    PREFERRED_PLUS = "preferred_plus"
    PREFERRED = "preferred"
    STANDARD_PLUS = "standard_plus"
    STANDARD = "standard"
    TABLE_B = "table_b"
    TABLE_C = "table_c"
    TABLE_D = "table_d"
    TABLE_E = "table_e"
    TABLE_F = "table_f"
    DECLINE = "decline"


_TABLE_MULTIPLIERS: dict[str, float] = {
    UWClass.PREFERRED_PLUS: 0.75,
    UWClass.PREFERRED: 0.85,
    UWClass.STANDARD_PLUS: 0.95,
    UWClass.STANDARD: 1.00,
    UWClass.TABLE_B: 1.25,
    UWClass.TABLE_C: 1.50,
    UWClass.TABLE_D: 2.00,
    UWClass.TABLE_E: 2.50,
    UWClass.TABLE_F: 3.00,
    UWClass.DECLINE: float("inf"),
}


# ── Health Status ────────────────────────────────────────────────────


class BMICategory(str, Enum):
    UNDERWEIGHT = "underweight"
    NORMAL = "normal"
    OVERWEIGHT = "overweight"
    OBESE_I = "obese_i"
    OBESE_II = "obese_ii"
    OBESE_III = "obese_iii"


class BPCategory(str, Enum):
    OPTIMAL = "optimal"
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH_STAGE1 = "high_stage_1"
    HIGH_STAGE2 = "high_stage_2"
    CRISIS = "crisis"


class CholesterolCategory(str, Enum):
    OPTIMAL = "optimal"
    NEAR_OPTIMAL = "near_optimal"
    BORDERLINE = "borderline"
    HIGH = "very_high"


@dataclass
class HealthAssessment:
    """Step 3A: Current Health Status & Stability."""

    bmi: float = 0.0
    bmi_category: str = "unknown"
    systolic_bp: int = 120
    diastolic_bp: int = 80
    bp_category: str = "normal"
    total_cholesterol: int = 190
    hdl: int = 55
    ldl: int = 110
    cholesterol_category: str = "optimal"
    fasting_glucose: int = 90
    hba1c: float = 5.2
    nicotine_metabolite: str = "negative"
    # Labs
    bun: int = 15
    creatinine: float = 1.0
    egfr: int = 100
    ast: int = 25
    alt: int = 25
    ggt: int = 30
    # Risk
    chronic_disease_risk: str = "low"
    stability_years: int = 5
    risk_score: float = 0.0
    findings: list[str] = field(default_factory=list)


@dataclass
class MedicalHistoryAssessment:
    """Step 3B: Medical History & Family Longevity."""

    personal_conditions: list[str] = field(default_factory=list)
    family_conditions: list[str] = field(default_factory=list)
    parent_ages_at_death: list[int] = field(default_factory=list)
    parent_causes: list[str] = field(default_factory=list)
    surgical_history: list[str] = field(default_factory=list)
    family_longevity_risk: str = "low"
    risk_score: float = 0.0
    findings: list[str] = field(default_factory=list)


@dataclass
class LifestyleAssessment:
    """Step 3C: Lifestyle & Avocation Risks."""

    tobacco_use: str = "none"  # none, occasional, regular, heavy
    tobacco_years: int = 0
    alcohol_use: str = "none"  # none, social, moderate, heavy
    substance_use: str = "none"
    hazardous_hobbies: list[str] = field(default_factory=list)
    occupation_risk: str = "standard"  # standard, elevated, hazardous
    travel_risk: str = "low"  # low, moderate, high
    diving_certified: bool = False
    pilot_license: bool = False
    rock_climbing: bool = False
    risk_score: float = 0.0
    findings: list[str] = field(default_factory=list)


@dataclass
class FinancialJustification:
    """Step 4: Financial Justification & Insurable Interest."""

    annual_income: float = 0.0
    net_worth: float = 0.0
    requested_face: float = 0.0
    existing_coverage: float = 0.0
    mortgage_balance: float = 0.0
    dependents: int = 0
    income_multiplier: float = 0.0
    hlv_estimate: float = 0.0
    estate_need: float = 0.0
    total_need: float = 0.0
    overinsurance_flag: bool = False
    overinsurance_amount: float = 0.0
    suitability: str = "approved"  # approved, review, decline
    risk_score: float = 0.0
    findings: list[str] = field(default_factory=list)


@dataclass
class PersistencyAssessment:
    """Step 5: Persistency & Longevity of Need."""

    stated_purpose: str = ""
    mortgage_years_remaining: int = 0
    children_age_range: str = ""
    retirement_age: int = 65
    need_duration_years: int = 0
    term_length_aligned: bool = True
    lapse_risk: str = "low"
    persistency_score: float = 0.0
    findings: list[str] = field(default_factory=list)


@dataclass
class UWFactors:
    """Aggregated underwriting factors for the mortality classification."""

    health: HealthAssessment = field(default_factory=HealthAssessment)
    medical: MedicalHistoryAssessment = field(default_factory=MedicalHistoryAssessment)
    lifestyle: LifestyleAssessment = field(default_factory=LifestyleAssessment)
    financial: FinancialJustification = field(default_factory=FinancialJustification)
    persistency: PersistencyAssessment = field(default_factory=PersistencyAssessment)
    # Mortality
    base_q_x: float = 0.0
    risk_adjusted_q_x: float = 0.0
    mortality_multiplier: float = 1.0
    # Classification
    uw_class: str = "standard"
    premium_multiplier: float = 1.0
    flat_extra: float = 0.0
    # Totals
    total_risk_score: float = 0.0
    findings: list[str] = field(default_factory=list)
    decision: str = "REFER"  # ISSUE, REFER, DECLINE

    def to_metadata(self) -> dict[str, Any]:
        return {
            "health": {
                "bmi": self.health.bmi,
                "bmi_category": self.health.bmi_category,
                "bp_category": self.health.bp_category,
                "cholesterol_category": self.health.cholesterol_category,
                "risk_score": self.health.risk_score,
            },
            "medical": {
                "personal_conditions": self.medical.personal_conditions,
                "family_conditions": self.medical.family_conditions,
                "family_longevity_risk": self.medical.family_longevity_risk,
                "risk_score": self.medical.risk_score,
            },
            "lifestyle": {
                "tobacco_use": self.lifestyle.tobacco_use,
                "alcohol_use": self.lifestyle.alcohol_use,
                "hazardous_hobbies": self.lifestyle.hazardous_hobbies,
                "occupation_risk": self.lifestyle.occupation_risk,
                "risk_score": self.lifestyle.risk_score,
            },
            "financial": {
                "annual_income": self.financial.annual_income,
                "net_worth": self.financial.net_worth,
                "requested_face": self.financial.requested_face,
                "hlv_estimate": self.financial.hlv_estimate,
                "overinsurance_flag": self.financial.overinsurance_flag,
                "suitability": self.financial.suitability,
                "risk_score": self.financial.risk_score,
            },
            "persistency": {
                "stated_purpose": self.persistency.stated_purpose,
                "need_duration_years": self.persistency.need_duration_years,
                "term_length_aligned": self.persistency.term_length_aligned,
                "lapse_risk": self.persistency.lapse_risk,
                "persistency_score": self.persistency.persistency_score,
            },
            "mortality": {
                "base_q_x": self.base_q_x,
                "risk_adjusted_q_x": self.risk_adjusted_q_x,
                "mortality_multiplier": self.mortality_multiplier,
            },
            "classification": {
                "uw_class": self.uw_class,
                "premium_multiplier": self.premium_multiplier,
                "flat_extra": self.flat_extra,
            },
            "total_risk_score": self.total_risk_score,
            "decision": self.decision,
            "findings": self.findings,
        }


# ── Health Assessment ────────────────────────────────────────────────


def compute_bmi(height_inches: float, weight_lbs: float) -> tuple[float, str]:
    """BMI = (Weight lbs / Height in²) × 703"""
    if height_inches <= 0:
        return 0.0, "unknown"
    bmi = round((weight_lbs / (height_inches**2)) * 703, 1)
    if bmi < 18.5:
        cat = "underweight"
    elif bmi <= 25.0:
        cat = "normal"
    elif bmi <= 30.0:
        cat = "overweight"
    elif bmi <= 35.0:
        cat = "obese_i"
    elif bmi <= 40.0:
        cat = "obese_ii"
    else:
        cat = "obese_iii"
    return bmi, cat


def classify_bp(systolic: int, diastolic: int) -> str:
    """Classify blood pressure per AHA guidelines."""
    if systolic < 120 and diastolic < 80:
        return "optimal"
    if systolic < 130 and diastolic < 80:
        return "normal"
    if systolic < 140 or diastolic < 90:
        return "elevated"
    if systolic < 160 or diastolic < 100:
        return "high_stage_1"
    if systolic < 180 or diastolic < 120:
        return "high_stage_2"
    return "crisis"


def classify_cholesterol(total: int, hdl: int, ldl: int) -> str:
    """Classify cholesterol risk level."""
    if ldl < 100 and total < 200:
        return "optimal"
    if ldl < 130 and total < 240:
        return "near_optimal"
    if ldl < 160 and total < 280:
        return "borderline"
    return "very_high"


def assess_health(
    height_inches: float,
    weight_lbs: float,
    systolic_bp: int = 120,
    diastolic_bp: int = 80,
    total_cholesterol: int = 190,
    hdl: int = 55,
    ldl: int = 110,
    fasting_glucose: int = 90,
    hba1c: float = 5.2,
    nicotine_metabolite: str = "negative",
    bun: int = 15,
    creatinine: float = 1.0,
    egfr: int = 100,
    ast: int = 25,
    alt: int = 25,
    ggt: int = 30,
    stability_years: int = 5,
) -> HealthAssessment:
    """Compute health status assessment with risk scoring."""
    bmi, bmi_cat = compute_bmi(height_inches, weight_lbs)
    bp_cat = classify_bp(systolic_bp, diastolic_bp)
    chol_cat = classify_cholesterol(total_cholesterol, hdl, ldl)

    score = 0.0
    findings = []

    # BMI scoring
    bmi_scores = {
        "underweight": 0.15,
        "normal": 0.0,
        "overweight": 0.10,
        "obese_i": 0.30,
        "obese_ii": 0.50,
        "obese_iii": 0.80,
    }
    score += bmi_scores.get(bmi_cat, 0.0)
    if bmi_cat in ("obese_ii", "obese_iii"):
        findings.append(f"BMI {bmi} ({bmi_cat}) — significant mortality risk")
    elif bmi_cat == "overweight":
        findings.append(f"BMI {bmi} — mildly elevated")

    # BP scoring
    bp_scores = {
        "optimal": 0.0,
        "normal": 0.05,
        "elevated": 0.15,
        "high_stage_1": 0.35,
        "high_stage_2": 0.60,
        "crisis": 0.90,
    }
    score += bp_scores.get(bp_cat, 0.0)
    if bp_cat in ("high_stage_1", "high_stage_2", "crisis"):
        findings.append(f"Blood pressure {systolic_bp}/{diastolic_bp} ({bp_cat})")

    # Cholesterol scoring
    chol_scores = {
        "optimal": 0.0,
        "near_optimal": 0.05,
        "borderline": 0.15,
        "very_high": 0.35,
    }
    score += chol_scores.get(chol_cat, 0.0)
    if chol_cat == "very_high":
        findings.append(f"Cholesterol: LDL {ldl}, Total {total_cholesterol} — elevated risk")

    # HbA1c
    if hba1c >= 6.5:
        score += 0.40
        findings.append(f"HbA1c {hba1c}% — diabetic range")
    elif hba1c >= 5.7:
        score += 0.10
        findings.append(f"HbA1c {hba1c}% — pre-diabetic")

    # Nicotine
    if nicotine_metabolite != "negative":
        score += 0.50
        findings.append("Nicotine metabolite detected — smoker classification")

    # Renal
    if egfr < 60:
        score += 0.30
        findings.append(f"eGFR {egfr} — impaired renal function")
    elif egfr < 90:
        score += 0.10

    # Liver
    if ast > 40 or alt > 40:
        score += 0.15
        findings.append(f"Elevated liver enzymes (AST {ast}, ALT {alt})")

    # Stability bonus
    if stability_years >= 10:
        score = max(0.0, score - 0.05)

    chronic_risk = "low"
    if score >= 0.60:
        chronic_risk = "high"
    elif score >= 0.30:
        chronic_risk = "moderate"

    return HealthAssessment(
        bmi=bmi,
        bmi_category=bmi_cat,
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        bp_category=bp_cat,
        total_cholesterol=total_cholesterol,
        hdl=hdl,
        ldl=ldl,
        cholesterol_category=chol_cat,
        fasting_glucose=fasting_glucose,
        hba1c=hba1c,
        nicotine_metabolite=nicotine_metabolite,
        bun=bun,
        creatinine=creatinine,
        egfr=egfr,
        ast=ast,
        alt=alt,
        ggt=ggt,
        chronic_disease_risk=chronic_risk,
        stability_years=stability_years,
        risk_score=round(score, 4),
        findings=findings,
    )


# ── Medical History ──────────────────────────────────────────────────

_CONDITION_RISK: dict[str, float] = {
    "heart_attack": 0.40,
    "stroke": 0.35,
    "cancer": 0.30,
    "diabetes": 0.25,
    "kidney_disease": 0.25,
    "liver_disease": 0.20,
    "copd": 0.25,
    "sleep_apnea": 0.10,
    "depression": 0.10,
    "anxiety": 0.05,
    "autoimmune": 0.15,
    "epilepsy": 0.15,
}

_FAMILY_RISK: dict[str, float] = {
    "heart_disease_before_60": 0.20,
    "cancer_before_60": 0.15,
    "stroke_before_60": 0.15,
    "diabetes": 0.10,
    "suicide": 0.10,
    "sudden_death_before_50": 0.25,
}


def assess_medical_history(
    personal_conditions: list[str] | None = None,
    family_conditions: list[str] | None = None,
    parent_ages_at_death: list[int] | None = None,
    parent_causes: list[str] | None = None,
    surgical_history: list[str] | None = None,
) -> MedicalHistoryAssessment:
    """Assess personal and family medical history risk."""
    personal = personal_conditions or []
    family = family_conditions or []
    parent_ages = parent_ages_at_death or []
    parent_causes = parent_causes or []
    surgeries = surgical_history or []

    score = 0.0
    findings = []

    for cond in personal:
        risk = _CONDITION_RISK.get(cond.lower(), 0.10)
        score += risk
        findings.append(f"Personal history: {cond} (+{risk:.0%} risk)")

    for cond in family:
        risk = _FAMILY_RISK.get(cond.lower(), 0.10)
        score += risk
        findings.append(f"Family history: {cond} (+{risk:.0%} risk)")

    # Parent longevity
    for i, age in enumerate(parent_ages):
        cause = parent_causes[i] if i < len(parent_causes) else "unknown"
        if age < 50:
            score += 0.15
            findings.append(f"Parent died at {age} ({cause}) — elevated risk")
        elif age < 60:
            score += 0.08
            findings.append(f"Parent died at {age} ({cause})")

    longevity_risk = "low"
    if score >= 0.50:
        longevity_risk = "high"
    elif score >= 0.25:
        longevity_risk = "moderate"

    return MedicalHistoryAssessment(
        personal_conditions=personal,
        family_conditions=family,
        parent_ages_at_death=parent_ages,
        parent_causes=parent_causes,
        surgical_history=surgeries,
        family_longevity_risk=longevity_risk,
        risk_score=round(min(score, 1.0), 4),
        findings=findings,
    )


# ── Lifestyle Assessment ─────────────────────────────────────────────

_HOBBY_RISK: dict[str, float] = {
    "aviation": 0.30,
    "scuba_diving": 0.15,
    "rock_climbing": 0.20,
    "skydiving": 0.25,
    "base_jumping": 0.40,
    "motorsport": 0.20,
    "mountaineering": 0.25,
    "caving": 0.15,
    "wingsuit": 0.50,
}

_OCCUPATION_RISK: dict[str, float] = {
    "standard": 0.0,
    "elevated": 0.10,
    "hazardous": 0.30,
}


def assess_lifestyle(
    tobacco_use: str = "none",
    tobacco_years: int = 0,
    alcohol_use: str = "none",
    substance_use: str = "none",
    hazardous_hobbies: list[str] | None = None,
    occupation_risk: str = "standard",
    travel_risk: str = "low",
) -> LifestyleAssessment:
    """Assess lifestyle and avocation risks."""
    hobbies = hazardous_hobbies or []
    score = 0.0
    findings = []

    # Tobacco
    tobacco_scores = {"none": 0.0, "occasional": 0.40, "regular": 0.70, "heavy": 1.0}
    t_score = tobacco_scores.get(tobacco_use.lower(), 0.0)
    # Duration loading
    if tobacco_years > 0 and tobacco_use.lower() != "none":
        duration_load = min(tobacco_years * 0.02, 0.20)
        t_score = min(t_score + duration_load, 1.0)
    score += t_score
    if tobacco_use.lower() != "none":
        findings.append(f"Tobacco: {tobacco_use} ({tobacco_years} years)")

    # Alcohol
    alcohol_scores = {"none": 0.0, "social": 0.0, "moderate": 0.10, "heavy": 0.40}
    a_score = alcohol_scores.get(alcohol_use.lower(), 0.0)
    score += a_score
    if alcohol_use.lower() in ("moderate", "heavy"):
        findings.append(f"Alcohol: {alcohol_use}")

    # Substance
    if substance_use.lower() != "none":
        score += 0.30
        findings.append(f"Substance use: {substance_use}")

    # Hobbies
    for hobby in hobbies:
        risk = _HOBBY_RISK.get(hobby.lower().replace(" ", "_"), 0.15)
        score += risk
        findings.append(f"Hazardous hobby: {hobby} (+{risk:.0%})")

    # Occupation
    occ = _OCCUPATION_RISK.get(occupation_risk.lower(), 0.10)
    score += occ
    if occupation_risk.lower() != "standard":
        findings.append(f"Occupation risk: {occupation_risk}")

    # Travel
    travel_scores = {"low": 0.0, "moderate": 0.05, "high": 0.15}
    score += travel_scores.get(travel_risk.lower(), 0.0)

    return LifestyleAssessment(
        tobacco_use=tobacco_use,
        tobacco_years=tobacco_years,
        alcohol_use=alcohol_use,
        substance_use=substance_use,
        hazardous_hobbies=hobbies,
        occupation_risk=occupation_risk,
        travel_risk=travel_risk,
        risk_score=round(min(score, 1.0), 4),
        findings=findings,
    )


# ── Financial Justification ──────────────────────────────────────────


def calculate_hlv(income: float, age: int) -> float:
    """Human Life Value: Income × Age Multiplier."""
    if age <= 25:
        mult = 30.0
    elif age <= 30:
        mult = 25.0
    elif age <= 35:
        mult = 22.0
    elif age <= 40:
        mult = 20.0
    elif age <= 45:
        mult = 17.0
    elif age <= 50:
        mult = 15.0
    elif age <= 55:
        mult = 12.0
    elif age <= 60:
        mult = 10.0
    elif age <= 65:
        mult = 7.0
    else:
        mult = 5.0
    return round(income * mult, 2)


def assess_financial(
    annual_income: float,
    net_worth: float,
    requested_face: float,
    existing_coverage: float = 0.0,
    mortgage_balance: float = 0.0,
    dependents: int = 0,
    age: int = 35,
) -> FinancialJustification:
    """Assess financial justification and insurable interest."""
    findings = []
    score = 0.0

    hlv = calculate_hlv(annual_income, age)
    estate_need = round(net_worth * 0.15, 2)  # 15% of net worth for estate taxes/liquidity

    # Income multiplier
    if annual_income > 0:
        income_mult = round(requested_face / annual_income, 1)
    else:
        income_mult = 0.0

    total_need = hlv + estate_need + mortgage_balance
    total_existing = existing_coverage + requested_face
    overinsurance = max(0.0, total_existing - total_need * 1.10)  # 10% tolerance

    suitability = "approved"
    if overinsurance > 0:
        suitability = "review"
        score += 0.20
        findings.append(f"Potential over-insurance: ${overinsurance:,.0f} (total ${total_existing:,.0f} vs need ${total_need:,.0f})")

    if income_mult > 30 and annual_income > 0:
        score += 0.15
        findings.append(f"Income multiplier {income_mult}× exceeds 30× guideline")

    if dependents == 0 and requested_face > 1_000_000:
        score += 0.10
        findings.append("No dependents but face exceeds $1M")

    if annual_income <= 0:
        score += 0.20
        findings.append("No income documentation provided")

    return FinancialJustification(
        annual_income=annual_income,
        net_worth=net_worth,
        requested_face=requested_face,
        existing_coverage=existing_coverage,
        mortgage_balance=mortgage_balance,
        dependents=dependents,
        income_multiplier=income_mult,
        hlv_estimate=hlv,
        estate_need=estate_need,
        total_need=round(total_need, 2),
        overinsurance_flag=overinsurance > 0,
        overinsurance_amount=round(overinsurance, 2),
        suitability=suitability,
        risk_score=round(min(score, 1.0), 4),
        findings=findings,
    )


# ── Persistency Assessment ───────────────────────────────────────────


def assess_persistency(
    stated_purpose: str = "",
    mortgage_years_remaining: int = 0,
    children_min_age: int = 0,
    children_max_age: int = 0,
    retirement_age: int = 65,
    requested_term: int = 20,
    current_age: int = 30,
) -> PersistencyAssessment:
    """Assess persistency and longevity of need alignment."""
    findings = []
    score = 0.0

    # Determine need duration
    need_duration = max(
        mortgage_years_remaining,
        (retirement_age - current_age) if retirement_age > current_age else 0,
    )
    if children_max_age > 0:
        child_need = max(0, 25 - children_min_age)  # until youngest is ~25
        need_duration = max(need_duration, child_need)

    # Term alignment
    aligned = abs(requested_term - need_duration) <= 5  # within 5 years is acceptable
    if not aligned:
        gap = requested_term - need_duration
        if gap > 5:
            score += 0.15
            findings.append(f"Term {requested_term}yr exceeds estimated need {need_duration}yr by {gap}yr")
        else:
            score += 0.05
            findings.append(f"Term {requested_term}yr shorter than estimated need {need_duration}yr")

    if stated_purpose.lower() in ("mortgage_protection", "mortgage"):
        if mortgage_years_remaining > 0:
            findings.append(f"Mortgage protection: {mortgage_years_remaining}yr remaining")

    children_range = ""
    if children_min_age > 0 or children_max_age > 0:
        children_range = f"{children_min_age}-{children_max_age}"

    lapse_risk = "low"
    if score >= 0.20:
        lapse_risk = "moderate"
    if score >= 0.40:
        lapse_risk = "high"

    return PersistencyAssessment(
        stated_purpose=stated_purpose,
        mortgage_years_remaining=mortgage_years_remaining,
        children_age_range=children_range,
        retirement_age=retirement_age,
        need_duration_years=need_duration,
        term_length_aligned=aligned,
        lapse_risk=lapse_risk,
        persistency_score=round(min(score, 1.0), 4),
        findings=findings,
    )


# ── Aggregate Classification ─────────────────────────────────────────


def classify_uw_risk(
    age: int,
    sex: str,
    smoker: bool,
    health: HealthAssessment,
    medical: MedicalHistoryAssessment,
    lifestyle: LifestyleAssessment,
    financial: FinancialJustification,
    persistency: PersistencyAssessment,
) -> UWFactors:
    """Aggregate all factors into a final UW classification.

    Uses weighted risk scoring:
      Health:       30%
      Medical:      20%
      Lifestyle:    25%
      Financial:    15%
      Persistency:  10%
    """
    base = q_x(age, sex, smoker)

    # Weighted aggregate
    total = health.risk_score * 0.30 + medical.risk_score * 0.20 + lifestyle.risk_score * 0.25 + financial.risk_score * 0.15 + persistency.persistency_score * 0.10

    # Classify
    if total >= 0.70 or financial.suitability == "decline":
        uw_class = "decline"
        multiplier = float("inf")
        flat_extra = 0.0
        decision = "DECLINE"
    elif total >= 0.55:
        uw_class = "table_f"
        multiplier = 3.00
        flat_extra = 0.0
        decision = "REFER"
    elif total >= 0.45:
        uw_class = "table_e"
        multiplier = 2.50
        flat_extra = 0.0
        decision = "REFER"
    elif total >= 0.35:
        uw_class = "table_d"
        multiplier = 2.00
        flat_extra = 0.0
        decision = "REFER"
    elif total >= 0.25:
        uw_class = "table_c"
        multiplier = 1.50
        flat_extra = 0.0
        decision = "REFER"
    elif total >= 0.18:
        uw_class = "table_b"
        multiplier = 1.25
        flat_extra = 0.0
        decision = "ISSUE"
    elif total >= 0.10:
        uw_class = "standard"
        multiplier = 1.00
        flat_extra = 0.0
        decision = "ISSUE"
    elif total >= 0.05:
        uw_class = "standard_plus"
        multiplier = 0.95
        flat_extra = 0.0
        decision = "ISSUE"
    elif total >= 0.02:
        uw_class = "preferred"
        multiplier = 0.85
        flat_extra = 0.0
        decision = "ISSUE"
    else:
        uw_class = "preferred_plus"
        multiplier = 0.75
        flat_extra = 0.0
        decision = "ISSUE"

    # Flat extras for specific conditions
    if lifestyle.tobacco_use.lower() in ("regular", "heavy"):
        flat_extra += 2.00  # $2.00 per $1,000 per month smoker flat

    # Mortality-adjusted q_x
    risk_q_x = round(base * multiplier, 8) if multiplier != float("inf") else 1.0

    all_findings = health.findings + medical.findings + lifestyle.findings + financial.findings + persistency.findings

    return UWFactors(
        health=health,
        medical=medical,
        lifestyle=lifestyle,
        financial=financial,
        persistency=persistency,
        base_q_x=base,
        risk_adjusted_q_x=risk_q_x,
        mortality_multiplier=multiplier if multiplier != float("inf") else 99.0,
        uw_class=uw_class,
        premium_multiplier=multiplier if multiplier != float("inf") else 99.0,
        flat_extra=flat_extra,
        total_risk_score=round(total, 4),
        findings=all_findings,
        decision=decision,
    )
