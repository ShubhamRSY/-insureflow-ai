"""Schematic / floor-plan parser.

Commercial property submissions are frequently accompanied by floor plans,
schematics, and fire-zone drawings. Underwriters rely on them for the
egress/compartmentalization assessment: total floor area, number of stories,
fire compartments, exit routes, and stairwells materially affect fire-loss
potential and code compliance.

This parser extracts those features from plain-text or tabular plan documents
("Floor Area: 42,000 sq ft", "| Exits | 4 |"), classifies the plan type, and
exposes the features through both the per-field extracted map
(:meth:`parse`) and the rich :class:`FloorPlanData` model
(:meth:`parse_structured`).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from insureflow.ingestion.base import BaseParser
from insureflow.models.submissions import (
    ExtractedChunk,
    ExtractedField,
    FloorPlanData,
    UnstructuredSubmission,
)

_FLOOR_AREA_RE = re.compile(
    r"(?i)(?:total\s+)?(?:floor|gross|building|net|usable)?\s*area"
    r"[^0-9$€£(\-\n]{0,12}?([\d,]+(?:\.\d+)?)\s*(?:sq\s*\.?\s*ft\.?|sf|square\s+feet|ft\s*2)"
)
_FLOOR_AREA_M2_RE = re.compile(
    r"(?i)(?:total\s+)?(?:floor|gross|building|net|usable)?\s*area"
    r"[^0-9$€£(\-\n]{0,12}?([\d,]+(?:\.\d+)?)\s*(?:m\s*2|m&sup2;|square\s+meters?|sq\.?\s*m\.?)"
)
_STORIES_RE = re.compile(r"(?i)(?:number\s+of\s+)?(?:stories|storeys?|levels?)\s*(?:[:#|]\s*)?(\d{1,3})")
_STORIES_ORDINAL_RE = re.compile(r"(?i)(\d{1,2})\s*[-/]?\s*(?:story|storey)\b")
_COMPARTMENTS_RE = re.compile(r"(?i)(?:number\s+of\s+)?(?:fire\s+)?(?:compartments?|fire\s+walls?|fire\s+zones?)\s*(?:[:#|]\s*)?(\d{1,3})")
_COMPARTMENTALIZATION_RE = re.compile(r"(?i)(?:compartmentaliz(?:ed|ation)|fire\s+compartment)\s*(?:[:#|]\s*)?(compartmented|compartmentalized|open\s+plan|open|mixed|partial)")
_EXITS_RE = re.compile(r"(?i)(?:number\s+of\s+)?(?:exits?|emergency\s+exits?|exit\s+doors?|means\s+of\s+egress)\s*(?:[:#|]\s*)?(\d{1,3})")
_EXIT_TYPES_RE = re.compile(r"(?i)\b(?:stairwells?|stairs?|fire\s+escapes?|exterior\s+doors?|corridors?|exit\s+doors?|ramps?)\b")
_STAIRWELLS_RE = re.compile(r"(?i)(?:number\s+of\s+)?stairwells?\s*(?:[:#|]\s*)?(\d{1,3})")
_FIRE_ALARM_RE = re.compile(r"(?i)(?:fire\s+alarm\s+system|fire\s+alarms?|alarm\s+system)\s*(?:[:#|]\s*)?(yes|no|partial|full|none|installed|not\s+installed|absent)")
_SPRINKLER_RE = re.compile(r"(?i)(?:sprinkler(?:ed|s)?|fire\s+sprinklers?)\s*(?:[:#|]\s*)?(yes|no|partial|full|none|fully\s+sprinklered|not\s+sprinklered)")
_MONEY_FREE_RE = re.compile(r"^\s*([\d,]+(?:\.\d+)?)\s*$")


def _extract_number(raw: str) -> Optional[float]:
    raw = raw.strip().replace(",", "")
    if not _MONEY_FREE_RE.match(raw):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


class SchematicParser(BaseParser):
    """Parse floor-plan / schematic documents for area, compartments, and egress."""

    def parse(self, raw_text: str, submission_id: str) -> UnstructuredSubmission:
        features, confidence = self._extract_features(raw_text)

        submission = UnstructuredSubmission(
            submission_id=submission_id,
            source="schematic_floor_plan",
            document_type="floor_plan",
            raw_text=raw_text,
            processed_at=datetime.now(timezone.utc),
        )

        submission.extracted_fields = {}
        for key, value in features.items():
            if key in ("exit_types", "notes"):
                continue
            submission.extracted_fields[key] = [
                ExtractedField(
                    field_name=key,
                    value=str(value),
                    confidence=confidence,
                    context=f"{key} from floor plan",
                )
            ]
        submission.extracted_fields["exit_types"] = [
            ExtractedField(
                field_name="exit_types",
                value=", ".join(features.get("exit_types", [])),
                confidence=confidence,
                context="exit types from floor plan",
            )
        ]

        submission.chunks = [ExtractedChunk(chunk_index=0, text=raw_text, start_char=0, end_char=len(raw_text))]
        return submission

    def parse_structured(self, raw_text: str) -> FloorPlanData:
        features, _ = self._extract_features(raw_text)
        data = FloorPlanData()
        for key, value in features.items():
            if value is None or key == "notes":
                continue
            setattr(data, key, value)
        data.notes = features.get("notes", "")
        data.source = "schematic_floor_plan"
        return data

    # ── Extraction ─────────────────────────────────────────────────────────
    def _extract_features(self, text: str) -> tuple[dict[str, Any], float]:
        features: dict[str, Any] = {}
        confidence = 0.75

        for pattern, key in (
            (_FLOOR_AREA_M2_RE, "floor_area_m2"),
            (_FLOOR_AREA_RE, "floor_area_sqft"),
        ):
            match = pattern.search(text)
            if match:
                value = _extract_number(match.group(1))
                if value is not None:
                    features[key] = value
                    confidence += 0.05
                    break

        match = _STORIES_RE.search(text) or _STORIES_ORDINAL_RE.search(text)
        if match:
            features["number_of_stories"] = int(float(match.group(1)))
            confidence += 0.05

        match = _COMPARTMENTS_RE.search(text)
        if match:
            features["fire_compartments"] = int(float(match.group(1)))
            confidence += 0.05

        match = _COMPARTMENTALIZATION_RE.search(text)
        if match:
            raw = match.group(1).strip().lower()
            if "open" in raw:
                features["compartmentalization"] = "open"
            elif "mixed" in raw or "partial" in raw:
                features["compartmentalization"] = "mixed"
            else:
                features["compartmentalization"] = "compartmented"
            confidence += 0.05

        match = _EXITS_RE.search(text)
        if match:
            features["number_of_exits"] = int(float(match.group(1)))
            confidence += 0.05

        exit_types = list(dict.fromkeys(m.lower().rstrip(".") for m in _EXIT_TYPES_RE.findall(text)))
        if exit_types:
            features["exit_types"] = exit_types
            confidence += 0.05
        match = _STAIRWELLS_RE.search(text)
        if match:
            features["stairwells"] = int(float(match.group(1)))
            confidence += 0.05

        for pattern, key in (
            (_FIRE_ALARM_RE, "fire_alarm"),
            (_SPRINKLER_RE, "sprinklered"),
        ):
            match = pattern.search(text)
            if match:
                raw = match.group(1).strip().lower()
                if raw in ("none", "absent", "not installed", "no"):
                    features[key] = "no"
                elif raw in ("partial",):
                    features[key] = "partial"
                elif raw in ("installed", "full", "fully sprinklered", "yes"):
                    features[key] = "yes"
                else:
                    features[key] = "unknown"
                confidence += 0.05

        if re.search(r"(?i)(floor\s+plan|schematic|blueprint|floor\s+layout|floor\s+area|exit\s+route|fire\s+zone|means\s+of\s+egress)", text):
            confidence += 0.05

        features["notes"] = self._build_notes(features)
        return features, round(min(confidence, 0.95), 2)

    @staticmethod
    def _build_notes(features: dict[str, Any]) -> str:
        parts: list[str] = []
        if features.get("floor_area_sqft"):
            parts.append(f"{int(features['floor_area_sqft']):,} sq ft")
        if features.get("number_of_stories"):
            parts.append(f"{features['number_of_stories']} stories")
        if features.get("fire_compartments"):
            parts.append(f"{features['fire_compartments']} fire compartments")
        if features.get("number_of_exits"):
            parts.append(f"{features['number_of_exits']} exits")
        if features.get("exit_types"):
            parts.append("egress via " + ", ".join(features["exit_types"]))
        return "; ".join(parts) if parts else "Floor-plan features not quantified"
