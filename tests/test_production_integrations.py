"""Tests for production integration HTTP clients and live oracle adapters."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from insureflow.integrations.http_client import IntegrationHTTPClient
from insureflow.integrations.parsers import parse_clue_response
from insureflow.oracles.bureau_client import CreditBureauClient
from insureflow.oracles.clue_client import CLUEClient
from insureflow.oracles.osha_client import OSHAClient
from insureflow.oracles.public_records_client import PublicRecordsClient
from insureflow.oracles.rating_agency_client import CreditRatingAgencyClient


def test_parse_clue_response_records() -> None:
    payload = {"records": [{"claim_id": "C1", "paid_amount": 1000, "loss_type": "property", "current_status": "closed", "date_of_loss": "2024-01-15"}]}
    parsed = parse_clue_response(payload)
    assert parsed["total_claims_found"] == 1
    assert parsed["records"][0]["claim_id"] == "C1"


def test_clue_live_api_parses_response() -> None:
    client = CLUEClient(api_key="test-key", base_url="https://api.example.com", mode="live")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json_dict.return_value = {
        "records": [
            {
                "claim_id": "CLUE-1",
                "date_of_loss": "2023-06-01",
                "loss_type": "general_liability",
                "paid_amount": 25000,
                "current_status": "closed",
                "policy_type": "CGL",
                "claimant_name": "Acme Corp",
                "description": "Test claim",
            }
        ],
        "total_claims_found": 1,
    }
    with patch.object(client.http, "post", return_value=mock_resp):
        result = client.query_by_name_and_address("Acme Corp", "1 Main St")
    assert result.error == ""
    assert result.total_claims_found == 1
    assert result.records[0].claim_id == "CLUE-1"


def test_clue_misconfigured_live_mode() -> None:
    client = CLUEClient(api_key="", base_url="", mode="live")
    result = client.query_by_name_and_address("Acme Corp")
    assert result.query_completed is False
    assert "CLUE_API_KEY" in result.error


def test_http_client_health_check_success() -> None:
    client = IntegrationHTTPClient(api_key="k", base_url="https://api.example.com")

    class FakeResp:
        status = 200
        headers: dict[str, str] = {}

        def read(self) -> bytes:
            return b"{}"

        def __enter__(self) -> "FakeResp":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    with patch("urllib.request.urlopen", return_value=FakeResp()):
        health = client.health_check()
    assert health["reachable"] is True


def test_bureau_live_api_parses_response() -> None:
    client = CreditBureauClient(api_key="test-key", base_url="https://api.example.com", mode="live")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json_dict.return_value = {
        "paydex_score": 35,
        "financial_strength_rating": "2A",
        "failure_risk_score": 0.46,
        "records": [
            {
                "trade_id": "TR-1",
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
        "mode": "live",
    }
    with patch.object(client.http, "post", return_value=mock_resp):
        result = client.query_by_tax_id("12-3456789", "Veririsk Construction")
    assert result.query_completed
    assert result.paydex_score == 35
    assert result.has_bankruptcy_indicator
    assert result.records[0].creditor == "Heavy Equipment Leasing"
    assert result.risk_band == "critical"


def test_public_records_live_api_parses_response() -> None:
    client = PublicRecordsClient(api_key="test-key", base_url="https://api.example.com", mode="live")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json_dict.return_value = {
        "records": [
            {
                "record_id": "JUD-1",
                "record_type": "judgment",
                "jurisdiction": "CA Superior Court",
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
        "has_active_lien": True,
        "mode": "live",
    }
    with patch.object(client.http, "post", return_value=mock_resp):
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
    assert result.query_completed
    assert result.has_bankruptcy
    assert result.records[0].is_active
    assert result.total_judgment_amount == 125000


def test_osha_live_api_parses_response() -> None:
    client = OSHAClient(api_key="test-key", base_url="https://api.example.com", mode="live")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json_dict.return_value = {
        "violations": [
            {
                "violation_id": "VIO-1",
                "inspection_number": "INSP-1",
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
        "has_open_inspection": True,
        "safety_rating": "critical",
        "mode": "live",
    }
    with patch.object(client.http, "post", return_value=mock_resp):
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
    assert result.query_completed
    assert result.has_willful_violation
    assert result.safety_rating == "critical"
    assert result.violations[0].risk_weight == 1.0


def test_rating_agency_live_api_parses_response() -> None:
    client = CreditRatingAgencyClient(api_key="test-key", base_url="https://api.example.com", mode="live")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json_dict.return_value = {
        "issuer_rating": "B",
        "outlook": "negative",
        "watch": "on-watch",
        "agency": "S&P Global",
        "not_rated": False,
        "mode": "live",
    }
    with patch.object(client.http, "post", return_value=mock_resp):
        result = client.query_by_entity("Veririsk Construction", "12-3456789")
    assert result.query_completed
    assert result.issuer_rating == "B"
    assert result.outlook == "negative"
    assert not result.is_investment_grade
    assert result.risk_band == "high"


def test_bureau_misconfigured_live_mode() -> None:
    client = CreditBureauClient(api_key="", base_url="", mode="live")
    result = client.query_by_tax_id("12-3456789", "Veririsk Construction")
    assert result.query_completed is False
    assert "BUREAU_API_KEY" in result.error


def test_osha_misconfigured_live_mode() -> None:
    client = OSHAClient(api_key="", base_url="", mode="live")
    result = client.query_by_entity("Veririsk Construction")
    assert result.query_completed is False
    assert "OSHA_API_KEY" in result.error


def test_public_records_misconfigured_live_mode() -> None:
    client = PublicRecordsClient(api_key="", base_url="", mode="live")
    result = client.query_by_entity("Veririsk Construction")
    assert result.query_completed is False
    assert "PUBLIC_RECORDS_API_KEY" in result.error


def test_rating_agency_misconfigured_live_mode() -> None:
    client = CreditRatingAgencyClient(api_key="", base_url="", mode="live")
    result = client.query_by_entity("Veririsk Construction")
    assert result.query_completed is False
    assert "RATING_AGENCY_API_KEY" in result.error
