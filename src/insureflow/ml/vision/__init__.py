"""Property photo analysis module — Vision LLM, satellite imagery, damage detection."""

from __future__ import annotations

from insureflow.ml.vision.analyzer import VisionLLMAnalyzer
from insureflow.ml.vision.damage_detector import DamageAssessment, DamageDetector, DamageSeverity, DamageType
from insureflow.ml.vision.models import PhotoAnalysis, PhotoQuality, PropertyVisualProfile, SatelliteAnalysis, VisualFinding, VisualRisk
from insureflow.ml.vision.photo_scorer import score_photo_quality
from insureflow.ml.vision.pipeline import PropertyPhotoAnalyzer, analyze_property_photos
from insureflow.ml.vision.satellite import SatelliteImageryProvider, fetch_satellite_imagery

__all__ = [
    "PropertyPhotoAnalyzer",
    "analyze_property_photos",
    "DamageAssessment",
    "DamageDetector",
    "DamageSeverity",
    "DamageType",
    "PhotoAnalysis",
    "PhotoQuality",
    "PropertyVisualProfile",
    "SatelliteAnalysis",
    "SatelliteImageryProvider",
    "VisualFinding",
    "VisualRisk",
    "VisionLLMAnalyzer",
    "fetch_satellite_imagery",
    "score_photo_quality",
]
