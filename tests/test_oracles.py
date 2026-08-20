from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from insureflow.integrations.parsers import parse_bureau_response, parse_osha_response, parse_public_records_response, parse_rating_agency_response
from insureflow.oracles.aplus_client import APlusClient, APlusResult, PropertyClaimType
from insureflow.oracles.bureau_client import BureauResult, CreditBureauClient, TradeCreditRecord
from insureflow.oracles.clue_client import CLUEClient, CLUEResult
from insureflow.oracles.ncci_client import NCCIClient, NCCIExperienceMod, NCCIResult
from insureflow.oracles.ncci_codes import NCCI_CLASS_CODES, get_ncci_description, get_ncci_risk_level, is_high_risk_ncci_class
from insureflow.oracles.osha_client import OSHAClient, OSHAInspectionResult, OSHAViolation
from insureflow.oracles.public_records_client import PublicRecord, PublicRecordsClient, PublicRecordsResult
from insureflow.oracles.rating_agency_client import CreditRatingAgencyClient, CreditRatingResult


class TestCLUEClient:
    def test_misconfigured_returns_error(self) -> None:
        client = CLUEClient()
        result = client.query_by_name_and_address("Pacific Marine Supply", "123 Harbor Blvd")
        assert not result.query_completed
        assert "CLUE" in result.error
        assert "configured" in result.error.lower() or "key" in result.error.lower()

    def test_live_mode_misconfigured(self) -> None:
        client = CLUEClient(mode="live")
        result = client.query_by_name_and_address("Test Name")
        assert result.query_completed is False
        assert "CLUE_API_KEY" in result.error

    def test_result_model_defaults(self) -> None:
        result = CLUEResult(
            subject_name="Test",
            subject_address="123 Main St",
            total_claims_found=0,
            total_paid=0.0,
            has_prior_litigation=False,
            has_prior_cancellation=False,
        )
        assert result.query_completed is True
        assert result.total_claims_found == 0
        assert "0" in result.summary

    def test_result_summary_with_error(self) -> None:
        result = CLUEResult(
            subject_name="Test",
            subject_address="",
            query_completed=False,
            error="API timeout",
        )
        assert "failed" in result.summary.lower()

    def test_result_summary_clean(self) -> None:
        result = CLUEResult(
            subject_name="CleanCo",
            subject_address="123 Main St",
            total_claims_found=0,
            total_paid=0.0,
        )
        assert "0" in result.summary

    def test_disabled_client(self) -> None:
        client = CLUEClient(api_key="fake", base_url="http://localhost:1", mode="live")
        result = client.query_by_name_and_address("Test")
        assert result.query_completed is False


class TestNCCIClient:
    def test_misconfigured_returns_error(self) -> None:
        client = NCCIClient()
        result = client.query_by_fein("98-7654321", "Pacific Marine Supply")
        assert not result.query_completed
        assert "NCCI" in result.error

    def test_live_mode_misconfigured(self) -> None:
        client = NCCIClient(mode="live")
        result = client.query_by_fein("00-0000000", "Test")
        assert result.query_completed is False
        assert "NCCI_API_KEY" in result.error

    def test_experience_mod_model(self) -> None:
        mod = NCCIExperienceMod(
            mod_factor=1.12,
            class_code="8380",
            class_code_description="Marine",
            expected_losses=50000,
            actual_losses=60000,
            primary_losses=30000,
            excess_losses=30000,
            payroll=500000,
        )
        assert mod.is_debit_mod is True
        assert mod.is_credit_mod is False
        assert mod.risk_band == "moderate"

    def test_credit_mod(self) -> None:
        mod = NCCIExperienceMod(mod_factor=0.88, class_code="8810")
        assert mod.is_credit_mod is True
        assert mod.is_debit_mod is False

    def test_risk_bands(self) -> None:
        assert NCCIExperienceMod(mod_factor=1.55, class_code="X").risk_band == "critical"
        assert NCCIExperienceMod(mod_factor=1.30, class_code="X").risk_band == "high"
        assert NCCIExperienceMod(mod_factor=1.05, class_code="X").risk_band == "moderate"
        assert NCCIExperienceMod(mod_factor=0.90, class_code="X").risk_band == "low"

    def test_result_worst_mod(self) -> None:
        result = NCCIResult(
            employer_name="Test",
            fein="12-3456789",
            experience_mods=[
                NCCIExperienceMod(mod_factor=0.88, class_code="8810"),
                NCCIExperienceMod(mod_factor=1.35, class_code="5221"),
            ],
        )
        assert result.worst_mod is not None
        assert result.worst_mod.class_code == "5221"
        assert result.worst_mod.mod_factor == 1.35


class TestAPlusClient:
    def test_misconfigured_returns_error(self) -> None:
        client = APlusClient()
        result = client.query_by_property("Pacific Marine Supply", "123 Harbor Blvd")
        assert not result.query_completed
        assert "A-PLUS" in result.error or "APLUS" in result.error

    def test_live_mode_misconfigured(self) -> None:
        client = APlusClient(mode="live")
        result = client.query_by_property("Test")
        assert result.query_completed is False
        assert "APLUS_API_KEY" in result.error

    def test_result_model_defaults(self) -> None:
        result = APlusResult(
            subject_name="Test",
            subject_address="123 Main St",
            total_claims_found=0,
            total_paid=0.0,
        )
        assert result.total_claims_found == 0
        assert "A-PLUS" in result.summary

    def test_result_summary_with_error(self) -> None:
        result = APlusResult(
            subject_name="Test",
            subject_address="",
            query_completed=False,
            error="timeout",
        )
        assert "failed" in result.summary.lower()

    def test_property_claim_type_enum(self) -> None:
        assert PropertyClaimType.FIRE.value == "fire"
        assert PropertyClaimType.WATER_DAMAGE.value == "water_damage"
        assert PropertyClaimType.OTHER.value == "other"


class TestCreditBureauClient:
    def test_misconfigured_returns_error(self) -> None:
        client = CreditBureauClient()
        result = client.query_by_tax_id("12-3456789", "Pacific Marine Supply")
        assert not result.query_completed
        assert "Bureau" in result.error or "BUREAU" in result.error

    def test_live_mode_misconfigured(self) -> None:
        client = CreditBureauClient(mode="live")
        result = client.query_by_tax_id("12-3456789", "Test Name")
        assert result.query_completed is False
        assert "BUREAU_API_KEY" in result.error

    def test_result_model_defaults(self) -> None:
        result = BureauResult(
            subject_name="Test Corp",
            tax_id="12-3456789",
            paydex_score=50,
        )
        assert result.paydex_score == 50
        assert result.risk_band == "moderate"

    def test_trade_record_model(self) -> None:
        record = TradeCreditRecord(
            trade_id="TR-1",
            creditor="Test Creditor",
            credit_limit=100_000,
            highest_credit=80_000,
            current_balance=50_000,
            past_due_days=0,
            payment_status="current",
            opened_at=date(2020, 1, 1),
        )
        assert record.is_derogatory is False

    def test_trade_record_derogatory(self) -> None:
        record = TradeCreditRecord(
            trade_id="TR-1",
            creditor="Test Creditor",
            credit_limit=100_000,
            highest_credit=80_000,
            current_balance=50_000,
            past_due_days=120,
            payment_status="derogatory",
            opened_at=date(2020, 1, 1),
        )
        assert record.is_derogatory is True

    def test_risk_bands(self) -> None:
        r_bankruptcy = BureauResult(
            subject_name="Test",
            tax_id="12-3456789",
            has_bankruptcy_indicator=True,
        )
        assert r_bankruptcy.risk_band == "critical"

        r_derogatory = BureauResult(
            subject_name="Test",
            tax_id="12-3456789",
            number_of_derogatory_trades=3,
            paydex_score=50,
        )
        assert r_derogatory.risk_band == "high"

        r_clean = BureauResult(
            subject_name="Test",
            tax_id="12-3456789",
            paydex_score=85,
        )
        assert r_clean.risk_band == "low"

    def test_summary_synthetic(self) -> None:
        result = BureauResult(
            subject_name="Test Corp",
            tax_id="12-3456789",
            paydex_score=35,
            synthetic=True,
        )
        assert "SYNTHETIC/UNVERIFIED" in result.summary
        assert "Paydex 35" in result.summary


class TestPublicRecordsClient:
    def test_misconfigured_returns_error(self) -> None:
        client = PublicRecordsClient()
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
        assert not result.query_completed
        assert "Public" in result.error or "PUBLIC" in result.error

    def test_live_mode_misconfigured(self) -> None:
        client = PublicRecordsClient(mode="live")
        result = client.query_by_entity("Test Name")
        assert result.query_completed is False
        assert "PUBLIC_RECORDS_API_KEY" in result.error

    def test_record_model(self) -> None:
        record = PublicRecord(
            record_id="JUD-1",
            record_type="judgment",
            jurisdiction="CA",
            amount=50_000,
            status="open",
        )
        assert record.is_active is True

    def test_record_satisfied(self) -> None:
        record = PublicRecord(
            record_id="JUD-1",
            record_type="judgment",
            jurisdiction="CA",
            amount=50_000,
            status="satisfied",
        )
        assert record.is_active is False

    def test_risk_banks(self) -> None:
        r_bankruptcy = PublicRecordsResult(
            subject_name="Test",
            tax_id="12-3456789",
            has_bankruptcy=True,
        )
        assert r_bankruptcy.risk_band == "critical"

        r_judgment = PublicRecordsResult(
            subject_name="Test",
            tax_id="12-3456789",
            has_active_judgment=True,
            total_judgment_amount=125_000,
        )
        assert r_judgment.risk_band == "high"

        r_clean = PublicRecordsResult(
            subject_name="Test",
            tax_id="12-3456789",
            total_records_found=0,
        )
        assert r_clean.risk_band == "low"


class TestOSHAClient:
    def test_misconfigured_returns_error(self) -> None:
        client = OSHAClient()
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
        assert not result.query_completed
        assert "OSHA" in result.error

    def test_live_mode_misconfigured(self) -> None:
        client = OSHAClient(mode="live")
        result = client.query_by_entity("Test Name")
        assert result.query_completed is False
        assert "OSHA_API_KEY" in result.error

    def test_violation_model(self) -> None:
        violation = OSHAViolation(
            violation_id="V-1",
            inspection_number="I-1",
            inspection_type="accident",
            violation_type="willful",
            penalty=72_000,
        )
        assert violation.risk_weight == 1.0
        assert violation.serious is False

    def test_risk_weights(self) -> None:
        assert OSHAViolation(violation_id="1", inspection_number="", inspection_type="", violation_type="willful").risk_weight == 1.0
        assert OSHAViolation(violation_id="1", inspection_number="", inspection_type="", violation_type="repeat").risk_weight == 0.8
        assert OSHAViolation(violation_id="1", inspection_number="", inspection_type="", violation_type="serious").risk_weight == 0.6
        assert OSHAViolation(violation_id="1", inspection_number="", inspection_type="", violation_type="other").risk_weight == 0.3

    def test_result_summary(self) -> None:
        result = OSHAInspectionResult(
            subject_name="Test Corp",
            tax_id="12-3456789",
            total_violations=5,
            total_penalty=50_000,
            has_willful_violation=True,
        )
        assert "5" in result.summary
        assert "WILLFUL" in result.summary


class TestCreditRatingAgencyClient:
    def test_misconfigured_returns_error(self) -> None:
        client = CreditRatingAgencyClient()
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
        assert not result.query_completed
        assert "Rating" in result.error or "RATING" in result.error

    def test_live_mode_misconfigured(self) -> None:
        client = CreditRatingAgencyClient(mode="live")
        result = client.query_by_entity("Test Name")
        assert result.query_completed is False
        assert "RATING_AGENCY_API_KEY" in result.error

    def test_investment_grade(self) -> None:
        result = CreditRatingResult(
            subject_name="Test",
            tax_id="12-3456789",
            issuer_rating="A-",
        )
        assert result.is_investment_grade is True
        assert result.risk_band == "low"

    def test_speculative_grade(self) -> None:
        result = CreditRatingResult(
            subject_name="Test",
            tax_id="12-3456789",
            issuer_rating="BB+",
        )
        assert result.is_investment_grade is False

    def test_not_rated(self) -> None:
        result = CreditRatingResult(
            subject_name="Test",
            tax_id="12-3456789",
            not_rated=True,
        )
        assert result.is_investment_grade is False
        assert result.risk_band == "moderate"
        assert "Not rated" in result.summary

    def test_risk_bands(self) -> None:
        assert CreditRatingResult(subject_name="T", tax_id="1", issuer_rating="D").risk_band == "critical"
        assert CreditRatingResult(subject_name="T", tax_id="1", issuer_rating="CCC", outlook="negative").risk_band == "high"
        assert CreditRatingResult(subject_name="T", tax_id="1", outlook="developing").risk_band == "moderate"
        assert CreditRatingResult(subject_name="T", tax_id="1", issuer_rating="AA", outlook="stable").risk_band == "low"


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


class TestOracleFailurePropagation:
    def test_oracle_failure_model(self) -> None:
        from insureflow.models.agents import OracleFailure
        failure = OracleFailure(
            oracle_name="CLUE",
            status="error",
            error_code="CLUE_QUERY_FAILED",
            error_message="API timeout",
            query_completed=False,
            mode="live",
            is_critical=True,
        )
        assert failure.oracle_name == "CLUE"
        assert failure.status == "error"
        assert failure.is_critical is True
        assert failure.timestamp is not None

    def test_clue_failure_records_failure(self) -> None:
        from insureflow.models.submissions import SubmissionBundle
        from insureflow.oracles.oracle_agent import OracleAgent

        agent = OracleAgent()
        mock_bundle = MagicMock(spec=SubmissionBundle)
        mock_bundle.bundle_id = "test-bundle"
        mock_bundle.structured = MagicMock()
        mock_bundle.structured.named_insured = MagicMock()
        mock_bundle.structured.named_insured.tax_id = "12-3456789"
        mock_bundle.structured.named_insured.legal_name = "Test Corp"
        mock_bundle.structured.locations = []

        with patch.object(agent.clue, 'query_by_name_and_address') as mock_clue:
            mock_result = MagicMock()
            mock_result.error = "CLUE API timeout"
            mock_result.query_completed = False
            mock_result.mode = "live"
            mock_clue.return_value = mock_result

            agent._query_clue(mock_bundle)

            assert len(agent._oracle_failures) == 1
            assert agent._oracle_failures[0].oracle_name == "CLUE"
            assert agent._oracle_failures[0].status == "error"
            assert agent._oracle_failures[0].error_code == "CLUE_QUERY_FAILED"

    def test_critical_oracle_failures_collected(self) -> None:
        from insureflow.models.submissions import SubmissionBundle
        from insureflow.oracles.oracle_agent import OracleAgent

        agent = OracleAgent()
        mock_bundle = MagicMock(spec=SubmissionBundle)
        mock_bundle.bundle_id = "test-bundle"
        mock_bundle.structured = MagicMock()
        mock_bundle.structured.named_insured = MagicMock()
        mock_bundle.structured.named_insured.tax_id = "12-3456789"
        mock_bundle.structured.named_insured.legal_name = "Test Corp"
        mock_bundle.structured.locations = []
        mock_bundle.structured.risk_profile = MagicMock()
        mock_bundle.structured.risk_profile.naics_code = "332710"
        mock_bundle.structured.risk_profile.naics_description = "Machine Shops"

        with patch.object(agent.clue, 'query_by_name_and_address') as mock_clue, \
             patch.object(agent.aplus, 'query_by_property') as mock_aplus, \
             patch.object(agent.ncci, 'query_by_fein') as mock_ncci:

            mock_clue_result = MagicMock()
            mock_clue_result.error = "CLUE API timeout"
            mock_clue_result.query_completed = False
            mock_clue_result.mode = "live"
            mock_clue.return_value = mock_clue_result

            mock_aplus_result = MagicMock()
            mock_aplus_result.error = "A-PLUS service unavailable"
            mock_aplus_result.query_completed = False
            mock_aplus_result.mode = "live"
            mock_aplus.return_value = mock_aplus_result

            mock_ncci_result = MagicMock()
            mock_ncci_result.error = "NCCI connection failed"
            mock_ncci_result.query_completed = False
            mock_ncci_result.mode = "live"
            mock_ncci.return_value = mock_ncci_result

            agent._query_clue(mock_bundle)
            agent._query_aplus(mock_bundle)
            agent._query_ncci(mock_bundle)

            critical_failures = [f for f in agent._oracle_failures if f.is_critical]
            assert len(critical_failures) == 3
            assert critical_failures[0].oracle_name == "CLUE"
            assert critical_failures[1].oracle_name == "A-PLUS"
            assert critical_failures[2].oracle_name == "NCCI"

    def test_misconfigured_oracles_recorded_as_failures(self) -> None:
        from insureflow.models.submissions import SubmissionBundle
        from insureflow.oracles.oracle_agent import OracleAgent

        agent = OracleAgent()
        mock_bundle = MagicMock(spec=SubmissionBundle)
        mock_bundle.bundle_id = "test-bundle"
        mock_bundle.structured = MagicMock()
        mock_bundle.structured.named_insured = MagicMock()
        mock_bundle.structured.named_insured.tax_id = "12-3456789"
        mock_bundle.structured.named_insured.legal_name = "Test Corp"
        mock_bundle.structured.locations = []

        with patch.object(agent.clue, 'query_by_name_and_address') as mock_clue, \
             patch.object(agent.clue, '_resolved_mode', return_value='misconfigured'):

            mock_result = MagicMock()
            mock_result.error = "CLUE requires CLUE_API_KEY"
            mock_result.query_completed = False
            mock_result.total_claims_found = 0
            mock_result.has_prior_litigation = False
            mock_result.has_prior_cancellation = False
            mock_result.synthetic = False
            mock_result.mode = "misconfigured"
            mock_clue.return_value = mock_result

            agent._query_clue(mock_bundle)

            not_live_failures = [f for f in agent._oracle_failures if f.oracle_name == "CLUE"]
            assert len(not_live_failures) == 1
            assert not_live_failures[0].oracle_name == "CLUE"
            assert not_live_failures[0].status == "error"
            assert not_live_failures[0].error_code == "CLUE_QUERY_FAILED"
