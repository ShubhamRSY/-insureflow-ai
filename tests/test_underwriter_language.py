"""Underwriter-language reporting: findings, memo text, and PDF must be desk-ready.

Guards against engineering jargon (hallucination / bbox / citation / CV / STP /
issue codes) leaking into underwriter-facing surfaces.
"""

from __future__ import annotations

from insureflow.agents.compliance_agent import ComplianceAgent
from insureflow.agents.loss_run_analyst import LossRunAnalystAgent
from insureflow.models.submissions import (
    ExtractedField,
    NamedInsured,
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)
from insureflow.rating.report_document import (
    generate_memo_report_html,
    uw_finding_description,
    uw_finding_title,
)
from insureflow.underwriting.memo_sync import build_memo_summary
from insureflow.underwriting.sanctions_gate import screen_submission
from insureflow.verification.aggregate import verification_findings
from insureflow.verification.citation_gate import citation_issues
from insureflow.verification.common import uw_field
from insureflow.verification.uncertainty import uncertainty_issues
from insureflow.verification.zero_hallucination import HallucinationHit

_JARGON = (
    "hallucination",
    "bbox",
    "hypothesis",
    "citation gate",
    "ungrounded_field",
    "uncited_claim",
    "extraction pass",
    "CV ",
)


def _assert_no_jargon(text: str) -> None:
    low = (text or "").lower()
    for term in _JARGON:
        assert term.lower() not in low, f"jargon {term!r} leaked into: {text!r}"


# ── Field-key humanizer ───────────────────────────────────────────────────────


def test_uw_field_strips_engine_prefixes_and_underscores() -> None:
    assert uw_field("spacy.amount") == "stated amount"
    assert uw_field("face_amount") == "face amount"
    assert uw_field("llm.total_incurred") == "total incurred"
    assert uw_field("") == "the value"


# ── Citation gate ─────────────────────────────────────────────────────────────


def test_citation_issue_message_is_desk_ready() -> None:
    fields = {
        "spacy.amount": [ExtractedField(field_name="spacy.amount", value="750000", confidence=0.9)],
    }
    issues = citation_issues(fields)
    assert issues, "critical ungrounded field must be flagged"
    msg = issues[0].message
    _assert_no_jargon(msg)
    assert "stated amount of 750000" in msg
    assert "supporting paperwork" in msg


# ── Uncertainty (self-consistency) ────────────────────────────────────────────


def test_uncertainty_message_is_desk_ready() -> None:
    issues = uncertainty_issues({"face_amount": 0.676})
    assert issues
    msg = issues[0].message
    _assert_no_jargon(msg)
    assert "did not read consistently" in msg
    assert "68%" in msg or "67%" in msg


# ── Zero-hallucination finding ────────────────────────────────────────────────


def test_hallucination_hit_finding_reads_in_underwriter_language() -> None:
    hit = HallucinationHit(
        code="uncited_claim",
        message="face_amount='750000' has no page/bbox/source citation — blocks STP; treat as hypothesis until grounded",
        field_name="face_amount",
        claim_text="face_amount='750000'",
    )
    finding = hit.to_finding()
    _assert_no_jargon(finding.title)
    assert "documentation" in finding.description.lower()
    # uw_message path used for the description
    assert "paperwork" in finding.description.lower() or "documents" in finding.description.lower()


# ── Verification aggregation ──────────────────────────────────────────────────


def test_verification_findings_are_desk_ready() -> None:
    from insureflow.models.submissions import VerificationIssue, VerificationReport

    issues = [
        VerificationIssue(code="uncited_claim", severity="error", message="x", field_name="face_amount"),
        *[VerificationIssue(code="ungrounded_field", severity="warning", message="y", field_name=f"f{i}") for i in range(4)],
    ]
    doc = UnstructuredSubmission(
        submission_id="d-1",
        document_type="life_application",
        extracted_fields={},
        verification=VerificationReport(passed=False, auto_approve=False, flagged_for_review=True, checks_run=["layered"], issues=issues),
    )
    bundle = SubmissionBundle(bundle_id="b-1", unstructured=[doc])
    findings = verification_findings(bundle)
    assert len(findings) == 1
    title, desc = findings[0]["title"], findings[0]["description"]
    _assert_no_jargon(title + " " + desc)
    assert "manual review" in title.lower()
    assert "life application" in desc.lower()


# ── Sanctions gate ────────────────────────────────────────────────────────────


def test_sanctions_finding_without_insured_is_desk_ready() -> None:
    bundle = SubmissionBundle(bundle_id="s-1")
    result = screen_submission(bundle)
    assert result.findings
    f = result.findings[0]
    _assert_no_jargon(f"{f.title} {f.description}")
    assert "named insured" in f.title.lower()
    assert "legal name" in f.description.lower()


# ── Missing-document agents ───────────────────────────────────────────────────


def test_loss_run_analyst_missing_data_is_desk_ready() -> None:
    bundle = SubmissionBundle(bundle_id="lr-1")
    agent = LossRunAnalystAgent()
    agent._analyze(bundle)
    assert agent._findings
    text = f"{agent._findings[0].title} {agent._findings[0].description}"
    _assert_no_jargon(text)
    assert "loss run" in text.lower()


def test_compliance_agent_missing_coverage_is_desk_ready() -> None:
    bundle = SubmissionBundle(
        bundle_id="c-1",
        structured=StructuredSubmission(submission_id="c-1", named_insured=NamedInsured(legal_name="X")),
    )
    agent = ComplianceAgent()
    agent._analyze(bundle)
    coverage_findings = [f for f in agent._findings if "coverage" in (f.title or "").lower()]
    assert coverage_findings
    text = f"{coverage_findings[0].title} {coverage_findings[0].description}"
    _assert_no_jargon(text)


# ── Memo summary ──────────────────────────────────────────────────────────────


def test_memo_summary_risk_line_has_no_stray_period_and_steps_are_desk_ready() -> None:
    from insureflow.models.agents import Finding, RiskSeverity, UWDecision

    findings = [
        Finding(title="MIB check not performed", description="order bureau report", severity=RiskSeverity.HIGH),
        Finding(title="Sanctions screening incomplete", description="no named insured", severity=RiskSeverity.HIGH),
        Finding(title="Extraction verification failed — human review required", description="...", severity=RiskSeverity.HIGH),
    ]
    summary = build_memo_summary(UWDecision.REFER, 0.8, findings)
    assert "findings (0 critical, 3 high).\n" not in summary  # no stray trailing period
    next_section = summary.split("What to do next")[-1]
    assert "Order an MIB report" in next_section
    assert "sanctions screening" in next_section.lower()
    assert "source paperwork" in next_section.lower() or "verify against source paperwork" in next_section.lower()


# ── Report document ───────────────────────────────────────────────────────────


_SAMPLE_MEMO = """================================================================================
                       UNDERWRITING EVALUATION MEMO
================================================================================
CASE ID / POLICY #: LT-2026-8942-SY              DATE: August 20, 2026
PRODUCT TYPE: Level Term Life Insurance (20-Year)   FACE AMOUNT: $1,500,000
================================================================================

1. APPLICANT IDENTIFICATION & SUBMISSION CHECKLIST (ACORD 100)
--------------------------------------------------------------------------------
  Gov-Issued Photo ID: Verified (Pass)

2. FINAL UNDERWRITING DECISION & DISPOSITION
--------------------------------------------------------------------------------
[X] ISSUE AS APPLIED (Preferred Plus, Level 20-Year Term)
[ ] DECLINE

Underwriter Signature: ___________________________   Date: 08/20/2026
"""


def test_memo_report_html_renders_template_sections() -> None:
    html = generate_memo_report_html({"memo_text": _SAMPLE_MEMO}, "job-1", "August 20, 2026")
    assert html is not None
    assert "Underwriting Evaluation Memo" in html
    assert "APPLICANT IDENTIFICATION" in html.upper()
    assert "ISSUE AS APPLIED" in html
    assert "&#9745;" in html and "&#9744;" in html  # checked / unchecked boxes
    assert "CASE ID / POLICY #" in html


def test_memo_report_html_returns_none_without_memo_text() -> None:
    assert generate_memo_report_html({}, "job-1", "now") is None
    assert generate_memo_report_html({"memo_text": "not a memo"}, "job-1", "now") is None


def test_report_finding_translations() -> None:
    assert uw_finding_title("Hallucination blocked — uncited claim") == ("Unverified figure — supporting documentation required")
    assert uw_finding_title("MIB no-hit (uploaded codes absent)") == "MIB check not performed — order bureau report"
    assert uw_finding_title("OFAC: no named insured to screen") == ("Sanctions screening incomplete — no named insured on file")
    desc = uw_finding_description("face_amount='750000' has no page/bbox/source citation — blocks STP; treat as hypothesis until grounded")
    _assert_no_jargon(desc)
    assert "supporting paperwork" in desc
