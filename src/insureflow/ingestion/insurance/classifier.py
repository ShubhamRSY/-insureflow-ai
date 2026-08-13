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
    IRRELEVANT = "irrelevant"
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
    # Life — base package (US document set)
    PHOTO_ID = "photo_id"
    SOCIAL_SECURITY_NUMBER = "social_security_number"
    PROOF_OF_ADDRESS = "proof_of_address"
    HIPAA_AUTHORIZATION = "hipaa_authorization"
    MIB_RX_AUTHORIZATION = "mib_rx_authorization"
    HEALTH_QUESTIONNAIRE = "health_questionnaire"
    INCOME_PROOF = "income_proof"
    # Life — product-specific add-ons
    ILLUSTRATION_ACKNOWLEDGMENT = "illustration_acknowledgment"
    SUITABILITY_QUESTIONNAIRE = "suitability_questionnaire"
    PROSPECTUS_ACKNOWLEDGMENT = "prospectus_acknowledgment"
    SUB_ACCOUNT_ELECTION = "sub_account_election"
    BROKER_DEALER_FORM = "broker_dealer_form"
    SOURCE_OF_FUNDS = "source_of_funds"
    AML_DECLARATION = "aml_declaration"
    DIVIDEND_ELECTION = "dividend_election"
    INDEX_ALLOCATION_ELECTION = "index_allocation_election"
    GRADED_BENEFIT_DISCLOSURE = "graded_benefit_disclosure"
    MORTGAGE_STATEMENT = "mortgage_statement"
    LOAN_AGREEMENT = "loan_agreement"
    LENDER_INFORMATION = "lender_information"
    ENROLLMENT_FORM = "enrollment_form"
    RENEWAL_FORM = "renewal_form"
    CONVERSION_REQUEST_FORM = "conversion_request_form"
    BANK_ACH_FORM = "bank_ach_form"
    CHILD_BIRTH_CERTIFICATE = "child_birth_certificate"
    PREMIUM_WAIVER_RIDER = "premium_waiver_rider"
    RETIREMENT_ACCOUNT_STATEMENT = "retirement_account_statement"
    TAX_FORM_1098Q = "tax_form_1098q"
    COURT_ORDER = "court_order"
    ATTORNEY_DOCUMENTATION = "attorney_documentation"
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
    OSHA_LOG = "osha_log"
    ENVIRONMENTAL_SITE_ASSESSMENT = "environmental_site_assessment"
    LIQUOR_LICENSE = "liquor_license"
    EXPERIENCE_MOD_WORKSHEET = "experience_mod_worksheet"
    ACORD_126 = "acord_126"
    ACORD_127 = "acord_127"
    ACORD_130 = "acord_130"
    ACORD_131 = "acord_131"
    CYBER_QUESTIONNAIRE = "cyber_questionnaire"
    REPLACEMENT_1035 = "replacement_1035"
    SURPLUS_LINES_AFFIDAVIT = "surplus_lines_affidavit"


# Life insurance document types — used to route LLM extraction schema.
LIFE_DOCUMENT_TYPES: frozenset[str] = frozenset(
    {
        "life_application",
        "medical_exam",
        "aps_records",
        "beneficiary_form",
        "photo_id",
        "social_security_number",
        "proof_of_address",
        "hipaa_authorization",
        "mib_rx_authorization",
        "health_questionnaire",
        "income_proof",
        "illustration_acknowledgment",
        "suitability_questionnaire",
        "prospectus_acknowledgment",
        "sub_account_election",
        "broker_dealer_form",
        "source_of_funds",
        "aml_declaration",
        "dividend_election",
        "index_allocation_election",
        "graded_benefit_disclosure",
        "mortgage_statement",
        "loan_agreement",
        "lender_information",
        "enrollment_form",
        "renewal_form",
        "conversion_request_form",
        "bank_ach_form",
        "child_birth_certificate",
        "premium_waiver_rider",
        "retirement_account_statement",
        "tax_form_1098q",
        "court_order",
        "attorney_documentation",
    }
)


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
        if any(k in name or k in combined for k in ("beneficiary designation", "beneficiary_designation", "beneficiary form", "beneficiary_form")):
            return InsuranceDocumentType.BENEFICIARY_FORM

        # Life — base package (US document set)
        if any(k in name or k in combined for k in ("hipaa", "medical records release", "health information release")):
            return InsuranceDocumentType.HIPAA_AUTHORIZATION
        if any(k in name or k in combined for k in ("mib", "medical information bureau", "rx database", "rx check", "mib_rx")):
            return InsuranceDocumentType.MIB_RX_AUTHORIZATION
        if any(k in name or k in combined for k in ("photo id", "government id", "government-issued photo", "passport", "state id", "photo_id")):
            return InsuranceDocumentType.PHOTO_ID
        if any(k in name or k in combined for k in ("social security number", "social_security", "ssn form", "proof of ssn")):
            return InsuranceDocumentType.SOCIAL_SECURITY_NUMBER
        if any(k in name or k in combined for k in ("proof of address", "proof_of_address", "utility bill", "proof of residency", "lease agreement")):
            return InsuranceDocumentType.PROOF_OF_ADDRESS
        if any(k in name or k in combined for k in ("health questionnaire", "health_questionnaire", "health declaration", "medical questionnaire")):
            return InsuranceDocumentType.HEALTH_QUESTIONNAIRE
        if any(k in name or k in combined for k in ("income proof", "income_proof", "pay stub", "paystub", "w-2", "tax returns")):
            return InsuranceDocumentType.INCOME_PROOF

        # Life — product-specific add-ons
        if any(k in name or k in combined for k in ("illustration acknowledgment", "illustration acknowledgement", "illustration_acknowledgment", "cash value illustration")):
            return InsuranceDocumentType.ILLUSTRATION_ACKNOWLEDGMENT
        if any(k in name or k in combined for k in ("suitability questionnaire", "suitability", "risk profiling", "finra")):
            return InsuranceDocumentType.SUITABILITY_QUESTIONNAIRE
        if any(k in name or k in combined for k in ("prospectus",)):
            return InsuranceDocumentType.PROSPECTUS_ACKNOWLEDGMENT
        if any(k in name or k in combined for k in ("sub-account election", "sub-account allocation", "subaccount", "fund allocation election", "sub_account")):
            return InsuranceDocumentType.SUB_ACCOUNT_ELECTION
        if any(k in name or k in combined for k in ("broker-dealer", "broker dealer account", "broker_dealer")):
            return InsuranceDocumentType.BROKER_DEALER_FORM
        if any(k in name or k in combined for k in ("source of funds", "proof of lump sum", "funding source", "source_of_funds")):
            return InsuranceDocumentType.SOURCE_OF_FUNDS
        if any(k in name or k in combined for k in ("anti-money laundering", "aml declaration", "aml_declaration")):
            return InsuranceDocumentType.AML_DECLARATION
        if any(k in name or k in combined for k in ("dividend option", "dividend election", "bonus option election", "dividend_election")):
            return InsuranceDocumentType.DIVIDEND_ELECTION
        if any(k in name or k in combined for k in ("index allocation", "index crediting strategy", "index election", "index_allocation")):
            return InsuranceDocumentType.INDEX_ALLOCATION_ELECTION
        if any(k in name or k in combined for k in ("graded benefit disclosure", "graded_benefit_disclosure")):
            return InsuranceDocumentType.GRADED_BENEFIT_DISCLOSURE
        if any(k in name or k in combined for k in ("mortgage statement", "mortgage documents", "loan statement", "mortgage_statement")):
            return InsuranceDocumentType.MORTGAGE_STATEMENT
        if any(k in name or k in combined for k in ("loan agreement", "credit account documents", "credit agreement", "loan_agreement")):
            return InsuranceDocumentType.LOAN_AGREEMENT
        if any(k in name or k in combined for k in ("lender information", "lender's name", "lender name", "lender account number", "lender_information")):
            return InsuranceDocumentType.LENDER_INFORMATION
        if any(k in name or k in combined for k in ("enrollment form", "enrollment packet", "enrollment_form")):
            return InsuranceDocumentType.ENROLLMENT_FORM
        if any(k in name or k in combined for k in ("renewal form", "renewal_form")):
            return InsuranceDocumentType.RENEWAL_FORM
        if any(k in name or k in combined for k in ("conversion request", "conversion form", "conversion_request")):
            return InsuranceDocumentType.CONVERSION_REQUEST_FORM
        if any(k in name or k in combined for k in ("ach form", "ach authorization", "bank account", "auto-debit", "bank_ach", "direct deposit")):
            return InsuranceDocumentType.BANK_ACH_FORM
        if any(k in name or k in combined for k in ("birth certificate", "birth_certificate")):
            return InsuranceDocumentType.CHILD_BIRTH_CERTIFICATE
        if any(k in name or k in combined for k in ("premium waiver", "waiver rider", "premium_waiver")):
            return InsuranceDocumentType.PREMIUM_WAIVER_RIDER
        if any(k in name or k in combined for k in ("retirement account statement", "retirement account", "custodian transfer", "401(k)", "rollover", "retirement_account")):
            return InsuranceDocumentType.RETIREMENT_ACCOUNT_STATEMENT
        if any(k in name or k in combined for k in ("1098-q", "form 1098", "tax_form_1098q")):
            return InsuranceDocumentType.TAX_FORM_1098Q
        if any(k in name or k in combined for k in ("court order", "settlement agreement", "court_order")):
            return InsuranceDocumentType.COURT_ORDER
        if any(k in name or k in combined for k in ("attorney", "legal representative", "attorney_documentation")):
            return InsuranceDocumentType.ATTORNEY_DOCUMENTATION
        if any(k in name or k in combined for k in ("simplified issue application", "no-exam application", "guaranteed issue application")):
            return InsuranceDocumentType.LIFE_APPLICATION
        if any(k in name or k in combined for k in ("osha 300", "osha-300", "osha log", "300a summary")):
            return InsuranceDocumentType.OSHA_LOG
        if any(k in name or k in combined for k in ("phase i esa", "phase 1 esa", "environmental site assessment", "phase i environmental")):
            return InsuranceDocumentType.ENVIRONMENTAL_SITE_ASSESSMENT
        if any(k in name or k in combined for k in ("liquor license", "abc license", "alcohol beverage")):
            return InsuranceDocumentType.LIQUOR_LICENSE
        if any(k in name or k in combined for k in ("e-mod worksheet", "emod worksheet", "experience mod worksheet", "experience modification worksheet", "ncci worksheet")):
            return InsuranceDocumentType.EXPERIENCE_MOD_WORKSHEET
        if any(k in name or k in combined for k in ("acord 126", "acord-126")):
            return InsuranceDocumentType.ACORD_126
        if any(k in name or k in combined for k in ("acord 127", "acord-127")):
            return InsuranceDocumentType.ACORD_127
        if any(k in name or k in combined for k in ("acord 130", "acord-130")):
            return InsuranceDocumentType.ACORD_130
        if any(k in name or k in combined for k in ("acord 131", "acord-131")):
            return InsuranceDocumentType.ACORD_131
        if any(k in name or k in combined for k in ("cyber questionnaire", "cyber application", "ransomware questionnaire")):
            return InsuranceDocumentType.CYBER_QUESTIONNAIRE
        if any(k in name or k in combined for k in ("1035 exchange", "replacement form", "naic replacement", "absolute assignment")):
            return InsuranceDocumentType.REPLACEMENT_1035
        if any(k in name or k in combined for k in ("diligent search", "surplus lines affidavit", "stamping office", "due diligence affidavit")):
            return InsuranceDocumentType.SURPLUS_LINES_AFFIDAVIT
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

        if any(k in combined for k in ("balance sheet", "income statement", "financial statement", "financial_statement", "annual revenue")):
            return InsuranceDocumentType.FINANCIAL_STATEMENT

        # Demote obvious non-UW junk before defaulting to supplemental
        if any(
            k in combined
            for k in (
                "restaurant menu",
                "curriculum vitae",
                "wedding invitation",
                "spotify playlist",
                "homework assignment",
                "recipe for",
            )
        ):
            return InsuranceDocumentType.IRRELEVANT

        return InsuranceDocumentType.SUPPLEMENTAL
