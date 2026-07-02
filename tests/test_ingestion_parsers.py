from __future__ import annotations

import json

from insureflow.ingestion.acord_parser import ACORDParser
from insureflow.ingestion.classifier import DocumentClassifier
from insureflow.ingestion.json_parser import JSONBrokerParser
from insureflow.ingestion.loader import SubmissionLoader
from insureflow.ingestion.loss_run_parser import LossRunParser
from insureflow.ingestion.sov_parser import SOVParser
from insureflow.models.submissions import DocumentType

SAMPLE_JSON = json.dumps(
    {
        "insured": {
            "legalName": "Pacific Coast Distributors, Inc.",
            "doingBusinessAs": "PCD Logistics",
            "taxId": "94-3328410",
            "entityType": "Corporation",
            "financials": {"annualRevenue": 94700000, "payroll": 18400000, "totalAssets": 82500000},
        },
        "broker": {
            "brokerName": "Golden Gate Insurance Brokers",
            "contactName": "Sarah Chen",
        },
        "policy": {
            "effectiveDate": "2026-09-01",
            "expirationDate": "2027-09-01",
        },
        "coverages": [
            {
                "coverageType": "General Liability",
                "limitAmount": 2000000,
                "deductible": 0,
                "annualPremium": 168500,
                "sublimits": {"Products Aggregate": 4000000, "Fire Damage": 300000},
            },
        ],
        "locations": [
            {
                "address": "2450 Maritime Blvd",
                "city": "Oakland",
                "state": "CA",
                "zipCode": "94607",
                "occupancy": "Warehouse",
                "yearBuilt": 2005,
                "squareFootage": 210000,
            }
        ],
        "financial": {"annualRevenue": 94700000, "payroll": 18400000, "totalAssets": 82500000},
        "risk": {
            "naicsCode": 493120,
            "sicCode": 4222,
            "constructionType": "Masonry",
            "protectionClass": 3,
        },
    }
)


SAMPLE_LOSS_RUN = """# LOSS RUN / CLAIMS HISTORY

**Insured:** Pacific Coast Distributors, Inc.
**Total claims:** 3
**Total incurred:** $845,700

## CLAIM DETAIL

### Claim ZUR-2023-005211 — Property / Spoilage
**Date of loss:** 2023-10-12
**Line:** Property
**Cause:** Ammonia refrigerant leak caused product spoilage.
**Incurred:** $612,500  **Paid:** $612,500  **Status:** Closed

### Claim ZUR-2024-000978 — Workers Compensation
**Date of loss:** 2024-02-10
**Line:** Workers Compensation
**Cause:** Struck by forklift; fractured ankle.
**Incurred:** $215,800  **Paid:** $192,400  **Open reserve:** $23,400  **Status:** Open

### Claim ZUR-2025-001233 — General Liability (BI)
**Date of loss:** 2025-01-22
**Line:** General Liability
**Cause:** Dock leveler injury; litigation pending.
**Incurred:** $150,000  **Paid:** $0  **Open reserve:** $150,000  **Status:** Open
"""


SAMPLE_SOV = """# SCHEDULE OF VALUES (SOV)
## Pacific Coast Distributors, Inc.

This Schedule of Values details the building valuations and replacement cost breakdown for all insured locations.

### Building — Oakland HQ
Replacement cost: $18,500,000
Contents value: $12,500,000
Business Interruption: $8,500,000
Stock/Inventory: $8,500,000
Equipment: $15,000,000
Coinsurance: 90%

### Location 2 — Stockton
Building: $6,200,000
Contents: $3,800,000
Business Income: $2,200,000
Coinsurance: 80%
"""


class TestDocumentClassifier:
    def test_classify_acord_xml(self) -> None:
        result = DocumentClassifier.classify('<?xml version="1.0"?><ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD"><Submission/></ACORD>')
        assert result == DocumentType.ACORD_XML

    def test_classify_json_broker(self) -> None:
        result = DocumentClassifier.classify(SAMPLE_JSON)
        assert result == DocumentType.BROKER_API_JSON

    def test_classify_loss_run(self) -> None:
        result = DocumentClassifier.classify(SAMPLE_LOSS_RUN)
        assert result == DocumentType.LOSS_RUN

    def test_classify_inspection_report(self) -> None:
        text = "# COMMERCIAL PROPERTY INSPECTION REPORT\n## Building Construction\nThe building is steel frame."
        result = DocumentClassifier.classify(text)
        assert result == DocumentType.INSPECTION_REPORT

    def test_classify_sov(self) -> None:
        result = DocumentClassifier.classify(SAMPLE_SOV)
        assert result == DocumentType.SCHEDULE_OF_VALUES

    def test_classify_supplemental_fallback(self) -> None:
        result = DocumentClassifier.classify("Just a random note about something.")
        assert result == DocumentType.SUPPLEMENTAL

    def test_classify_empty(self) -> None:
        result = DocumentClassifier.classify("")
        assert result == DocumentType.SUPPLEMENTAL


class TestJSONBrokerParser:
    def test_parse_named_insured(self) -> None:
        parser = JSONBrokerParser()
        sub = parser.parse(SAMPLE_JSON, "json-001")
        assert sub.named_insured is not None
        assert sub.named_insured.legal_name == "Pacific Coast Distributors, Inc."
        assert sub.named_insured.dba == "PCD Logistics"
        assert sub.named_insured.tax_id == "94-3328410"

    def test_parse_broker(self) -> None:
        parser = JSONBrokerParser()
        sub = parser.parse(SAMPLE_JSON, "json-001")
        assert sub.broker is not None
        assert sub.broker.broker_name == "Golden Gate Insurance Brokers"
        assert sub.broker.contact_name == "Sarah Chen"

    def test_parse_policy_period(self) -> None:
        parser = JSONBrokerParser()
        sub = parser.parse(SAMPLE_JSON, "json-001")
        assert sub.policy_period is not None
        assert sub.policy_period.effective_date.year == 2026
        assert sub.policy_period.expiration_date.year == 2027

    def test_parse_coverages_with_sublimits(self) -> None:
        parser = JSONBrokerParser()
        sub = parser.parse(SAMPLE_JSON, "json-001")
        assert len(sub.coverages) == 1
        assert sub.coverages[0].coverage_type == "General Liability"
        assert sub.coverages[0].limit_amount == 2_000_000
        assert "Products Aggregate" in sub.coverages[0].sublimits
        assert sub.coverages[0].sublimits["Products Aggregate"] == 4_000_000

    def test_parse_locations(self) -> None:
        parser = JSONBrokerParser()
        sub = parser.parse(SAMPLE_JSON, "json-001")
        assert len(sub.locations) == 1
        assert sub.locations[0].city == "Oakland"
        assert sub.locations[0].square_footage == 210_000

    def test_parse_financial(self) -> None:
        parser = JSONBrokerParser()
        sub = parser.parse(SAMPLE_JSON, "json-001")
        assert sub.financial is not None
        assert sub.financial.annual_revenue == 94_700_000
        assert sub.financial.payroll == 18_400_000

    def test_parse_risk_profile(self) -> None:
        parser = JSONBrokerParser()
        sub = parser.parse(SAMPLE_JSON, "json-001")
        assert sub.risk_profile is not None
        assert sub.risk_profile.naics_code == "493120"
        assert sub.risk_profile.protection_class == 3


class TestLossRunParser:
    def test_parse_claims_count(self) -> None:
        parser = LossRunParser()
        result = parser.parse(SAMPLE_LOSS_RUN, "lr-001")
        assert "total_claims" in result.extracted_fields
        assert result.extracted_fields["total_claims"][0].value == "3"

    def test_parse_structured_claims(self) -> None:
        parser = LossRunParser()
        data = parser.parse_structured(SAMPLE_LOSS_RUN)
        assert data.total_claims == 3
        assert abs(data.total_incurred - 978300) < 1

    def test_parse_claim_details(self) -> None:
        parser = LossRunParser()
        data = parser.parse_structured(SAMPLE_LOSS_RUN)
        claims = {c.claim_id: c for c in data.claims}
        assert "ZUR-2023-005211" in claims
        c = claims["ZUR-2023-005211"]
        assert abs(c.incurred_amount - 612500) < 1
        assert c.line_of_business == "Property"
        assert c.claim_status.value == "closed"

    def test_parse_open_claim_with_reserve(self) -> None:
        parser = LossRunParser()
        data = parser.parse_structured(SAMPLE_LOSS_RUN)
        claims = {c.claim_id: c for c in data.claims}
        assert "ZUR-2024-000978" in claims
        c = claims["ZUR-2024-000978"]
        assert c.claim_status.value == "open"
        assert abs(c.open_reserve - 23400) < 1

    def test_parse_litigation_claim(self) -> None:
        parser = LossRunParser()
        data = parser.parse_structured(SAMPLE_LOSS_RUN)
        claims = {c.claim_id: c for c in data.claims}
        assert "ZUR-2025-001233" in claims
        c = claims["ZUR-2025-001233"]
        assert c.claim_status.value == "open"
        assert c.paid_amount == 0
        assert "litigation" in c.cause.lower()

    def test_empty_loss_run(self) -> None:
        parser = LossRunParser()
        data = parser.parse_structured("Nothing here")
        assert data.total_claims == 0
        assert data.claims == []


class TestSOVParser:
    def test_parse_structured(self) -> None:
        parser = SOVParser()
        sows = parser.parse_structured(SAMPLE_SOV)
        assert len(sows) >= 1

    def test_parse_values(self) -> None:
        parser = SOVParser()
        sows = parser.parse_structured(SAMPLE_SOV)
        assert len(sows) >= 1
        all_values = [i.value for sov in sows for i in sov.items]
        large_values = [v for v in all_values if v >= 1_000_000]
        assert len(large_values) >= 3

    def test_parse_sov_with_location(self) -> None:
        parser = SOVParser()
        sows = parser.parse_structured(SAMPLE_SOV)
        assert len(sows) > 0
        total = sum(s.total_value for s in sows)
        assert total > 0


class TestEnhancedACORDParser:
    def test_parse_sublimits_from_acord(self) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>120000</Premium>
      <CoverageSubLimit>
        <SubLimitType>Building</SubLimitType>
        <SubLimitAmount>3500000</SubLimitAmount>
      </CoverageSubLimit>
      <CoverageSubLimit>
        <SubLimitType>Contents</SubLimitType>
        <SubLimitAmount>1500000</SubLimitAmount>
      </CoverageSubLimit>
    </Coverage>
    <Risk>
      <NAICSCode>332710</NAICSCode>
      <Sprinklered>Yes</Sprinklered>
    </Risk>
  </Submission>
</ACORD>"""
        parser = ACORDParser()
        sub = parser.parse(xml, "test-sublimits")
        assert len(sub.coverages) == 1
        assert len(sub.coverages[0].sublimits) == 2
        assert sub.coverages[0].sublimits["Building"] == 3_500_000
        assert sub.coverages[0].sublimits["Contents"] == 1_500_000

    def test_parse_sprinklered(self) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <Risk>
      <NAICSCode>332710</NAICSCode>
      <Sprinklered>Yes</Sprinklered>
    </Risk>
  </Submission>
</ACORD>"""
        parser = ACORDParser()
        sub = parser.parse(xml, "test-sprinkler")
        assert sub.risk_profile is not None
        assert sub.risk_profile.sprinklered is True

    def test_parse_sprinklered_no(self) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <Risk>
      <NAICSCode>332710</NAICSCode>
      <Sprinklered>No</Sprinklered>
    </Risk>
  </Submission>
</ACORD>"""
        parser = ACORDParser()
        sub = parser.parse(xml, "test-sprinkler-no")
        assert sub.risk_profile is not None
        assert sub.risk_profile.sprinklered is False

    def test_parse_location_building_value(self) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <Location>
      <Addr1>123 Main St</Addr1>
      <City>Oakland</City>
      <StateProvCd>CA</StateProvCd>
      <PostalCode>94607</PostalCode>
      <EstimatedValue>5000000</EstimatedValue>
    </Location>
    <Risk>
      <NAICSCode>332710</NAICSCode>
    </Risk>
  </Submission>
</ACORD>"""
        parser = ACORDParser()
        sub = parser.parse(xml, "test-loc-val")
        assert len(sub.locations) == 1
        assert sub.locations[0].building_value == 5_000_000


class TestAutoClassification:
    def test_auto_classify_mixed_docs(self) -> None:
        loss_run = SAMPLE_LOSS_RUN
        sov = SAMPLE_SOV
        xml = '<?xml version="1.0"?><ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD"><Submission><NamedInsured><GeneralPartyInfo><NameInfo><CommercialName><Name>Test Corp</Name></CommercialName></NameInfo><Addr1>123 Main</Addr1><City>SF</City><StateProvCd>CA</StateProvCd><PostalCode>94105</PostalCode></GeneralPartyInfo></NamedInsured><Risk><NAICSCode>123456</NAICSCode></Risk></Submission></ACORD>'  # noqa: E501

        loader = SubmissionLoader()
        bundle = loader.load_bundle(
            raw_docs=[xml, loss_run, sov],
            auto_classify=True,
            bundle_id="test-auto-001",
        )

        assert bundle.structured is not None
        assert bundle.structured.named_insured is not None
        assert bundle.structured.named_insured.legal_name == "Test Corp"

        loss_run_subs = [u for u in bundle.unstructured if u.document_type == "loss_run"]
        sov_subs = [u for u in bundle.unstructured if u.document_type == "schedule_of_values"]
        assert len(loss_run_subs) >= 1
        assert len(sov_subs) >= 1

    def test_auto_classify_json_only(self) -> None:
        loader = SubmissionLoader()
        bundle = loader.load_bundle(
            raw_docs=[SAMPLE_JSON],
            auto_classify=True,
            bundle_id="test-json-only",
        )
        assert bundle.structured is not None
        assert bundle.structured.named_insured is not None
        assert bundle.structured.source == "broker_api_json"
        assert bundle.structured.named_insured.legal_name == "Pacific Coast Distributors, Inc."

    def test_auto_classify_no_structured(self) -> None:
        loader = SubmissionLoader()
        bundle = loader.load_bundle(
            raw_docs=["Just some random text notes"],
            auto_classify=True,
            bundle_id="test-notes",
        )
        assert bundle.structured is None
        assert len(bundle.supplemental) == 1


class TestLoaderNewInputTypes:
    def test_loader_json_payload(self) -> None:
        loader = SubmissionLoader()
        bundle = loader.load_bundle(
            json_payload=SAMPLE_JSON,
            bundle_id="test-json-loader",
        )
        assert bundle.structured is not None
        assert bundle.structured.named_insured is not None
        assert bundle.structured.source == "broker_api_json"
        assert bundle.structured.named_insured.legal_name == "Pacific Coast Distributors, Inc."

    def test_loader_loss_run(self) -> None:
        loader = SubmissionLoader()
        bundle = loader.load_bundle(
            loss_run=SAMPLE_LOSS_RUN,
            bundle_id="test-lr-loader",
        )
        loss_run_subs = [u for u in bundle.unstructured if u.document_type == "loss_run"]
        assert len(loss_run_subs) == 1

    def test_loader_sov(self) -> None:
        loader = SubmissionLoader()
        bundle = loader.load_bundle(
            schedule_of_values=SAMPLE_SOV,
            bundle_id="test-sov-loader",
        )
        sov_subs = [u for u in bundle.unstructured if u.document_type == "schedule_of_values"]
        assert len(sov_subs) == 1
