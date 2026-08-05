"""Tests for memo narrative sync and LOB-aware report/checklist."""

from __future__ import annotations

from insureflow.insurance.package_checklist import detect_lob, package_checklist
from insureflow.models.agents import Finding, Recommendation, RiskSeverity, UnderwritingMemo, UWDecision
from insureflow.rating.report_document import generate_report_html
from insureflow.underwriting.memo_sync import resync_memo_narrative, worst_decision


def test_worst_decision_prefers_decline() -> None:
    assert worst_decision(UWDecision.ACCEPT, UWDecision.DECLINE) == UWDecision.DECLINE
    assert worst_decision(UWDecision.ACCEPT, UWDecision.REFER) == UWDecision.REFER
    assert worst_decision(UWDecision.CONDITIONAL_ACCEPT, UWDecision.ACCEPT) == UWDecision.CONDITIONAL_ACCEPT


def test_resync_aligns_summary_with_decision() -> None:
    memo = UnderwritingMemo(
        bundle_id="b1",
        insured_name="Test",
        decision=UWDecision.ACCEPT,
        overall_risk_score=1.0,
        summary="Underwriting recommendation is DECLINE based on stale text.",
        key_findings=[
            Finding(title="Missing Data", description="No ACORD", severity=RiskSeverity.CRITICAL),
            Finding(title="Missing Data", description="No ACORD", severity=RiskSeverity.CRITICAL),
        ],
        recommendation=Recommendation(action="decline", rationale="stale"),
    )
    memo.decision = UWDecision.DECLINE
    resync_memo_narrative(memo)
    assert memo.decision == UWDecision.DECLINE
    assert "DECLINE" in memo.summary
    assert "ACCEPT" not in memo.summary.split("based on")[0]
    assert memo.recommendation is not None
    assert memo.recommendation.action == "decline"
    assert len(memo.key_findings) == 1  # deduped


def test_detect_lob_life_from_hint() -> None:
    assert detect_lob("", "life") == "life"
    checklist = package_checklist(["life_application"], lob="life")
    assert checklist["lob"] == "life"
    assert "Life application" in checklist["present"]
    assert "Auto application" not in checklist["missing"]


def test_report_action_matches_decision_badge() -> None:
    html = generate_report_html(
        {
            "ai_decision": "decline",
            "insurance_line": "life",
            "insured_name": "Ada Life",
            "memo": {
                "decision": "decline",
                "summary": "Underwriting recommendation is DECLINE based on 2 findings.",
                "overall_risk_score": 1.0,
                "overall_risk_severity": "critical",
                "key_findings": [
                    {"title": "Missing Data", "description": "x", "severity": "critical", "category": "compliance"},
                    {"title": "Missing Data", "description": "x", "severity": "critical", "category": "compliance"},
                ],
                "recommendation": {"action": "accept", "conditions": []},
            },
            "quote": {"base_premium": 1000, "adjusted_premium": 823},
            "quote_full": {
                "base_premium": 1000,
                "adjusted_premium": 823,
                "metadata": {
                    "insurance_line": "life",
                    "personal_lines": True,
                    "filing_id": "RYT-LIFE-2026-01",
                    "medical": {"underwriting_class": "preferred", "tobacco": False},
                    "face_amount": 750000,
                },
                "schedule_modifications": [],
            },
        },
        "demo-test",
    )
    assert "DECLINE" in html
    # Stale recommendation.action must not win over ai_decision
    assert ">ACCEPT<" not in html.replace(" ", "")
    assert "Life Rating" in html or "UW Class" in html
    assert "COPE Schedule" not in html
    assert html.count("Missing Data") == 1  # deduped in findings section
