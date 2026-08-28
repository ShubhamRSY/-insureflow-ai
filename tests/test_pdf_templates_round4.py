"""Regression tests for the round-4 Quote/Report PDF template fixes."""

from __future__ import annotations

import re
from typing import Any

from insureflow.models.agents import Finding, Recommendation, RiskSeverity, UnderwritingMemo, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.rating.quote_document import generate_quote_html
from insureflow.rating.report_document import CONFIDENCE_LEGEND, generate_report_html
from insureflow.underwriting.memo_sync import build_memo_summary


def _life_results(**overrides: Any) -> dict[str, Any]:
    base = {
        "insurance_line": "life",
        "insured_name": "Priya Nair",
        "assigned_to": None,
        "memo": {
            "decision": "refer",
            "insured_name": "Priya Nair",
            "overall_risk_score": 0.77,
            "overall_risk_severity": "high",
            "recommendation": {"action": "refer", "conditions": []},
            "risk_analyst_findings": [],
            "compliance_findings": [],
            "key_findings": [
                {"title": "MIB check not performed", "description": "x", "severity": "high", "category": "mib"},
                {"title": "Sanctions screening incomplete", "description": "x", "severity": "high", "category": "sanctions"},
                {"title": "Elevated aggregate risk score", "description": "x", "severity": "high", "category": "uw_decision"},
            ],
        },
        "quote": {"base_premium": 1000.0, "adjusted_premium": 900.0},
        "quote_full": {
            "base_premium": 1000.0,
            "adjusted_premium": 900.0,
            "policy_admin_reference": "GU-1",
            "metadata": {"insurance_line": "life", "personal_lines": True, "face_amount": 750000},
            "schedule_modifications": [
                {"name": "underwriting_class", "amount": 0.82, "basis": "preferred", "modifier_pct": 0},
                {"name": "mortality_per_1000", "amount": 1.5, "basis": "age=42/female", "modifier_pct": 0},
            ],
        },
    }
    base.update(overrides)
    return base


def test_decision_logic_gate_counts_match_canonical_findings_list() -> None:
    """Round-4 item #1: the Decision Logic gate counts must be derived from
    the same key_findings list the page displays, not the separate
    per-agent finding buckets (which miss pipeline-level findings like
    MIB/sanctions that get merged into key_findings later)."""
    html = generate_report_html(_life_results(), "demo-test")

    i = html.find("Decision Logic")
    section = html[i : i + 800]
    # 2 compliance-category findings (mib, sanctions) are in key_findings —
    # the gate count must reflect that, not "0 finding(s)".
    assert 'Compliance gate</span><span class="kv-value">2 finding(s)' in section
    assert "NO FINDINGS" not in section.split("Compliance gate")[1][:100]


def test_what_to_do_next_uses_manual_numbering_not_native_ol() -> None:
    """Round-4 item #2: WeasyPrint has a pagination bug where a native <ol>
    counter can bleed into an unrelated later block as empty numbered
    markers. This list must use manually-numbered flex rows instead."""
    memo_summary = build_memo_summary(UWDecision.REFER, 0.77, [Finding(title="X", description="y", severity=RiskSeverity.HIGH, category="risk")])
    results = _life_results()
    results["memo"]["summary"] = memo_summary

    html = generate_report_html(results, "demo-test")
    assert "<ol" not in html
    assert re.search(r"<span[^>]*>1\.</span><span>[^<]+</span>", html) or "1." in html


def test_title_and_headline_never_render_missing_identity_string() -> None:
    """Round-4 item #3: the page title/headline must always be a fixed
    string, never the "Named insured not provided" data-field fallback."""
    results = _life_results(insured_name="")
    results["memo"]["insured_name"] = ""
    results["named_insured"] = None

    html = generate_report_html(results, "demo-test")
    title_match = re.search(r"<title>(.*?)</title>", html)
    h1_match = re.search(r"<h1>(.*?)</h1>", html)
    assert title_match is not None
    assert h1_match is not None
    title = title_match.group(1)
    h1 = h1_match.group(1)

    assert "not provided" not in title.lower()
    assert "not provided" not in h1.lower()


def test_premium_breakdown_has_applied_to_and_adjustment_columns() -> None:
    """Round-4 item #4: the Report's Premium Breakdown table must show the
    same 4 columns as the in-app Premium Build-up table, with the same
    derived adjustment percentages (single source of truth)."""
    html = generate_report_html(_life_results(), "demo-test")

    assert "Applied To" in html
    assert "Rating Component" in html
    i = html.find("Premium Breakdown")
    section = html[i : i + 1200]
    assert "preferred" in section  # basis for underwriting_class
    assert "-18.0%" in section  # derived adjustment for 0.82 factor
    assert "age=42/female" in section  # basis for mortality_per_1000
    assert "n/a" in section  # mortality_per_1000 has no meaningful % swing


def test_quote_premium_breakdown_wraps_rows_in_table() -> None:
    """Round-4 item #4, Quote side — regression guard for the exact bug
    class fixed in an earlier round: bare <tr> fragments with no enclosing
    <table> render as one run-on line in some viewers."""
    bundle = SubmissionBundle(bundle_id="b1", structured=None)
    memo = UnderwritingMemo(bundle_id="b1", insured_name="Test", decision=UWDecision.REFER, recommendation=Recommendation(action="refer"))
    quote = QuoteResult(
        bundle_id="b1",
        line=InsuranceLine.LIFE,
        base_premium=1000.0,
        adjusted_premium=900.0,
        schedule_modifications=[RateComponent(name="underwriting_class", amount=0.82, basis="preferred")],
        metadata={"insurance_line": "life", "face_amount": 750000},
    )
    html = generate_quote_html(bundle, memo, quote)

    assert "Applied To" in html
    assert "<table" in html and "preferred" in html
    depth = 0
    for tag in re.findall(r"<table[ >]|</table>|<tr>", html):
        if tag.startswith("<table"):
            depth += 1
        elif tag == "</table>":
            depth -= 1
        elif tag == "<tr>":
            assert depth > 0, "Found a <tr> not inside any <table>"


def test_findings_count_breakdown_includes_all_severities() -> None:
    """Round-4 item #5: the summary line's severity breakdown must sum to
    the total findings count — silently dropping moderate/low findings
    from the parenthetical (while still counting them in the total) was
    the bug ("6 findings (1 critical, 3 high)" for 1+3=4 != 6)."""
    findings = [
        Finding(title="a", description="x", severity=RiskSeverity.CRITICAL, category="risk"),
        Finding(title="b", description="x", severity=RiskSeverity.HIGH, category="risk"),
        Finding(title="c", description="x", severity=RiskSeverity.HIGH, category="risk"),
        Finding(title="d", description="x", severity=RiskSeverity.MODERATE, category="risk"),
        Finding(title="e", description="x", severity=RiskSeverity.LOW, category="risk"),
    ]
    text = build_memo_summary(UWDecision.REFER, 0.6, findings)

    m = re.search(r"(\d+) findings \(([^)]+)\)", text)
    assert m is not None
    total = int(m.group(1))
    breakdown = m.group(2)
    counted = sum(int(n) for n in re.findall(r"(\d+) \w+", breakdown))
    assert total == len(findings) == counted
    assert "1 critical" in breakdown
    assert "2 high" in breakdown
    assert "1 moderate" in breakdown
    assert "1 low" in breakdown


def test_underwriter_of_record_field_present() -> None:
    """Round-4 item #6."""
    html_unassigned = generate_report_html(_life_results(assigned_to=None), "demo-test")
    assert "Underwriter of Record" in html_unassigned
    assert "Unassigned" in html_unassigned

    html_assigned = generate_report_html(_life_results(assigned_to="jane@carrier.com"), "demo-test")
    assert "jane@carrier.com" in html_assigned


def test_confidence_legend_present_near_key_findings() -> None:
    """Round-4 item #7."""
    html = generate_report_html(_life_results(), "demo-test")
    assert CONFIDENCE_LEGEND in html
    assert html.find(CONFIDENCE_LEGEND) > html.find("Key Findings")


def test_risk_legend_sits_under_risk_score_not_after_doc_completeness() -> None:
    """Round-4 item #8: the risk score legend must render inside the Risk
    Score stat card, before Doc Completeness — not after it."""
    html = generate_report_html(_life_results(), "demo-test")
    risk_score_idx = html.find("Risk Score</div>")
    legend_idx = html.find("Risk Score Scale:")
    doc_completeness_idx = html.find("Doc Completeness")
    assert risk_score_idx < legend_idx < doc_completeness_idx


def test_quote_and_report_identity_banners_describe_same_gaps() -> None:
    """Round-4 item #9: both PDFs must describe an identity gap identically
    (same set of missing fields, same phrasing), not one document naming
    only 'named insured' while the other lists all three gaps."""
    bundle = SubmissionBundle(bundle_id="b1", structured=None)
    memo = UnderwritingMemo(bundle_id="b1", insured_name="", decision=UWDecision.REFER, recommendation=Recommendation(action="refer"))
    quote = QuoteResult(
        bundle_id="b1",
        line=InsuranceLine.LIFE,
        base_premium=1000.0,
        adjusted_premium=900.0,
        metadata={"insurance_line": "life"},
    )
    quote_html = generate_quote_html(bundle, memo, quote)

    report_results = _life_results(insured_name="")
    report_results["memo"]["insured_name"] = ""
    report_results["named_insured"] = None
    report_html = generate_report_html(report_results, "demo-test")

    for doc_html in (quote_html, report_html):
        assert "date of birth" in doc_html.lower()
        assert "state of residence" in doc_html.lower()
        assert "named insured" in doc_html.lower()
