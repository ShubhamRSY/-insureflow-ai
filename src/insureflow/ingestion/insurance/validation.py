"""Extraction validation pass.

After regex and LLM extraction land on a bundle, we run a deterministic
sanity pass over the extracted field values. The pass does not mutate the
bundle; it returns a list of issue dicts that the pipeline surfaces in the
result payload and the underwriting memo:

    {"field", "document_type", "issue", "severity", "detail"}

Severity is either "error" (the value cannot plausibly be right) or "warning"
(the value is unusual but possibly legitimate, e.g. a metric/imperial mix).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from insureflow.ingestion.insurance.value_normalizers import normalize_amount, normalize_date
from insureflow.models.submissions import SubmissionBundle

_FLOAT_FIELDS = frozenset(
    {
        "face_amount",
        "premium",
        "income_amount",
        "funding_amount",
        "outstanding_balance",
        "account_value",
        "rider_benefit",
        "allocation_percent",
        "weight",
    }
)
_MIN_POSITIVE_FIELDS = frozenset(
    {
        "face_amount",
        "premium",
        "income_amount",
    }
)
_NON_NEGATIVE_FIELDS = frozenset(
    {
        "funding_amount",
        "outstanding_balance",
        "account_value",
        "rider_benefit",
    }
)
_CONFLICT_SENSITIVE_FIELDS = frozenset(
    {
        "insured_name",
        "full_name",
        "dob",
        "face_amount",
        "premium",
        "policy_number",
        "employer",
        "income_amount",
        "beneficiary_name",
    }
)
_MULTIVALUED_FIELDS = frozenset(
    {
        "survey.mismatches",
        "excel.sov_versions",
    }
)
_DATE_FIELDS = frozenset({"dob", "date_of_birth", "effective_date", "expiration_date"})


def _to_float(value: Any) -> float | None:
    try:
        return float(normalize_amount(str(value)))
    except (TypeError, ValueError):
        return None


def _lax_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _parse_iso_or_raw(value: str) -> datetime | None:
    normalized = normalize_date(value)
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    return None


def validate_extraction(bundle: SubmissionBundle) -> list[dict[str, Any]]:
    """Run the extraction sanity pass over a bundle and return issue dicts."""
    issues: list[dict[str, Any]] = []

    allocations: list[float] = []
    all_fields: dict[str, list[tuple[str, str]]] = {}

    for doc in bundle.unstructured:
        doc_type = doc.document_type or doc.source or "unstructured"
        for key, field_list in (doc.extracted_fields or {}).items():
            for ef in field_list:
                value = str(ef.value)
                all_fields.setdefault(key, []).append((doc_type, value))
                if key == "allocation_percent":
                    parsed = _to_float(value)
                    if parsed is not None:
                        allocations.append(parsed)
                if key in _FLOAT_FIELDS:
                    _check_numeric_range(key, value, doc_type, issues)
                elif key in _DATE_FIELDS:
                    _check_date(key, value, doc_type, issues)

    _check_allocations(allocations, issues)
    _check_conflicts(all_fields, issues)
    return issues


def _add_issue(
    issues: list[dict[str, Any]],
    field: str,
    doc_type: str,
    issue: str,
    severity: str,
    detail: str,
) -> None:
    issues.append(
        {
            "field": field,
            "document_type": doc_type,
            "issue": issue,
            "severity": severity,
            "detail": detail,
        }
    )


def _check_numeric_range(field: str, value: str, doc_type: str, issues: list[dict[str, Any]]) -> None:
    parsed = _to_float(value)
    if parsed is None:
        _add_issue(issues, field, doc_type, "non_numeric_value", "warning", f"'{value}' is not a numeric value")
        return

    if field in _MIN_POSITIVE_FIELDS and parsed <= 0:
        _add_issue(issues, field, doc_type, "non_positive_value", "error", f"{field} must be greater than 0, got '{value}'")
    elif field in _NON_NEGATIVE_FIELDS and parsed < 0:
        _add_issue(issues, field, doc_type, "negative_value", "warning", f"{field} should not be negative, got '{value}'")
    elif field == "allocation_percent" and (parsed < 0 or parsed > 100):
        _add_issue(issues, field, doc_type, "out_of_range", "error", f"allocation_percent must be 0-100, got '{value}'")
    elif field == "weight" and (parsed < 30 or parsed > 1000):
        _add_issue(issues, field, doc_type, "out_of_range", "warning", f"weight is implausible (30-1000 expected), got '{value}'")


def _check_date(field: str, value: str, doc_type: str, issues: list[dict[str, Any]]) -> None:
    parsed = _parse_iso_or_raw(value)
    if parsed is None:
        _add_issue(issues, field, doc_type, "unparseable_date", "warning", f"'{value}' is not a recognizable date")
        return
    today = datetime.now()
    if parsed.date() > today.date():
        _add_issue(issues, field, doc_type, "future_date", "error", f"{field} '{value}' is in the future")
    elif field == "dob":
        age = today.year - parsed.year
        if age > 120:
            _add_issue(issues, field, doc_type, "implausible_age", "warning", f"dob '{value}' implies age {age}")


def _check_allocations(allocations: list[float], issues: list[dict[str, Any]]) -> None:
    if not allocations:
        return
    total = sum(allocations)
    if total > 100:
        _add_issue(issues, "allocation_percent", "beneficiary_form", "allocation_sum_exceeds_100", "error", f"beneficiary allocations sum to {total:g}%")
    elif total < 100:
        _add_issue(issues, "allocation_percent", "beneficiary_form", "allocation_sum_below_100", "warning", f"beneficiary allocations sum to {total:g}%")


def _check_conflicts(all_fields: dict[str, list[tuple[str, str]]], issues: list[dict[str, Any]]) -> None:
    for key, entries in all_fields.items():
        if key in _MULTIVALUED_FIELDS:
            continue
        if key not in _CONFLICT_SENSITIVE_FIELDS:
            continue
        distinct: dict[str, str] = {}
        for doc_type, value in entries:
            distinct.setdefault(_lax_key(value), f"{doc_type}: {value}")
        if len(distinct) > 1:
            pairs = " | ".join(sorted(distinct.values()))
            _add_issue(issues, key, ", ".join(doc for doc, _ in entries), "conflicting_values", "warning", f"multiple different values for {key}: {pairs}")


def severity_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0}
    for issue in issues:
        counts[issue.get("severity", "warning")] = counts.get(issue.get("severity", "warning"), 0) + 1
    return counts
