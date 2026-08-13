"""Buyer gates: live oracles, carrier SERFF book, Guidewire bind without re-key."""

from __future__ import annotations

from pathlib import Path

import pytest

from insureflow.billing.plan import current_plan, is_customer_rate_book, resolve_plan
from insureflow.integration.base_adapter import PolicySubmissionPayload
from insureflow.integration.policy_admin_service import PolicyAdminService
from insureflow.integrations.http_client import IntegrationHTTPClient
from insureflow.models.agents import Recommendation, UnderwritingMemo
from insureflow.models.submissions import (
    CoverageDetail,
    FinancialData,
    LocationData,
    NamedInsured,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
)
from insureflow.oracles._live import is_bundled_gateway_url, resolve_integration_mode
from insureflow.oracles.oracle_agent import OracleAgent
from insureflow.rating.book_import import filings_from_csv_text, import_filings
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.rating.leaf_filings import carrier_book_status, clear_carrier_book_cache, should_use_leaf_filing
from insureflow.rating.models import InsuranceLine, QuoteResult


def _bundle(bid: str = "gate") -> SubmissionBundle:
    structured = StructuredSubmission(
        submission_id=bid,
        named_insured=NamedInsured(legal_name="Gate Co"),
        locations=[
            LocationData(
                address="1 Main",
                city="Austin",
                state="TX",
                zip_code="78701",
                building_value=2_000_000,
                contents_value=400_000,
            )
        ],
        financial=FinancialData(annual_revenue=5_000_000, payroll=1_500_000),
        risk_profile=RiskProfile(),
        coverages=[CoverageDetail(coverage_type="building", limit_amount=2_000_000, deductible=25_000, premium=0)],
    )
    return SubmissionBundle(bundle_id=bid, structured=structured)


def test_default_plan_is_pilot() -> None:
    plan = current_plan()
    assert plan.plan_id == "pilot"
    assert plan.allow_simulated_oracles is True
    assert plan.require_carrier_book is False
    assert plan.allow_bind is False


def test_desk_entitlements_fail_closed() -> None:
    desk = resolve_plan("desk")
    assert desk.require_live_oracles is True
    assert desk.require_carrier_book is True
    assert desk.allow_simulated_oracles is False
    assert desk.allow_bind is True


def test_desk_simulated_oracles_do_not_invent_clean_history(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RYTERA_PLAN", "desk")
    agent = OracleAgent()
    result = agent.run(_bundle("oracle-desk"))
    titles = [f.title for f in result.findings]
    assert any("Live oracles required" in t for t in titles)
    assert not any("CLUE" in t and "claim" in t.lower() for t in titles)


def test_pilot_oracles_still_run_simulated() -> None:
    agent = OracleAgent()
    result = agent.run(_bundle("oracle-pilot"))
    assert not any("Live oracles required" in f.title for f in result.findings)


def test_desk_quote_blocks_pilot_rate_book(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RYTERA_PLAN", "desk")
    clear_carrier_book_cache()
    status = carrier_book_status()
    assert is_customer_rate_book(status) is False
    memo = UnderwritingMemo(bundle_id="desk-book", recommendation=Recommendation(suggested_premium_modification=0.0))
    quote = InsuranceRatingEngine().quote(_bundle("desk-book"), memo, line=InsuranceLine.GENERAL_LIABILITY, commercial_product_id="product_liability")
    assert quote.eligible is False
    assert quote.metadata.get("rate_book_gate") == "blocked_demo_book"
    assert any("SERFF" in r for r in quote.ineligibility_reasons)


def test_imported_book_is_customer_book(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    book_path = tmp_path / "carrier_book.live.json"
    monkeypatch.setenv("CARRIER_BOOK_PATH", str(book_path))
    clear_carrier_book_cache()
    result = import_filings(
        filings={"product_liability": {"loss_cost": 0.42, "lcm": 1.8, "filing_id": "SERFF-TX-001", "minimum_premium": 750}},
        book_path=book_path,
        carrier="Meridian Mutual",
        book_id="meridian-serff-2026",
    )
    assert result["posture"] == "carrier_imported"
    status = carrier_book_status()
    assert is_customer_rate_book(status) is True
    monkeypatch.setenv("RYTERA_PLAN", "desk")
    memo = UnderwritingMemo(bundle_id="serff", recommendation=Recommendation(suggested_premium_modification=0.0))
    quote = InsuranceRatingEngine().quote(_bundle("serff"), memo, line=InsuranceLine.GENERAL_LIABILITY, commercial_product_id="product_liability")
    assert quote.metadata.get("rate_book_gate") == "ok"
    assert quote.eligible is True
    clear_carrier_book_cache()


def test_bundled_gateway_is_not_live() -> None:
    assert is_bundled_gateway_url("https://integrations.rytera.ai/oracles/clue/v2", "real-looking-key")
    assert is_bundled_gateway_url("https://api.lexisnexis.com/clue/v2", "rytera-dev-gateway-key-change-in-production")
    assert not is_bundled_gateway_url("https://api.lexisnexis.com/clue/v2", "vendor-sandbox-key")
    http = IntegrationHTTPClient(api_key="k", base_url="https://integrations.rytera.ai/oracles/clue/v2")
    assert resolve_integration_mode("auto", http) == "gateway_synthetic"
    assert resolve_integration_mode("live", http) == "gateway_synthetic"


def test_gateway_url_is_not_live_pas(monkeypatch: pytest.MonkeyPatch) -> None:
    from insureflow.integration.guidewire_adapter import GuidewireAdapter
    from insureflow.pilot.sandbox_readiness import bind_is_allowed, is_shadow_mode

    monkeypatch.setenv("GUIDEWIRE_API_KEY", "live-key-not-dev-placeholder-xxxxxx")
    monkeypatch.setenv("GUIDEWIRE_API_URL", "https://integrations.rytera.ai/policy/guidewire/v1")
    monkeypatch.delenv("BRITECORE_API_KEY", raising=False)
    monkeypatch.delenv("OPERATING_MODE", raising=False)
    monkeypatch.delenv("PILOT_SHADOW_MODE", raising=False)
    assert is_shadow_mode() is False
    assert bind_is_allowed() is False
    gw = GuidewireAdapter(
        api_key="live-key-not-dev-placeholder-xxxxxx",
        base_url="https://integrations.rytera.ai/policy/guidewire/v1",
        mode="live",
    )
    assert gw._resolved_mode() == "gateway_synthetic"


def test_customer_book_rates_dedicated_workers_comp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    book_path = tmp_path / "carrier_book.live.json"
    monkeypatch.setenv("CARRIER_BOOK_PATH", str(book_path))
    clear_carrier_book_cache()
    import_filings(
        filings={
            "workers_comp": {
                "loss_cost": 1.15,
                "lcm": 1.0,
                "filing_id": "SERFF-WC-88",
                "exposure_basis": "payroll",
                "minimum_premium": 600,
            }
        },
        book_path=book_path,
        carrier="Meridian Mutual",
        book_id="meridian-serff-wc",
    )
    assert should_use_leaf_filing("workers_comp") is True
    memo = UnderwritingMemo(bundle_id="wc-serff", recommendation=Recommendation(suggested_premium_modification=0.0))
    quote = InsuranceRatingEngine().quote(_bundle("wc-serff"), memo, line=InsuranceLine.WORKERS_COMP, commercial_product_id="workers_comp")
    assert quote.metadata.get("rating_engine") == "carrier_leaf_filing"
    assert quote.metadata.get("serff_tracking") == "SERFF-WC-88"
    assert quote.eligible is True
    monkeypatch.delenv("CARRIER_BOOK_PATH", raising=False)
    clear_carrier_book_cache()
    assert should_use_leaf_filing("workers_comp") is False


def test_pas_submit_stamps_job_reference() -> None:
    bundle = _bundle("pas-ref")
    memo = UnderwritingMemo(
        bundle_id="pas-ref",
        insured_name="Gate Co",
        recommendation=Recommendation(suggested_premium_modification=0.0),
    )
    quote = QuoteResult(
        bundle_id="pas-ref",
        line=InsuranceLine.COMMERCIAL_PROPERTY,
        base_premium=1000,
        adjusted_premium=1000,
        eligible=True,
        policy_admin_reference="ISO-OLDREF",
        metadata={},
    )
    results = PolicyAdminService().submit_to_core_systems(bundle, memo, quote, "org-1")
    successful = [r for r in results if r.get("success")]
    assert successful
    ref = str(successful[0].get("external_reference") or "")
    assert ref
    assert ref != "ISO-OLDREF"
    assert quote.metadata.get("pas_bind_payload")


def test_csv_import_parses_serff_tracking() -> None:
    csv_text = "product_id,loss_cost,lcm,minimum_premium,filing_id\ngl,0.31,2.0,500,SERFF-GL-9\n"
    filings = filings_from_csv_text(csv_text)
    assert filings["gl"]["serff_tracking"] == "SERFF-GL-9"


def test_guidewire_payload_has_terms_not_just_premium() -> None:
    bundle = _bundle("pas")
    memo = UnderwritingMemo(
        bundle_id="pas",
        insured_name="Gate Co",
        summary="Accept with subjectivities",
        recommendation=Recommendation(suggested_premium_modification=0.0),
    )
    quote = QuoteResult(
        bundle_id="pas",
        line=InsuranceLine.COMMERCIAL_PROPERTY,
        base_premium=12000,
        adjusted_premium=11800,
        eligible=True,
        metadata={"filing_id": "SERFF-TX-001", "rating_engine": "carrier_leaf_filing", "product_id": "commercial_property"},
    )
    payload = PolicyAdminService()._build_payload(bundle, memo, quote, "org-1")
    dumped = payload.to_dict()
    assert dumped["coverages"]
    assert dumped["coverages"][0]["limit_amount"] == 2_000_000
    assert dumped["rating"]["filing_id"] == "SERFF-TX-001"
    assert dumped["locations"]
    restored = PolicySubmissionPayload.from_dict(dumped)
    assert restored.insured_name == "Gate Co"
    assert restored.rating["filing_id"] == "SERFF-TX-001"


def test_bind_from_summary_uses_captured_payload() -> None:
    summary = {
        "bundle_id": "pas",
        "insured_name": "Gate Co",
        "pas_bind_payload": {
            "bundle_id": "pas",
            "org_id": "org-1",
            "insured_name": "Gate Co",
            "adjusted_premium": 11800,
            "coverages": [{"coverage_type": "building", "limit_amount": 2_000_000, "deductible": 25_000}],
            "rating": {"filing_id": "SERFF-TX-001"},
            "subjectivities": [{"id": "inspect", "status": "open"}],
        },
        "subjectivities": [{"id": "inspect", "status": "cleared"}],
    }
    results = PolicyAdminService().bind_from_summary(summary, "GW-JOB-1", "org-1")
    assert results
    assert all("system" in r for r in results)
