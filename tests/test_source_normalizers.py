"""Tests for source normalization across 24 enterprise systems."""

from __future__ import annotations

import json

import pytest

from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader
from insureflow.ingestion.insurance.normalizers import (
    ACORDAL3Normalizer,
    AppliedEpicNormalizer,
    AzureBlobNormalizer,
    BoldPenguinNormalizer,
    BoxNormalizer,
    CoreLogicNormalizer,
    DocuSignNormalizer,
    DuckCreekNormalizer,
    EmailInboxNormalizer,
    GoogleDriveNormalizer,
    GuidewireNormalizer,
    HawkSoftNormalizer,
    ImageRightNormalizer,
    IVANSDownloadNormalizer,
    MajescoNormalizer,
    MicrosoftTeamsNormalizer,
    S3BucketNormalizer,
    SalesforceNormalizer,
    SFTPNormalizer,
    SharePointNormalizer,
    SlackIntakeNormalizer,
    SnowflakeNormalizer,
    VeriskISONormalizer,
    get_normalizer,
    normalize_source,
    supported_sources,
)

SAMPLE_PAYLOAD = {
    "insured_name": "Pacific Coast Distributors, Inc.",
    "tax_id": "94-3328410",
    "broker_name": "Golden Gate Insurance Brokers",
    "effective_date": "2026-09-01",
    "expiration_date": "2027-09-01",
    "locations": [
        {
            "address": "2450 Maritime Blvd",
            "city": "Oakland",
            "state": "CA",
            "zip": "94607",
            "year_built": 2005,
            "square_footage": 210000,
        }
    ],
    "coverages": [
        {
            "type": "General Liability",
            "limit": 2000000,
            "deductible": 0,
            "premium": 168500,
        }
    ],
    "financial": {"annual_revenue": 94700000, "payroll": 18400000},
    "risk": {
        "naics_code": "493120",
        "construction_type": "Masonry",
        "protection_class": 3,
    },
}


# ── Registry Tests ───────────────────────────────────────────────


class TestSourceRegistry:
    def test_all_sources_registered(self) -> None:
        sources = supported_sources()
        assert len(sources) >= 23
        expected = [
            "google-drive",
            "sharepoint",
            "s3-bucket",
            "azure-blob",
            "box",
            "email-inbox",
            "sftp",
            "bold-penguin",
            "ivans-download",
            "acord-al3",
            "guidewire-policycenter",
            "duck-creek",
            "majesco-policy",
            "applied-epic",
            "hawksoft",
            "salesforce-crm",
            "verisk-iso",
            "corelogic",
            "imageright",
            "docusign",
            "microsoft-teams",
            "slack-intake",
            "snowflake",
        ]
        for src in expected:
            assert src in sources

    def test_get_normalizer_returns_instance(self) -> None:
        norm = get_normalizer("google-drive")
        assert norm is not None
        assert norm.source_id == "google-drive"

    def test_get_normalizer_unknown_returns_none(self) -> None:
        assert get_normalizer("nonexistent-system") is None

    def test_normalize_source_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="No normalizer"):
            normalize_source("nonexistent-system", {})


# ── Cloud Storage (5) ────────────────────────────────────────────


class TestGoogleDriveNormalizer:
    def test_normalize_basic(self) -> None:
        norm = GoogleDriveNormalizer()
        raw = {
            "metadata": {
                "insured_name": "Acme Corp",
                "effective_date": "2026-01-15",
                "expiration_date": "2027-01-15",
            },
            "locations": [{"address": "100 Main St", "city": "SF", "state": "CA", "zip": "94105"}],
            "coverages": [{"type": "Property", "limit": 5000000, "deductible": 25000, "premium": 45000}],
        }
        sub = norm.normalize(raw, "gd-001")
        assert sub.source == "google-drive"
        assert sub.named_insured is not None
        assert sub.named_insured.legal_name == "Acme Corp"
        assert sub.policy_period is not None
        assert sub.policy_period.effective_date.year == 2026
        assert len(sub.locations) == 1
        assert len(sub.coverages) == 1
        assert sub.coverages[0].limit_amount == 5_000_000

    def test_financial_and_risk(self) -> None:
        norm = GoogleDriveNormalizer()
        raw = {
            "metadata": {"insured_name": "Test"},
            "financial": {"annual_revenue": 1000000, "payroll": 500000},
            "risk": {"naics_code": "123456", "construction_type": "Steel"},
        }
        sub = norm.normalize(raw)
        assert sub.financial is not None
        assert sub.financial.annual_revenue == 1_000_000
        assert sub.risk_profile is not None
        assert sub.risk_profile.naics_code == "123456"


class TestSharePointNormalizer:
    def test_inherits_from_gdrive(self) -> None:
        norm = SharePointNormalizer()
        assert norm.source_id == "sharepoint"
        sub = norm.normalize({"metadata": {"insured_name": "SP Corp"}})
        assert sub.source == "sharepoint"


class TestS3BucketNormalizer:
    def test_inherits_from_gdrive(self) -> None:
        norm = S3BucketNormalizer()
        assert norm.source_id == "s3-bucket"
        sub = norm.normalize({"metadata": {"insured_name": "S3 Corp"}})
        assert sub.source == "s3-bucket"


class TestAzureBlobNormalizer:
    def test_inherits_from_gdrive(self) -> None:
        norm = AzureBlobNormalizer()
        assert norm.source_id == "azure-blob"
        sub = norm.normalize({"metadata": {"insured_name": "Azure Corp"}})
        assert sub.source == "azure-blob"


class TestBoxNormalizer:
    def test_inherits_from_gdrive(self) -> None:
        norm = BoxNormalizer()
        assert norm.source_id == "box"
        sub = norm.normalize({"metadata": {"insured_name": "Box Corp"}})
        assert sub.source == "box"


# ── Submission Intake (4) ────────────────────────────────────────


class TestEmailInboxNormalizer:
    def test_normalize_email(self) -> None:
        norm = EmailInboxNormalizer()
        raw = {
            "email": {
                "insured_name": "Email Corp",
                "from_name": "Broker Bob",
                "effective_date": "2026-06-01",
                "expiration_date": "2027-06-01",
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "email-inbox"
        assert sub.named_insured.legal_name == "Email Corp"
        assert sub.broker is not None
        assert sub.broker.broker_name == "Broker Bob"


class TestSFTPNormalizer:
    def test_normalize_sftp_json(self) -> None:
        norm = SFTPNormalizer()
        nested_json = json.dumps(
            {
                "insured": {
                    "legalName": "Pacific Coast Distributors, Inc.",
                    "taxId": "94-3328410",
                },
                "broker": {"brokerName": "Golden Gate Insurance Brokers"},
                "policy": {"effectiveDate": "2026-09-01", "expirationDate": "2027-09-01"},
                "coverages": [{"coverageType": "GL", "limitAmount": 1000000, "deductible": 0, "annualPremium": 25000}],
            }
        )
        raw = {"file": {"format": "json", "content": nested_json}}
        sub = norm.normalize(raw)
        assert sub.source == "sftp"
        assert sub.named_insured is not None
        assert sub.named_insured.legal_name == "Pacific Coast Distributors, Inc."

    def test_normalize_sftp_plain(self) -> None:
        norm = SFTPNormalizer()
        raw = {"file": {"format": "csv", "content": "name,amount\nAcme,1000", "insured_name": "Plain Corp"}}
        sub = norm.normalize(raw)
        assert sub.source == "sftp"
        assert sub.named_insured.legal_name == "Plain Corp"


class TestBoldPenguinNormalizer:
    def test_normalize_bold_penguin(self) -> None:
        norm = BoldPenguinNormalizer()
        raw = {
            "application": {
                "business_name": "BP Logistics",
                "ein": "12-3456789",
                "effective_date": "2026-03-01",
                "expiration_date": "2027-03-01",
                "locations": [{"city": "Denver", "state": "CO"}],
                "coverages": [{"type": "GL", "limit": 1000000}],
                "financial": {"annual_revenue": 5000000},
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "bold-penguin"
        assert sub.named_insured.legal_name == "BP Logistics"
        assert len(sub.locations) == 1
        assert len(sub.coverages) == 1


class TestIVANSDownloadNormalizer:
    def test_normalize_ivans_al3(self) -> None:
        norm = IVANSDownloadNormalizer()
        al3 = "01ABC Insurance                              \n052026090120270901                           \nNAMPacific Coast Dist                       \n"
        raw = {"transaction": {"format": "al3", "content": al3}}
        sub = norm.normalize(raw)
        assert sub.source == "ivans-download"

    def test_normalize_ivans_xml(self) -> None:
        norm = IVANSDownloadNormalizer()
        xml = (
            '<?xml version="1.0"?><ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">'
            "<Submission><NamedInsured><GeneralPartyInfo><NameInfo><CommercialName>"
            "<Name>IVANS Corp</Name></CommercialName></NameInfo></GeneralPartyInfo>"
            "</NamedInsured><Risk><NAICSCode>999999</NAICSCode></Risk></Submission></ACORD>"
        )
        raw = {"transaction": {"format": "acord_xml", "content": xml}}
        sub = norm.normalize(raw)
        assert sub.named_insured is not None


# ── Industry Exchange ────────────────────────────────────────────


class TestACORDAL3Normalizer:
    def test_normalize_acord_xml(self) -> None:
        norm = ACORDAL3Normalizer()
        xml = (
            '<?xml version="1.0"?><ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">'
            "<Submission><NamedInsured><GeneralPartyInfo><NameInfo><CommercialName>"
            "<Name>AL3 Corp</Name></CommercialName></NameInfo></GeneralPartyInfo>"
            "</NamedInsured><Risk><NAICSCode>111111</NAICSCode></Risk></Submission></ACORD>"
        )
        raw = {"content": xml}
        sub = norm.normalize(raw)
        assert sub.named_insured is not None
        assert sub.source == "acord-al3"


# ── Policy Admin (3) ─────────────────────────────────────────────


class TestGuidewireNormalizer:
    def test_normalize_guidewire(self) -> None:
        norm = GuidewireNormalizer()
        raw = {
            "policy": {
                "insured": {"displayName": "GW Corp", "taxId": "12-3456789"},
                "producer": {"displayName": "GW Broker"},
                "policyPeriod": {"startDate": "2026-01-01", "expirationDate": "2027-01-01"},
                "coverages": [{"coverageType": "Property", "limitAmount": 3000000, "deductibleAmount": 10000, "premium": 25000}],
                "locations": [{"address": {"addressLine1": "500 Tech Way", "city": "San Jose", "state": "CA", "postalCode": "95112"}, "yearBuilt": 2010}],
                "financial": {"annualRevenue": 50000000, "payroll": 10000000},
                "risk": {"naicsCode": "541512", "constructionType": "Steel Frame", "sprinklered": True},
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "guidewire-policycenter"
        assert sub.named_insured.legal_name == "GW Corp"
        assert sub.broker.broker_name == "GW Broker"
        assert len(sub.coverages) == 1
        assert sub.coverages[0].limit_amount == 3_000_000
        assert sub.risk_profile.sprinklered is True


class TestDuckCreekNormalizer:
    def test_inherits_from_guidewire(self) -> None:
        norm = DuckCreekNormalizer()
        assert norm.source_id == "duck-creek"
        raw = {"policy": {"insured": {"displayName": "DC Corp"}, "coverages": []}}
        sub = norm.normalize(raw)
        assert sub.source == "duck-creek"


class TestMajescoNormalizer:
    def test_inherits_from_guidewire(self) -> None:
        norm = MajescoNormalizer()
        assert norm.source_id == "majesco-policy"


# ── Agency Management (2) ───────────────────────────────────────


class TestAppliedEpicNormalizer:
    def test_normalize_applied_epic(self) -> None:
        norm = AppliedEpicNormalizer()
        raw = {
            "submission": {
                "client": {"companyName": "Epic Logistics", "ein": "98-7654321"},
                "agent": {"agentName": "Epic Agent", "email": "agent@epic.com"},
                "policy": {"effectiveDate": "2026-04-01", "expirationDate": "2027-04-01"},
                "locations": [{"address": "1000 Oak St", "city": "Portland", "state": "OR", "zip": "97201"}],
                "coverages": [{"type": "CGL", "limit": 1000000, "deductible": 0, "premium": 12000}],
                "financial": {"annualRevenue": 8000000, "payroll": 2000000},
                "risk": {"naicsCode": "484120", "construction_type": "Frame"},
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "applied-epic"
        assert sub.named_insured.legal_name == "Epic Logistics"
        assert sub.broker.broker_name == "Epic Agent"
        assert sub.financial.annual_revenue == 8_000_000


class TestHawkSoftNormalizer:
    def test_inherits_from_applied_epic(self) -> None:
        norm = HawkSoftNormalizer()
        assert norm.source_id == "hawksoft"


# ── CRM (1) ──────────────────────────────────────────────────────


class TestSalesforceNormalizer:
    def test_normalize_salesforce(self) -> None:
        norm = SalesforceNormalizer()
        raw = {
            "opportunity": {
                "account": {"Name": "SF Logistics Inc"},
                "broker": {"Name": "SF Broker"},
                "Effective_Date__c": "2026-05-01",
                "Expiration_Date__c": "2027-05-01",
                "locations": [{"City__c": "Austin", "State__c": "TX"}],
                "coverages": [{"Type__c": "Workers Comp", "Limit__c": 500000}],
                "financial": {"Annual_Revenue__c": 15000000},
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "salesforce-crm"
        assert sub.named_insured.legal_name == "SF Logistics Inc"
        assert len(sub.coverages) == 1


# ── Rating & Loss Data (2) ──────────────────────────────────────


class TestVeriskISONormalizer:
    def test_normalize_verisk(self) -> None:
        norm = VeriskISONormalizer()
        raw = {
            "rating_data": {
                "insured_name": "ISO Corp",
                "naics_code": "332710",
                "construction_type": "Masonry",
                "territory": {"city": "Chicago", "state": "IL", "zip_code": "60601"},
                "loss_costs": [{"line": "Property", "loss_cost": 8.50}],
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "verisk-iso"
        assert sub.risk_profile.naics_code == "332710"
        assert len(sub.coverages) == 1


class TestCoreLogicNormalizer:
    def test_normalize_corelogic(self) -> None:
        norm = CoreLogicNormalizer()
        raw = {
            "property": {
                "insured_name": "CL Corp",
                "address": "200 Lake Dr",
                "city": "Miami",
                "state": "FL",
                "year_built": 1998,
                "replacement_cost": 4500000,
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "corelogic"
        assert len(sub.locations) == 1
        assert sub.locations[0].building_value == 4_500_000


# ── Document Storage (1) ─────────────────────────────────────────


class TestImageRightNormalizer:
    def test_normalize_imageright(self) -> None:
        norm = ImageRightNormalizer()
        raw = {"document": {"metadata": {"insured_name": "IR Corp", "broker_name": "IR Broker"}}}
        sub = norm.normalize(raw)
        assert sub.source == "imageright"
        assert sub.named_insured.legal_name == "IR Corp"


# ── eSignature (1) ───────────────────────────────────────────────


class TestDocuSignNormalizer:
    def test_normalize_docusign(self) -> None:
        norm = DocuSignNormalizer()
        raw = {
            "envelope": {
                "signer": {"name": "DS Signer"},
                "insured_name": "DS Corp",
                "effective_date": "2026-07-01",
                "expiration_date": "2027-07-01",
                "documents": [],
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "docusign"
        assert sub.named_insured.legal_name == "DS Corp"


# ── Collaboration (2) ────────────────────────────────────────────


class TestMicrosoftTeamsNormalizer:
    def test_normalize_teams(self) -> None:
        norm = MicrosoftTeamsNormalizer()
        raw = {
            "message": {
                "from": {"name": "Teams User"},
                "insured_name": "Teams Corp",
                "attachments": [],
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "microsoft-teams"
        assert sub.named_insured.legal_name == "Teams Corp"


class TestSlackIntakeNormalizer:
    def test_normalize_slack(self) -> None:
        norm = SlackIntakeNormalizer()
        raw = {
            "event": {
                "user": {"name": "Slack User"},
                "insured_name": "Slack Corp",
                "files": [],
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "slack-intake"
        assert sub.named_insured.legal_name == "Slack Corp"


# ── Data Warehouse (1) ──────────────────────────────────────────


class TestSnowflakeNormalizer:
    def test_normalize_snowflake(self) -> None:
        norm = SnowflakeNormalizer()
        raw = {
            "row": {
                "legal_name": "SF Snow Corp",
                "tax_id": "11-2233445",
                "broker_name": "Snow Broker",
                "effective_date": "2026-08-01",
                "expiration_date": "2027-08-01",
                "annual_revenue": 25000000,
                "payroll": 8000000,
                "naics_code": "423310",
                "locations": [{"address": "1 Snow Way", "city": "Denver", "state": "CO", "zip_code": "80202"}],
                "coverages": [{"type": "Inland Marine", "limit": 1000000, "deductible": 5000, "premium": 8000}],
                "loss_run": [{"claim_id": "SN-001", "date_of_loss": "2025-01-15", "line": "Property", "cause": "Fire", "incurred": 100000, "paid": 90000, "reserve": 10000, "status": "open"}],
            }
        }
        sub = norm.normalize(raw)
        assert sub.source == "snowflake"
        assert sub.named_insured.legal_name == "SF Snow Corp"
        assert sub.financial.loss_run is not None
        assert sub.financial.loss_run.total_claims == 1
        assert sub.risk_profile.prior_claims[0].claim_id == "SN-001"


# ── Integration with Loader ──────────────────────────────────────


class TestLoaderFromSource:
    def test_load_from_source(self) -> None:
        loader = InsuranceDocumentLoader()
        bundle = loader.load_from_source(
            "google-drive",
            {"metadata": {"insured_name": "Loader Test Corp"}},
            bundle_id="loader-test-001",
        )
        assert bundle.bundle_id == "loader-test-001"
        assert bundle.structured is not None
        assert bundle.structured.source == "google-drive"
        assert bundle.structured.named_insured.legal_name == "Loader Test Corp"
        assert bundle.status.value == "parsed"

    def test_load_from_source_unknown_raises(self) -> None:
        loader = InsuranceDocumentLoader()
        with pytest.raises(ValueError, match="No normalizer"):
            loader.load_from_source("nonexistent", {})


# ── Utility Functions ────────────────────────────────────────────


class TestUtilityFunctions:
    def test_supported_sources_sorted(self) -> None:
        sources = supported_sources()
        assert sources == sorted(sources)

    def test_all_normalizers_have_source_id(self) -> None:
        sources = supported_sources()
        for src in sources:
            norm = get_normalizer(src)
            assert norm is not None
            assert norm.source_id == src
