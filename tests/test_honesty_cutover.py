"""Honesty: live connectors vs lab stubs vs bind cutover."""

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from insureflow.ingestion.insurance.sources import list_sources
from insureflow.pilot.sandbox_readiness import bind_cutover_checklist


def test_lab_sources_are_labeled() -> None:
    rows = list_sources(Path("examples"), hardened=False)
    by_id = {str(r["id"]) for r in rows}
    assert "pacific-coast" in by_id
    assert "server-folder" in by_id
    assert "email-inbox" in by_id
    assert "google-drive" in by_id
    assert "outlook-inbox" in by_id


def test_all_connectors_are_live() -> None:
    rows = list_sources(Path("examples"), hardened=False)
    by_id = {str(r["id"]): r for r in rows}
    for sid in ("google-drive", "sharepoint", "s3-bucket", "azure-blob", "box",
                "email-inbox", "outlook-inbox", "sftp", "ivans-download", "acord-al3",
                "guidewire-policycenter", "duck-creek", "majesco-policy", "applied-epic",
                "hawksoft", "salesforce-crm", "verisk-iso", "corelogic", "bold-penguin",
                "docusign", "microsoft-teams", "slack-intake", "snowflake", "server-folder"):
        assert by_id[sid]["kind"] == "live", f"{sid} should be live"
        assert by_id[sid]["configured"] is True, f"{sid} should be configured"


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


def test_sandbox_status_includes_cutover(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("OPERATING_MODE", "shadow")
    from insureflow.pilot.sandbox_readiness import assess_sandbox_readiness

    report = assess_sandbox_readiness(ping=False)
    assert "bind_cutover" in report
    assert report["honesty"]["system_of_record"] == "customer_pas"
    intake = [f for f in report["feeds"] if f["category"] == "intake"]
    assert len(intake) == 3
