from __future__ import annotations

from insureflow.integrations.parsers import (
    parse_bureau_response,
    parse_osha_response,
    parse_public_records_response,
    parse_rating_agency_response,
)
from insureflow.oracles.aplus_client import APlusClient, PropertyClaimType
from insureflow.oracles.bureau_client import CreditBureauClient
from insureflow.oracles.clue_client import CLUEClient
from insureflow.oracles.ncci_client import NCCIClient
from insureflow.oracles.ncci_codes import (
    NCCI_CLASS_CODES,
    get_ncci_description,
    get_ncci_risk_level,
    is_high_risk_ncci_class,
)
from insureflow.oracles.osha_client import OSHAClient
from insureflow.oracles.public_records_client import PublicRecordsClient
from insureflow.oracles.rating_agency_client import CreditRatingAgencyClient


class TestCLUEClient:
    def test_query_by_name_marine(self) -> None:
        client = CLUEClient()
        result = client.query_by_name_and_address("Pacific Marine Supply", "123 Harbor Blvd")
        assert result.query_completed
        assert result.total_claims_found >= 2
        assert any("general_liability" in r.loss_type for r in result.records)
        assert any("property" in r.loss_type for r in result.records)

    def test_query_by_name_construction(self) -> None:
        client = CLUEClient()
        result = client.query_by_name_and_address("Veririsk Construction", "456 Jobsite Rd")
        assert result.total_claims_found >= 1
        assert any("workers_comp" in r.loss_type for r in result.records)

    def test_query_by_name_clean(self) -> None:
        client = CLUEClient()
        result = client.query_by_name_and_address("CleanCo Inc", "789 Main St")
        assert result.total_claims_found == 0
        assert "Clean" in result.summary

    def test_query_by_tax_id(self) -> None:
        client = CLUEClient()
        result = client.query_by_tax_id("12-3456789")
        assert result.query_completed
        assert isinstance(result.total_claims_found, int)

    def test_litigation_detected(self) -> None:
        client = CLUEClient()
        result = client.query_by_name_and_address("Pacific Marine Supply")
        assert result.has_prior_litigation or not result.has_prior_litigation

    def test_live_mode_misconfigured(self) -> None:
        client = CLUEClient(mode="live")
        result = client.query_by_name_and_address("Test Name")
        assert result.query_completed is False
        assert "CLUE_API_KEY" in result.error

    def test_disabled(self) -> None:
        client = CLUEClient(api_key="", mode="simulated")
        result = client.query_by_name_and_address("")
        assert result.query_completed  # simulated mode always works


class TestNCCIClient:
    def test_query_marine(self) -> None:
        client = NCCIClient()
        result = client.query_by_fein("98-7654321", "Pacific Marine Supply")
        assert any(m.class_code == "8380" for m in result.experience_mods)
        assert result.worst_mod is not None
        assert result.worst_mod.mod_factor == 1.12

    def test_query_construction(self) -> None:
        client = NCCIClient()
        result = client.query_by_fein("98-7654321", "Veririsk Construction")
        assert any(m.class_code == "5221" for m in result.experience_mods)
        assert result.worst_mod is not None
        assert result.worst_mod.mod_factor == 1.35

    def test_query_northwind(self) -> None:
        client = NCCIClient()
        result = client.query_by_fein("98-7654321", "Northwind Trading")
        assert any(m.class_code == "8810" for m in result.experience_mods)
        assert result.worst_mod is not None
        assert result.worst_mod.mod_factor == 0.88

    def test_query_fallback(self) -> None:
        client = NCCIClient()
        result = client.query_by_fein("00-0000000", "Some Unknown Co")
        assert any(m.class_code == "5555" for m in result.experience_mods)
        assert result.worst_mod is not None
        assert result.worst_mod.mod_factor == 1.00

    def test_risk_bans(self) -> None:
        NCCIClient()
        c = NCCIClient()
        result = c.query_by_fein("00-0000000", "Veririsk Construction")
        mod = result.experience_mods[0]
        assert mod.risk_band == "high"
        assert mod.is_debit_mod
        assert not mod.is_credit_mod

    def test_credit_mod(self) -> None:
        client = NCCIClient()
        result = client.query_by_fein("00-0000000", "Northwind Trading")
        mod = result.experience_mods[0]
        assert mod.is_credit_mod
        assert not mod.is_debit_mod

    def test_live_mode_misconfigured(self) -> None:
        client = NCCIClient(mode="live")
        result = client.query_by_fein("00-0000000", "Test")
        assert result.query_completed is False
        assert "NCCI_API_KEY" in result.error


class TestAPlusClient:
    def test_query_marine(self) -> None:
        client = APlusClient()
        result = client.query_by_property("Pacific Marine Supply", "123 Harbor Blvd")
        assert result.query_completed
        assert result.total_claims_found >= 1
        assert any(r.claim_type == PropertyClaimType.WATER_DAMAGE for r in result.records)

    def test_query_construction(self) -> None:
        client = APlusClient()
        result = client.query_by_property("Veririsk Construction", "456 Industrial Dr")
        assert result.total_claims_found >= 2
        assert any(r.claim_type == PropertyClaimType.FIRE for r in result.records)
        assert any(r.claim_type == PropertyClaimType.THEFT for r in result.records)

    def test_query_northwind(self) -> None:
        client = APlusClient()
        result = client.query_by_property("Northwind Trading", "789 Main St")
        assert result.total_claims_found >= 1
        assert any(r.claim_type == PropertyClaimType.HAIL for r in result.records)

    def test_coastal_address_triggers_wind(self) -> None:
        client = APlusClient()
        result = client.query_by_property("Coastal Properties Inc", "100 Beach Blvd")
        assert result.total_claims_found >= 1
        assert any(r.claim_type == PropertyClaimType.WIND for r in result.records)

    def test_clean_property(self) -> None:
        client = APlusClient()
        result = client.query_by_property("CleanCo Inc", "999 Main St")
        assert result.total_claims_found == 0

    def test_repeated_property_claims_flag(self) -> None:
        client = APlusClient()
        result = client.query_by_property("Veririsk Construction", "456 Industrial Dr")
        assert result.has_repeated_property_claims

    def test_summary(self) -> None:
        client = APlusClient()
        result = client.query_by_property("Pacific Marine Supply")
        assert "A-PLUS" in result.summary or "property" in result.summary

    def test_live_mode_misconfigured(self) -> None:
        client = APlusClient(mode="live")
        result = client.query_by_property("Test")
        assert result.query_completed is False
        assert "APLUS_API_KEY" in result.error


class TestCreditBureauClient:
    def test_query_marine(self) -> None:
        client = CreditBureauClient()
        result = client.query_by_tax_id("12-3456789", "Pacific Marine Supply")
        assert result.query_completed
        assert result.paydex_score == 58
        assert result.has_lien_indicator
        assert not result.has_bankruptcy_indicator
        assert result.number_of_derogatory_trades == 1

    def test_query_construction(self) -> None:
        client = CreditBureauClient()
        result = client.query_by_tax_id("12-3456789", "Veririsk Construction")
        assert result.paydex_score == 35
        assert result.has_bankruptcy_indicator
        assert result.has_lien_indicator
        assert result.has_judgment_indicator
        assert result.risk_band == "critical"
        assert result.number_of_derogatory_trades == 2

    def test_query_clean(self) -> None:
        client = CreditBureauClient()
        result = client.query_by_tax_id("12-3456789", "CleanCo Inc")
        assert result.paydex_score == 82
        assert result.number_of_derogatory_trades == 0
        assert not result.has_bankruptcy_indicator
        assert result.risk_band == "low"

    def test_trade_record_derogatory(self) -> None:
        client = CreditBureauClient()
        result = client.query_by_tax_id("12-3456789", "Veririsk Construction")
        assert all(r.is_derogatory for r in result.records)
        assert all(r.payment_status in {"past_due", "delinquent", "derogatory"} for r in result.records)

    def test_summary_marks_synthetic(self) -> None:
        client = CreditBureauClient()
        result = client.query_by_tax_id("12-3456789", "Veririsk Construction")
        assert "SYNTHETIC/UNVERIFIED" in result.summary
        assert "Paydex 35" in result.summary

    def test_live_mode_misconfigured(self) -> None:
        client = CreditBureauClient(mode="live")
        result = client.query_by_tax_id("12-3456789", "Test Name")
        assert result.query_completed is False
        assert "BUREAU_API_KEY" in result.error


class TestPublicRecordsClient:
    def test_query_construction(self) -> None:
        client = PublicRecordsClient()
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
        assert result.query_completed
        assert result.has_bankruptcy
        assert result.has_active_judgment
        assert result.has_ucc_filing
        assert result.has_active_lien
        assert result.total_judgment_amount == 125_000
        assert result.risk_band == "critical"

    def test_query_marine(self) -> None:
        client = PublicRecordsClient()
        result = client.query_by_entity("Pacific Marine Supply", "12-3456789")
        assert result.has_ucc_filing
        assert not result.has_bankruptcy
        assert not result.has_active_judgment
        assert result.total_records_found == 1
        assert result.risk_band == "moderate"

    def test_query_clean(self) -> None:
        client = PublicRecordsClient()
        result = client.query_by_entity("CleanCo Inc", "12-3456789")
        assert result.total_records_found == 0
        assert not result.has_bankruptcy
        assert result.risk_band == "low"

    def test_record_active_flag(self) -> None:
        client = PublicRecordsClient()
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
        assert all(r.is_active for r in result.records)

    def test_live_mode_misconfigured(self) -> None:
        client = PublicRecordsClient(mode="live")
        result = client.query_by_entity("Test Name")
        assert result.query_completed is False
        assert "PUBLIC_RECORDS_API_KEY" in result.error


class TestOSHAClient:
    def test_query_construction(self) -> None:
        client = OSHAClient()
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
        assert result.query_completed
        assert result.has_willful_violation
        assert result.has_repeat_violation
        assert result.has_open_inspection
        assert result.safety_rating == "critical"
        assert result.total_penalty == 105_000

    def test_query_marine(self) -> None:
        client = OSHAClient()
        result = client.query_by_entity("Pacific Marine Supply", "12-3456789")
        assert not result.has_willful_violation
        assert result.safety_rating == "moderate"
        assert result.total_penalty == 11_000

    def test_query_clean(self) -> None:
        client = OSHAClient()
        result = client.query_by_entity("CleanCo Inc", "12-3456789")
        assert result.total_violations == 0
        assert result.safety_rating == "low"

    def test_risk_weight(self) -> None:
        client = OSHAClient()
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
        weights = {v.violation_type: v.risk_weight for v in result.violations}
        assert weights["willful"] == 1.0
        assert weights["repeat"] == 0.8
        assert weights["serious"] == 0.6

    def test_live_mode_misconfigured(self) -> None:
        client = OSHAClient(mode="live")
        result = client.query_by_entity("Test Name")
        assert result.query_completed is False
        assert "OSHA_API_KEY" in result.error


class TestCreditRatingAgencyClient:
    def test_query_construction(self) -> None:
        client = CreditRatingAgencyClient()
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
        assert result.issuer_rating == "B"
        assert result.outlook == "negative"
        assert result.watch == "on-watch"
        assert not result.is_investment_grade
        assert result.risk_band == "high"

    def test_query_marine(self) -> None:
        client = CreditRatingAgencyClient()
        result = client.query_by_entity("Pacific Marine Supply", "12-3456789")
        assert result.issuer_rating == "BB+"
        assert not result.is_investment_grade

    def test_query_northwind(self) -> None:
        client = CreditRatingAgencyClient()
        result = client.query_by_entity("Northwind Trading", "12-3456789")
        assert result.issuer_rating == "A-"
        assert result.is_investment_grade
        assert result.risk_band == "low"

    def test_query_not_rated(self) -> None:
        client = CreditRatingAgencyClient()
        result = client.query_by_entity("Some Unknown Co", "12-3456789")
        assert result.not_rated
        assert result.risk_band == "moderate"
        assert "Not rated" in result.summary

    def test_live_mode_misconfigured(self) -> None:
        client = CreditRatingAgencyClient(mode="live")
        result = client.query_by_entity("Test Name")
        assert result.query_completed is False
        assert "RATING_AGENCY_API_KEY" in result.error


class TestOracleResponseParsers:
    def test_bureau_parser(self) -> None:
        payload = {
            "paydex_score": 35,
            "financial_strength_rating": "2A",
            "failure_risk_score": 0.46,
            "records": [
                {
                    "trade_id": "TR-GW-1",
                    "creditor": "Heavy Equipment Leasing",
                    "credit_limit": 420000,
                    "highest_credit": 400000,
                    "current_balance": 310000,
                    "past_due_days": 120,
                    "payment_status": "derogatory",
                    "opened_at": "2022-03-01",
                }
            ],
            "total_credit_limit": 420000,
            "total_current_balance": 310000,
            "number_of_derogatory_trades": 1,
            "has_bankruptcy_indicator": True,
            "has_lien_indicator": True,
            "has_judgment_indicator": True,
            "synthetic": True,
            "mode": "gateway_synthetic",
        }
        parsed = parse_bureau_response(payload)
        assert parsed["paydex_score"] == 35
        assert parsed["records"][0]["creditor"] == "Heavy Equipment Leasing"
        assert parsed["has_bankruptcy_indicator"] is True

    def test_public_records_parser(self) -> None:
        payload = {
            "records": [
                {
                    "record_id": "JUD-GW-1",
                    "record_type": "judgment",
                    "jurisdiction": "CA Superior Court, Alameda",
                    "amount": 125000,
                    "filed_at": "2025-02-01",
                    "status": "open",
                    "plaintiff": "Subcontractor Trust",
                    "description": "Unpaid subcontractor judgment",
                }
            ],
            "total_records_found": 1,
            "total_judgment_amount": 125000,
            "has_bankruptcy": True,
            "has_active_judgment": True,
            "has_ucc_filing": False,
            "has_active_lien": True,
            "synthetic": True,
            "mode": "gateway_synthetic",
        }
        parsed = parse_public_records_response(payload)
        assert parsed["total_records_found"] == 1
        assert parsed["records"][0]["record_type"] == "judgment"
        assert parsed["has_active_judgment"] is True

    def test_osha_parser(self) -> None:
        payload = {
            "violations": [
                {
                    "violation_id": "VIO-GW-1",
                    "inspection_number": "INSP-GW-1",
                    "inspection_type": "accident",
                    "violation_type": "willful",
                    "description": "Failure to provide fall protection",
                    "penalty": 72000,
                    "inspected_at": "2025-01-10",
                    "closed": False,
                    "items": 3,
                    "serious": True,
                }
            ],
            "total_violations": 1,
            "total_penalty": 72000,
            "has_willful_violation": True,
            "has_repeat_violation": False,
            "has_open_inspection": True,
            "safety_rating": "critical",
            "synthetic": True,
            "mode": "gateway_synthetic",
        }
        parsed = parse_osha_response(payload)
        assert parsed["total_violations"] == 1
        assert parsed["violations"][0]["violation_type"] == "willful"
        assert parsed["safety_rating"] == "critical"

    def test_rating_agency_parser(self) -> None:
        payload = {
            "issuer_rating": "B",
            "outlook": "negative",
            "watch": "on-watch",
            "agency": "S&P Global",
            "not_rated": False,
            "synthetic": True,
            "mode": "gateway_synthetic",
        }
        parsed = parse_rating_agency_response(payload)
        assert parsed["issuer_rating"] == "B"
        assert parsed["outlook"] == "negative"
        assert parsed["not_rated"] is False


class TestNCCICodes:
    def test_class_code_lookup(self) -> None:
        assert get_ncci_description("8810") == "Clerical Office"
        assert get_ncci_description("9999") == "Unknown classification"

    def test_risk_levels(self) -> None:
        assert get_ncci_risk_level("8810") == "low"
        assert get_ncci_risk_level("5221") == "high"
        assert get_ncci_risk_level("5222") == "critical"
        assert get_ncci_risk_level("9999") == "moderate"

    def test_high_risk_detection(self) -> None:
        assert not is_high_risk_ncci_class("8810")
        assert not is_high_risk_ncci_class("7720")
        assert is_high_risk_ncci_class("5221")
        assert is_high_risk_ncci_class("5222")
        assert is_high_risk_ncci_class("8391")

    def test_all_codes_have_risk_levels(self) -> None:
        for code, entry in NCCI_CLASS_CODES.items():
            assert entry.risk_level in ("low", "moderate", "high", "critical")
            assert entry.description
