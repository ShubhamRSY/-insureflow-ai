"""Data models for property photo analysis and visual risk assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class VisualRisk(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class PhotoQuality(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"


@dataclass
class VisualFinding:
    category: str
    description: str
    severity: str = "info"
    confidence: float = 0.0
    bounding_box: Optional[list[float]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "description": self.description,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "bounding_box": self.bounding_box,
        }


@dataclass
class PhotoAnalysis:
    photo_id: str
    filename: str
    quality: PhotoQuality = PhotoQuality.ACCEPTABLE
    quality_score: float = 0.0
    width: int = 0
    height: int = 0
    file_size_kb: float = 0.0
    blur_score: float = 0.0
    brightness: float = 0.0
    findings: list[VisualFinding] = field(default_factory=list)
    visual_risk: VisualRisk = VisualRisk.LOW
    ai_description: str = ""
    detected_features: list[str] = field(default_factory=list)
    ocr_text: str = ""

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def has_damage(self) -> bool:
        return any(f.severity in ("warning", "critical") for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "photo_id": self.photo_id,
            "filename": self.filename,
            "quality": self.quality.value,
            "quality_score": round(self.quality_score, 3),
            "dimensions": f"{self.width}x{self.height}",
            "file_size_kb": round(self.file_size_kb, 1),
            "blur_score": round(self.blur_score, 3),
            "brightness": round(self.brightness, 3),
            "finding_count": self.finding_count,
            "has_damage": self.has_damage,
            "visual_risk": self.visual_risk.value,
            "ai_description": self.ai_description,
            "detected_features": self.detected_features,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class SatelliteAnalysis:
    address: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    zoom_level: int = 19
    image_width: int = 640
    image_height: int = 640
    roof_condition: str = "unknown"
    roof_material: str = "unknown"
    roof_age_estimate: str = "unknown"
    lot_coverage: float = 0.0
    nearby_hazards: list[str] = field(default_factory=list)
    vegetation_proximity: str = "unknown"
    parking_assessment: str = "unknown"
    aerial_risk: VisualRisk = VisualRisk.LOW
    findings: list[VisualFinding] = field(default_factory=list)
    image_url: str = ""
    analysis_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "coordinates": {"lat": self.latitude, "lng": self.longitude},
            "roof_condition": self.roof_condition,
            "roof_material": self.roof_material,
            "roof_age_estimate": self.roof_age_estimate,
            "lot_coverage": round(self.lot_coverage, 3),
            "nearby_hazards": self.nearby_hazards,
            "vegetation_proximity": self.vegetation_proximity,
            "parking_assessment": self.parking_assessment,
            "aerial_risk": self.aerial_risk.value,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "analysis_notes": self.analysis_notes,
        }


@dataclass
class PropertyVisualProfile:
    bundle_id: str = ""
    total_photos: int = 0
    analyzed_photos: int = 0
    overall_quality: PhotoQuality = PhotoQuality.ACCEPTABLE
    overall_visual_risk: VisualRisk = VisualRisk.LOW
    photo_analyses: list[PhotoAnalysis] = field(default_factory=list)
    satellite: Optional[SatelliteAnalysis] = None
    all_findings: list[VisualFinding] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    processing_notes: str = ""

    @property
    def damage_count(self) -> int:
        return sum(1 for f in self.all_findings if f.severity in ("warning", "critical"))

    @property
    def has_satellite_data(self) -> bool:
        return self.satellite is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "total_photos": self.total_photos,
            "analyzed_photos": self.analyzed_photos,
            "overall_quality": self.overall_quality.value,
            "overall_visual_risk": self.overall_visual_risk.value,
            "damage_count": self.damage_count,
            "has_satellite_data": self.has_satellite_data,
            "risk_factors": self.risk_factors,
            "recommendations": self.recommendations,
            "processing_notes": self.processing_notes,
            "photo_analyses": [p.to_dict() for p in self.photo_analyses],
            "satellite": self.satellite.to_dict() if self.satellite else None,
            "all_findings": [f.to_dict() for f in self.all_findings],
        }
