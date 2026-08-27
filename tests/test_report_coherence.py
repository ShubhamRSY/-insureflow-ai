"""Tests for memo narrative sync and LOB-aware report/checklist."""

from __future__ import annotations

import re

from insureflow.insurance.package_checklist import detect_lob, package_checklist
from insureflow.models.agents import Finding, Recommendation, RiskSeverity, UnderwritingMemo, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.rating.quote_document import generate_quote_html
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


def _life_schedule_mods() -> list[RateComponent]:
    return [
        RateComponent(name="mortality_per_1000", amount=1.5),
        RateComponent(name="underwriting_class", amount=0.82),
        RateComponent(name="sex_factor", amount=0.88),
    ]


def test_report_and_quote_render_identical_life_factors() -> None:
    """Regression guard for the bug where the Report showed 0.0% for every life
    rating factor (missing an is_life/amount fallback that the Quote already
    had) — same job, same schedule_modifications, must render the same values.
    """
    memo = UnderwritingMemo(
        bundle_id="b1",
        insured_name="Parity Test Insured",
        decision=UWDecision.REFER,
        overall_risk_score=0.5,
        overall_risk_severity=RiskSeverity.MODERATE,
        recommendation=Recommendation(action="refer"),
    )
    quote = QuoteResult(
        bundle_id="b1",
        line=InsuranceLine.LIFE,
        base_premium=1125.0,
        adjusted_premium=823.09,
        schedule_modifications=_life_schedule_mods(),
        metadata={"insurance_line": "life", "personal_lines": True, "face_amount": 750000},
    )
    bundle = SubmissionBundle(bundle_id="b1", structured=None)

    quote_html = generate_quote_html(bundle, memo, quote)

    results = {
        "insurance_line": "life",
        "insured_name": "Parity Test Insured",
        "memo": {
            "decision": "refer",
            "overall_risk_score": 0.5,
            "overall_risk_severity": "moderate",
            "recommendation": {"action": "refer"},
        },
        "quote": {"base_premium": 1125.0, "adjusted_premium": 823.09},
        "quote_full": {
            "base_premium": 1125.0,
            "adjusted_premium": 823.09,
            "metadata": {"insurance_line": "life", "personal_lines": True, "face_amount": 750000},
            "schedule_modifications": [
                {"name": mod.name, "amount": mod.amount, "modifier_pct": mod.modifier_pct} for mod in _life_schedule_mods()
            ],
        },
    }
    report_html = generate_report_html(results, "demo-parity-test")

    def factor_values(html: str) -> dict[str, str]:
        # Matches both the Quote's <div class='row'> pairs and the Report's <tr><td> pairs.
        found = {}
        for label, value in re.findall(r"Mortality Per 1000</span>\s*<span[^>]*>([^<]+)|Mortality Per 1000</td><td[^>]*>([^<]+)", html):
            found["mortality_per_1000"] = label or value
        for label, value in re.findall(r"Underwriting Class</span>\s*<span[^>]*>([^<]+)|Underwriting Class</td><td[^>]*>([^<]+)", html):
            found["underwriting_class"] = label or value
        return found

    quote_values = factor_values(quote_html)
    report_values = factor_values(report_html)

    assert quote_values == {"mortality_per_1000": "1.5", "underwriting_class": "0.82"}
    assert report_values == quote_values, (
        f"Report and Quote must render identical factor values for the same job: "
        f"quote={quote_values!r} report={report_values!r}"
    )
    # No bare, unwrapped <tr> in the Quote's factor list (markup bug regression guard)
    assert re.search(r"<div class=\"card\">\s*<div class=\"row\">.*?<tr>", quote_html, re.DOTALL) is None
