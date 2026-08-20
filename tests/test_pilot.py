"""Pilot sandbox readiness + package intake."""

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from insureflow.pilot.package_loader import discover_pilot_packages, export_scenario_as_pilot_package, load_pilot_package, run_pilot_package
from insureflow.pilot.sandbox_readiness import assess_sandbox_readiness, bind_is_allowed, is_ready_mode, is_shadow_mode, operating_mode


def test_sandbox_readiness_report_structure(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("CLUE_API_KEY", raising=False)
    monkeypatch.setenv("GUIDEWIRE_API_KEY", "")
    monkeypatch.setenv("OPERATING_MODE", "shadow")
    monkeypatch.setenv("PILOT_SHADOW_MODE", "true")
    report = assess_sandbox_readiness(ping=False)
    assert report["overall"] in {"not_ready", "pilot_shadow_ready", "pilot_ready", "pilot_live_ready"}
    assert "feeds" in report and len(report["feeds"]) >= 5
    assert "checklist" in report
    assert "partner_ask" in report
    assert report["shadow_mode"] is True
    assert report["ready_mode"] is False
    assert report["operating_mode"] == "shadow"


def test_infra_ready_marks_shadow_ready(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pilot_packages" / "demo" / "x").mkdir(parents=True)
    (tmp_path / "pilot_packages" / "demo" / "x" / "acord.xml").write_text("<ACORD/>", encoding="utf-8")
    monkeypatch.setenv("OPERATING_MODE", "shadow")
    monkeypatch.setenv("PILOT_SHADOW_MODE", "true")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENCRYPTION_KEY", "test-encryption-key-not-for-prod")
    monkeypatch.setenv("INTEGRATION_GATEWAY_API_KEY", "pilot-gateway-key-not-dev-placeholder")
    monkeypatch.delenv("CLUE_API_KEY", raising=False)
    monkeypatch.delenv("APLUS_API_KEY", raising=False)
    monkeypatch.delenv("GUIDEWIRE_API_KEY", raising=False)
    report = assess_sandbox_readiness(ping=False)
    assert report["overall"] == "pilot_shadow_ready"
    assert report["shadow_mode"] is True


def test_ready_mode_defaults_and_bind_gate(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("OPERATING_MODE", raising=False)
    monkeypatch.delenv("PILOT_SHADOW_MODE", raising=False)
    monkeypatch.setenv("GUIDEWIRE_API_KEY", "")
    monkeypatch.setenv("GUIDEWIRE_API_URL", "")
    monkeypatch.setenv("BRITECORE_API_KEY", "")
    monkeypatch.setenv("BRITECORE_API_URL", "")
    assert operating_mode() == "ready"
    assert is_ready_mode() is True
    assert is_shadow_mode() is False
    assert bind_is_allowed() is False

    monkeypatch.setenv("GUIDEWIRE_API_KEY", "live-key-not-dev-placeholder-xxxxxx")
    monkeypatch.setenv("GUIDEWIRE_API_URL", "https://example.com/gw")
    assert bind_is_allowed() is True

    monkeypatch.setenv("GUIDEWIRE_API_URL", "https://integrations.rytera.ai/policy/guidewire/v1")
    assert bind_is_allowed() is False
    monkeypatch.setenv("GUIDEWIRE_API_URL", "https://example.com/gw")

    monkeypatch.setenv("OPERATING_MODE", "shadow")
    assert is_shadow_mode() is True
    assert bind_is_allowed() is False


def test_infra_ready_marks_ready_when_pas_configured(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pilot_packages" / "demo" / "x").mkdir(parents=True)
    (tmp_path / "pilot_packages" / "demo" / "x" / "acord.xml").write_text("<ACORD/>", encoding="utf-8")
    monkeypatch.setenv("OPERATING_MODE", "ready")
    monkeypatch.setenv("PILOT_SHADOW_MODE", "false")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENCRYPTION_KEY", "test-encryption-key-not-for-prod")
    monkeypatch.setenv("INTEGRATION_GATEWAY_API_KEY", "pilot-gateway-key-not-dev-placeholder")
    monkeypatch.setenv("GUIDEWIRE_API_KEY", "live-gw-key-not-dev-placeholder")
    monkeypatch.setenv("GUIDEWIRE_API_URL", "https://example.com/gw")
    monkeypatch.delenv("CLUE_API_KEY", raising=False)
    monkeypatch.delenv("APLUS_API_KEY", raising=False)
    report = assess_sandbox_readiness(ping=False)
    assert report["overall"] == "pilot_ready"
    assert report["ready_mode"] is True
    assert report["bind_allowed"] is True


def test_export_and_run_pilot_package(tmp_path: Path) -> None:
    dest = tmp_path / "coastal"
    export_scenario_as_pilot_package("coastal_fl_appetite_decline", dest)
    assert (dest / "acord.xml").exists()
    assert (dest / "meta.json").exists()
    pkg = load_pilot_package(dest, partner="test")
    assert pkg.acord_xml
    result = run_pilot_package(pkg, org_id="pytest-pilot", shadow=True, use_llm=False)
    assert result["ai_decision"] == "decline"
    assert result["pilot"]["shadow_mode"] is True
    assert result["pilot"]["bind_allowed"] is False


def test_pii_gate_blocks_ssn(tmp_path: Path) -> None:
    from insureflow.pilot.package_loader import PilotPackage
    from insureflow.pilot.pii_gate import scan_pilot_package

    pkg = PilotPackage(
        partner="t",
        submission_id="ssn",
        path=tmp_path,
        acord_xml="<ACORD>SSN 123-45-6789</ACORD>",
        loss_run="clean",
    )
    scan = scan_pilot_package(pkg)
    assert scan["ok_to_run"] is False
    assert scan["blocking_count"] >= 1


def test_calibration_store(tmp_path: Path) -> None:
    from insureflow.pilot.calibration import PilotCalibrationStore, PilotRunRecord

    store = PilotCalibrationStore(path=tmp_path / "cal.jsonl")
    store.record(
        PilotRunRecord(
            partner="demo",
            submission_id="a",
            bundle_id="b1",
            ai_decision="decline",
            expected_decision="decline",
            decision_match=True,
        )
    )
    store.record(
        PilotRunRecord(
            partner="demo",
            submission_id="b",
            bundle_id="b2",
            ai_decision="refer",
            expected_decision="decline",
            decision_match=False,
        )
    )
    summary = store.summarize()
    assert summary["sample_size"] == 2
    assert summary["labeled_sample_size"] == 2
    assert summary["match_rate"] == 0.5


def test_auto_redact_clears_blocking_ssn(tmp_path: Path) -> None:
    from insureflow.pilot.auto_redact import redact_pilot_package
    from insureflow.pilot.package_loader import load_pilot_package
    from insureflow.pilot.pii_gate import scan_pilot_package

    dest = tmp_path / "pkg"
    dest.mkdir()
    (dest / "acord.xml").write_text("<ACORD>Named Insured SSN 123-45-6789</ACORD>", encoding="utf-8")
    (dest / "loss_run.md").write_text("Contact broker@agency.com — no losses", encoding="utf-8")
    pkg = load_pilot_package(dest, partner="t")
    assert scan_pilot_package(pkg)["ok_to_run"] is False

    result = redact_pilot_package(pkg, inplace=True)
    assert result["ok_to_run"] is True
    assert result["after"]["blocking_count"] == 0
    text = (dest / "acord.xml").read_text(encoding="utf-8")
    assert "123-45-6789" not in text
    # Broker email is warn-only and should remain
    assert "broker@agency.com" in (dest / "loss_run.md").read_text(encoding="utf-8")


def test_email_documents_to_pilot_package(tmp_path: Path) -> None:
    from insureflow.pilot.email_intake import documents_to_pilot_package

    result = documents_to_pilot_package(
        [
            {
                "filename": "Acord_125.xml",
                "content": "<ACORD><InsuredName>Riverside Plaza</InsuredName></ACORD>",
                "encoding": "utf-8",
            },
            {"filename": "loss_run.md", "content": "3yr loss free", "encoding": "utf-8"},
        ],
        partner="broker-co",
        submission_id="email-42",
        root=tmp_path,
        auto_redact=True,
    )
    assert result["has_acord"] is True
    assert (tmp_path / "broker-co" / "email-42" / "acord.xml").exists()
    found = discover_pilot_packages(tmp_path)
    assert any(p.submission_id == "email-42" for p in found)
