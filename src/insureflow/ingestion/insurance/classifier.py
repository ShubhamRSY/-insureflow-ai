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
    PROPERTY_PHOTOS = "property_photos"
    # Directors & Officers / management liability package
    DO_APPLICATION = "do_application"
    DO_QUESTIONNAIRE = "do_questionnaire"
    DO_FINANCIALS_10K = "do_financials_10k"
    DO_BYLAWS_CHARTER = "do_bylaws_charter"
    DO_BOARD_ROSTER = "do_board_roster"
    DO_OWNERSHIP_CHART = "do_ownership_chart"
    DO_CLAIMS_HISTORY = "do_claims_history"
    DO_PRIOR_ACTS_WARRANTY = "do_prior_acts_warranty"
    # Personal homeowners
    HOMEOWNERS_APPLICATION = "homeowners_application"
    DWELLING_INSPECTION = "dwelling_inspection"
    HOME_CLAIMS_HISTORY = "home_claims_history"
    # Personal auto
    AUTO_APPLICATION = "auto_application"
    MVR_REPORT = "mvr_report"
    VEHICLE_DECLARATIONS = "vehicle_declarations"
    # Life
    LIFE_APPLICATION = "life_application"
    MEDICAL_EXAM = "medical_exam"
    APS_RECORDS = "aps_records"
    BENEFICIARY_FORM = "beneficiary_form"
    # Trade credit
    TRADE_CREDIT_APPLICATION = "trade_credit_application"
    AR_AGING_REPORT = "ar_aging_report"
    BUYER_EXPOSURE_LIST = "buyer_exposure_list"
    # Errors & Omissions
    EO_APPLICATION = "eo_application"
    ENGAGEMENT_LETTER = "engagement_letter"
    # Key person
    KEY_PERSON_APPLICATION = "key_person_application"
    CORPORATE_RESOLUTION = "corporate_resolution"


class InsuranceDocumentClassifier:
    """Classify broker PDFs and text submissions by filename + content heuristics."""

    @staticmethod
    def classify(text: str, filename: str = "") -> InsuranceDocumentType:
        combined = f"{filename}\n{text[:8000]}".lower()
        name = filename.lower()

        if filename.endswith(".xml") or "<acord" in combined or "acord xmlns" in combined:
            return InsuranceDocumentType.ACORD_XML

        # Personal lines (before generic financials / supplemental)
        if any(k in name or k in combined for k in ("life application", "life_application", "term life application", "whole life application")):
            return InsuranceDocumentType.LIFE_APPLICATION
        if any(k in name or k in combined for k in ("paramedical", "medical exam", "medical_exam", "examone")):
            return InsuranceDocumentType.MEDICAL_EXAM
        if any(k in name or k in combined for k in ("attending physician", "aps_", "aps records", "medical records summary")):
            return InsuranceDocumentType.APS_RECORDS
        if any(k in name or k in combined for k in ("beneficiary designation", "beneficiary form", "beneficiary_form")):
            return InsuranceDocumentType.BENEFICIARY_FORM
        if any(k in name or k in combined for k in ("mvr", "motor vehicle report", "driving record report")):
            return InsuranceDocumentType.MVR_REPORT
        if any(k in name or k in combined for k in ("auto application", "personal auto application", "auto_application")):
            return InsuranceDocumentType.AUTO_APPLICATION
        if any(k in name or k in combined for k in ("vehicle declarations", "auto declarations", "vin declaration")):
            return InsuranceDocumentType.VEHICLE_DECLARATIONS
        if any(k in name or k in combined for k in ("homeowners application", "ho-3 application", "homeowners_application", "dwelling application")):
            return InsuranceDocumentType.HOMEOWNERS_APPLICATION
        if any(k in name or k in combined for k in ("dwelling inspection", "home inspection", "residential inspection")):
            return InsuranceDocumentType.DWELLING_INSPECTION
        if any(k in name or k in combined for k in ("home claims history", "homeowners claims", "clue report")):
            return InsuranceDocumentType.HOME_CLAIMS_HISTORY

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

        # Trade credit / E&O / key person
        if any(k in name or k in combined for k in ("trade credit application", "trade_credit_application", "credit insurance application")):
            return InsuranceDocumentType.TRADE_CREDIT_APPLICATION
        if any(k in name or k in combined for k in ("ar aging", "a/r aging", "accounts receivable aging", "receivables aging")):
            return InsuranceDocumentType.AR_AGING_REPORT
        if any(k in name or k in combined for k in ("buyer list", "customer exposure", "buyer exposure", "credit limit schedule")):
            return InsuranceDocumentType.BUYER_EXPOSURE_LIST
        if any(k in name or k in combined for k in ("e&o application", "eo_application", "errors and omissions application", "professional liability application", "acord 126")):
            return InsuranceDocumentType.EO_APPLICATION
        if any(k in name or k in combined for k in ("engagement letter", "sample contract", "client agreement template")):
            return InsuranceDocumentType.ENGAGEMENT_LETTER
        if any(k in name or k in combined for k in ("key person application", "key_person_application", "keyman application", "key person medical")):
            return InsuranceDocumentType.KEY_PERSON_APPLICATION
        if any(k in name or k in combined for k in ("corporate resolution", "board resolution authorizing", "resolution authorizing policy")):
            return InsuranceDocumentType.CORPORATE_RESOLUTION

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
