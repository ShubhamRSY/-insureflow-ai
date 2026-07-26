"""Tests for the property photo analysis vision module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from insureflow.ml.vision.damage_detector import DamageAssessment, DamageDetector, DamageSeverity, DamageType
from insureflow.ml.vision.models import (
    PhotoAnalysis,
    PhotoQuality,
    PropertyVisualProfile,
    SatelliteAnalysis,
    VisualFinding,
    VisualRisk,
)
from insureflow.ml.vision.photo_scorer import score_photo_quality


# ─── Data Model Tests ───

class TestPhotoAnalysis:
    def test_default_values(self):
        pa = PhotoAnalysis(photo_id="test-1", filename="test.jpg")
        assert pa.photo_id == "test-1"
        assert pa.quality == PhotoQuality.ACCEPTABLE
        assert pa.visual_risk == VisualRisk.LOW
        assert pa.finding_count == 0
        assert not pa.has_damage

    def test_has_damage_with_critical_finding(self):
        pa = PhotoAnalysis(photo_id="test-1", filename="test.jpg")
        pa.findings.append(VisualFinding(category="damage", description="crack", severity="critical"))
        assert pa.has_damage

    def test_has_damage_with_info_finding(self):
        pa = PhotoAnalysis(photo_id="test-1", filename="test.jpg")
        pa.findings.append(VisualFinding(category="quality", description="blurry", severity="info"))
        assert not pa.has_damage

    def test_to_dict(self):
        pa = PhotoAnalysis(photo_id="p1", filename="img.jpg")
        pa.findings.append(VisualFinding(category="damage", description="test", severity="warning"))
        d = pa.to_dict()
        assert d["photo_id"] == "p1"
        assert d["finding_count"] == 1
        assert d["has_damage"] is True
        assert len(d["findings"]) == 1


class TestPropertyVisualProfile:
    def test_empty_profile(self):
        pvp = PropertyVisualProfile(bundle_id="b1")
        assert pvp.total_photos == 0
        assert pvp.damage_count == 0
        assert not pvp.has_satellite_data

    def test_damage_count(self):
        pvp = PropertyVisualProfile(bundle_id="b1")
        pvp.all_findings = [
            VisualFinding(category="d", description="a", severity="warning"),
            VisualFinding(category="d", description="b", severity="critical"),
            VisualFinding(category="q", description="c", severity="info"),
        ]
        assert pvp.damage_count == 2

    def test_has_satellite_data(self):
        pvp = PropertyVisualProfile(bundle_id="b1")
        assert not pvp.has_satellite_data
        pvp.satellite = SatelliteAnalysis(address="123 Main St")
        assert pvp.has_satellite_data

    def test_to_dict(self):
        pvp = PropertyVisualProfile(bundle_id="b1")
        pvp.total_photos = 3
        d = pvp.to_dict()
        assert d["bundle_id"] == "b1"
        assert d["total_photos"] == 3


class TestSatelliteAnalysis:
    def test_to_dict(self):
        sa = SatelliteAnalysis(address="123 Main St", latitude=37.7, longitude=-122.4)
        d = sa.to_dict()
        assert d["address"] == "123 Main St"
        assert d["coordinates"]["lat"] == 37.7


class TestVisualFinding:
    def test_to_dict(self):
        vf = VisualFinding(category="damage", description="crack in wall", severity="warning", confidence=0.85)
        d = vf.to_dict()
        assert d["category"] == "damage"
        assert d["severity"] == "warning"
        assert d["confidence"] == 0.85


# ─── Photo Quality Scorer Tests ───

class TestPhotoQualityScorer:
    def test_with_minimal_image(self):
        image_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        analysis = score_photo_quality(image_data, "test.png", "p1")
        assert analysis.photo_id == "p1"
        assert analysis.filename == "test.png"
        assert 0 <= analysis.quality_score <= 1
        assert isinstance(analysis.quality, PhotoQuality)

    def test_with_empty_data(self):
        analysis = score_photo_quality(b"", "empty.jpg", "p2")
        assert analysis.photo_id == "p2"
        assert analysis.file_size_kb == 0.0


# ─── Damage Detector Tests ───

class TestDamageDetector:
    def test_empty_findings(self):
        detector = DamageDetector()
        analysis = PhotoAnalysis(photo_id="p1", filename="test.jpg")
        assessments = detector.detect_from_analysis(analysis)
        assert len(assessments) == 0

    def test_damage_finding_to_assessment(self):
        detector = DamageDetector()
        analysis = PhotoAnalysis(photo_id="p1", filename="test.jpg")
        analysis.findings.append(VisualFinding(category="damage", description="Water stain on ceiling", severity="warning"))
        assessments = detector.detect_from_analysis(analysis)
        assert len(assessments) == 1
        assert assessments[0].severity == DamageSeverity.MODERATE

    def test_assess_property_risk_no_damage(self):
        detector = DamageDetector()
        risk, factors = detector.assess_property_risk([])
        assert risk == VisualRisk.LOW
        assert len(factors) == 0

    def test_assess_property_risk_with_damage(self):
        detector = DamageDetector()
        assessments = [
            DamageAssessment(damage_type=DamageType.WATER, severity=DamageSeverity.SEVERE, description="Major leak"),
        ]
        risk, factors = detector.assess_property_risk(assessments)
        assert risk == VisualRisk.HIGH
        assert len(factors) == 1

    def test_parse_damage_response(self):
        detector = DamageDetector()
        response = {
            "damages": [
                {"type": "hail", "severity": "moderate", "location": "roof", "description": "Hail dents on shingles"}
            ],
            "overall_damage_level": "moderate",
            "summary": "Moderate hail damage visible on roof",
        }
        assessments = detector._parse_damage_response(response)
        assert len(assessments) == 1
        assert assessments[0].damage_type == DamageType.HAIL
        assert assessments[0].severity == DamageSeverity.MODERATE


# ─── Vision LLM Analyzer Tests ───

class TestVisionLLMAnalyzer:
    def test_unavailable_without_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            from insureflow.ml.vision.analyzer import VisionLLMAnalyzer

            analyzer = VisionLLMAnalyzer()
            assert not analyzer.available

    def test_parse_json_response_valid(self):
        from insureflow.ml.vision.analyzer import _parse_json_response

        text = '{"building_condition": "good", "overall_risk": "low"}'
        result = _parse_json_response(text)
        assert result["building_condition"] == "good"

    def test_parse_json_response_with_code_block(self):
        from insureflow.ml.vision.analyzer import _parse_json_response

        text = '```json\n{"building_condition": "poor"}\n```'
        result = _parse_json_response(text)
        assert result["building_condition"] == "poor"

    def test_parse_json_response_malformed(self):
        from insureflow.ml.vision.analyzer import _parse_json_response

        result = _parse_json_response("not json at all")
        assert result == {}


# ─── Satellite Tests ───

class TestSatelliteImageryProvider:
    def test_unavailable_without_keys(self):
        from insureflow.ml.vision.satellite import SatelliteImageryProvider

        with patch.dict("os.environ", {}, clear=True):
            provider = SatelliteImageryProvider()
            assert not provider.available

    def test_analyze_satellite_no_image(self):
        from insureflow.ml.vision.satellite import SatelliteImageryProvider

        provider = SatelliteImageryProvider()
        analysis = provider.analyze_satellite(37.7, -122.4, "123 Main St")
        assert analysis.address == "123 Main St"
        assert analysis.latitude == 37.7


# ─── Pipeline Orchestrator Tests ───

class TestPropertyPhotoAnalyzer:
    def test_analyze_photos_empty(self):
        from insureflow.ml.vision.pipeline import PropertyPhotoAnalyzer

        analyzer = PropertyPhotoAnalyzer()
        profile = analyzer.analyze_photos([], bundle_id="b1")
        assert profile.total_photos == 0
        assert profile.analyzed_photos == 0

    def test_analyze_photos_with_invalid_data(self):
        from insureflow.ml.vision.pipeline import PropertyPhotoAnalyzer

        analyzer = PropertyPhotoAnalyzer()
        photos = [{"image_data": b"", "filename": "empty.jpg"}]
        profile = analyzer.analyze_photos(photos, bundle_id="b1")
        assert profile.total_photos == 1
        assert profile.analyzed_photos == 0

    def test_analyze_photos_without_apis(self):
        from insureflow.ml.vision.pipeline import PropertyPhotoAnalyzer

        analyzer = PropertyPhotoAnalyzer()
        assert not analyzer.vision_available
        assert not analyzer.satellite_available

        photos = [{"image_data": b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "filename": "test.png"}]
        profile = analyzer.analyze_photos(photos, bundle_id="b1")
        assert profile.total_photos == 1
        assert profile.analyzed_photos == 1
        assert profile.processing_notes != ""


# ─── Triage Agent Photo Detection Tests ───

class TestTriagePhotoDetection:
    def test_photos_detected_with_visual_analysis(self):
        from insureflow.agents.triage_agent import TriageAgent
        from insureflow.models.submissions import SubmissionBundle

        agent = TriageAgent()
        bundle = SubmissionBundle(bundle_id="b1")
        bundle.visual_analysis = {"analyzed_photos": 2, "overall_visual_risk": "low"}
        result = agent.score_submission(bundle)
        assert result.document_checklist.photos is True

    def test_photos_not_detected_without_visual_analysis(self):
        from insureflow.agents.triage_agent import TriageAgent
        from insureflow.models.submissions import SubmissionBundle

        agent = TriageAgent()
        bundle = SubmissionBundle(bundle_id="b1")
        result = agent.score_submission(bundle)
        assert result.document_checklist.photos is False

    def test_inspection_report_detected(self):
        from insureflow.agents.triage_agent import TriageAgent
        from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission

        agent = TriageAgent()
        bundle = SubmissionBundle(bundle_id="b1")
        bundle.unstructured.append(UnstructuredSubmission(
            submission_id="u1",
            source="inspection_report",
            document_type="inspection_report",
            raw_text="Inspection report content",
        ))
        result = agent.score_submission(bundle)
        assert result.document_checklist.inspection_report is True
