"""Property photo analysis module — Vision LLM, satellite imagery, damage detection."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from insureflow.ml.vision.analyzer import VisionLLMAnalyzer
    from insureflow.ml.vision.damage_detector import DamageAssessment, DamageDetector, DamageSeverity, DamageType
    from insureflow.ml.vision.forensics import inspect_photo_forensics
    from insureflow.ml.vision.models import PhotoAnalysis, PhotoQuality, PropertyVisualProfile, SatelliteAnalysis, VisualFinding, VisualRisk
    from insureflow.ml.vision.photo_scorer import score_photo_quality
    from insureflow.ml.vision.pipeline import PropertyPhotoAnalyzer, analyze_property_photos
    from insureflow.ml.vision.satellite import SatelliteImageryProvider, fetch_satellite_imagery

_LAZY_MAP: dict[str, tuple[str, str]] = {
    "PropertyPhotoAnalyzer": ("insureflow.ml.vision.pipeline", "PropertyPhotoAnalyzer"),
    "analyze_property_photos": ("insureflow.ml.vision.pipeline", "analyze_property_photos"),
    "DamageAssessment": ("insureflow.ml.vision.damage_detector", "DamageAssessment"),
    "DamageDetector": ("insureflow.ml.vision.damage_detector", "DamageDetector"),
    "DamageSeverity": ("insureflow.ml.vision.damage_detector", "DamageSeverity"),
    "DamageType": ("insureflow.ml.vision.damage_detector", "DamageType"),
    "PhotoAnalysis": ("insureflow.ml.vision.models", "PhotoAnalysis"),
    "PhotoQuality": ("insureflow.ml.vision.models", "PhotoQuality"),
    "PropertyVisualProfile": ("insureflow.ml.vision.models", "PropertyVisualProfile"),
    "SatelliteAnalysis": ("insureflow.ml.vision.models", "SatelliteAnalysis"),
    "SatelliteImageryProvider": ("insureflow.ml.vision.satellite", "SatelliteImageryProvider"),
    "VisualFinding": ("insureflow.ml.vision.models", "VisualFinding"),
    "VisualRisk": ("insureflow.ml.vision.models", "VisualRisk"),
    "VisionLLMAnalyzer": ("insureflow.ml.vision.analyzer", "VisionLLMAnalyzer"),
    "fetch_satellite_imagery": ("insureflow.ml.vision.satellite", "fetch_satellite_imagery"),
    "score_photo_quality": ("insureflow.ml.vision.photo_scorer", "score_photo_quality"),
    "inspect_photo_forensics": ("insureflow.ml.vision.forensics", "inspect_photo_forensics"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_MAP:
        mod_path, attr = _LAZY_MAP[name]
        return getattr(import_module(mod_path), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    "inspect_photo_forensics",
]
