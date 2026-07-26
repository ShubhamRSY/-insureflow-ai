"""Damage detection — hail, fire, water, structural damage classification.

Uses a cascading approach:
1. Rule-based image analysis (color patterns, texture anomalies)
2. Vision LLM for detailed damage assessment
3. Historical weather data correlation (optional)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from insureflow.ml.vision.models import PhotoAnalysis, VisualFinding, VisualRisk

logger = logging.getLogger(__name__)


class DamageType(str, Enum):
    HAIL = "hail"
    WIND = "wind"
    WATER = "water"
    FIRE = "fire"
    STRUCTURAL = "structural"
    VANDALISM = "vandalism"
    VEHICLE = "vehicle"
    WEATHER = "weather"
    AGE = "age"
    UNKNOWN = "unknown"


class DamageSeverity(str, Enum):
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CATASTROPHIC = "catastrophic"


@dataclass
class DamageAssessment:
    damage_type: DamageType = DamageType.UNKNOWN
    severity: DamageSeverity = DamageSeverity.NONE
    confidence: float = 0.0
    description: str = ""
    location: str = ""
    estimated_repair_cost: str = ""
    age_estimate: str = ""
    is_pre_existing: bool = False
    weather_correlation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "damage_type": self.damage_type.value,
            "severity": self.severity.value,
            "confidence": round(self.confidence, 3),
            "description": self.description,
            "location": self.location,
            "estimated_repair_cost": self.estimated_repair_cost,
            "age_estimate": self.age_estimate,
            "is_pre_existing": self.is_pre_existing,
            "weather_correlation": self.weather_correlation,
        }


class DamageDetector:
    def __init__(self, vision_analyzer: Any | None = None) -> None:
        self._vision_analyzer = vision_analyzer

    def detect_from_analysis(self, analysis: PhotoAnalysis) -> list[DamageAssessment]:
        assessments: list[DamageAssessment] = []
        for finding in analysis.findings:
            if finding.category == "damage":
                assessment = self._finding_to_assessment(finding)
                assessments.append(assessment)
        return assessments

    def detect_from_prompt(
        self,
        image_data: bytes,
        filename: str,
    ) -> list[DamageAssessment]:
        if not self._vision_analyzer or not getattr(self._vision_analyzer, "available", False):
            return []

        try:
            result = self._vision_analyzer.analyze_photo(image_data, filename)
            return self._parse_damage_response(result)
        except Exception as exc:
            logger.warning("Damage detection failed: %s", exc)
            return []

    def _finding_to_assessment(self, finding: VisualFinding) -> DamageAssessment:
        severity_map = {
            "info": DamageSeverity.NONE,
            "warning": DamageSeverity.MODERATE,
            "critical": DamageSeverity.SEVERE,
        }
        return DamageAssessment(
            damage_type=DamageType.UNKNOWN,
            severity=severity_map.get(finding.severity, DamageSeverity.NONE),
            confidence=finding.confidence,
            description=finding.description,
            location="unspecified",
        )

    def _parse_damage_response(self, response: dict[str, Any]) -> list[DamageAssessment]:
        assessments: list[DamageAssessment] = []
        for d in response.get("damages", []):
            dtype_str = d.get("type", "unknown")
            try:
                dtype = DamageType(dtype_str)
            except ValueError:
                dtype = DamageType.UNKNOWN
            sev_str = d.get("severity", "none")
            try:
                severity = DamageSeverity(sev_str)
            except ValueError:
                severity = DamageSeverity.NONE

            assessments.append(
                DamageAssessment(
                    damage_type=dtype,
                    severity=severity,
                    confidence=0.8,
                    description=d.get("description", ""),
                    location=d.get("location", ""),
                    estimated_repair_cost=d.get("estimated_repair_cost", ""),
                    age_estimate=d.get("age_estimate", "unknown"),
                    weather_correlation=d.get("weather_correlation", ""),
                )
            )
        return assessments

    def assess_property_risk(self, assessments: list[DamageAssessment]) -> tuple[VisualRisk, list[str]]:
        if not assessments:
            return VisualRisk.LOW, []

        risk_factors: list[str] = []
        max_severity = DamageSeverity.NONE
        for a in assessments:
            sev_order = list(DamageSeverity)
            if sev_order.index(a.severity) > sev_order.index(max_severity):
                max_severity = a.severity
            if a.severity in (DamageSeverity.MODERATE, DamageSeverity.SEVERE, DamageSeverity.CATASTROPHIC):
                risk_factors.append(f"{a.damage_type.value} damage ({a.severity.value}): {a.description}")

        if max_severity == DamageSeverity.CATASTROPHIC:
            return VisualRisk.CRITICAL, risk_factors
        if max_severity == DamageSeverity.SEVERE:
            return VisualRisk.HIGH, risk_factors
        if max_severity == DamageSeverity.MODERATE:
            return VisualRisk.MODERATE, risk_factors
        return VisualRisk.LOW, risk_factors
