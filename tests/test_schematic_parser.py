from __future__ import annotations

from insureflow.ingestion.classifier import DocumentClassifier
from insureflow.ingestion.loader import SubmissionLoader
from insureflow.ingestion.schematic_parser import SchematicParser
from insureflow.models.submissions import DocumentType
from insureflow.underwriting.hazards import assess_physical_hazard

FLOOR_PLAN = """RIVERFRONT DISTRIBUTION CENTER — FLOOR PLAN
Floor Area: 42,000 sq ft
Number of Stories: 2
Fire Compartments: 3
Compartmentalization: Compartmented
Number of Exits: 4
Exit doors: 2, Stairwells: 2, Corridors
Fire Alarm System: Yes
Sprinklered: Fully Sprinklered
"""

POOR_EGRESS_PLAN = """DOWNTOWN OFFICE BUILDING — SCHEMATIC
Floor Area: 8,000 sq ft
Number of Stories: 1
Number of Exits: 1
Exit Door: 1
Fire Alarm System: No
"""


class TestSchematicParser:
    def test_parse_structured_full_plan(self) -> None:
        data = SchematicParser().parse_structured(FLOOR_PLAN)
        assert data.floor_area_sqft == 42000.0
        assert data.number_of_stories == 2
        assert data.fire_compartments == 3
        assert data.compartmentalization == "compartmented"
        assert data.number_of_exits == 4
        assert "exit doors" in data.exit_types
        assert "stairwells" in data.exit_types
        assert data.stairwells == 2
        assert data.fire_alarm == "yes"
        assert data.sprinklered == "yes"
        assert data.source == "schematic_floor_plan"

    def test_parse_unstructured(self) -> None:
        parsed = SchematicParser().parse(FLOOR_PLAN, "fp-1")
        assert parsed.submission_id == "fp-1"
        assert parsed.document_type == "floor_plan"
        assert parsed.source == "schematic_floor_plan"
        assert parsed.extracted_fields["floor_area_sqft"][0].value == "42000.0"
        assert parsed.extracted_fields["number_of_exits"][0].value == "4"

    def test_tabular_format(self) -> None:
        table = """| Floor Plan Summary | |
|---|---|
| Floor Area | 42,000 sq ft |
| Number of Stories | 2 |
| Number of Exits | 4 |
| Stairwells | 2 |
| Fire Compartments | 3 |
"""
        data = SchematicParser().parse_structured(table)
        assert data.floor_area_sqft == 42000.0
        assert data.number_of_exits == 4
        assert data.number_of_stories == 2


class TestFloorPlanClassifier:
    def test_classifies_floor_plan(self) -> None:
        assert DocumentClassifier.classify(FLOOR_PLAN, "doc-1") == DocumentType.FLOOR_PLAN


class TestLoaderFloorPlanIntegration:
    def test_load_bundle_floor_plans(self) -> None:
        bundle = SubmissionLoader().load_bundle(
            bundle_id="fp-bundle-1",
            floor_plans=[FLOOR_PLAN],
        )
        assert len(bundle.unstructured) == 1
        assert bundle.structured is not None
        assert bundle.structured.floor_plan is not None
        assert bundle.structured.floor_plan.floor_area_sqft == 42000.0
        assert bundle.structured.risk_profile is not None
        assert bundle.structured.risk_profile.total_square_footage == 42000.0
        assert bundle.structured.risk_profile.number_of_stories == 2
        assert bundle.structured.risk_profile.sprinklered is True

    def test_load_bundle_auto_classified(self) -> None:
        bundle = SubmissionLoader().load_bundle(
            bundle_id="fp-bundle-2",
            raw_docs=[FLOOR_PLAN],
            auto_classify=True,
        )
        assert bundle.structured is not None
        assert bundle.structured.floor_plan is not None
        assert bundle.structured.floor_plan.number_of_exits == 4


class TestFloorPlanHazards:
    def test_adequate_egress_no_hazard(self) -> None:
        bundle = SubmissionLoader().load_bundle(bundle_id="fp-haz-1", floor_plans=[FLOOR_PLAN])
        assessment = assess_physical_hazard(bundle)
        assert not any(s.source == "floor_plan" and s.severity.value == "high" for s in assessment.signals)

    def test_inadequate_egress_flagged(self) -> None:
        bundle = SubmissionLoader().load_bundle(bundle_id="fp-haz-2", floor_plans=[POOR_EGRESS_PLAN])
        assessment = assess_physical_hazard(bundle)
        floor_signals = [s for s in assessment.signals if s.source == "floor_plan"]
        assert any("only 1 exit" in s.detail for s in floor_signals)
        assert any(s.severity.value == "high" for s in floor_signals)
