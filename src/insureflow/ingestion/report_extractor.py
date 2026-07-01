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

    def parse(self, raw_text: str, submission_id: str) -> UnstructuredSubmission:
        submission = UnstructuredSubmission(
            submission_id=submission_id,
            source="inspection_report",
            raw_text=raw_text,
            processed_at=datetime.now(timezone.utc),
        )

        submission.chunks = self._chunk_document(raw_text)
        submission.extracted_fields = self._extract_fields(raw_text)

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
                        context_start = max(0, m.start() - 60)
                        context_end = min(len(text), m.end() + 60)
                        context = text[context_start:context_end].replace("\n", " ")

                        matches.append(
                            ExtractedField(
                                field_name=field_name,
                                value=value,
                                confidence=0.7 if i == 0 else 0.5,
                                context=context.strip(),
                            )
                        )
            if matches:
                extracted[field_name] = matches
        return extracted
