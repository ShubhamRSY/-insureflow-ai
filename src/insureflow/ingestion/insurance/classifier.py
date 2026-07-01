from __future__ import annotations

import re
from enum import Enum


class InsuranceDocumentType(str, Enum):
    ACORD_XML = "acord_xml"
    BROKER_SLIP = "broker_slip"
    DEC_PAGE = "dec_page"
    LOSS_RUN = "loss_run"
    SCHEDULE_OF_VALUES = "schedule_of_values"
    INSPECTION_REPORT = "inspection_report"
    FINANCIAL_STATEMENT = "financial_statement"
    SUPPLEMENTAL = "supplemental"


class InsuranceDocumentClassifier:
    """Classify broker PDFs and text submissions by filename + content heuristics."""

    @staticmethod
    def classify(text: str, filename: str = "") -> InsuranceDocumentType:
        combined = f"{filename}\n{text[:8000]}".lower()

        if filename.endswith(".xml") or "<acord" in combined or "acord xmlns" in combined:
            return InsuranceDocumentType.ACORD_XML

        if any(k in combined for k in ("declaration page", "dec page", "policy declarations", "policy number:")):
            return InsuranceDocumentType.DEC_PAGE

        if any(k in combined for k in ("loss run", "claims history", "claim #", "date of loss", "incurred")):
            if re.search(r"claim\s*#?\s*\d+", combined) or "total incurred" in combined:
                return InsuranceDocumentType.LOSS_RUN

        if any(
            k in combined
            for k in (
                "broker slip",
                "submission summary",
                "coverage requested",
                "underwriting submission",
            )
        ):
            return InsuranceDocumentType.BROKER_SLIP

        if any(k in combined for k in ("schedule of values", "sov", "building value", "total insurable")):
            return InsuranceDocumentType.SCHEDULE_OF_VALUES

        if any(k in combined for k in ("inspection report", "inspector", "property condition", "roof condition")):
            return InsuranceDocumentType.INSPECTION_REPORT

        if any(k in combined for k in ("balance sheet", "income statement", "financial statement", "annual revenue")):
            return InsuranceDocumentType.FINANCIAL_STATEMENT

        return InsuranceDocumentType.SUPPLEMENTAL
