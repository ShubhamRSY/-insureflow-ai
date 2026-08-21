"""Step 3 — Medical & Build Evaluation.

BMI calculation, paramedical exam thresholds, vitals assessment, class assignment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.life_medical import LifeMedicalDecision, _parse_vitals, underwrite_life
from insureflow.underwriting.personal_lines import _blob, extract_life_factors

# Paramedical exam thresholds by face amount tier
PARAMED_THRESHOLDS: list[dict[str, Any]] = [
    {"min_face": 0, "max_face": 100_000, "paramed_required": False, "label": "No exam required"},
    {"min_face": 100_001, "max_face": 250_000, "paramed_required": True, "label": "Basic paramedical exam"},
    {"min_face": 250_001, "max_face": 500_000, "paramed_required": True, "label": "Full paramedical + blood panel"},
    {"min_face": 500_001, "max_face": 1_000_000, "paramed_required": True, "label": "Full paramedical + blood + EKG"},
    {"min_face": 1_000_001, "max_face": 5_000_000, "paramed_required": True, "label": "Full paramedical + blood + EKG + APS"},
    {"min_face": 5_000_001, "max_face": 999_999_999, "paramed_required": True, "label": "Full paramedical + blood + EKG + APS + financial audit"},
]

# BMI classification tiers
BMI_TIERS: list[dict[str, Any]] = [
    {"max_bmi": 18.5, "label": "Underweight", "class_floor": "standard", "risk": "moderate"},
    {"max_bmi": 25.0, "label": "Preferred Plus eligible", "class_floor": "super_preferred", "risk": "low"},
    {"max_bmi": 27.5, "label": "Preferred eligible", "class_floor": "preferred", "risk": "low"},
    {"max_bmi": 30.0, "label": "Standard Plus eligible", "class_floor": "standard_plus", "risk": "moderate"},
    {"max_bmi": 35.0, "label": "Standard / Table A", "class_floor": "table_a", "risk": "elevated"},
    {"max_bmi": 40.0, "label": "Table B-C", "class_floor": "table_c", "risk": "high"},
    {"max_bmi": 999.0, "label": "Decline threshold", "class_floor": "substandard", "risk": "critical"},
]


def calculate_bmi(weight_lbs: float, height_inches: float) -> float:
    """BMI = (Weight in pounds / Height in inches^2) * 703"""
    if height_inches <= 0:
        return 0.0
    return round((weight_lbs / (height_inches**2)) * 703, 1)


def _parse_height_weight(blob: str) -> tuple[float | None, float | None]:
    """Extract height (inches) and weight (lbs) from submission text."""
    weight = None
    height = None

    # Weight patterns
    wm = re.search(r"weight\s*[:=]?\s*(\d{2,3})\s*(?:lb|pound|#)", blob, re.I)
    if wm:
        weight = float(wm.group(1))

    # Height patterns — feet'inches" or total inches
    hm = re.search(r"height\s*[:=]?\s*(\d)\s*['′]\s*(\d{1,2})\s*[\"″]", blob, re.I)
    if hm:
        height = float(hm.group(1)) * 12 + float(hm.group(2))
    else:
        hm2 = re.search(r"height\s*[:=]?\s*(\d{2,3})\s*(?:in|inch)", blob, re.I)
        if hm2:
            height = float(hm2.group(1))

    return weight, height


def _get_bmi_tier(bmi: float) -> dict[str, Any]:
    for tier in BMI_TIERS:
        if bmi <= tier["max_bmi"]:
            return tier
    return BMI_TIERS[-1]


def get_paramed_threshold(face_amount: float) -> dict[str, Any]:
    for t in PARAMED_THRESHOLDS:
        if t["min_face"] <= face_amount <= t["max_face"]:
            return t
    return PARAMED_THRESHOLDS[-1]


@dataclass
class MedicalEvalResult:
    bmi: float | None = None
    bmi_tier: str = ""
    height_inches: float | None = None
    weight_lbs: float | None = None
    paramed_required: bool = False
    paramed_level: str = ""
    medical_decision: LifeMedicalDecision | None = None
    findings: list[Finding] = field(default_factory=list)
    decision: UWDecision = UWDecision.ACCEPT

    def to_metadata(self) -> dict[str, Any]:
        return {
            "bmi": self.bmi,
            "bmi_tier": self.bmi_tier,
            "height_inches": self.height_inches,
            "weight_lbs": self.weight_lbs,
            "paramed_required": self.paramed_required,
            "paramed_level": self.paramed_level,
            "medical_decision": self.medical_decision.to_metadata() if self.medical_decision else None,
        }


def run_medical_eval(bundle: SubmissionBundle) -> MedicalEvalResult:
    blob = _blob(bundle)
    factors = extract_life_factors(bundle)
    result = MedicalEvalResult()

    # Parse height/weight and calculate BMI
    weight, height = _parse_height_weight(blob)
    if weight and height:
        result.height_inches = height
        result.weight_lbs = weight
        result.bmi = calculate_bmi(weight, height)
        tier = _get_bmi_tier(result.bmi)
        result.bmi_tier = tier["label"]

        if result.bmi > 40.0:
            result.findings.append(
                Finding(
                    title=f"BMI {result.bmi} exceeds issue limits",
                    description=f"BMI of {result.bmi} ({tier['label']}) exceeds the preferred threshold of 25. Applicant is stepped down to {tier['class_floor']}.",
                    severity=RiskSeverity.HIGH,
                    category="life_medical",
                )
            )
        elif result.bmi > 30.0:
            result.findings.append(
                Finding(
                    title=f"BMI {result.bmi} — table rating consideration",
                    description=f"BMI of {result.bmi} ({tier['label']}) blocks preferred class. Minimum class: {tier['class_floor']}.",
                    severity=RiskSeverity.MODERATE,
                    category="life_medical",
                )
            )
        elif result.bmi <= 25.0:
            result.findings.append(
                Finding(
                    title=f"BMI {result.bmi} — Preferred Plus eligible",
                    description=f"BMI of {result.bmi} is within Preferred Plus range (≤25).",
                    severity=RiskSeverity.LOW,
                    category="life_medical",
                )
            )
    else:
        # Try existing vitals from the medical guide
        vitals = _parse_vitals(blob)
        if "bmi" in vitals:
            result.bmi = vitals["bmi"]
            tier = _get_bmi_tier(result.bmi)
            result.bmi_tier = tier["label"]

    # Paramedical exam threshold
    face = float(factors.face_amount or 0)
    paramed = get_paramed_threshold(face)
    result.paramed_required = paramed["paramed_required"]
    result.paramed_level = paramed["label"]

    if result.paramed_required:
        result.findings.append(
            Finding(
                title=f"Paramedical exam required: {result.paramed_level}",
                description=f"Face amount ${face:,.0f} exceeds the no-exam threshold. {result.paramed_level} is required.",
                severity=RiskSeverity.MODERATE,
                category="life_medical",
            )
        )

    # Delegate to existing medical UW engine
    medical_decision = underwrite_life(bundle)
    result.medical_decision = medical_decision
    result.findings.extend(medical_decision.findings)
    result.decision = medical_decision.decision

    return result
