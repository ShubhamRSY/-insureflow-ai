"""Shared helpers for the verification layers: issue construction, numeric
parsing, env toggles, and per-field source-location lookup for HITL UIs."""

from __future__ import annotations

import os
import re
from typing import Mapping, Sequence

from insureflow.models.submissions import ExtractedField, VerificationIssue

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"

_NUM_RE = re.compile(r"^[+-]?\d[\d,]*\.?\d*$")


def verification_enabled() -> bool:
    raw = os.getenv("USE_VERIFICATION", "1").strip().lower()
    return raw not in {"0", "false", "off", "no", "none"}


def to_number(value: str) -> float | None:
    """Loose currency/number parse; returns None when not numeric."""
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    if not cleaned or not _NUM_RE.match(cleaned):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def numeric_fields(fields: Mapping[str, Sequence[ExtractedField]]) -> dict[str, float]:
    """First numeric value per field key."""
    out: dict[str, float] = {}
    for key, entries in fields.items():
        if not entries:
            continue
        num = to_number(entries[0].value)
        if num is not None:
            out[key] = num
    return out


def location_of(fields: Mapping[str, Sequence[ExtractedField]], key: str) -> tuple[int | None, list[float] | None]:
    """Look up (page_number, bbox) for a field so issues can cite the source box."""
    entries = fields.get(key) or []
    if not entries:
        return None, None
    field = entries[0]
    return field.page_number, field.bbox


def make_issue(
    code: str,
    severity: str,
    message: str,
    fields: Mapping[str, Sequence[ExtractedField]] | None = None,
    field_name: str = "",
) -> VerificationIssue:
    page, bbox = None, None
    if fields is not None and field_name:
        page, bbox = location_of(fields, field_name)
    return VerificationIssue(
        code=code,
        severity=severity,
        message=message,
        field_name=field_name,
        page_number=page,
        bbox=bbox,
    )
