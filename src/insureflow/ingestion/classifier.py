from __future__ import annotations

import json
import re

from insureflow.models.submissions import DocumentType


class DocumentClassifier:
    XML_DECL_RE = re.compile(r"<\?xml\s+version")
    ACORD_NS_RE = re.compile(r"xmlns=.*acord", re.IGNORECASE)
    ACORD_ROOT_RE = re.compile(r"<ACORD[>\s]")
    JSON_OBJECT_RE = re.compile(r"^\s*\{")
    JSON_ARRAY_RE = re.compile(r"^\s*\[")

    LOSS_RUN_KEYWORDS = re.compile(
        r"(?i)(loss\s+run|claims?\s+history|loss\s+history|"
        r"claim\s+detail|incurred|total\s+paid|open\s+reserve)"
    )
    SOV_KEYWORDS = re.compile(
        r"(?i)(schedule\s+of\s+values?|sov|building\s+valuation|"
        r"replacement\s+cost\s+breakdown|coinsurance|"
        r"schedule\s+of\s+coverages\s+and\s+values)"
    )
    INSPECTION_KEYWORDS = re.compile(
        r"(?i)(inspection\s+report|property\s+inspection|"
        r"survey\s+data\s+summary|engineer(?:ing)?\s+report|"
        r"physical\s+inspection|site\s+survey)"
    )
    EXCEL_KEYWORDS = re.compile(
        r"(?i)(sheet\s*\d|schedule\s+of\s+values|"
        r"coverage\s+summary|exposure\s+summary|"
        r"location\s+details?|claim\s+summary|"
        r"underwriting\s+worksheet)"
    )

    @classmethod
    def classify(cls, content: str, filename: str = "") -> DocumentType:
        content_stripped = content.strip()
        if not content_stripped:
            return DocumentType.SUPPLEMENTAL

        if cls.XML_DECL_RE.match(content_stripped) or cls.ACORD_ROOT_RE.search(content_stripped[:2000]):
            ns_match = cls.ACORD_NS_RE.search(content_stripped[:2000])
            if ns_match or cls.ACORD_ROOT_RE.search(content_stripped[:2000]):
                return DocumentType.ACORD_XML

        if cls.JSON_OBJECT_RE.match(content_stripped):
            try:
                parsed = json.loads(content_stripped)
                if isinstance(parsed, dict):
                    top_keys = " ".join(parsed.keys()).lower()
                    if any(k in top_keys for k in ("submission", "insured", "broker", "coverage", "applicant")):
                        return DocumentType.BROKER_API_JSON
            except (json.JSONDecodeError, ValueError):
                pass

        loss_score = len(cls.LOSS_RUN_KEYWORDS.findall(content_stripped[:2000]))
        sov_score = len(cls.SOV_KEYWORDS.findall(content_stripped[:2000]))
        insp_score = len(cls.INSPECTION_KEYWORDS.findall(content_stripped[:2000]))

        if loss_score > sov_score and loss_score > insp_score and loss_score >= 2:
            return DocumentType.LOSS_RUN

        if sov_score >= 2:
            return DocumentType.SCHEDULE_OF_VALUES

        if insp_score >= 1:
            return DocumentType.INSPECTION_REPORT

        if loss_score >= 1:
            return DocumentType.LOSS_RUN

        excel_score = len(cls.EXCEL_KEYWORDS.findall(content_stripped[:3000]))
        if excel_score >= 2:
            return DocumentType.SCHEDULE_OF_VALUES

        return DocumentType.SUPPLEMENTAL
