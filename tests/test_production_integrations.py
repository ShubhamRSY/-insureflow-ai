"""Tests for production integration HTTP clients and live oracle adapters."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from insureflow.integrations.http_client import IntegrationHTTPClient
from insureflow.integrations.parsers import parse_clue_response
from insureflow.oracles.clue_client import CLUEClient


def test_parse_clue_response_records() -> None:
    payload = {
        "records": [
            {"claim_id": "C1", "paid_amount": 1000, "loss_type": "property", "current_status": "closed", "date_of_loss": "2024-01-15"}
        ]
    }
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
