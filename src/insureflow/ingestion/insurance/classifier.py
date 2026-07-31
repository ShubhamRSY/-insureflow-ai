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
    # Directors & Officers / management liability package
    DO_APPLICATION = "do_application"
    DO_QUESTIONNAIRE = "do_questionnaire"
    DO_FINANCIALS_10K = "do_financials_10k"
    DO_BYLAWS_CHARTER = "do_bylaws_charter"
    DO_BOARD_ROSTER = "do_board_roster"
    DO_OWNERSHIP_CHART = "do_ownership_chart"
    DO_CLAIMS_HISTORY = "do_claims_history"
    DO_PRIOR_ACTS_WARRANTY = "do_prior_acts_warranty"


class InsuranceDocumentClassifier:
    """Classify broker PDFs and text submissions by filename + content heuristics."""

    @staticmethod
    def classify(text: str, filename: str = "") -> InsuranceDocumentType:
        combined = f"{filename}\n{text[:8000]}".lower()
        name = filename.lower()

        if filename.endswith(".xml") or "<acord" in combined or "acord xmlns" in combined:
            return InsuranceDocumentType.ACORD_XML

        # D&O package heuristics (before generic financials / supplemental)
        if any(k in name or k in combined for k in ("prior_acts", "prior acts warranty", "continuity date")):
            return InsuranceDocumentType.DO_PRIOR_ACTS_WARRANTY
        if any(k in name or k in combined for k in ("board_roster", "directors and officers list", "list of directors", "officer roster")):
            return InsuranceDocumentType.DO_BOARD_ROSTER
        if any(k in name or k in combined for k in ("ownership_chart", "org chart", "ownership structure", "cap table")):
            return InsuranceDocumentType.DO_OWNERSHIP_CHART
        if any(k in name or k in combined for k in ("bylaws", "articles of incorporation", "corporate charter", "certificate of incorporation")):
            return InsuranceDocumentType.DO_BYLAWS_CHARTER
        if any(k in name or k in combined for k in ("10-k", "10k", "form 10-k", "annual report")):
            return InsuranceDocumentType.DO_FINANCIALS_10K
        if any(k in name or k in combined for k in ("d&o questionnaire", "do_questionnaire", "management liability questionnaire", "d and o questionnaire")):
            return InsuranceDocumentType.DO_QUESTIONNAIRE
        if any(k in name or k in combined for k in ("d&o application", "do_application", "directors and officers application", "management liability application")):
            return InsuranceDocumentType.DO_APPLICATION
        if any(k in combined for k in ("d&o claims", "securities claim", "employment practices claim history")) and "loss run" not in combined:
            return InsuranceDocumentType.DO_CLAIMS_HISTORY

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
