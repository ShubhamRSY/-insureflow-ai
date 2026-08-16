"""Layer 3 — structural, range & format guardrails.

Stops impossible or improbable values before they reach the underwriting engine:

- **Range checks**: domain bounds (DTI in [0,1], credit score in [300,850], ...)
  plus a blanket "non-negative" rule for financial magnitudes.
- **Regex & pattern checks**: deterministic validators for EINs, SSNs, ABA
  routing numbers (including the mod-10 checksum), policy numbers and dates —
  catching structural OCR errors like ``S``→``5`` or ``O``→``0``.
- **Schema validation**: strict typing — counts/quantities must be integers,
  currency/ratio fields must be numeric, dates must parse.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Iterable, Mapping

from insureflow.models.submissions import ExtractedField, VerificationIssue
from insureflow.verification.common import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    make_issue,
    to_number,
)

_EIN_RE = re.compile(r"^\d{2}-?\d{7}$")
_SSN_RE = re.compile(r"^\d{3}-?\d{2}-?\d{4}$")
_ROUTING_RE = re.compile(r"^\d{9}$")
_POLICY_RE = re.compile(r"^[A-Z]{1,8}[-\s]?\d{4,14}$|^\d{6,20}$")
_DATE_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_SLASH_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")

# (field name pattern, low, high)
_RANGE_SPECS: list[tuple[re.Pattern[str], float, float]] = [
    (re.compile(r"credit_score|fico", re.IGNORECASE), 300.0, 850.0),
    (re.compile(r"debt_to_income|\bdti\b", re.IGNORECASE), 0.0, 1.0),
    (re.compile(r"loan_to_value|\bltv\b", re.IGNORECASE), 0.0, 1.0),
    (re.compile(r"occupancy_rate|occupancy_pct", re.IGNORECASE), 0.0, 1.0),
    (re.compile(r"interest_rate", re.IGNORECASE), 0.0, 1.0),
    (re.compile(r"loss_ratio|combined_ratio", re.IGNORECASE), 0.0, 5.0),
    (re.compile(r"tax_rate", re.IGNORECASE), 0.0, 1.0),
]

# Financial magnitudes that can never legitimately be negative.
_NON_NEGATIVE_TERMS = (
    "total",
    "assets",
    "revenue",
    "premium",
    "value",
    "incurred",
    "limit",
    "amount",
    "salary",
    "income",
    "equity",
    "liab",
    "reserve",
    "payroll",
)

_COUNT_TERMS = ("count", "_num", "number_of", "quantity", "policies", "claims")
_CURRENCY_TERMS = (
    "value",
    "amount",
    "premium",
    "limit",
    "incurred",
    "revenue",
    "assets",
    "liab",
    "equity",
    "salary",
    "income",
    "reserve",
    "payroll",
    "deductible",
)
_RATIO_TERMS = ("ratio", "_pct", "percent", "rate")


def _fmt(value: float) -> str:
    return f"{value:g}"


def range_checks(fields: Mapping[str, Iterable[ExtractedField]]) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    for key, entries in fields.items():
        if not entries:
            continue
        value = entries[0].value
        num = to_number(value)
        if num is None:
            continue
        lower = key.lower()
        for pattern, lo, hi in _RANGE_SPECS:
            if pattern.search(lower) and not (lo <= num <= hi):
                issues.append(
                    make_issue(
                        "range_bound",
                        SEVERITY_ERROR,
                        f"{key}={_fmt(num)} out of valid range [{_fmt(lo)}, {_fmt(hi)}]",
                        fields,
                        key,
                    )
                )
        if any(term in lower for term in _NON_NEGATIVE_TERMS) and num < 0:
            issues.append(
                make_issue(
                    "negative_value",
                    SEVERITY_ERROR,
                    f"{key}={_fmt(num)} cannot be negative for a financial magnitude",
                    fields,
                    key,
                )
            )
    return issues


def _aba_checksum_ok(digits: str) -> bool:
    d = [int(c) for c in digits]
    return (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])) % 10 == 0


def pattern_checks(fields: Mapping[str, Iterable[ExtractedField]]) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    for key, entries in fields.items():
        if not entries:
            continue
        value = entries[0].value.strip()
        lower = key.lower()
        if not value:
            continue

        if "ein" in lower or ("tax" in lower and "id" in lower):
            if not _EIN_RE.match(value):
                issues.append(
                    make_issue(
                        "ein_format",
                        SEVERITY_ERROR,
                        f"{key}={value!r} is not a valid EIN (expects NN-NNNNNNN)",
                        fields,
                        key,
                    )
                )
        if "ssn" in lower or "social_security" in lower:
            if not _SSN_RE.match(value):
                issues.append(
                    make_issue(
                        "ssn_format",
                        SEVERITY_ERROR,
                        f"{key}={value!r} is not a valid SSN",
                        fields,
                        key,
                    )
                )
        if "routing" in lower or "aba" in lower or "bank_identifier" in lower:
            digits = re.sub(r"[^0-9]", "", value)
            if not _ROUTING_RE.match(digits) or not _aba_checksum_ok(digits):
                issues.append(
                    make_issue(
                        "aba_checksum",
                        SEVERITY_ERROR,
                        f"{key}={value!r} failed the ABA routing-number checksum",
                        fields,
                        key,
                    )
                )
        if "policy" in lower and "number" in lower:
            if not _POLICY_RE.match(value):
                issues.append(
                    make_issue(
                        "policy_format",
                        SEVERITY_WARNING,
                        f"{key}={value!r} does not look like a standard policy number "
                        "(possible OCR confusion of S/5, O/0, I/1)",
                        fields,
                        key,
                    )
                )
        if "date" in lower or "period" in lower:
            if value:
                if not (_DATE_ISO_RE.match(value) or _DATE_SLASH_RE.match(value)):
                    issues.append(
                        make_issue(
                            "date_format",
                            SEVERITY_ERROR,
                            f"{key}={value!r} is not a parseable date (expects ISO YYYY-MM-DD or MM/DD/YYYY)",
                            fields,
                            key,
                        )
                    )
                elif _DATE_SLASH_RE.match(value):
                    try:
                        datetime.strptime(value, "%m/%d/%Y")
                    except ValueError:
                        issues.append(
                            make_issue("date_format", SEVERITY_ERROR, f"{key}={value!r} is an impossible date", fields, key)
                        )
    return issues


def schema_validation(fields: Mapping[str, Iterable[ExtractedField]]) -> list[VerificationIssue]:
    """Strict typing: counts must be integers, currency/ratios numeric, dates real."""
    issues: list[VerificationIssue] = []
    for key, entries in fields.items():
        if not entries:
            continue
        value = entries[0].value.strip()
        lower = key.lower()
        if not value:
            continue
        if any(term in lower for term in _COUNT_TERMS):
            digits = re.sub(r"[^0-9-]", "", value)
            if digits and not digits.isdigit():
                issues.append(
                    make_issue(
                        "schema_type",
                        SEVERITY_ERROR,
                        f"{key}={value!r} must be an integer count",
                        fields,
                        key,
                    )
                )
        if any(term in lower for term in _RATIO_TERMS):
            if to_number(value) is None:
                issues.append(
                    make_issue(
                        "schema_type",
                        SEVERITY_ERROR,
                        f"{key}={value!r} must be a numeric ratio/percent",
                        fields,
                        key,
                    )
                )
        if any(term in lower for term in _CURRENCY_TERMS):
            if to_number(value) is None:
                issues.append(
                    make_issue(
                        "schema_type",
                        SEVERITY_ERROR,
                        f"{key}={value!r} must be a numeric currency value",
                        fields,
                        key,
                    )
                )
        if ("date" in lower or "period" in lower) and value:
            parsed = _try_parse_date(value)
            if parsed is None:
                issues.append(
                    make_issue(
                        "schema_type",
                        SEVERITY_ERROR,
                        f"{key}={value!r} must be an ISO or US date",
                        fields,
                        key,
                    )
                )
    return issues


def _try_parse_date(value: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
