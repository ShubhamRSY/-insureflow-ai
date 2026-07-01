from __future__ import annotations

from insureflow.ingestion.loader import SubmissionLoader
from insureflow.pipeline import UnderwritingPipeline


def test_loader_creates_bundle(
    sample_acord_xml: str, sample_inspection_report: str
) -> None:
    loader = SubmissionLoader()
    bundle = loader.load_bundle(
        acord_xml=sample_acord_xml,
        inspection_reports=[sample_inspection_report],
    )
    assert bundle.structured is not None
    assert len(bundle.unstructured) == 1
    assert bundle.structured.named_insured is not None
    assert bundle.structured.named_insured.legal_name == "Acme Manufacturing Corp"


def test_pipeline_run(sample_acord_xml: str, sample_inspection_report: str) -> None:
    pipeline = UnderwritingPipeline()
    results = pipeline.run(
        acord_xml=sample_acord_xml,
        inspection_reports=[sample_inspection_report],
    )

    assert results["status"] in ("completed", "flagged")
    assert "bundle_id" in results
    assert results["steps"]["ingestion"]["status"] == "complete"
    assert results["steps"]["extraction"]["status"] == "complete"

    recon = results.get("reconciliation", {})
    assert "match_rate" in recon
    assert "discrepancies" in recon

    audit = results.get("audit_summary", {})
    assert audit["total_audit_entries"] > 0


def test_pipeline_with_discrepancy() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo>
          <CommercialName>
            <Name>Acme Manufacturing Corp</Name>
          </CommercialName>
        </NameInfo>
      </GeneralPartyInfo>
    </NamedInsured>
    <Risk>
      <NAICSCode>332710</NAICSCode>
      <ConstructionType>Frame</ConstructionType>
      <Occupancy>Warehouse</Occupancy>
      <ProtectionClass>3</ProtectionClass>
      <NumberOfStories>1</NumberOfStories>
      <TotalSquareFootage>50000</TotalSquareFootage>
    </Risk>
  </Submission>
</ACORD>"""

    report = """# INSPECTION REPORT
### BUILDING CONSTRUCTION
Construction type: Masonry
Year built: 2000
Number of stories: 3
Total square footage: 75000

### FIRE PROTECTION
Protection class: 5.
"""

    pipeline = UnderwritingPipeline()
    results = pipeline.run(acord_xml=xml, inspection_reports=[report])

    recon = results.get("reconciliation", {})
    discrepancies = recon.get("discrepancies", [])
    assert len(discrepancies) > 0


def test_pipeline_no_input() -> None:
    pipeline = UnderwritingPipeline()
    results = pipeline.run()
    assert results["status"] == "completed"
