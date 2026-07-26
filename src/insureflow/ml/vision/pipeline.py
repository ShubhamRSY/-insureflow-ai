"""Vision pipeline orchestrator — combines photo quality, LLM analysis, satellite, and damage detection.

This is the main entry point for property photo analysis. It coordinates:
1. Photo quality scoring (local, no API needed)
2. Vision LLM analysis (GPT-4V / Claude Vision)
3. Satellite imagery analysis
4. Damage detection and risk assessment
"""

from __future__ import annotations

import logging
from typing import Any

from insureflow.ml.vision.analyzer import VisionLLMAnalyzer
from insureflow.ml.vision.damage_detector import DamageDetector
from insureflow.ml.vision.local_analyzer import enrich_with_local_analysis
from insureflow.ml.vision.models import (
    PhotoAnalysis,
    PhotoQuality,
    PropertyVisualProfile,
    VisualFinding,
    VisualRisk,
)
from insureflow.ml.vision.photo_scorer import score_photo_quality
from insureflow.ml.vision.satellite import SatelliteImageryProvider

logger = logging.getLogger(__name__)


class PropertyPhotoAnalyzer:
    def __init__(
        self,
        vision_provider: str | None = None,
        google_maps_key: str | None = None,
        nearmap_key: str | None = None,
    ) -> None:
        self._vision = VisionLLMAnalyzer(provider=vision_provider)
        self._satellite = SatelliteImageryProvider(
            google_api_key=google_maps_key,
            nearmap_api_key=nearmap_key,
        )
        self._damage = DamageDetector(vision_analyzer=self._vision)

    @property
    def vision_available(self) -> bool:
        return self._vision.available

    @property
    def satellite_available(self) -> bool:
        return self._satellite.available

    def analyze_photos(
        self,
        photos: list[dict[str, Any]],
        latitude: float | None = None,
        longitude: float | None = None,
        address: str = "",
        bundle_id: str = "",
    ) -> PropertyVisualProfile:
        profile = PropertyVisualProfile(bundle_id=bundle_id)
        profile.total_photos = len(photos)

        for i, photo in enumerate(photos):
            image_data = photo.get("image_data", b"")
            filename = photo.get("filename", f"photo-{i}.jpg")
            photo_id = photo.get("photo_id", f"{bundle_id}-photo-{i}")

            if not image_data:
                continue

            analysis = self._analyze_single_photo(image_data, filename, photo_id)
            profile.photo_analyses.append(analysis)
            profile.analyzed_photos += 1

        if latitude is not None and longitude is not None:
            profile.satellite = self._satellite.analyze_satellite(latitude, longitude, address)

        self._compile_findings(profile)
        self._assess_overall_risk(profile)
        self._generate_recommendations(profile)

        profile.processing_notes = self._build_notes(profile)
        return profile

    def _analyze_single_photo(
        self,
        image_data: bytes,
        filename: str,
        photo_id: str,
    ) -> PhotoAnalysis:
        analysis = score_photo_quality(image_data, filename, photo_id)

        if self._vision.available:
            analysis = self._vision.enrich_analysis(analysis, image_data)
        else:
            analysis = enrich_with_local_analysis(analysis)

        return analysis

    def _compile_findings(self, profile: PropertyVisualProfile) -> None:
        all_findings: list[VisualFinding] = []
        for photo in profile.photo_analyses:
            all_findings.extend(photo.findings)
        if profile.satellite:
            all_findings.extend(profile.satellite.findings)
        profile.all_findings = all_findings

    def _assess_overall_risk(self, profile: PropertyVisualProfile) -> None:
        risk_scores = []
        for photo in profile.photo_analyses:
            risk_map = {VisualRisk.LOW: 0, VisualRisk.MODERATE: 1, VisualRisk.HIGH: 2, VisualRisk.CRITICAL: 3}
            risk_scores.append(risk_map.get(photo.visual_risk, 0))

        if profile.satellite:
            risk_map = {VisualRisk.LOW: 0, VisualRisk.MODERATE: 1, VisualRisk.HIGH: 2, VisualRisk.CRITICAL: 3}
            risk_scores.append(risk_map.get(profile.satellite.aerial_risk, 0))

        if not risk_scores:
            profile.overall_visual_risk = VisualRisk.LOW
            return

        max_risk = max(risk_scores)
        risk_names = [VisualRisk.LOW, VisualRisk.MODERATE, VisualRisk.HIGH, VisualRisk.CRITICAL]
        profile.overall_visual_risk = risk_names[min(max_risk, 3)]

        risk_factors: list[str] = []
        if max_risk >= 2:
            risk_factors.append("Multiple high-risk visual findings detected")
        if profile.damage_count > 0:
            risk_factors.append(f"{profile.damage_count} damage indicators found")

        damage_assessments = []
        for photo in profile.photo_analyses:
            damage_assessments.extend(self._damage.detect_from_analysis(photo))
        if damage_assessments:
            _, damage_risks = self._damage.assess_property_risk(damage_assessments)
            risk_factors.extend(damage_risks)

        profile.risk_factors = risk_factors

    def _generate_recommendations(self, profile: PropertyVisualProfile) -> None:
        recs: list[str] = []
        damage_count = profile.damage_count
        if damage_count > 0:
            recs.append(f"Schedule on-site inspection — {damage_count} damage indicators from photos")

        poor_photos = sum(1 for p in profile.photo_analyses if p.quality in (PhotoQuality.POOR, PhotoQuality.UNUSABLE))
        if poor_photos > 0:
            recs.append(f"Request {poor_photos} higher-quality photos for accurate assessment")

        if profile.satellite and profile.satellite.aerial_risk in (VisualRisk.HIGH, VisualRisk.CRITICAL):
            recs.append("Satellite analysis flagged high-risk features — verify with field inspection")

        if not profile.has_satellite_data:
            recs.append("No satellite imagery available — consider aerial inspection for roof/lot assessment")

        low_res = sum(1 for p in profile.photo_analyses if p.width < 640 or p.height < 480)
        if low_res > 0:
            recs.append(f"{low_res} photos below minimum resolution — request re-shoot")

        if not recs:
            recs.append("Visual assessment complete — no immediate concerns identified")

        profile.recommendations = recs

    def _build_notes(self, profile: PropertyVisualProfile) -> str:
        parts = [f"Analyzed {profile.analyzed_photos}/{profile.total_photos} photos"]
        if self._vision.available:
            parts.append("Vision LLM: active")
        else:
            parts.append("Vision LLM: local heuristic fallback")
        if self._satellite.available:
            parts.append("Satellite: active")
        else:
            parts.append("Satellite: Nominatim/Overpass fallback")
        return " | ".join(parts)


def analyze_property_photos(
    photos: list[dict[str, Any]],
    latitude: float | None = None,
    longitude: float | None = None,
    address: str = "",
    bundle_id: str = "",
    vision_provider: str | None = None,
    google_maps_key: str | None = None,
) -> PropertyVisualProfile:
    analyzer = PropertyPhotoAnalyzer(
        vision_provider=vision_provider,
        google_maps_key=google_maps_key,
    )
    return analyzer.analyze_photos(
        photos,
        latitude=latitude,
        longitude=longitude,
        address=address,
        bundle_id=bundle_id,
    )
