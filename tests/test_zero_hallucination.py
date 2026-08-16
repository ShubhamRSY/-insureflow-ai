"""Zero-hallucination gate: uncited money/limits force REFER; count must stay ≤ 0."""

from __future__ import annotations

import os

from insureflow.models.agents import Finding, RiskSeverity, UnderwritingMemo, UWDecision
from insureflow.models.submissions import (
    CoverageDetail,
    ExtractedField,
    NamedInsured,
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)
from insureflow.verification.self_consistency import critical_self_consistency_issues
from insureflow.verification.zero_hallucination import (
    enforce_zero_hallucination_on_memo,
    evaluate_zero_hallucination,
    grounded_money_set,
    scan_text_for_ungrounded_money,
)


def _bundle_with_grounded_limit() -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="zh-1",
        structured=StructuredSubmission(
            submission_id="zh-1",
            named_insured=NamedInsured(legal_name="Acme"),
            coverages=[CoverageDetail(coverage_type="GL", limit_amount=2_000_000, deductible=5_000, premium=12_000)],
        ),
        unstructured=[
            UnstructuredSubmission(
                submission_id="zh-1",
                extracted_fields={
                    "general_aggregate_limit": [
                        ExtractedField(
                            field_name="general_aggregate_limit",
                            value="$2,000,000",
                            confidence=0.99,
                            page_number=1,
                            bbox=[0.1, 0.2, 0.4, 0.25],
                            source_ref="page 1",
                        )
                    ]
                },
            )
        ],
    )


def test_grounded_money_set_includes_structured_and_cited() -> None:
    bundle = _bundle_with_grounded_limit()
    fields = bundle.unstructured[0].extracted_fields
    allowed = grounded_money_set(fields, extra_values=[2_000_000, 5000, 12000])
    assert "2000000.00" in allowed
    assert scan_text_for_ungrounded_money("Limit is $2,000,000", allowed) == []
    assert scan_text_for_ungrounded_money("Secretly $9,999,999 incurred", allowed)


def test_evaluate_fails_on_uncited_critical_field() -> None:
    os.environ["USE_ZERO_HALLUCINATION"] = "1"
    os.environ["USE_CITATION_GATE"] = "1"
    os.environ["MAX_HALLUCINATIONS"] = "0"
    bundle = SubmissionBundle(
        bundle_id="zh-2",
        unstructured=[
            UnstructuredSubmission(
                submission_id="zh-2",
                extracted_fields={
                    "total_incurred": [ExtractedField(field_name="total_incurred", value="$500,000", confidence=0.99)],
                },
            )
        ],
    )
    report = evaluate_zero_hallucination(bundle)
    assert report.hallucination_count >= 1
    assert report.passed is False
    assert report.max_allowed == 0


def test_enforce_strips_invented_money_finding_and_refers() -> None:
    os.environ["USE_ZERO_HALLUCINATION"] = "1"
    os.environ["MAX_HALLUCINATIONS"] = "0"
    bundle = _bundle_with_grounded_limit()
    memo = UnderwritingMemo(
        bundle_id="zh-1",
        decision=UWDecision.ACCEPT,
        key_findings=[
            Finding(
                title="Hidden loss",
                description="Applicant has $9,999,999 in undisclosed losses",
                severity=RiskSeverity.HIGH,
                category="fraud",
            ),
            Finding(
                title="Limit confirmed",
                description="General aggregate is $2,000,000 on the ACORD",
                severity=RiskSeverity.LOW,
                category="coverage",
            ),
        ],
    )
    report = enforce_zero_hallucination_on_memo(memo, bundle)
    assert report.passed is False
    assert memo.decision == UWDecision.REFER
    assert memo.human_review_required is True
    titles = [f.title for f in memo.key_findings]
    assert "Hidden loss" not in titles  # stripped as ungrounded money
    assert any(f.category == "hallucination" for f in memo.key_findings)


def test_enforce_passes_when_all_money_grounded() -> None:
    os.environ["USE_ZERO_HALLUCINATION"] = "1"
    os.environ["MAX_HALLUCINATIONS"] = "0"
    os.environ["USE_CITATION_GATE"] = "1"
    bundle = _bundle_with_grounded_limit()
    memo = UnderwritingMemo(
        bundle_id="zh-1",
        decision=UWDecision.ACCEPT,
        key_findings=[
            Finding(
                title="Limit confirmed",
                description="General aggregate is $2,000,000 on the ACORD",
                severity=RiskSeverity.LOW,
                category="coverage",
            ),
        ],
    )
    report = enforce_zero_hallucination_on_memo(memo, bundle)
    assert report.passed is True
    assert report.hallucination_count == 0
    assert memo.decision == UWDecision.ACCEPT


def test_critical_self_consistency_promotes_disagreement() -> None:
    os.environ["USE_SELF_CONSISTENCY"] = "1"
    fields = {
        "total_incurred": [
            ExtractedField(field_name="total_incurred", value="100000", confidence=0.9, page_number=1),
            ExtractedField(field_name="total_incurred", value="250000", confidence=0.9, page_number=4),
        ]
    }
    issues = critical_self_consistency_issues(fields)
    assert issues
    assert any(i.code == "critical_self_consistency" and i.severity == "error" for i in issues)


def test_max_hallucinations_env_zero() -> None:
    os.environ["MAX_HALLUCINATIONS"] = "0"
    from insureflow.verification.zero_hallucination import max_allowed_hallucinations

    assert max_allowed_hallucinations() == 0
