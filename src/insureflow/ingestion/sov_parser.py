from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from insureflow.ingestion.base import BaseParser
from insureflow.models.submissions import (
    ExtractedChunk,
    ExtractedField,
    ScheduleItem,
    ScheduleOfValues,
    UnstructuredSubmission,
)


class SOVParser(BaseParser):
    PIPE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
    SKIP_LINE_RE = re.compile(r"^[\s\|\-:=+#]+$")

    VALUE_LINE_RE = re.compile(
        r"(?i)([\w\s/&()#.-]+?)\s*[:\-]\s*\$?\s*([\d,]+(?:\.\d{2})?)"
    )

    SECTION_RE = re.compile(
        r"(?i)^(?:#{1,3}\s+)?(.+?(?:schedule|values?|valuation|"
        r"breakdown|coverage|limit))",
        re.MULTILINE,
    )

    COVERAGE_MAP = {
        "building": "Property",
        "contents": "Property",
        "bpp": "Property",
        "business income": "Property",
        "business interruption": "Property",
        "equipment breakdown": "Equipment Breakdown",
        "general liability": "Commercial General Liability",
        "auto": "Commercial Auto",
        "crime": "Commercial Crime",
        "inland marine": "Inland Marine",
        "umbrella": "Umbrella",
    }

    LOCATION_ADDR_RE = re.compile(
        r"(?i)(?:location|address|site|premises)[:\s]*"
        r"(.+?\d{5})",
    )

    def parse(self, raw_text: str, submission_id: str) -> UnstructuredSubmission:
        sows = self.parse_structured(raw_text)

        submission = UnstructuredSubmission(
            submission_id=submission_id,
            source="schedule_of_values",
            document_type="schedule_of_values",
            raw_text=raw_text,
            processed_at=datetime.now(timezone.utc),
        )

        for i, sov in enumerate(sows):
            submission.extracted_fields[f"sov.{i}.type"] = [
                ExtractedField(
                    field_name=f"sov.{i}.type",
                    value=sov.schedule_type,
                    confidence=0.8,
                    context=f"{sov.schedule_type} — {len(sov.items)} items",
                )
            ]
            submission.extracted_fields[f"sov.{i}.total"] = [
                ExtractedField(
                    field_name=f"sov.{i}.total",
                    value=str(sov.total_value),
                    confidence=0.8,
                    context=f"Total value: ${sov.total_value:,.0f}",
                )
            ]

        submission.chunks = [
            ExtractedChunk(
                chunk_index=0,
                start_char=0,
                end_char=len(raw_text),
                text=raw_text,
            )
        ]

        return submission

    def parse_structured(self, raw_text: str) -> list[ScheduleOfValues]:
        sections = self._split_sections(raw_text)
        sows: list[ScheduleOfValues] = []

        for section_text in sections:
            sov = self._parse_section(section_text)
            if sov and sov.items:
                sows.append(sov)

        if not sows:
            fallback = self._parse_flat(raw_text)
            if fallback:
                sows.append(fallback)

        return sows

    def _split_sections(self, text: str) -> list[str]:
        lines = text.split("\n")
        sections: list[str] = []
        current: list[str] = []

        for line in lines:
            if re.match(
                r"(?i)^(?:#{1,3}\s+)?(?:schedule|building|coverage|property|"
                r"contents|auto|liability|crime|marine|umbrella|location)\b",
                line,
            ):
                if current:
                    sections.append("\n".join(current))
                    current = []
            current.append(line)

        if current:
            sections.append("\n".join(current))
        return sections

    def _parse_section(self, text: str) -> Optional[ScheduleOfValues]:
        coverage_type = self._detect_coverage_type(text)
        schedule_type = self._detect_schedule_type(text)
        items = self._extract_items(text)

        if not items:
            return None

        for item in items:
            loc_ref = self.LOCATION_ADDR_RE.search(text)
            if loc_ref:
                item.location_ref = loc_ref.group(1).strip()

        total = sum(i.value for i in items)
        return ScheduleOfValues(
            schedule_type=schedule_type,
            coverage_type=coverage_type,
            items=items,
            total_value=total,
        )

    def _detect_coverage_type(self, text: str) -> str:
        first_line = text.strip().split("\n")[0]
        text_lower = first_line.lower()
        for keyword, coverage in self.COVERAGE_MAP.items():
            if keyword in text_lower:
                return coverage
        return "Property"

    def _detect_schedule_type(self, text: str) -> str:
        match = re.search(
            r"(?i)(schedule\s+of\s+values|schedule|valuation|breakdown)",
            text[:200],
        )
        if match:
            raw = match.group(1)
            return raw.strip().title()
        first_line = text.strip().split("\n")[0].strip()
        return first_line.replace("#", "").strip()[:50]

    def _extract_items(self, text: str) -> list[ScheduleItem]:
        items: list[ScheduleItem] = []
        seen: set[str] = set()

        for line in text.split("\n"):
            line_stripped = line.strip()
            if not line_stripped or self.SKIP_LINE_RE.match(line_stripped):
                continue

            # Try pipe table format: | ... | $amount |
            m = self.PIPE_ROW_RE.match(line)
            if m:
                cols = [c.strip() for c in m.group(1).split("|")]
                amount_col = None
                amount_val = None
                for i in reversed(range(len(cols))):
                    amt_match = re.match(
                        r"^[\*\s]*\$?\s*([\d,]+(?:\.\d{2})?)\s*[\*\s]*$", cols[i]
                    )
                    if amt_match:
                        amount_col = i
                        amount_val = float(amt_match.group(1).replace(",", ""))
                        break
                if amount_val is not None and amount_val > 0:
                    desc_parts = []
                    for c in cols[:amount_col]:
                        clean = re.sub(r"[\*\#]", "", c).strip()
                        if clean and not re.match(r"^[\d,]+(?:\s*[-–]\s*[\d,]+)?$", clean):
                            desc_parts.append(clean)
                    desc = " ".join(desc_parts).strip()
                    desc = re.sub(r"\s+", " ", desc).strip()
                    if desc and len(desc) > 3 and desc.lower()[:40] not in seen:
                        seen.add(desc.lower()[:40])
                        items.append(ScheduleItem(description=desc, value=amount_val))
                    continue

            # Try key-value format: Description: $Amount  or  Description - $Amount
            for match in self.VALUE_LINE_RE.finditer(line):
                desc = match.group(1).strip()
                value = float(match.group(2).replace(",", ""))
                key = desc.lower()[:30]
                if key not in seen and value > 0 and len(desc) > 2:
                    seen.add(key)
                    items.append(ScheduleItem(description=desc, value=value))

        return items

    def _parse_flat(self, text: str) -> Optional[ScheduleOfValues]:
        items = self._extract_items(text)
        if not items:
            return None
        coverage = self._detect_coverage_type(text)
        total = sum(i.value for i in items)
        return ScheduleOfValues(
            schedule_type="Schedule of Values",
            coverage_type=coverage,
            items=items,
            total_value=total,
        )
