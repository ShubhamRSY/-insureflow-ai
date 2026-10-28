"""Honesty: live connectors vs lab stubs vs bind cutover."""

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from insureflow.ingestion.insurance.sources import LIVE_CONNECTOR_IDS, list_sources
from insureflow.pilot.sandbox_readiness import bind_cutover_checklist


def test_lab_sources_are_labeled() -> None:
    rows = list_sources(Path("examples"), hardened=False)
    by_id = {str(r["id"]) for r in rows}
    assert "pacific-coast" in by_id
    assert "server-folder" in by_id
    assert "email-inbox" in by_id
    assert "google-drive" in by_id
    assert "outlook-inbox" in by_id


def test_live_vs_stub_connector_honesty() -> None:
    rows = list_sources(Path("examples"), hardened=False)
    by_id = {str(r["id"]): r for r in rows}

    # Always-on live filesystem connector
    assert by_id["server-folder"]["kind"] == "live"
    assert by_id["server-folder"]["configured"] is True

    # Real pull adapters without env credentials → needs_config
    for sid in ("email-inbox", "outlook-inbox", "s3-bucket", "sftp"):
        assert sid in LIVE_CONNECTOR_IDS
        assert by_id[sid]["kind"] == "needs_config", f"{sid} should need creds when unset"
        assert by_id[sid]["configured"] is False

    # Catalog stubs must not claim to be live vendor feeds
    for sid in (
        "google-drive",
        "sharepoint",
        "azure-blob",
        "box",
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
        "bold-penguin",
        "docusign",
        "microsoft-teams",
        "slack-intake",
        "snowflake",
    ):
        assert by_id[sid]["kind"] == "catalog_stub", f"{sid} should be catalog_stub"
        assert by_id[sid]["configured"] is False
        assert "not contracted" in str(by_id[sid]["honesty"]).lower()


def test_bind_cutover_not_ready_in_shadow(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("OPERATING_MODE", "shadow")
    monkeypatch.setenv("GUIDEWIRE_API_KEY", "")
    monkeypatch.setenv("GUIDEWIRE_API_URL", "")
    monkeypatch.setenv("BRITECORE_API_KEY", "")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    cut = bind_cutover_checklist()
    assert cut["bind_allowed"] is False
    assert cut["cutover_ready"] is False
    assert cut["system_of_record"] == "customer_pas"
    ids = {s["id"]: s for s in cut["steps"]}
    assert ids["shadow_off"]["done"] is False
    assert ids["not_sor"]["done"] is True
    assert ids["uw_hitl"]["done"] is True
    assert "import_carrier_filings" in ids["carrier_book"]["note"]
    assert cut["carrier_book"]["is_customer_book"] is False


def test_bind_cutover_rejects_localhost_pas_as_dev_gateway(monkeypatch: MonkeyPatch) -> None:
    """The bundled local integration gateway (127.0.0.1:8002) is a real,
    reachable HTTP server that returns live-shaped responses on purpose —
    exactly what .env.example ships for local dev. Pointing Guidewire/
    BriteCore at it must never be mistaken for a genuine live PAS, or
    `bind_allowed` would lie about being ready to bind against a real
    carrier system."""
    monkeypatch.setenv("OPERATING_MODE", "ready")
    monkeypatch.setenv("GUIDEWIRE_API_KEY", "rytera-pilot-test-key-not-real")
    monkeypatch.setenv("GUIDEWIRE_API_URL", "http://127.0.0.1:8002/integrations/policy/guidewire/v1")
    monkeypatch.setenv("BRITECORE_API_KEY", "")
    monkeypatch.setenv("BRITECORE_API_URL", "")
    cut = bind_cutover_checklist()
    ids = {s["id"]: s for s in cut["steps"]}
    assert ids["pas_live"]["done"] is False
    assert cut["bind_allowed"] is False


def test_bind_cutover_rejects_pilot_prefixed_oracle_keys(monkeypatch: MonkeyPatch) -> None:
    """Same class of gap for CLUE/A-PLUS: a rytera-pilot-* key against the
    local gateway must not count as a 'live oracle' either."""
    monkeypatch.setenv("CLUE_API_KEY", "rytera-pilot-test-key-not-real")
    monkeypatch.setenv("CLUE_API_URL", "http://127.0.0.1:8002/integrations/oracles/clue/v2")
    monkeypatch.setenv("APLUS_API_KEY", "")
    monkeypatch.setenv("APLUS_API_URL", "")
    cut = bind_cutover_checklist()
    ids = {s["id"]: s for s in cut["steps"]}
    assert ids["one_oracle"]["done"] is False


def test_bind_cutover_accepts_a_genuine_external_pas_url(monkeypatch: MonkeyPatch) -> None:
    """Sanity check the fix isn't overly broad — a real-looking external
    vendor URL with a non-placeholder key must still pass."""
    monkeypatch.setenv("OPERATING_MODE", "ready")
    monkeypatch.setenv("GUIDEWIRE_API_KEY", "test-key-not-real-00")
    monkeypatch.setenv("GUIDEWIRE_API_URL", "https://api.guidewire-carrier.example.com/policy/v1")
    monkeypatch.setenv("BRITECORE_API_KEY", "")
    monkeypatch.setenv("BRITECORE_API_URL", "")
    cut = bind_cutover_checklist()
    ids = {s["id"]: s for s in cut["steps"]}
    assert ids["pas_live"]["done"] is True
    assert cut["bind_allowed"] is True


def test_sandbox_status_includes_cutover(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("OPERATING_MODE", "shadow")
    from insureflow.pilot.sandbox_readiness import assess_sandbox_readiness

    report = assess_sandbox_readiness(ping=False)
    assert "bind_cutover" in report
    assert report["honesty"]["system_of_record"] == "customer_pas"
    intake = [f for f in report["feeds"] if f["category"] == "intake"]
    assert len(intake) == 3
