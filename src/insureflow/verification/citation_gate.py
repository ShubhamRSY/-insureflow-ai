"""Hard citation / grounding gate for underwriting extractions and memo claims.

A critical figure without a page, bbox, or source_ref is not a fact — it is a
hypothesis. This gate turns that into an error so straight-through processing
cannot swallow an uncited number. Deterministic. No LLM required.
"""

from __future__ import annotations

import os
import re
from typing import Any, Iterable, Mapping

from insureflow.models.submissions import ExtractedField, VerificationIssue
from insureflow.verification.common import SEVERITY_ERROR, SEVERITY_WARNING, uw_field

_CRITICAL_TERMS = (
    "total",
    "assets",
    "revenue",
    "incurred",
    "premium",
    "limit",
    "deductible",
    "payroll",
    "tiv",
    "replacement",
    "building_value",
    "contents_value",
    "loss",
    "claim",
    "emod",
    "mod_factor",
)

_MONEY_RE = re.compile(r"[$€£]?\s*-?\d[\d,]*(?:\.\d+)?")


def citation_gate_enabled() -> bool:
    raw = os.getenv("USE_CITATION_GATE", "1").strip().lower()
    return raw not in {"0", "false", "off", "no", "none"}


def is_grounded(field: ExtractedField) -> bool:
    """True when the field can point at a page, box, or explicit source ref."""
    if field.page_number is not None:
        return True
    if field.bbox and len(field.bbox) >= 4:
        return True
    if (field.source_ref or "").strip():
        return True
    return False


def _is_critical(key: str, value: str) -> bool:
    key_l = (key or "").lower()
    if any(term in key_l for term in _CRITICAL_TERMS):
        return True
    # Any dollar/euro/pound figure is critical for the zero-hallucination bar.
    if re.search(r"(?:USD|US\$|\$|€|£)\s*-?\d", value or "", re.I):
        return True
    if re.search(r"\d{1,3}(?:,\d{3})+", value or ""):
        return True
    return bool(_MONEY_RE.search(value or "")) and any(tok in key_l for tok in ("amount", "value", "cost", "price", "limit"))


def citation_issues(
    fields: Mapping[str, list[ExtractedField]],
    *,
    require_critical: bool = True,
) -> list[VerificationIssue]:
    """Flag ungrounded critical fields. Soft-warn on other ungrounded values."""
    if not citation_gate_enabled():
        return []
    issues: list[VerificationIssue] = []
    for key, entries in fields.items():
        if not entries:
            continue
        field = entries[0]
        value = (field.value or "").strip()
        if not value:
            continue
        if is_grounded(field):
            continue
        critical = require_critical and _is_critical(key, value)
        issues.append(
            VerificationIssue(
                code="uncited_claim" if critical else "ungrounded_field",
                severity=SEVERITY_ERROR if critical else SEVERITY_WARNING,
                message=(
                    f"{uw_field(key)} of {value} cannot be traced to a page in the submitted documents — "
                    + ("do not rely on this figure until supporting paperwork is received and matched" if critical else "route to manual review")
                ),
                field_name=key,
                page_number=field.page_number,
                bbox=field.bbox,
            )
        )
    return issues


def gate_memo_claims(
    claims: Iterable[Mapping[str, Any]],
    grounded_keys: Iterable[str] | None = None,
) -> list[VerificationIssue]:
    """Gate free-form memo assertions that name a field without a grounded key.

    ``claims`` entries may carry ``field_name``, ``title``, ``description``,
    and optional ``page_number`` / ``bbox`` / ``source_ref``.
    """
    if not citation_gate_enabled():
        return []
    allowed = {k.lower() for k in (grounded_keys or [])}
    issues: list[VerificationIssue] = []
    for claim in claims:
        page = claim.get("page_number")
        bbox = claim.get("bbox")
        source_ref = (claim.get("source_ref") or "").strip()
        if page is not None or (bbox and len(bbox) >= 4) or source_ref:
            continue
        field_name = str(claim.get("field_name") or claim.get("field_path") or "").strip()
        title = str(claim.get("title") or "")
        description = str(claim.get("description") or "")
        blob = f"{field_name} {title} {description}".lower()
        if field_name and field_name.lower() in allowed:
            continue
        if not any(term in blob for term in _CRITICAL_TERMS) and not _MONEY_RE.search(blob):
            continue
        issues.append(
            VerificationIssue(
                code="memo_uncited_claim",
                severity=SEVERITY_ERROR,
                message=(f"Memo claim {title or field_name or description[:60]!r} cannot point at a page — do not treat as fact"),
                field_name=field_name,
            )
        )
    return issues


def grounded_field_keys(fields: Mapping[str, list[ExtractedField]]) -> list[str]:
    return [k for k, entries in fields.items() if entries and is_grounded(entries[0])]
