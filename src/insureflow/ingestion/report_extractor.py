from __future__ import annotations

import re
from datetime import datetime, timezone

from insureflow.config import settings
from insureflow.ingestion.base import BaseParser
from insureflow.models.submissions import (
    ExtractedChunk,
    ExtractedField,
    UnstructuredSubmission,
)


class InspectionReportExtractor(BaseParser):
    SECTION_PATTERNS = [
        r"(?i)(?:^|\n)(#{1,3}\s*)?(?:EXECUTIVE\s+SUMMARY|EXECUTIVE SUMMARY)",
        r"(?i)(?:^|\n)(#{1,3}\s*)?(?:BUILDING\s+CONSTRUCTION|BUILDING DESCRIPTION)",
        r"(?i)(?:^|\n)(#{1,3}\s*)?(?:PROPERTY\s+CONDITIONS?|CONDITION)",
        r"(?i)(?:^|\n)(#{1,3}\s*)?(?:LOSS\s+HISTORY|PRIOR\s+LOSSES)",
        r"(?i)(?:^|\n)(#{1,3}\s*)?(?:OCCUPANCY|OCCUPANCY DETAILS)",
        r"(?i)(?:^|\n)(#{1,3}\s*)?(?:PROTECTION|FIRE PROTECTION|SPRINKLER)",
        r"(?i)(?:^|\n)(#{1,3}\s*)?(?:RECOMMENDATIONS?|UNDERWRITING RECOMMENDATIONS)",
        r"(?i)(?:^|\n)(#{1,3}\s*)?(?:PHOTOGRAPHS?|ATTACHMENTS|APPENDIX)",
    ]

    FIELD_EXTRACTION_PATTERNS: dict[str, list[str]] = {
        "construction_type": [
            r"(?i)(?:construction\s+type|construction)[:\s]*([A-Za-z\s]+?)(?:\n|$)",
            r"(?i)(?:frame|masonry|fireproof|concrete|steel)\s+(?:construction)?",
        ],
        "year_built": [
            r"(?i)(?:year\s+built|built|constructed|age)[:\s]*(\d{4})",
            r"(?i)(?:yr\.?\s*built|constructed)[:\s]*(\d{4})",
        ],
        "square_footage": [
            r"(?i)(?:square\s+footage|sq\.?\s*ft\.?|sqft|area)[:\s]*([\d,]+(?:\.\d+)?)",
            r"(?i)(?:total\s+area|building\s+area)[:\s]*([\d,]+)",
        ],
        "number_of_stories": [
            r"(?i)(?:stories|story|storeys?|floors?|levels?)[:\s]*(\d+)",
            r"(?i)(\d+)[-\s]?(?:story|storey)",
        ],
        "occupancy_type": [
            r"(?i)(?:occupancy|occupancy\s+type)[:\s]*([A-Za-z\s]+?)(?:\n|$)",
            r"(?i)(?:office|retail|warehouse|manufacturing|industrial|mixed-use)",
        ],
        "sprinklered": [
            r"(?i)(?:sprinklered|sprinklers?|fire\s+sprinkler)[:\s]*(yes|no|partial|fully|none|full)",
            r"(?i)(?:sprinkler)(?:.*?)(?:yes|no|present|absent|installed)",
        ],
        "protection_class": [
            r"(?i)(?:protection\s+class|pc|fire\s+class)[:\s]*(\d{1,2})",
            r"(?i)(?:class)[:\s]*(\d{1,2})\s*(?:protection|fire)",
        ],
        "prior_claims": [
            r"(?i)(?:prior\s+(?:claims?|losses?)|loss\s+history|claims?\s+history)[:\s]*(.+?)(?:\n\n|\n#{1,3}|\Z)",
        ],
        "roof_type": [
            r"(?i)(?:roof|roofing|roof\s+type)[:\s]*([A-Za-z\s]+?)(?:\n|$)",
        ],
        "security_features": [
            r"(?i)(?:security|alarm|monitoring|camera)[:\s]*([A-Za-z\s]+?)(?:\n|$)",
        ],
    }

    # ── Survey comparison tables: | Field | Application Value | Surveyor Value | Match? | ──
    SURVEY_HEADER_RE = re.compile(
        r"(?i)\|\s*field\s*\|\s*(?:application\s*value|app\s*value|broker)\s*\|"
        r"\s*(?:surveyor\s*value|surveyor|inspected)\s*\|"
        r"\s*(?:match\??|match\?|status)\s*\|"
    )
    SURVEY_SECTION_RE = re.compile(r"(?i)\b(survey\s+data\s+summary)\b")
    # Normalize a survey field label to the field_mapping key when it matches.
    SURVEY_FIELD_ALIASES: dict[str, str] = {
        "construction type": "construction_type",
        "year built": "year_built",
        "square footage": "square_footage",
        "number of stories": "number_of_stories",
        "stories": "number_of_stories",
        "occupancy": "occupancy_type",
        "sprinklered": "sprinklered",
        "protection class": "protection_class",
        "roof type": "roof_type",
        "security": "security_features",
    }

    @staticmethod
    def _is_valid_value(field_name: str, value: str) -> bool:
        value = value.strip()
        if not value:
            return False
        if field_name == "year_built":
            return bool(re.fullmatch(r"\d{4}", value))
        if field_name in ("number_of_stories", "protection_class"):
            return bool(re.fullmatch(r"\d{1,3}", value))
        if field_name in ("square_footage",):
            return bool(re.fullmatch(r"[\d,]+(?:\.\d+)?", value))
        return True

    @staticmethod
    def _pattern_confidence(field_name: str, value: str, pattern_idx: int, total_matches: int) -> float:
        base = 0.7 if pattern_idx == 0 else 0.5
        if not InspectionReportExtractor._is_valid_value(field_name, value):
            base -= 0.3
        elif total_matches > 1:
            base += 0.15  # multiple independent patterns agree
        return round(min(max(base, 0.2), 0.95), 2)

    def parse(self, raw_text: str, submission_id: str) -> UnstructuredSubmission:
        submission = UnstructuredSubmission(
            submission_id=submission_id,
            source="inspection_report",
            document_type="inspection_report",
            raw_text=raw_text,
            processed_at=datetime.now(timezone.utc),
        )

        submission.chunks = self._chunk_document(raw_text)
        submission.extracted_fields = self._extract_fields(raw_text)
        self._extract_survey_tables(submission.extracted_fields, raw_text)

        return submission

    def _chunk_document(self, text: str) -> list[ExtractedChunk]:
        chunks: list[ExtractedChunk] = []
        chunk_size = settings.extraction_chunk_size
        overlap = settings.extraction_overlap

        if len(text) <= chunk_size:
            return [
                ExtractedChunk(
                    chunk_index=0,
                    text=text,
                    start_char=0,
                    end_char=len(text),
                )
            ]

        start = 0
        idx = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))

            if end < len(text):
                section_break = self._find_section_break(text, end - overlap, end + overlap)
                if section_break != -1:
                    end = section_break
                else:
                    last_newline = text.rfind("\n", start, end)
                    if last_newline > start + chunk_size // 2:
                        end = last_newline

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    ExtractedChunk(
                        chunk_index=idx,
                        text=chunk_text,
                        start_char=start,
                        end_char=end,
                    )
                )
                idx += 1

            start = end

        return chunks

    def _find_section_break(self, text: str, start: int, end: int) -> int:
        search_region = text[start:end]
        for pattern in self.SECTION_PATTERNS:
            match = re.search(pattern, search_region)
            if match:
                return start + match.start()
        return -1

    def _extract_fields(self, text: str) -> dict[str, list[ExtractedField]]:
        extracted: dict[str, list[ExtractedField]] = {}
        for field_name, patterns in self.FIELD_EXTRACTION_PATTERNS.items():
            matches: list[ExtractedField] = []
            for i, pattern in enumerate(patterns):
                for m in re.finditer(pattern, text, re.MULTILINE | re.DOTALL):
                    if m.lastindex and m.group(1):
                        value = m.group(1).strip()
                        if field_name == "prior_claims":
                            value = re.sub(r"^\**\s*", "", value)
                            value = re.sub(r"\s+", " ", value).strip()
                        context_start = max(0, m.start() - 60)
                        context_end = min(len(text), m.end() + 60)
                        context = text[context_start:context_end].replace("\n", " ")

                        confidence = self._pattern_confidence(field_name, value, i, 0)
                        matches.append(
                            ExtractedField(
                                field_name=field_name,
                                value=value,
                                confidence=confidence,
                                context=context.strip(),
                            )
                        )
            if matches:
                # Count matches per pattern for agreement bonus; recompute the
                # best-scoring value's confidence when multiple sources agree.
                by_value: dict[str, list[ExtractedField]] = {}
                for ef in matches:
                    by_value.setdefault(ef.value.lower(), []).append(ef)
                for group in by_value.values():
                    if len(group) > 1:
                        for ef in group:
                            ef.confidence = min(0.9, ef.confidence + 0.1)
                extracted[field_name] = matches
        return extracted

    # ── Survey comparison tables ─────────────────────────────────────────
    def _extract_survey_tables(self, extracted: dict[str, list[ExtractedField]], text: str) -> None:
        lines = text.split("\n")
        i = 0
        table_idx = 0
        mismatches: list[str] = []
        while i < len(lines):
            header_cells = self._split_pipe_cells(lines[i])
            if header_cells and self.SURVEY_HEADER_RE.search(lines[i]):
                # Section label: look back for "SURVEY DATA SUMMARY — <LOC>".
                section = self._find_survey_section_label(lines, i)
                table_idx += 1
                i += 1
                while i < len(lines):
                    row_cells = self._split_pipe_cells(lines[i])
                    if not row_cells:
                        break
                    if all(re.fullmatch(r"[\s\-_:+.,=~|]+", c or "") for c in row_cells):
                        i += 1
                        continue
                    if len(row_cells) < 4:
                        i += 1
                        continue
                    self._index_survey_row(extracted, row_cells, section, table_idx, mismatches, is_primary=table_idx == 1)
                    i += 1
            i += 1
        if mismatches:
            extracted["survey.mismatches"] = [
                ExtractedField(
                    field_name="survey.mismatches",
                    value="\n".join(mismatches),
                    confidence=0.9,
                    context="Surveyor-applied value conflicts with the broker application",
                )
            ]

    @staticmethod
    def _split_pipe_cells(line: str) -> list[str]:
        if "|" not in line:
            return []
        cells = [c.strip() for c in line.split("|")]
        return [c for c in cells if c != ""]

    @staticmethod
    def _find_survey_section_label(lines: list[str], header_idx: int) -> str:
        for line in lines[max(0, header_idx - 4) : header_idx]:
            if "SURVEY DATA SUMMARY" in line.upper():
                label = re.sub(r"(?i)\bsurvey\s+data\s+summary\b", "", line)
                label = label.strip(" #—-–()").strip()
                return label or "primary"
        return "primary"

    @staticmethod
    def _normalize_survey_field(label: str) -> str:
        norm = label.strip().lower()
        return InspectionReportExtractor.SURVEY_FIELD_ALIASES.get(norm, re.sub(r"[^a-z0-9]+", "_", norm).strip("_"))

    def _index_survey_row(
        self,
        extracted: dict[str, list[ExtractedField]],
        cells: list[str],
        section: str,
        table_idx: int,
        mismatches: list[str],
        is_primary: bool,
    ) -> None:
        field_label = cells[0]
        app_value = cells[1] if len(cells) > 1 else ""
        surveyor_value = cells[2] if len(cells) > 2 else ""
        match_flag = cells[3].strip() if len(cells) > 3 else ""

        field_slug = self._normalize_survey_field(field_label)
        is_match = match_flag.upper() in ("YES", "Y", "MATCH", "OK", "TRUE")
        is_partial = match_flag.upper() in ("PARTIAL", "CLOSE", "APPROX", "NEAR")

        if not is_match:
            base_conf = 0.6 if not is_partial else 0.8
        else:
            base_conf = 0.95
        base_conf = max(base_conf, 0.6 if surveyor_value else 0.5)
        base_conf = round(base_conf, 2)

        prefix = f"survey.{table_idx}.{field_slug}"
        extracted.setdefault(f"{prefix}.application", []).append(
            ExtractedField(
                field_name=f"{prefix}.application",
                value=app_value,
                confidence=base_conf,
                context=f"{section} · application value",
            )
        )
        extracted.setdefault(f"{prefix}.surveyor", []).append(
            ExtractedField(
                field_name=f"{prefix}.surveyor",
                value=surveyor_value,
                confidence=base_conf,
                context=f"{section} · surveyor measured value",
            )
        )
        extracted.setdefault(f"{prefix}.match", []).append(
            ExtractedField(
                field_name=f"{prefix}.match",
                value=match_flag or "unknown",
                confidence=base_conf,
                context=f"{section} · {field_label}",
            )
        )

        if not is_match:
            mismatches.append(f"{section}: {field_label} — app '{app_value}' vs surveyor '{surveyor_value}' ({match_flag})")

        # Surface the surveyor's measured value under the shared canonical field
        # path so reconciliation sees app-vs-surveyor conflicts as provenance
        # contradictions (e.g. risk_profile.protection_class: app 3 vs 4).
        # Only the PRIMARY location maps onto the canonical paths; secondary
        # locations keep descriptive survey.* fields only.
        canonical = settings.field_mapping.get(field_slug)
        if canonical and is_primary:
            extracted.setdefault(f"surveyor.{field_slug}", []).append(
                ExtractedField(
                    field_name=f"surveyor.{field_slug}",
                    value=surveyor_value,
                    confidence=base_conf,
                    context=f"{section} · surveyor measured value for {field_label}",
                )
            )
