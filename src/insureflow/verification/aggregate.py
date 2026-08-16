"""Aggregation of per-document verification reports for the pipeline & API.

The loader attaches a ``VerificationReport`` to every unstructured submission.
This module rolls those up into a bundle-level summary (exception queue, issue
rollup by code, STP signal) and turns flagged documents into underwriting
findings so the pipeline can force human review instead of straight-through
processing.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission, VerificationIssue, VerificationReport


def _report(doc: UnstructuredSubmission) -> VerificationReport | None:
    return getattr(doc, "verification", None)


def aggregate_verification(bundle: SubmissionBundle) -> dict[str, Any]:
    """Roll up all per-doc verification reports into one bundle-level dict."""
    flagged_docs: list[dict[str, Any]] = []
    exception_queue: list[dict[str, Any]] = []
    issues_by_code: Counter[str] = Counter()
    error_count = 0
    warning_count = 0
    info_count = 0
    checked_docs = 0
    auto_approve_all = True

    for doc in bundle.unstructured:
        report = _report(doc)
        if report is None:
            continue
        checked_docs += 1
        auto_approve_all = auto_approve_all and report.auto_approve
        error_count += len(report.errors)
        warning_count += len(report.warnings)
        info_count += sum(1 for i in report.issues if i.severity == "info")
        for issue in report.issues:
            issues_by_code[issue.code] += 1
        if report.flagged_for_review:
            flagged_docs.append(
                {
                    "submission_id": doc.submission_id,
                    "document_type": doc.document_type,
                    "source": doc.source,
                    "issue_count": len(report.issues),
                    "checks_run": report.checks_run,
                }
            )
        for issue in report.issues:
            if issue.severity != "info":
                exception_queue.append(_issue_entry(doc, issue))

    return {
        "checked_docs": checked_docs,
        "flagged_docs": flagged_docs,
        "flagged_doc_count": len(flagged_docs),
        "exception_queue": exception_queue,
        "exception_count": len(exception_queue),
        "issues_by_code": dict(issues_by_code),
        "error_count": error_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "auto_approve": auto_approve_all,
        "straight_through_processing": bool(checked_docs and auto_approve_all and not exception_queue),
    }


def _issue_entry(doc: UnstructuredSubmission, issue: VerificationIssue) -> dict[str, Any]:
    """Serializable exception-queue entry with the source box for UI highlighting."""
    return {
        "submission_id": doc.submission_id,
        "document_type": doc.document_type,
        "code": issue.code,
        "severity": issue.severity,
        "message": issue.message,
        "field_name": issue.field_name,
        "page_number": issue.page_number,
        "bbox": issue.bbox,
    }


def verification_findings(
    bundle: SubmissionBundle,
) -> list[dict[str, Any]]:
    """Underwriting-ready findings (title/description/severity) for flagged docs."""
    findings: list[dict[str, Any]] = []
    summary = aggregate_verification(bundle)
    issues_by_code = summary["issues_by_code"]
    top_codes = ", ".join(f"{code} × {count}" for code, count in list(issues_by_code.items())[:5])
    for doc in bundle.unstructured:
        report = _report(doc)
        if report is None or not report.flagged_for_review:
            continue
        findings.append(
            {
                "title": "Extraction verification failed — human review required",
                "description": (
                    f"{doc.document_type} ({doc.submission_id}) failed layered extraction "
                    f"verification with {len(report.errors)} error(s), {len(report.warnings)} warning(s). "
                    f"Top issue codes: {top_codes or 'none'}. Do not rely on extracted figures without review."
                ),
                "severity": "high",
                "category": "data_quality",
                "evidence": [entry["submission_id"] for entry in exception_queue_for(doc)],
            }
        )
    return findings


def exception_queue_for(doc: UnstructuredSubmission) -> list[dict[str, Any]]:
    report = _report(doc)
    if report is None:
        return []
    return [_issue_entry(doc, issue) for issue in report.issues if issue.severity != "info"]


def flagged_submissions(bundle: SubmissionBundle) -> list[UnstructuredSubmission]:
    return [doc for doc in bundle.unstructured if (_report(doc) is not None and _report(doc).flagged_for_review)]


def iter_reports(bundle: SubmissionBundle) -> Iterable[tuple[UnstructuredSubmission, VerificationReport]]:
    for doc in bundle.unstructured:
        report = _report(doc)
        if report is not None:
            yield doc, report
