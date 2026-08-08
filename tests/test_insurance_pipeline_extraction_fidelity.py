from __future__ import annotations

from pathlib import Path

from insureflow.ingestion.acord_parser import ACORDParser
from insureflow.ingestion.json_parser import JSONBrokerParser
from insureflow.ingestion.loader import SubmissionLoader
from insureflow.ingestion.loss_run_parser import LossRunParser
from insureflow.ingestion.report_extractor import InspectionReportExtractor
from insureflow.provenance.hierarchy import ProvenanceEngine
from insureflow.reconciliation.engine import ReconciliationEngine

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "insurance"


def _fixture(name: str) -> str:
    return (EXAMPLES / name).read_text(encoding="utf-8")


PACIFIC_LOSS_RUN = _fixture("pacific_coast_loss_run.md")
PACIFIC_INSPECTION = _fixture("pacific_coast_inspection_report.md")
PACIFIC_ACORD = _fixture("pacific_coast_acord.xml")
PACIFIC_BROKER_JSON = _fixture("pacific_coast_broker_api.json")
PACIFIC_SOV = _fixture("pacific_coast_sov.md")


class TestLossRunFidelity:
    def test_table_aware_claim_extraction(self) -> None:
        data = LossRunParser().parse_structured(PACIFIC_LOSS_RUN)
        assert data.total_claims == 12
        assert len(data.claims) == 12

    def test_claim_line_item_values(self) -> None:
        data = LossRunParser().parse_structured(PACIFIC_LOSS_RUN)
        by_id = {c.claim_id: c for c in data.claims}
        assert abs(by_id["ZUR-2023-005211"].incurred_amount - 612_500) < 1
        assert abs(by_id["ZUR-2021-003411"].incurred_amount - 45_200) < 1
        assert by_id["ZUR-2021-003411"].line_of_business.lower() == "workers compensation"
        assert abs(by_id["ZUR-2024-000978"].paid_amount - 192_400) < 1

    def test_open_claims_carry_reserves(self) -> None:
        data = LossRunParser().parse_structured(PACIFIC_LOSS_RUN)
        by_id = {c.claim_id: c for c in data.claims}
        open8 = by_id["ZUR-2024-000978"]
        assert open8.claim_status.value == "open"
        assert abs(open8.open_reserve - 23_400) < 1
        assert abs(data.total_open_reserves - 173_400) < 1

    def test_litigation_claim_status(self) -> None:
        data = LossRunParser().parse_structured(PACIFIC_LOSS_RUN)
        c = {x.claim_id: x for x in data.claims}["ZUR-2025-001233"]
        assert c.claim_status.value == "pending_litigation"
        assert c.paid_amount == 0
        assert c.claim_id == "ZUR-2025-001233"

    def test_detail_blocks_enrich_table_rows(self) -> None:
        # Claim 11's detail block records the report date and location; the table
        # row supplies status. The merged record must carry both signals.
        data = LossRunParser().parse_structured(PACIFIC_LOSS_RUN)
        c = {x.claim_id: x for x in data.claims}["ZUR-2025-001233"]
        assert c.date_of_loss.isoformat() == "2025-01-22"
        assert "dock" in (c.cause or "").lower()

    def test_per_claim_confidence_is_computed(self) -> None:
        data = LossRunParser().parse_structured(PACIFIC_LOSS_RUN)
        assert all(c.extraction_confidence > 0.0 for c in data.claims)
        # Fully specified rows (both sources agree) score higher than the
        # litigation row where the table and detail only partially agree.
        by_id = {c.claim_id: c for c in data.claims}
        assert by_id["ZUR-2021-003411"].extraction_confidence >= by_id["ZUR-2025-001233"].extraction_confidence

    def test_loss_ratios_parsed(self) -> None:
        data = LossRunParser().parse_structured(PACIFIC_LOSS_RUN)
        assert len(data.loss_ratios) >= 5
        assert abs(data.loss_ratios["2023-2024 (Zurich)"] - 58.1) < 0.1
        assert abs(data.loss_ratios["2021-2022 (Zurich)"] - 15.3) < 0.1

    def test_table_only_loss_run(self) -> None:
        # Real carrier export: a bare pipe table, no claim-detail blocks.
        text = """# LOSS RUN
| Claim ID | Date of Loss | Line of Business | Cause | Incurred | Paid | Status |
|---|---|---|---|---|---|---|
| CL-1001 | 2023-05-01 | Workers Compensation | Back injury | $12,500 | $12,500 | Closed |
| CL-1002 | 2024-09-15 | General Liability | Slip and fall | $44,000 | $10,000 | Open |
"""
        data = LossRunParser().parse_structured(text)
        assert data.total_claims == 2
        by_id = {c.claim_id: c for c in data.claims}
        assert abs(by_id["CL-1001"].incurred_amount - 12_500) < 1
        assert by_id["CL-1001"].claim_status.value == "closed"
        assert by_id["CL-1002"].claim_status.value == "open"
        assert abs(data.total_incurred - 56_500) < 1

    def test_scan_artifacts_do_not_create_phantom_claims(self) -> None:
        # Prose and comma-heavy narratives must not be mistaken for table rows.
        text = """# CLAIM DETAIL

### Claim X-1
**Cause:** The floor drain was blocked, allowing meltwater to refreeze overnight.
**Incurred:** $45,200  **Paid:** $45,200  **Status:** Closed

### Claim X-2
**Cause:** Forklift impact, damaged equipment and racking, no product damage.
**Incurred:** $94,300  **Paid:** $94,300  **Status:** Closed
"""
        data = LossRunParser().parse_structured(text)
        assert data.total_claims == 2
        assert all(abs(c.incurred_amount) > 0 for c in data.claims)


class TestInspectionSurveyFidelity:
    def test_survey_table_parsed(self) -> None:
        sub = InspectionReportExtractor().parse(PACIFIC_INSPECTION, "insp-1")
        fields = sub.extracted_fields
        assert "survey.1.protection_class.application" in fields
        assert "survey.1.protection_class.surveyor" in fields
        assert fields["survey.1.protection_class.application"][0].value == "3"
        assert fields["survey.1.protection_class.surveyor"][0].value == "4 (per ISO)"
        assert fields["survey.1.protection_class.match"][0].value == "NO"

    def test_primary_location_maps_to_canonical_paths(self) -> None:
        sub = InspectionReportExtractor().parse(PACIFIC_INSPECTION, "insp-2")
        fields = sub.extracted_fields
        # Primary (Oakland) surveyor values land on the canonical field names.
        protection = fields.get("surveyor.protection_class", [])
        values = {ef.value for ef in protection}
        assert "4 (per ISO)" in values
        assert "6 (per ISO)" not in values  # secondary location excluded
        square = fields.get("surveyor.square_footage", [])
        assert any("198,750" in ef.value for ef in square)

    def test_mismatches_surface(self) -> None:
        sub = InspectionReportExtractor().parse(PACIFIC_INSPECTION, "insp-3")
        mm = sub.extracted_fields.get("survey.mismatches", [])
        assert len(mm) == 1
        assert "Protection Class" in mm[0].value
        assert "Square Footage" in mm[0].value


class TestStructuredFidelity:
    def test_acord_and_json_merge_keeps_risk_profile(self) -> None:
        bundle = SubmissionLoader().load_bundle(
            acord_xml=PACIFIC_ACORD,
            json_payload=PACIFIC_BROKER_JSON,
            bundle_id="merge-1",
        )
        assert bundle.structured is not None
        rp = bundle.structured.risk_profile
        assert rp is not None
        assert rp.naics_code == "493120"
        assert rp.protection_class == 3
        assert rp.construction_type == "Masonry Non-Combustible"
        assert rp.sprinklered is True
        assert len(bundle.structured.locations) >= 4

    def test_acord_field_confidence_populated(self) -> None:
        sub = ACORDParser().parse(PACIFIC_ACORD, "acord-conf")
        fc = sub.field_confidence
        assert fc.get("named_insured.legal_name", 0) > 0.9
        assert fc.get("risk_profile.protection_class", 0) > 0.9
        assert fc.get("risk_profile.sprinklered", 0) > 0.9
        assert fc.get("coverage.0.limit", 0) > 0.9

    def test_json_field_confidence_populated(self) -> None:
        sub = JSONBrokerParser().parse(PACIFIC_BROKER_JSON, "json-conf")
        assert sub.field_confidence.get("named_insured.legal_name", 0) > 0.9
        assert sub.field_confidence.get("coverage.0.limit", 0) > 0.9

    def test_provenance_uses_computed_field_confidence(self) -> None:
        bundle = SubmissionLoader().load_bundle(
            acord_xml=PACIFIC_ACORD,
            json_payload=PACIFIC_BROKER_JSON,
            bundle_id="prov-conf",
        )
        prov = ProvenanceEngine(deduplicate=False).build_provenance(bundle)
        node = prov.nodes["risk_profile.protection_class"][0]
        assert node.confidence > 0.9
        node = prov.nodes["coverage.0.limit"][0]
        assert node.confidence > 0.9


class TestReconciliationFidelity:
    def test_app_vs_surveyor_conflicts_detected(self) -> None:
        bundle = SubmissionLoader().load_bundle(
            acord_xml=PACIFIC_ACORD,
            json_payload=PACIFIC_BROKER_JSON,
            loss_run=PACIFIC_LOSS_RUN,
            schedule_of_values=PACIFIC_SOV,
            inspection_reports=[PACIFIC_INSPECTION],
            bundle_id="recon-1",
        )
        prov = ProvenanceEngine().build_provenance(bundle)
        result = ReconciliationEngine().reconcile(prov)
        paths = {d.field_path for d in result.discrepancies}
        assert "risk_profile.protection_class" in paths
        assert "risk_profile.construction_type" in paths
        assert "location.0.square_footage" in paths

    def test_reconciliation_not_noisy_on_sov(self) -> None:
        # SOV totals are values, not coverage limits — they must not produce
        # critical coverage.limit conflicts.
        bundle = SubmissionLoader().load_bundle(
            acord_xml=PACIFIC_ACORD,
            json_payload=PACIFIC_BROKER_JSON,
            loss_run=PACIFIC_LOSS_RUN,
            schedule_of_values=PACIFIC_SOV,
            inspection_reports=[PACIFIC_INSPECTION],
            bundle_id="recon-2",
        )
        prov = ProvenanceEngine().build_provenance(bundle)
        result = ReconciliationEngine().reconcile(prov)
        critical = [d for d in result.discrepancies if d.severity.value == "critical"]
        assert critical == []
        # The five real app-vs-surveyor conflicts carry warning severity.
        warnings = [d for d in result.discrepancies if d.severity.value == "warning"]
        assert len(warnings) >= 4
