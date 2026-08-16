"""Agentic multi-step extraction with self-correction (technique #2).

Instead of one shot, extraction runs in a loop: a primary deterministic pass is
checked against structural constraints (required fields present, arithmetic
consistency of totals, per-field confidence), discrepancies feed a targeted
LLM refinement prompt, and the loop re-merges until clean or out of budget.
Each pass is recorded so the audit trail shows exactly what was verified.

Opt-in via ``USE_AGENTIC_EXTRACTION`` (default off); ``AGENTIC_MAX_LOOPS``
(default 2) caps refinement passes and ``AGENTIC_MIN_CONFIDENCE`` (default 0.6)
is the bar below which a field is flagged for re-scan.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from insureflow.models.submissions import ExtractedField

logger = logging.getLogger(__name__)

_REQUIRED_BY_DOC: dict[str, list[str]] = {
    "loss_run": ["total_claims", "total_incurred", "policy_period_start", "policy_period_end"],
    "schedule_of_values": ["total_value", "location"],
    "financial_statement": ["total_assets", "total_revenue"],
    "inspection_report": ["construction_type", "occupancy_type"],
    "acord": ["named_insured", "policy_period"],
}

_TOTAL_RE = re.compile(r"(grand_)?total|subtotal|_total", re.IGNORECASE)
_NUM_RE = re.compile(r"^[-+]?\d[\d,]*\.?\d*$")

_AGENTIC_CONFIDENCE = 0.75


def agentic_enabled() -> bool:
    raw = os.getenv("USE_AGENTIC_EXTRACTION", "").strip().lower()
    return raw not in {"", "0", "false", "off", "no", "none"}


def consistency_issues(fields: dict[str, list[ExtractedField]], document_type: str = "", min_confidence: float = 0.6) -> list[str]:
    """Deterministic structural checks → list of human/LLM-readable issues."""
    issues: list[str] = []

    present = {k: v[0].value for k, v in fields.items() if v and v[0].value}
    for required in _REQUIRED_BY_DOC.get(document_type, []):
        if required not in present or not present[required].strip():
            issues.append(f"missing required field: {required}")

    for key, value in present.items():
        field = fields[key][0]
        if field.confidence < min_confidence:
            issues.append(f"low confidence ({field.confidence:.2f}) for {key}={value}")

    issues.extend(_arithmetic_issues(present))
    return issues


def _arithmetic_issues(fields: dict[str, str]) -> list[str]:
    """Cross-check line-item sums against declared totals where a family exists."""
    totals: dict[str, float] = {}
    items: dict[str, float] = {}
    for key, value in fields.items():
        num = _as_number(value)
        if num is None:
            continue
        if _TOTAL_RE.search(key):
            totals[key] = num
        elif "item" in key.lower() or "claim" in key.lower() or "premium" in key.lower():
            items[key] = num
    if not totals or len(items) < 2:
        return []
    issues: list[str] = []
    summed = sum(items.values())
    for key, total in totals.items():
        if abs(summed - total) > max(0.05 * abs(total), 1.0):
            issues.append(f"arithmetic mismatch: line items sum to {summed:.2f} but {key}={total:.2f}")
    return issues


def _as_number(value: str) -> float | None:
    cleaned = re.sub(r"[^0-9.\-]", "", value)
    if not cleaned or not _NUM_RE.match(cleaned):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


class AgenticExtractionLoop:
    """Primary pass → validate → LLM refine → re-merge, up to ``max_loops``."""

    def __init__(self, llm: Any = None, max_loops: int = 0, min_confidence: float = 0.0) -> None:
        self.llm = llm
        self.max_loops = max_loops or int(os.getenv("AGENTIC_MAX_LOOPS", "2"))
        self.min_confidence = min_confidence or float(os.getenv("AGENTIC_MIN_CONFIDENCE", "0.6"))

    def run(
        self,
        raw_text: str,
        seed_fields: dict[str, list[ExtractedField]],
        document_type: str = "",
    ) -> tuple[dict[str, list[ExtractedField]], list[str]]:
        """Returns ``(fields, report)``; fields is a shallow-copied enriched map."""
        if not agentic_enabled() or self.llm is None or not getattr(self.llm, "api_key", None):
            return seed_fields, ["agentic disabled or no LLM available"]
        fields = {k: list(v) for k, v in seed_fields.items()}
        report: list[str] = []
        loop = 0
        while loop < self.max_loops:
            loop += 1
            issues = consistency_issues(fields, document_type, self.min_confidence)
            if not issues:
                report.append(f"pass {loop}: all structural checks clean")
                break
            report.append(f"pass {loop}: {len(issues)} issues ({'; '.join(issues[:3])})")
            refined = self._refine(raw_text, issues, document_type)
            if not refined:
                report.append(f"pass {loop}: LLM returned no refinements — stopping")
                break
            merged = self._merge_refinements(fields, refined, loop)
            fields.update(merged)
            report.append(f"pass {loop}: merged {len(merged)} refined fields")
        else:
            report.append(f"stopped at max_loops={self.max_loops}")
        self._record_agentic_meta(fields, report)
        return fields, report

    def _refine(self, raw_text: str, issues: list[str], document_type: str) -> dict[str, str] | None:
        prompt = (
            "You are correcting an underwriting document extraction. The extractor "
            f"found these issues: {json.dumps(issues)}. From the source text, return a "
            "JSON object mapping the affected field names to their correct values. "
            "Only include fields you are certain about. Respond with JSON only.\n\n"
            f"SOURCE:\n{raw_text[:6000]}"
        )
        try:
            raw = self.llm.complete(prompt)
        except Exception as exc:
            logger.warning("agentic refine call failed: %s", exc)
            return None
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str) -> dict[str, str] | None:
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
        try:
            parsed = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(parsed, dict):
            return None
        return {str(k): str(v) for k, v in parsed.items() if v is not None and str(v).strip()}

    def _merge_refinements(
        self,
        fields: dict[str, list[ExtractedField]],
        refined: dict[str, str],
        pass_number: int,
    ) -> dict[str, list[ExtractedField]]:
        merged: dict[str, list[ExtractedField]] = {}
        for key, value in refined.items():
            existing = fields.get(key)
            if existing and existing[0].value == value:
                continue  # already correct — no churn
            if existing and existing[0].confidence >= self.min_confidence and existing[0].value:
                continue  # high-confidence seed is authoritative
            merged[key] = [
                ExtractedField(
                    field_name=key,
                    value=value,
                    confidence=_AGENTIC_CONFIDENCE,
                    context=f"agentic_refinement_pass_{pass_number}",
                )
            ]
        return merged

    @staticmethod
    def _record_agentic_meta(fields: dict[str, list[ExtractedField]], report: list[str]) -> None:
        fields.setdefault("agentic", []).append(
            ExtractedField(field_name="agentic", value="; ".join(report), confidence=1.0, context="agentic_loop")
        )
