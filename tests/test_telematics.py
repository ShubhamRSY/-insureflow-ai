"""Connected-car and cyber-scan oracles: simulated never invents a clean score."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from insureflow.models.submissions import StructuredSubmission, SubmissionBundle, UnstructuredSubmission
from insureflow.oracles.oracle_agent import OracleAgent
from insureflow.oracles.telematics_client import (
    CyberScanClient,
    TelematicsClient,
    extract_domain,
    extract_vin,
)

_VIN = "1HGCM82633A004352"


def _auto_bundle(*, text: str) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="auto-1",
        structured=StructuredSubmission(submission_id="auto-1"),
        unstructured=[UnstructuredSubmission(submission_id="auto-1", raw_text=text)],
    )


def test_extract_vin_and_domain() -> None:
    assert extract_vin(f"VIN {_VIN} on the ACORD") == _VIN
    assert extract_domain("Scan acme-widgets.com for MFA") == "acme-widgets.com"


def test_simulated_telematics_is_synthetic_not_clean() -> None:
    result = TelematicsClient(mode="simulated").query_vehicle(_VIN, stated_mileage=8000)
    assert result.query_completed
    assert result.synthetic is True
    assert result.annual_mileage is None
    assert result.hard_brake_per_1k is None


def test_simulated_cyber_scan_is_synthetic_not_clean() -> None:
    result = CyberScanClient(mode="simulated").query_domain("acme-widgets.com")
    assert result.query_completed
    assert result.synthetic is True
    assert result.mfa_observed is None
    assert result.critical_findings is None


def test_live_telematics_without_key_fails_closed() -> None:
    result = TelematicsClient(api_key="", base_url="https://vendor.example.com", mode="live").query_vehicle(_VIN)
    assert result.query_completed is False
    assert result.synthetic is False
    assert result.error


def test_bundled_gateway_telematics_is_not_a_clean_score() -> None:
    result = TelematicsClient(mode="simulated").query_vehicle(_VIN, stated_mileage=8000)
    assert result.synthetic is True
    assert result.annual_mileage is None


def test_live_mileage_mismatch() -> None:
    client = TelematicsClient(api_key="test-key", base_url="https://api.example.com", mode="live")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json_dict.return_value = {"vin": _VIN, "annual_mileage": 24000, "hard_brake_per_1k": 2.0}
    agent = OracleAgent(telematics_client=client)
    with patch.object(client.http, "post", return_value=mock_resp):
        result = client.query_vehicle(_VIN, stated_mileage=8000)
        findings = agent._query_telematics(_auto_bundle(text=f"VIN {_VIN}. Annual mileage: 8000"))
    assert result.synthetic is False
    assert result.annual_mileage == 24000
    titles = [f.title for f in findings]
    assert any("mileage" in t.lower() for t in titles)


def test_oracle_agent_simulated_telematics_is_a_finding() -> None:
    agent = OracleAgent(telematics_client=TelematicsClient(mode="simulated"))
    findings = agent._query_telematics(_auto_bundle(text=f"VIN {_VIN}. Annual mileage: 12000"))
    assert findings
    assert findings[0].severity.value != "low"
    assert "unverified" in findings[0].title.lower() or "not a clean" in findings[0].description.lower()
    assert not any("consistent" in f.title.lower() for f in findings)


def test_live_cyber_mfa_contradiction() -> None:
    client = CyberScanClient(api_key="test-key", base_url="https://api.example.com", mode="live")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json_dict.return_value = {"domain": "acme-widgets.com", "critical_findings": 0, "mfa_observed": False}
    agent = OracleAgent(cyber_scan_client=client)
    with patch.object(client.http, "post", return_value=mock_resp):
        result = client.query_domain("acme-widgets.com")
        findings = agent._query_cyber_scan(_auto_bundle(text="Cyber application for acme-widgets.com. MFA: yes, enabled in place."))
    assert result.mfa_observed is False
    assert any("MFA" in f.title or "mfa" in f.description.lower() for f in findings)
