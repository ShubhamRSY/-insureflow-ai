"""Honesty: live connectors vs lab stubs vs bind cutover."""

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from insureflow.ingestion.insurance.sources import LIVE_CONNECTOR_IDS, list_sources
from insureflow.pilot.sandbox_readiness import bind_cutover_checklist


def test_lab_sources_are_labeled() -> None:
    rows = list_sources(Path("examples"), hardened=False)
    by_id = {str(r["id"]): r for r in rows}
    assert by_id["pacific-coast"]["kind"] == "lab_demo"
    assert by_id["google-drive"]["kind"] == "simulated"
    assert by_id["sharepoint"]["kind"] == "simulated"
    assert by_id["ivans-download"]["kind"] == "simulated"
    assert by_id["server-folder"]["kind"] in {"live", "needs_config"}
    assert by_id["email-inbox"]["kind"] in {"live", "needs_config"}
    assert "email-inbox" in LIVE_CONNECTOR_IDS


def test_bank_hides_uncontracted_stubs() -> None:
    rows = list_sources(Path("examples"), hardened=True)
    ids = {str(r["id"]) for r in rows}
    assert "google-drive" not in ids
    assert "sharepoint" not in ids
    assert "ivans-download" not in ids
    assert "pacific-coast" not in ids
    assert "server-folder" in ids
    assert "email-inbox" in ids
    assert "s3-bucket" in ids
    assert "sftp" in ids
    assert all(r.get("kind") in {"live", "needs_config"} for r in rows)


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
