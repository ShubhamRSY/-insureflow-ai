"""Layer 2 — multi-agent verification & self-correction (critic patterns).

Two patterns:

- **Extraction-critique loop**: Agent A extracted the fields; a second agent
  (the Critic) is handed the raw source snippet *and* the extracted JSON and its
  only job is line-by-line grounding — did each value actually appear in the
  source, and at the stated location? Ungrounded/contradicted values become
  issues. Critic review is opt-in (``USE_CRITIC_REVIEW``) and needs an LLM.
- **Dual-model consensus**: run two distinct engines (e.g. OCR-based parser and
  a VLM) over the same document; numeric divergence beyond a relative tolerance
  routes the field to the exception queue (``consensus_divergence`` issues).

Both are degradation-safe: no LLM / no second engine → clean, no exception.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Mapping

from insureflow.models.submissions import ExtractedField, VerificationIssue
from insureflow.verification.common import SEVERITY_ERROR, SEVERITY_WARNING, to_number

logger = logging.getLogger(__name__)

_DEFAULT_TOLERANCE = 0.05
_MAX_FIELDS_IN_PROMPT = 80


def critic_enabled() -> bool:
    raw = os.getenv("USE_CRITIC_REVIEW", "").strip().lower()
    return raw not in {"", "0", "false", "off", "no", "none"}


def critic_review(
    raw_text: str,
    fields: Mapping[str, list[ExtractedField]],
    llm: Any = None,
) -> list[VerificationIssue]:
    """Agent B audits extraction against the source; ungrounded values → issues."""
    if not critic_enabled() or llm is None or not getattr(llm, "api_key", None):
        return []
    flattened = [{"field": key, "value": entries[0].value} for key, entries in fields.items() if entries and entries[0].value][:_MAX_FIELDS_IN_PROMPT]
    if not flattened:
        return []
    prompt = (
        "You are the Critic auditing an insurance underwriting extraction. For every "
        "extracted field, confirm the value literally appears in the source snippet, or "
        "is directly and unambiguously derivable from it. Return JSON only:\n"
        '{"verdicts": [{"field": "<name>", "grounded": true/false, "note": "<short>"}]}\n\n'
        f"SOURCE:\n{raw_text[:8000]}\n\nEXTRACTED:\n{json.dumps(flattened)}"
    )
    try:
        raw = llm.complete(prompt)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("critic review call failed: %s", exc)
        return []
    verdicts = _parse_verdicts(raw)
    issues: list[VerificationIssue] = []
    for verdict in verdicts:
        if verdict.get("grounded") is True:
            continue
        issues.append(
            VerificationIssue(
                code="critic_ungrounded",
                severity=SEVERITY_ERROR if verdict.get("grounded") is False else SEVERITY_WARNING,
                message=(f"critic could not ground {verdict.get('field')} ({verdict.get('note', 'no note')}) — verify against source"),
                field_name=str(verdict.get("field", "")),
            )
        )
    return issues


def _parse_verdicts(raw: str) -> list[dict[str, Any]]:
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json") :]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return []
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return []
    verdicts = parsed.get("verdicts") if isinstance(parsed, dict) else None
    return verdicts if isinstance(verdicts, list) else []


def dual_model_consensus(
    primary: Mapping[str, list[ExtractedField]],
    secondary: Mapping[str, list[ExtractedField]],
    tolerance: float = _DEFAULT_TOLERANCE,
) -> list[VerificationIssue]:
    """Compare matching numeric fields from two engines; divergence → exception."""
    if not primary or not secondary:
        return []
    prim = {k: v[0].value for k, v in primary.items() if v and v[0].value}
    sec = {k: v[0].value for k, v in secondary.items() if v and v[0].value}
    issues: list[VerificationIssue] = []
    for key in prim:
        if key not in sec:
            continue
        a, b = to_number(prim[key]), to_number(sec[key])
        if a is None or b is None:
            continue
        denom = max(abs(a), abs(b), 1.0)
        if abs(a - b) / denom > tolerance:
            issues.append(
                VerificationIssue(
                    code="consensus_divergence",
                    severity=SEVERITY_ERROR,
                    message=(f"{key} diverges between engines: primary={prim[key]} vs secondary={sec[key]} (relative Δ {abs(a - b) / denom:.3f} > {tolerance:.2f}) — exception queue"),
                    field_name=key,
                )
            )
    return issues
