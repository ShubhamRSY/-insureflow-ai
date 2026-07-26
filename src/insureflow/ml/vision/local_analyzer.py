"""Local property analyzer — rule-based fallback when no Vision LLM API key is set.

Uses image metadata (dimensions, file size, blur, brightness) and basic heuristics
to generate a structured property analysis without any external API calls.
"""

from __future__ import annotations

import logging
from typing import Any

from insureflow.ml.vision.models import PhotoAnalysis, PhotoQuality, VisualFinding, VisualRisk

logger = logging.getLogger(__name__)

# Heuristic thresholds
_LARGE_FILE_KB = 2000
_WIDE_ASPECT = 1.5
_SQUARE_ASPECT = 1.1
_LOW_LIGHT = 0.2
_BRIGHT_LIGHT = 0.85
_HIGH_BLUR = 0.15


def infer_property_features(analysis: PhotoAnalysis) -> dict[str, Any]:
    """Infer property features from image metadata heuristics.

    Returns a dict matching the VisionLLMAnalyzer output schema so it can
    be consumed identically downstream.
    """
    w = analysis.width
    h = analysis.height
    blur = analysis.blur_score
    brightness = analysis.brightness
    kb = analysis.file_size_kb
    quality = analysis.quality

    features: dict[str, Any] = {
        "building_condition": "unknown",
        "construction_materials": [],
        "roof_condition": "not visible",
        "visible_damage": [],
        "exterior_features": [],
        "hazard_indicators": [],
        "fire_protection": "not assessable from metadata",
        "security_features": [],
        "occupancy_clues": "not assessable from metadata",
        "environmental_notes": "",
        "overall_risk": "low",
        "risk_summary": "",
        "underwriting_flags": [],
    }

    flags: list[str] = []
    hazards: list[dict[str, str]] = []

    # Image quality-based flags
    if quality in (PhotoQuality.POOR, PhotoQuality.UNUSABLE):
        flags.append("Low-quality image — limited visual assessment possible")
        hazards.append({"type": "image_quality", "description": "Poor image quality limits assessment", "risk_level": "medium"})

    if blur < _HIGH_BLUR:
        flags.append("Blurred image — structural details unclear")

    if brightness < _LOW_LIGHT:
        flags.append("Underexposed image — may hide damage or defects")
        hazards.append({"type": "visibility", "description": "Dark image may conceal damage", "risk_level": "low"})
    elif brightness > _BRIGHT_LIGHT:
        flags.append("Overexposed image — washed out details")

    # Resolution-based inference
    if w > 0 and h > 0:
        aspect = w / h
        if aspect > _WIDE_ASPECT:
            features["exterior_features"].append("wide_angle_view")
        elif aspect < (1 / _WIDE_ASPECT):
            features["exterior_features"].append("tall_angle_view")
        else:
            features["exterior_features"].append("standard_frame")

        total_pixels = w * h
        if total_pixels >= 1920 * 1080:
            features["exterior_features"].append("high_resolution")
        elif total_pixels < 640 * 480:
            flags.append(f"Low resolution ({w}x{h}) — request higher-quality photo")

    # File size heuristics
    if kb > _LARGE_FILE_KB:
        features["exterior_features"].append("large_file_size")
    elif kb < 50:
        flags.append("Very small file — may be thumbnail, not original")

    # Build risk summary
    risk_level = "low"
    if len(flags) >= 3:
        risk_level = "moderate"
    if any(h.get("risk_level") == "high" for h in hazards):
        risk_level = "high"

    features["overall_risk"] = risk_level
    features["hazard_indicators"] = hazards
    features["underwriting_flags"] = flags

    summary_parts = ["Local metadata analysis (no Vision LLM available)."]
    if flags:
        summary_parts.append(f"{len(flags)} quality concern(s) detected.")
    if hazards:
        summary_parts.append(f"{len(hazards)} hazard indicator(s) flagged.")
    if not flags and not hazards:
        summary_parts.append("Image metadata within normal parameters.")
    features["risk_summary"] = " ".join(summary_parts)

    return features


def enrich_with_local_analysis(analysis: PhotoAnalysis) -> PhotoAnalysis:
    """Enrich a PhotoAnalysis with local heuristic-based property features.

    This is the fallback used when VisionLLMAnalyzer is not available.
    """
    features = infer_property_features(analysis)

    analysis.ai_description = features.get("risk_summary", "")

    condition = features.get("building_condition", "")
    if condition and condition != "unknown":
        analysis.detected_features.append(f"building_condition:{condition}")

    for mat in features.get("construction_materials", []):
        analysis.detected_features.append(f"material:{mat}")

    for damage in features.get("visible_damage", []):
        severity_map = {"minor": "info", "moderate": "warning", "severe": "critical"}
        analysis.findings.append(
            VisualFinding(
                category="damage",
                description=f"{damage.get('type', 'Unknown')}: {damage.get('description', '')} ({damage.get('location', 'unspecified')})",
                severity=severity_map.get(damage.get("severity", "minor"), "info"),
                confidence=0.5,
            )
        )

    for hazard in features.get("hazard_indicators", []):
        risk_map = {"low": "info", "medium": "warning", "high": "critical"}
        analysis.findings.append(
            VisualFinding(
                category="hazard",
                description=f"{hazard.get('type', 'Unknown')}: {hazard.get('description', '')}",
                severity=risk_map.get(hazard.get("risk_level", "low"), "info"),
                confidence=0.5,
            )
        )

    overall = features.get("overall_risk", "low")
    risk_map_str = {"critical": VisualRisk.CRITICAL, "high": VisualRisk.HIGH, "moderate": VisualRisk.MODERATE}
    analysis.visual_risk = risk_map_str.get(overall, VisualRisk.LOW)

    for flag in features.get("underwriting_flags", []):
        analysis.findings.append(
            VisualFinding(
                category="underwriting_flag",
                description=flag,
                severity="warning",
                confidence=0.5,
            )
        )

    return analysis
