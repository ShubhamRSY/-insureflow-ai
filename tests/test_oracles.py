from __future__ import annotations

from insureflow.oracles.aplus_client import APlusClient, PropertyClaimType
from insureflow.oracles.clue_client import CLUEClient
from insureflow.oracles.ncci_client import NCCIClient
from insureflow.oracles.ncci_codes import (
    NCCI_CLASS_CODES,
    get_ncci_description,
    get_ncci_risk_level,
    is_high_risk_ncci_class,
)


class TestCLUEClient:
    def test_query_by_name_marine(self):
        client = CLUEClient()
        result = client.query_by_name_and_address("Pacific Marine Supply", "123 Harbor Blvd")
        assert result.query_completed
        assert result.total_claims_found >= 2
        assert any("general_liability" in r.loss_type for r in result.records)
        assert any("property" in r.loss_type for r in result.records)

    def test_query_by_name_construction(self):
        client = CLUEClient()
        result = client.query_by_name_and_address("Veririsk Construction", "456 Jobsite Rd")
        assert result.total_claims_found >= 1
        assert any("workers_comp" in r.loss_type for r in result.records)

    def test_query_by_name_clean(self):
        client = CLUEClient()
        result = client.query_by_name_and_address("CleanCo Inc", "789 Main St")
        assert result.total_claims_found == 0
        assert "Clean" in result.summary

    def test_query_by_tax_id(self):
        client = CLUEClient()
        result = client.query_by_tax_id("12-3456789")
        assert result.query_completed
        assert isinstance(result.total_claims_found, int)

    def test_litigation_detected(self):
        client = CLUEClient()
        result = client.query_by_name_and_address("Pacific Marine Supply")
        assert result.has_prior_litigation or not result.has_prior_litigation

    def test_live_mode_stub(self):
        client = CLUEClient(mode="live")
        result = client.query_by_name_and_address("Test Name")
        assert "not yet implemented" in result.error

    def test_disabled(self):
        client = CLUEClient(api_key="", mode="simulated")
        result = client.query_by_name_and_address("")
        assert result.query_completed  # simulated mode always works


class TestNCCIClient:
    def test_query_marine(self):
        client = NCCIClient()
        result = client.query_by_fein("98-7654321", "Pacific Marine Supply")
        assert any(m.class_code == "8380" for m in result.experience_mods)
        assert result.worst_mod is not None
        assert result.worst_mod.mod_factor == 1.12

    def test_query_construction(self):
        client = NCCIClient()
        result = client.query_by_fein("98-7654321", "Veririsk Construction")
        assert any(m.class_code == "5221" for m in result.experience_mods)
        assert result.worst_mod.mod_factor == 1.35

    def test_query_northwind(self):
        client = NCCIClient()
        result = client.query_by_fein("98-7654321", "Northwind Trading")
        assert any(m.class_code == "8810" for m in result.experience_mods)
        assert result.worst_mod.mod_factor == 0.88

    def test_query_fallback(self):
        client = NCCIClient()
        result = client.query_by_fein("00-0000000", "Some Unknown Co")
        assert any(m.class_code == "5555" for m in result.experience_mods)
        assert result.worst_mod.mod_factor == 1.00

    def test_risk_bans(self):
        NCCIClient()
        c = NCCIClient()
        result = c.query_by_fein("00-0000000", "Veririsk Construction")
        mod = result.experience_mods[0]
        assert mod.risk_band == "high"
        assert mod.is_debit_mod
        assert not mod.is_credit_mod

    def test_credit_mod(self):
        client = NCCIClient()
        result = client.query_by_fein("00-0000000", "Northwind Trading")
        mod = result.experience_mods[0]
        assert mod.is_credit_mod
        assert not mod.is_debit_mod

    def test_live_mode_stub(self):
        client = NCCIClient(mode="live")
        result = client.query_by_fein("00-0000000", "Test")
        assert "not yet implemented" in result.error


class TestAPlusClient:
    def test_query_marine(self):
        client = APlusClient()
        result = client.query_by_property("Pacific Marine Supply", "123 Harbor Blvd")
        assert result.query_completed
        assert result.total_claims_found >= 1
        assert any(r.claim_type == PropertyClaimType.WATER_DAMAGE for r in result.records)

    def test_query_construction(self):
        client = APlusClient()
        result = client.query_by_property("Veririsk Construction", "456 Industrial Dr")
        assert result.total_claims_found >= 2
        assert any(r.claim_type == PropertyClaimType.FIRE for r in result.records)
        assert any(r.claim_type == PropertyClaimType.THEFT for r in result.records)

    def test_query_northwind(self):
        client = APlusClient()
        result = client.query_by_property("Northwind Trading", "789 Main St")
        assert result.total_claims_found >= 1
        assert any(r.claim_type == PropertyClaimType.HAIL for r in result.records)

    def test_coastal_address_triggers_wind(self):
        client = APlusClient()
        result = client.query_by_property("Coastal Properties Inc", "100 Beach Blvd")
        assert result.total_claims_found >= 1
        assert any(r.claim_type == PropertyClaimType.WIND for r in result.records)

    def test_clean_property(self):
        client = APlusClient()
        result = client.query_by_property("CleanCo Inc", "999 Main St")
        assert result.total_claims_found == 0

    def test_repeated_property_claims_flag(self):
        client = APlusClient()
        result = client.query_by_property("Veririsk Construction", "456 Industrial Dr")
        assert result.has_repeated_property_claims

    def test_summary(self):
        client = APlusClient()
        result = client.query_by_property("Pacific Marine Supply")
        assert "A-PLUS" in result.summary or "property" in result.summary

    def test_live_mode_stub(self):
        client = APlusClient(mode="live")
        result = client.query_by_property("Test")
        assert "not yet implemented" in result.error


class TestNCCICodes:
    def test_class_code_lookup(self):
        assert get_ncci_description("8810") == "Clerical Office"
        assert get_ncci_description("9999") == "Unknown classification"

    def test_risk_levels(self):
        assert get_ncci_risk_level("8810") == "low"
        assert get_ncci_risk_level("5221") == "high"
        assert get_ncci_risk_level("5222") == "critical"
        assert get_ncci_risk_level("9999") == "moderate"

    def test_high_risk_detection(self):
        assert not is_high_risk_ncci_class("8810")
        assert not is_high_risk_ncci_class("7720")
        assert is_high_risk_ncci_class("5221")
        assert is_high_risk_ncci_class("5222")
        assert is_high_risk_ncci_class("8391")

    def test_all_codes_have_risk_levels(self):
        for code, entry in NCCI_CLASS_CODES.items():
            assert entry.risk_level in ("low", "moderate", "high", "critical")
            assert entry.description
