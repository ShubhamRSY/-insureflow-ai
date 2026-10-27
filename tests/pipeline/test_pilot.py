"""T-027 C1–C6: assist-only guards, per-value confirmation, labels, logs and failed-write visibility.

No model calls. Every write goes to a temp sandbox.
"""

from __future__ import annotations

import json
from pathlib import Path

import llm_extract
import package
import pilot
import prepare
import pytest
import quotes
import workbench


def run_payload(submission: str = "SUB-990", status: str = "complete") -> dict:
    fields = [
        {"field_id": "named_insured", "value": "Example LLC", "confidence": "high", "source": "application.md", "quote": "Named Insured: Example LLC"},
        {"field_id": "premises_address", "value": "100 Main St", "confidence": "high", "source": "application.md", "quote": "100 Main St"},
        {"field_id": "effective_date", "value": "2026-01-01", "confidence": "high", "source": "application.md", "quote": "2026-01-01"},
        {"field_id": "operations", "value": "general office work", "confidence": "high", "source": "application.md", "quote": "Operations: general office work"},
        {"field_id": "construction", "value": "masonry", "confidence": "high", "source": "application.md", "quote": "Construction: masonry"},
        {"field_id": "sales_or_payroll", "value": "500000", "confidence": "high", "source": "application.md", "quote": "Sales: 500000"},
    ]
    payload = {
        "submission": submission, "status": status, "complete": status == "complete",
        "conflicts": [], "needs_human": [], "sprinklers": None, "fields": fields,
        "scope": {"version": "scope-v4", "in_scope": True, "reasons": []},
    }
    payload["hash_algorithm"] = prepare.HASH_ALGORITHM
    payload["saved_hash"] = prepare.hash_payload(payload)
    return payload


@pytest.fixture
def box(tmp_path: Path, monkeypatch):
    """A pilot-mode sandbox with one in-scope saved run, restored after the test."""
    monkeypatch.setenv("PILOT_MODE", pilot.ASSIST_ONLY)
    names = ("PAGE", "LOG", "INBOX", "PENDING", "TO_PRODUCER", "TO_CARRIER", "BANNER")
    before = {name: getattr(workbench, name) for name in names}
    before_other = (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES,
                    quotes.TO_CARRIER, quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR,
                    llm_extract.CACHE, pilot.CORRECTIONS, pilot.EVENTS)
    workbench.sandbox(tmp_path / "box")
    try:
        folder = workbench.INBOX / "SUB-990"
        folder.mkdir(parents=True)
        (folder / "application.md").write_text(
            "Named Insured: Example LLC\nPremises: 100 Main St\nEffective Date: 2026-01-01\n"
            "Construction: masonry\nOperations: general office work\nSales: 500000\n"
        )
        prepare.EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
        (prepare.EXTRACT_DIR / "SUB-990.json").write_text(json.dumps(run_payload()))
        yield tmp_path / "box"
    finally:
        for name, value in before.items():
            setattr(workbench, name, value)
        (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES,
         quotes.TO_CARRIER, quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR,
         llm_extract.CACHE, pilot.CORRECTIONS, pilot.EVENTS) = before_other


def test_mode_defaults_off_and_refuses_an_unknown_value(monkeypatch):
    monkeypatch.delenv("PILOT_MODE", raising=False)
    assert pilot.mode() == "" and not pilot.active()
    monkeypatch.setenv("PILOT_MODE", "assist")
    with pytest.raises(ValueError, match="not a known pilot mode"):
        pilot.mode()


def test_c1_send_and_package_are_refused_for_every_actor(box):
    for actor in ("user", "account-manager", "UW-001"):
        with pytest.raises(ValueError, match="assist-only pilot: send disabled"):
            package.send_to_carrier("SUB-990", actor, box / "out", user_line="send to carrier SUB-990")
    with pytest.raises(ValueError, match="assist-only pilot: send disabled"):
        package.build_package("SUB-990")
    assert not (workbench.TO_CARRIER / "SUB-990.md").exists()


def test_c2_drafts_and_producer_requests_are_refused(box):
    with pytest.raises(ValueError, match="missing-info drafts and producer requests are disabled"):
        prepare.approve(workbench.PENDING / "SUB-990.md", "user", workbench.TO_PRODUCER, "please send")
    assert not (workbench.TO_PRODUCER / "SUB-990.md").exists()


def test_c1_confirm_needs_every_value_and_never_makes_the_file_sendable(box):
    assert not workbench.act("/decision", {"submission": "SUB-990", "underwriter_id": "user", "action": "approve", "reason": "ok"})[1]
    sub, ok, text = workbench.act("/decision", {"submission": "SUB-990", "underwriter_id": "user", "action": "confirm", "ack": ["named_insured"]})
    assert not ok and "confirm every value before recording: premises_address" in text
    sub, ok, text = workbench.act("/decision", {"submission": "SUB-990", "underwriter_id": "user", "action": "confirm",
                                                "ack": [
                                                    "named_insured", "premises_address", "effective_date",
                                                    "operations", "construction", "sales_or_payroll",
                                                ]})
    assert ok, text
    row = json.loads(workbench.LOG.read_text().splitlines()[-1])
    assert row["action"] == "confirm" and row["bound"] is False and row["sent_to_carrier"] is False
    assert len(row["acknowledged"]) == 6 and row["confirmed_values"]["operations"] == "general office work"
    assert not any(r.get("action") == "approve" for r in package.decisions("SUB-990", workbench.LOG))


def test_c3_c6_labels_scope_and_warning_are_on_the_card(box):
    page = workbench.render(workbench.load_queue(), None)
    card = page[page.index('<article id="SUB-990">'):]
    assert "ASSIST-ONLY PILOT — AI proposals only" in page
    assert "<b>Scope check:</b> in pilot scope (scope scope-v4)" in card
    assert "AI proposal — verify against the source" in card
    assert "Suggestion only — not a decision" in card
    assert "operations 9/20" in card and "loss runs 5/20" in card and "T-117" in card and "not approved" in card
    assert "<option>confirm</option>" in card and "<option>approve</option>" not in card
    assert "No send: assist-only pilot — send disabled for SUB-990" in card and 'action="/send"' not in card
    form = card[card.index('action="/decision"'):card.index("</form>", card.index('action="/decision"'))]
    for field in ("named_insured", "premises_address", "effective_date", "operations", "construction", "sales_or_payroll"):
        assert f'value="{field}"' in form, field


def test_c5_edit_is_logged_and_shown_read_only(box):
    sub, ok, text = workbench.act("/decision", {"submission": "SUB-990", "underwriter_id": "user", "action": "edit",
                                                "field_id": "operations", "new_value": "general office only",
                                                "reason": "the cited page says office only"})
    assert ok, text
    rows = pilot.corrections_for("SUB-990")
    assert len(rows) == 1
    assert (rows[0]["field"], rows[0]["suggested"], rows[0]["final"], rows[0]["reason"]) == (
        "operations", "general office work", "general office only", "the cited page says office only")
    page = workbench.render(workbench.load_queue(), None)
    card = page[page.index('<article id="SUB-990">'):]
    assert "<h3>Corrections</h3>" in card and "the cited page says office only" in card and 'action="/corrections"' not in card
    summary = pilot.summary(workbench.load_queue())
    assert summary["corrections"] == 1 and summary["per_field"] == {"operations": 1}
    assert "Pilot monitor" in page and "Edits per field: operations: 1" in page


def test_c5_every_confirmed_value_is_logged_and_the_rate_is_per_field(box):
    sub, ok, text = workbench.act("/decision", {"submission": "SUB-990", "underwriter_id": "user", "action": "edit",
                                                "field_id": "operations", "new_value": "general office only",
                                                "reason": "the cited page says office only"})
    assert ok, text
    sub, ok, text = workbench.act("/decision", {"submission": "SUB-990", "underwriter_id": "user", "action": "confirm",
                                                "ack": ["named_insured", "premises_address", "effective_date",
                                                        "operations", "construction", "sales_or_payroll"]})
    assert ok, text
    rows = pilot.corrections_for("SUB-990")
    confirms = [r for r in rows if r["kind"] == "confirm"]
    assert len(confirms) == 6, "one row per confirmed value, edited or not"
    assert len([r for r in rows if r["kind"] == "edit"]) == 1
    by_field = {r["field"]: r for r in confirms}
    assert by_field["operations"]["suggested"] == "general office work"
    assert by_field["operations"]["final"] == "general office only", "the value the underwriter stands behind"
    assert by_field["operations"]["corrected"] is True
    assert by_field["named_insured"]["suggested"] == by_field["named_insured"]["final"] == "Example LLC"
    assert by_field["named_insured"]["corrected"] is False
    assert by_field["named_insured"]["reason"] == "checked against the cited text"
    assert by_field["named_insured"]["actor"] == "user"
    decisions = [json.loads(line) for line in workbench.LOG.read_text().splitlines()]
    assert len([r for r in decisions if r.get("action") == "confirm"]) == 1, "one decision; six pilot rows"
    s = pilot.summary(workbench.load_queue())
    assert s["confirmations"] == 6
    assert s["corrections"] == 1, "the edit row; the confirmations are counted apart"
    assert s["per_field_confirmations"]["operations"] == 1 and s["per_field_confirmations"]["named_insured"] == 1
    assert s["per_field_corrected"]["operations"] == 1
    assert s["correction_rate"]["operations"] == 100
    assert s["correction_rate"]["named_insured"] == 0
    page = workbench.render(workbench.load_queue(), None)
    assert "Confirmations per field: named_insured: 1" in page
    assert "tiv_building: 0" in page
    assert "Correction rate per field (corrected ÷ confirmed):" in page
    assert "operations: 100% (1 of 1 confirmed values corrected)" in page
    assert "named_insured: 0% (0 of 1 confirmed values corrected)" in page
    assert "tiv_building: no confirmations yet" in page, "a field nobody confirmed is never hidden"
    card = page[page.index('<article id="SUB-990">'):]
    assert "confirmed" in card and "checked against the cited text" in card
    assert "the value the underwriter stands behind" in card, "the table says what AI said and Final mean"


def test_c5_a_confirmation_without_an_edit_is_still_logged(box):
    sub, ok, text = workbench.act("/decision", {"submission": "SUB-990", "underwriter_id": "user", "action": "confirm",
                                                "ack": ["named_insured", "premises_address", "effective_date",
                                                        "operations", "construction", "sales_or_payroll"]})
    assert ok, text
    confirms = [r for r in pilot.corrections_for("SUB-990") if r["kind"] == "confirm"]
    assert len(confirms) == 6
    assert all(r["corrected"] is False for r in confirms)
    s = pilot.summary(workbench.load_queue())
    assert s["confirmations"] == 6 and s["corrections"] == 0
    assert s["correction_rate"] == {f: 0 for f in ("construction", "effective_date", "named_insured",
                                                   "operations", "premises_address", "sales_or_payroll")}


def test_c5_refusal_is_logged_and_a_failed_log_is_visible(box, monkeypatch):
    sub, ok, text = workbench.act("/decision", {"submission": "SUB-990", "underwriter_id": "user", "action": "approve", "reason": "ok"})
    assert not ok and "assist-only pilot: approve is disabled" in text
    assert pilot.summary(workbench.load_queue())["refusals"] == 1

    def no_fsync(fd):
        raise OSError("disk full")

    monkeypatch.setattr(workbench.os, "fsync", no_fsync)
    sub, ok, text = workbench.act("/decision", {"submission": "SUB-990", "underwriter_id": "user", "action": "decline", "reason": "not a fit"})
    assert not ok and "disk full" in text, "B-191 item 2: a failed log write is never silent"


def test_c6_warning_names_both_runs_and_the_veto():
    text = pilot.warning_text()
    assert "operations 9/20" in text and "loss runs 5/20" in text
    assert "operations 13/20" in text and "loss runs 16/20" in text and "KEEP" in text


def test_c5_display_log_row_carries_the_run_hash_and_model(box):
    report = prepare.read_saved_run("SUB-990")
    pilot.record_event(action="view", submission="SUB-990", actor="user", outcome="view",
                       message="prompt=759b3e6bc9b2 model=qwen/qwen3.8-27b", run_hash=report["saved_hash"])
    row = json.loads(pilot.EVENTS.read_text().splitlines()[-1])
    assert row["action"] == "view" and row["actor"] == "user" and row["run_hash"] == report["saved_hash"]
    assert "prompt=759b3e6bc9b2" in row["message"] and "model=" in row["message"]
