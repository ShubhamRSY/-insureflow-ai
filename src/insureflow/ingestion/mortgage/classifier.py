from __future__ import annotations

import re
from pathlib import Path

from insureflow.models.mortgage import MortgageDocumentType, ProductLine


class MortgageDocumentClassifier:
    """Classify mortgage documents by filename hints and content keywords."""

    FILENAME_RULES: list[tuple[re.Pattern[str], MortgageDocumentType]] = [
        (re.compile(r"w2", re.I), MortgageDocumentType.W2),
        (re.compile(r"pay_stub", re.I), MortgageDocumentType.PAY_STUB),
        (re.compile(r"tax_return|1040|federal_tax", re.I), MortgageDocumentType.TAX_RETURN_1040),
        (re.compile(r"1065|business_tax", re.I), MortgageDocumentType.TAX_RETURN_1065),
        (re.compile(r"profit_loss|schedule_c", re.I), MortgageDocumentType.PROFIT_LOSS),
        (re.compile(r"bank_statement", re.I), MortgageDocumentType.BANK_STATEMENT),
        (re.compile(r"investment_account", re.I), MortgageDocumentType.INVESTMENT_STATEMENT),
        (re.compile(r"401k|retirement", re.I), MortgageDocumentType.RETIREMENT_401K),
        (re.compile(r"gift_letter", re.I), MortgageDocumentType.GIFT_LETTER),
        (re.compile(r"credit_report", re.I), MortgageDocumentType.CREDIT_REPORT),
        (re.compile(r"credit_card", re.I), MortgageDocumentType.CREDIT_CARD_STATEMENT),
        (re.compile(r"car_loan|auto_loan", re.I), MortgageDocumentType.AUTO_LOAN_STATEMENT),
        (re.compile(r"student_loan", re.I), MortgageDocumentType.STUDENT_LOAN_STATEMENT),
        (re.compile(r"rent_history", re.I), MortgageDocumentType.RENT_HISTORY),
        (re.compile(r"home_appraisal|appraisal_report", re.I), MortgageDocumentType.RESIDENTIAL_APPRAISAL),
        (re.compile(r"commercial_appraisal", re.I), MortgageDocumentType.COMMERCIAL_APPRAISAL),
        (re.compile(r"purchase_agreement", re.I), MortgageDocumentType.PURCHASE_AGREEMENT),
        (re.compile(r"homeowners_insurance|insurance_proof", re.I), MortgageDocumentType.HOMEOWNERS_INSURANCE),
        (re.compile(r"government_id|drivers_license", re.I), MortgageDocumentType.GOVERNMENT_ID),
        (re.compile(r"divorce_decree", re.I), MortgageDocumentType.DIVORCE_DECREE),
        (re.compile(r"balance_sheet", re.I), MortgageDocumentType.BALANCE_SHEET),
        (re.compile(r"commercial_lease|lease_agreement|lease_suite", re.I), MortgageDocumentType.COMMERCIAL_LEASE),
        (re.compile(r"estoppel", re.I), MortgageDocumentType.TENANT_ESTOPPEL),
        (re.compile(r"rent_roll", re.I), MortgageDocumentType.RENT_ROLL),
        (re.compile(r"operating_statement", re.I), MortgageDocumentType.OPERATING_STATEMENT),
        (re.compile(r"business_credit", re.I), MortgageDocumentType.BUSINESS_CREDIT_REPORT),
        (re.compile(r"debt_schedule", re.I), MortgageDocumentType.BUSINESS_DEBT_SCHEDULE),
        (re.compile(r"corporate_governance|operating_agreement", re.I), MortgageDocumentType.CORPORATE_GOVERNANCE),
        (re.compile(r"zoning", re.I), MortgageDocumentType.ZONING_REPORT),
        (re.compile(r"phase_i|environmental", re.I), MortgageDocumentType.PHASE_I_ESA),
        (re.compile(r"title_insurance|title_policy", re.I), MortgageDocumentType.TITLE_POLICY),
        (re.compile(r"property_survey|land_survey", re.I), MortgageDocumentType.PROPERTY_SURVEY),
        (re.compile(r"capex", re.I), MortgageDocumentType.CAPEX_BUDGET),
        (re.compile(r"property_manager|resume", re.I), MortgageDocumentType.PROPERTY_MANAGER_RESUME),
        # Underwriting doc types
        (re.compile(r"1003|urla|loan_application|uniform_residential", re.I), MortgageDocumentType.LOAN_APPLICATION_1003),
        (re.compile(r"pre.?approval|preapproval", re.I), MortgageDocumentType.PRE_APPROVAL_LETTER),
        (re.compile(r"flood|cert.*flood|flood.*zone", re.I), MortgageDocumentType.FLOOD_ZONE_DETERMINATION),
        (re.compile(r"title_commitment|title_commit|preliminary_title", re.I), MortgageDocumentType.TITLE_COMMITMENT),
        (re.compile(r"voe|verification.*employment", re.I), MortgageDocumentType.VERIFICATION_OF_EMPLOYMENT),
        (re.compile(r"vod|verification.*deposit", re.I), MortgageDocumentType.VERIFICATION_OF_DEPOSIT),
        (re.compile(r"hazard_insurance|declaration.*page|homeowners.*dec", re.I), MortgageDocumentType.HAZARD_INSURANCE_DECLARATION),
        (re.compile(r"property_tax|tax_bill|tax_receipt", re.I), MortgageDocumentType.PROPERTY_TAX_BILL),
        (re.compile(r"uw_approval|underwriting_memo|approval_memo", re.I), MortgageDocumentType.UNDERWRITING_APPROVAL_MEMO),
        (re.compile(r"closing_disclosure|trid.*closing|cd.*trid", re.I), MortgageDocumentType.CLOSING_DISCLOSURE),
        (re.compile(r"loan_estimate", re.I), MortgageDocumentType.LOAN_ESTIMATE),
        (re.compile(r"payoff_statement|payoff.*letter", re.I), MortgageDocumentType.PAYOFF_STATEMENT),
        (re.compile(r"rental_history|rental.*letter|landlord.*reference", re.I), MortgageDocumentType.RENTAL_HISTORY),
        (re.compile(r"mortgage_statement|mtg.*statement", re.I), MortgageDocumentType.MORTGAGE_STATEMENT),
    ]

    CONTENT_RULES: list[tuple[re.Pattern[str], MortgageDocumentType, int]] = [
        (re.compile(r"form w-2|wage and tax statement", re.I), MortgageDocumentType.W2, 5),
        (re.compile(r"pay period|pay date|net pay", re.I), MortgageDocumentType.PAY_STUB, 4),
        (re.compile(r"form 1040|individual income tax return", re.I), MortgageDocumentType.TAX_RETURN_1040, 5),
        (re.compile(r"form 1065|partnership return", re.I), MortgageDocumentType.TAX_RETURN_1065, 5),
        (re.compile(r"profit.*loss|schedule c", re.I), MortgageDocumentType.PROFIT_LOSS, 3),
        (re.compile(r"account statement|ending balance|beginning balance", re.I), MortgageDocumentType.BANK_STATEMENT, 4),
        (re.compile(r"equifax|experian|transunion|credit score", re.I), MortgageDocumentType.CREDIT_REPORT, 5),
        (re.compile(r"uniform residential appraisal|fhlmc form 70", re.I), MortgageDocumentType.RESIDENTIAL_APPRAISAL, 5),
        (re.compile(r"income approach|cap rate|noi", re.I), MortgageDocumentType.COMMERCIAL_APPRAISAL, 4),
        (re.compile(r"purchase agreement|earnest money", re.I), MortgageDocumentType.PURCHASE_AGREEMENT, 4),
        (re.compile(r"gift letter|non.?repayable", re.I), MortgageDocumentType.GIFT_LETTER, 4),
        (re.compile(r"rent roll|tenant estoppel", re.I), MortgageDocumentType.RENT_ROLL, 4),
        (re.compile(r"commercial lease|triple net|nnn", re.I), MortgageDocumentType.COMMERCIAL_LEASE, 4),
        (re.compile(r"balance sheet|member'?s equity", re.I), MortgageDocumentType.BALANCE_SHEET, 4),
        (re.compile(r"paydex|dun & bradstreet|d&b", re.I), MortgageDocumentType.BUSINESS_CREDIT_REPORT, 5),
        (re.compile(r"phase i environmental|recognized environmental condition", re.I), MortgageDocumentType.PHASE_I_ESA, 5),
        (re.compile(r"title insurance|schedule b", re.I), MortgageDocumentType.TITLE_POLICY, 4),
        (re.compile(r"alta|land survey|encroachment", re.I), MortgageDocumentType.PROPERTY_SURVEY, 3),
        (re.compile(r"debt service coverage|dscr", re.I), MortgageDocumentType.OPERATING_STATEMENT, 4),
        # Underwriting doc content rules
        (re.compile(r"uniform residential loan application|form 1003|urla 1003", re.I), MortgageDocumentType.LOAN_APPLICATION_1003, 5),
        (re.compile(r"pre.?approval letter|preapproval", re.I), MortgageDocumentType.PRE_APPROVAL_LETTER, 4),
        (re.compile(r"special flood hazard|flood zone|fema flood", re.I), MortgageDocumentType.FLOOD_ZONE_DETERMINATION, 5),
        (re.compile(r"title commitment|schedule b.*exception|preliminary title", re.I), MortgageDocumentType.TITLE_COMMITMENT, 5),
        (re.compile(r"verification of employment|voe.*form", re.I), MortgageDocumentType.VERIFICATION_OF_EMPLOYMENT, 4),
        (re.compile(r"verification of deposit|vod.*form", re.I), MortgageDocumentType.VERIFICATION_OF_DEPOSIT, 4),
        (re.compile(r"hazard insurance|declaration page|cov.*a.*deductible", re.I), MortgageDocumentType.HAZARD_INSURANCE_DECLARATION, 4),
        (re.compile(r"property tax|tax bill|tax receipt", re.I), MortgageDocumentType.PROPERTY_TAX_BILL, 3),
        (re.compile(r"underwriting approval|approval memo|uw memo", re.I), MortgageDocumentType.UNDERWRITING_APPROVAL_MEMO, 4),
        (re.compile(r"closing disclosure|trid|final cd", re.I), MortgageDocumentType.CLOSING_DISCLOSURE, 5),
        (re.compile(r"loan estimate|good faith", re.I), MortgageDocumentType.LOAN_ESTIMATE, 4),
        (re.compile(r"payoff statement|payoff amount|payoff letter", re.I), MortgageDocumentType.PAYOFF_STATEMENT, 4),
        (re.compile(r"rental history|rental reference|landlord confirmation", re.I), MortgageDocumentType.RENTAL_HISTORY, 3),
        (re.compile(r"mortgage statement|current mortgage|existing mortgage", re.I), MortgageDocumentType.MORTGAGE_STATEMENT, 3),
    ]

    @classmethod
    def infer_product_line(cls, path: str) -> ProductLine:
        lowered = path.lower()
        if "commercial_mortgage" in lowered:
            return ProductLine.COMMERCIAL_MORTGAGE
        return ProductLine.RESIDENTIAL_MORTGAGE

    @classmethod
    def classify(cls, content: str, filename: str = "") -> MortgageDocumentType:
        name = Path(filename).name if filename else ""

        for pattern, doc_type in cls.FILENAME_RULES:
            if pattern.search(name):
                return doc_type

        sample = content[:4000]
        scores: dict[MortgageDocumentType, int] = {}
        for pattern, doc_type, weight in cls.CONTENT_RULES:
            hits = len(pattern.findall(sample))
            if hits:
                scores[doc_type] = scores.get(doc_type, 0) + hits * weight

        if scores:
            return max(scores, key=scores.get)

        return MortgageDocumentType.UNKNOWN
