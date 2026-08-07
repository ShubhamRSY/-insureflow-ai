"""Broker notify + structured UW memo summary."""

from __future__ import annotations

from pathlib import Path

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.notifications.broker_notify import compose_document_request, notify_broker_document_request
from insureflow.underwriting.memo_sync import build_memo_summary


def test_compose_document_request_includes_docs_and_link() -> None:
    subject, body = compose_document_request(
        insured_name="Pacific Coast Distributors, Inc.",
        bundle_id="job-123",
        documents=["Loss run", "SOV"],
        notes="Need 5-year history",
        share_url="https://app.example/dashboard/broker/status/brk-abc",
        broker_name="Summit Brokerage",
    )
    assert "Pacific Coast" in subject
    assert "Loss run" in body
    assert "SOV" in body
    assert "brk-abc" in body
    assert "Summit" in body


def test_notify_writes_outbox_without_smtp(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BROKER_EMAIL_OUTBOX", str(tmp_path / "outbox"))
    monkeypatch.delenv("SMTP_HOST", raising=False)
    result = notify_broker_document_request(
        to_email="broker@example.com",
        insured_name="Test Co",
        bundle_id="job-9",
        documents=["Inspection report"],
        share_url="https://app.example/dashboard/broker/status/brk-x",
    )
    assert result["sent"] is False
    assert result["mode"] == "outbox"
    assert result["mailto"].startswith("mailto:broker@example.com")
    assert Path(result["outbox_path"]).exists()


def test_memo_summary_is_structured_and_actionable() -> None:
    findings = [
        Finding(
            title="Loss run provided but empty — no claims extracted",
            description="Attached loss run parsed zero claims",
            severity=RiskSeverity.CRITICAL,
            category="data_quality",
        ),
        Finding(
            title="Inadequate Commercial General Liability limit",
            description="Limit is 58% of TIV",
            severity=RiskSeverity.HIGH,
            category="limit_adequacy",
        ),
    ]
    text = build_memo_summary(UWDecision.REFER, 0.75, findings)
    assert "DECISION: REFER" in text
    assert "Why this decision" in text
    assert "What to do next" in text
    assert "Loss run" in text
    assert "Risk score: 75/100" in text
    assert "\n" in text
