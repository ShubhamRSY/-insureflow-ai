from __future__ import annotations

import re
from typing import Callable

from insureflow.models.mortgage import ExtractedMortgageField, MortgageDocumentType


def _field(name: str, value: str, confidence: float = 0.9, context: str = "") -> list[ExtractedMortgageField]:
    if not value or not str(value).strip():
        return []
    return [ExtractedMortgageField(field_name=name, value=str(value).strip(), confidence=confidence, context=context)]


def _first(pattern: re.Pattern[str], text: str, group: int = 1) -> str:
    match = pattern.search(text)
    if match:
        val = match.group(group)
        return val.strip() if val else ""
    return ""


def _money(pattern: re.Pattern[str], text: str) -> str:
    return _first(pattern, text)


def extract_w2(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    employee = _first(
        re.compile(
            r"Employee Name:.*?(?:\n\s*[^\n]*?\s)?([A-Z][a-z]+(?: [A-Z]\.?)? [A-Z][a-z]+)\s*(?:\n|SSN:)",
            re.I | re.S,
        ),
        text,
    )
    if not employee:
        employee = _first(re.compile(r"Employee Name:\s*(.+?)(?:\s+SSN:|\n)", re.I), text)
    for key, pattern in {
        "employee_name": re.compile(r"__employee__"),
        "employer_name": re.compile(r"Employer Name:\s*\n\s*(.+?)(?:\n\s*\d|\n\s*[A-Z])", re.I | re.S),
        "wages_box1": re.compile(r"1\.\s*Wages.*?compensation.*?([\d,]+\.?\d*)", re.I | re.S),
        "federal_tax_withheld": re.compile(r"2\.\s*Federal income tax withheld.*?([\d,]+\.?\d*)", re.I | re.S),
        "tax_year": re.compile(r"Form W-2 \(Rev\.\s*(\d{4})\)|^\s*(\d{4})\s*\|", re.I | re.M),
    }.items():
        if key == "employee_name":
            fields[key] = _field(key, employee)
            continue
        if key == "tax_year":
            val = _first(pattern, text) or _first(pattern, text, group=2)
            fields[key] = _field(key, val)
            continue
        val = _first(pattern, text) if key != "wages_box1" and key != "federal_tax_withheld" else _money(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_pay_stub(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "employee_name": re.compile(r"Employee(?: Name)?:\s*(.+)", re.I),
        "employer_name": re.compile(r"Employer(?: Name)?:\s*(.+)", re.I),
        "pay_period": re.compile(r"Pay Period:\s*(.+)", re.I),
        "gross_pay_current": re.compile(r"Gross Pay.*?Current\s+\$?([\d,]+\.?\d*)", re.I | re.S),
        "gross_pay_ytd": re.compile(r"Gross Pay.*?YTD\s+\$?([\d,]+\.?\d*)", re.I | re.S),
        "net_pay": re.compile(r"Net Pay(?: Current)?:\s*\$?([\d,]+\.?\d*)", re.I),
    }.items():
        val = _money(pattern, text) if "pay" in key or "gross" in key else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_tax_return_1040(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "primary_taxpayer": re.compile(r"PRIMARY TAXPAYER:\s*\n\s*Name:\s*(.+)", re.I),
        "spouse": re.compile(r"SPOUSE:\s*\n\s*Name:\s*(.+)", re.I),
        "filing_status": re.compile(r"FILING STATUS:\s*(.+)", re.I),
        "total_income": re.compile(
            r"(?:TOTAL INCOME \(Line 9\)|TOTAL INCOME \(line 9\)|9\.\s*TOTAL INCOME \(line 9\)).*?([\d,]+\.?\d*)",
            re.I | re.S,
        ),
        "adjusted_gross_income": re.compile(
            r"(?:ADJUSTED GROSS INCOME \(Line 11\)|11\.\s*ADJUSTED GROSS INCOME \(AGI\)).*?([\d,]+\.?\d*)",
            re.I | re.S,
        ),
        "wages_line1": re.compile(
            r"(?:Line 1:.*W-2\)|TOTAL WAGES:|Wages, salaries, tips.*?TOTAL WAGES:).*?([\d,]+\.?\d*)",
            re.I | re.S,
        ),
        "business_income": re.compile(r"Business income \(Schedule C.*?\)\s+\$?([\d,]+\.?\d*)", re.I),
        "taxable_income": re.compile(r"TAXABLE INCOME \(Line 15\)\s+\$?([\d,]+\.?\d*)", re.I),
    }.items():
        val = _money(pattern, text) if any(x in key for x in ("income", "wages", "business")) else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_credit_report(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    bureau = "Equifax" if "equifax" in text.lower() else "Experian" if "experian" in text.lower() else "TransUnion" if "transunion" in text.lower() else "Unknown"
    fields["bureau"] = _field("bureau", bureau)

    score = _first(re.compile(r"(?:Equifax|Experian|TransUnion)?\s*Credit Score:\s*(\d{3})", re.I), text)
    if not score:
        rep_scores = re.findall(r"REPRESENTATIVE SCORE:.*?(\d{3})", text, re.I | re.S)
        if rep_scores:
            score = min(rep_scores, key=int)
    if not score:
        mid_scores = re.findall(r"Median scores?:\s*(\d{3})\s*/\s*(\d{3})", text, re.I)
        if mid_scores:
            score = min(mid_scores[0], key=int)

    for key, pattern in {
        "borrower_name": re.compile(r"BORROWER:\s*(.+?)(?:\s+CO-BORROWER:|$)", re.I),
        "credit_score": re.compile(r"__credit_score__"),  # filled below
        "total_balance": re.compile(
            r"(?:Total Balance:|Current Balance.*?JOINT)\s+(?:\$?[\d,]+\.?\d*\s+){0,2}\$?([\d,]+\.?\d*)",
            re.I | re.S,
        ),
        "total_monthly_payment": re.compile(
            r"Monthly Payment\s+(?:\$?[\d,]+\.?\d*\s+){1,2}\$?([\d,]+\.?\d*)",
            re.I,
        ),
        "utilization_rate": re.compile(r"(?:Utilization Rate:|Credit Utilization)\s*([\d.]+)%?", re.I),
        "open_accounts": re.compile(r"Open Accounts:\s*(\d+)", re.I),
    }.items():
        if key == "credit_score":
            fields[key] = _field(key, score)
            continue
        val = _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_bank_statement(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "account_holder": re.compile(r"Customer Name:\s*(.+)", re.I),
        "account_type": re.compile(r"(CHECKING|SAVINGS|MONEY MARKET)", re.I),
        "statement_period": re.compile(r"Statement Period:\s*(.+)", re.I),
        "beginning_balance": re.compile(r"Beginning Balance.*?\$\s*([\d,]+\.?\d*)", re.I | re.S),
        "ending_balance": re.compile(r"ENDING BALANCE.*?\$\s*([\d,]+\.?\d*)", re.I | re.S),
    }.items():
        val = _money(pattern, text) if "balance" in key else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_appraisal(text: str, commercial: bool = False) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "property_address": re.compile(r"Property Address:\s*(.+?)(?:\n\s*\(|$)", re.I | re.S),
        "appraised_value": re.compile(
            r"(?:Opinion of Market Value|Final Reconciled Value|Indicated Value|Appraised Value).*?\$\s*([\d,]+)",
            re.I | re.S,
        ),
        "appraisal_date": re.compile(r"Appraisal Date:\s*(.+)", re.I),
        "noi": re.compile(r"Net Operating Income \(NOI\).*?\$\s*([\d,]+)", re.I | re.S),
        "cap_rate": re.compile(r"Cap Rate:\s*([\d.]+)%?", re.I),
    }.items():
        val = _money(pattern, text) if key in ("appraised_value", "noi") else _first(pattern, text)
        fields[key] = _field(key, val.replace("\n", " ").strip())
    if commercial:
        fields["property_type"] = _field("property_type", "commercial")
    else:
        fields["property_type"] = _field("property_type", "residential")
    return fields


def extract_purchase_agreement(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "buyer_name": re.compile(r"Buyer(?:\(s\))?:\s*(.+)", re.I),
        "seller_name": re.compile(r"Seller(?:\(s\))?:\s*(.+)", re.I),
        "property_address": re.compile(r"Property(?: Address)?:\s*(.+)", re.I),
        "purchase_price": re.compile(r"(?:Purchase Price|Sale Price):\s*\$?([\d,]+)", re.I),
        "earnest_money": re.compile(r"Earnest Money:\s*\$?([\d,]+)", re.I),
    }.items():
        val = _money(pattern, text) if "price" in key or "money" in key else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_gift_letter(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "donor_name": re.compile(r"Donor(?: Name)?:\s*(.+)", re.I),
        "recipient_name": re.compile(r"(?:Recipient|Borrower)(?: Name)?:\s*(.+)", re.I),
        "gift_amount": re.compile(r"(?:Gift )?Amount:\s*\$?([\d,]+)", re.I),
    }.items():
        val = _money(pattern, text) if "amount" in key else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_business_credit(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "business_name": re.compile(r"Business Name:\s*(.+)", re.I),
        "paydex_score": re.compile(r"PAYDEX Score:\s*(\d+)", re.I),
        "annual_sales": re.compile(r"Annual Sales.*?:\s*\$?([\d,]+)", re.I),
        "total_outstanding": re.compile(r"Total Outstanding:\s*\$?([\d,]+)", re.I),
    }.items():
        val = _money(pattern, text) if key in ("annual_sales", "total_outstanding") else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_rent_roll(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    units = len(re.findall(r"(?:Unit|Suite)\s+[A-Z0-9]+", text, re.I))
    vacant = len(re.findall(r"VACANT|vacant", text))
    total_rent = sum(float(m.replace(",", "")) for m in re.findall(r"(?:Base Rent|Monthly Rent):\s*\$?([\d,]+)", text, re.I))
    fields["unit_count"] = _field("unit_count", str(units))
    fields["vacant_units"] = _field("vacant_units", str(vacant))
    fields["total_monthly_rent"] = _field("total_monthly_rent", f"{total_rent:.2f}")
    return fields


def extract_operating_statement(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "noi": re.compile(r"Net Operating Income.*?\$\s*([\d,]+)", re.I),
        "dscr": re.compile(r"DSCR\s*([\d.]+)x?", re.I),
        "effective_gross_income": re.compile(r"Effective Gross Income.*?\$\s*([\d,]+)", re.I),
    }.items():
        fields[key] = _field(key, _money(pattern, text))
    return fields


def extract_form_1003(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "borrower_name": re.compile(r"BORROWER(?: NAME)?:\s*(.+)", re.I),
        "co_borrower_name": re.compile(r"CO.?BORROWER(?: NAME)?:\s*(.+)", re.I),
        "purpose": re.compile(r"PURPOSE OF LOAN:\s*(.+)", re.I),
        "amount": re.compile(r"LOAN AMOUNT:\s*\$?([\d,]+)", re.I),
        "property_address": re.compile(r"PROPERTY ADDRESS:\s*(.+)", re.I),
        "occupancy": re.compile(r"OCCUPANCY:\s*(.+)", re.I),
        "loan_type": re.compile(r"LOAN TYPE:\s*(.{5,30})", re.I),
        "loan_term": re.compile(r"LOAN TERM:\s*(.{5,20})", re.I),
        "amortization": re.compile(r"AMORTIZATION:\s*(.{5,20})", re.I),
        "employer_name": re.compile(r"EMPLOYER(?: NAME)?:\s*(.+)", re.I),
        "employment_years": re.compile(r"(?:YEARS|YRS) (?:ON JOB|EMPLOYED|AT JOB):\s*(\d+)", re.I),
        "monthly_income": re.compile(r"(?:MONTHLY|GROSS MONTHLY) (?:INCOME|BASE):?\s*\$?([\d,]+)", re.I),
        "down_payment": re.compile(r"DOWN PAYMENT(?: SOURCE)?:\s*(.+?(?:\$?[\d,]+)?)", re.I),
        "present_address": re.compile(r"PRESENT ADDRESS:\s*(.+)", re.I),
        "years_at_address": re.compile(r"YEARS AT ADDRESS:\s*(\d+)", re.I),
        "ssn": re.compile(r"SSN(?:#)?:\s*(\d{3}-\d{2}-\d{4})", re.I),
        "dob": re.compile(r"DOB|DATE OF BIRTH:\s*([\d/]+)", re.I),
    }.items():
        val = _money(pattern, text) if any(x in key for x in ("amount", "income", "payment")) else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_title_commitment(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "commitment_number": re.compile(r"Commitment (?:No|Number|#):\s*(\S+)", re.I),
        "insured_borrower": re.compile(r"Insured (?:Borrower|Party):\s*(.+)", re.I),
        "property_address": re.compile(r"Property Address:\s*(.+)", re.I),
        "amount": re.compile(r"(?:Amount|Policy Amount|Liability):\s*\$?([\d,]+)", re.I),
        "effective_date": re.compile(r"Effective Date:\s*(.+)", re.I),
        "exceptions": re.compile(r"(?:Schedule B|Exceptions).*?(\d+)\s*(?:item|exception)", re.I | re.S),
    }.items():
        val = _money(pattern, text) if key == "amount" else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_flood_cert(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "property_address": re.compile(r"Property Address:\s*(.+)", re.I),
        "flood_zone": re.compile(r"Flood Zone:\s*(\S+)", re.I),
        "community": re.compile(r"Community Name:\s*(.+)", re.I),
        "panel": re.compile(r"Panel(?: Number)?:\s*(\S+)", re.I),
        "in_special_flood_hazard": re.compile(r"(?:In|Within) (?:Special Flood Hazard|SFHA):\s*(Yes|No)", re.I),
        "map_date": re.compile(r"(?:Map|FIRM) Date:\s*(\S+)", re.I),
    }.items():
        fields[key] = _field(key, _first(pattern, text))
    return fields


def extract_uw_approval_memo(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "borrower_name": re.compile(r"Borrower(?: Name)?:\s*(.+)", re.I),
        "property_address": re.compile(r"Property Address:\s*(.+)", re.I),
        "decision": re.compile(r"(?:Underwriting |UW )?Decision:\s*(.{5,20})", re.I),
        "approved_amount": re.compile(r"Approved Amount:\s*\$?([\d,]+)", re.I),
        "loan_amount": re.compile(r"Loan Amount:\s*\$?([\d,]+)", re.I),
        "ltv": re.compile(r"(?:Combined )?LTV:\s*([\d.]+)%?", re.I),
        "dti": re.compile(r"DTI(?: Ratio)?:\s*([\d.]+)%?", re.I),
        "conditions": re.compile(r"Conditions(?: to Close)?:\s*(.{10,200})", re.I),
    }.items():
        val = _money(pattern, text) if any(x in key for x in ("amount",)) else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_closing_disclosure(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "borrower_name": re.compile(r"BORROWER:\s*(.+)", re.I),
        "seller_name": re.compile(r"SELLER:\s*(.+)", re.I),
        "lender_name": re.compile(r"LENDER:\s*(.+)", re.I),
        "property_address": re.compile(r"PROPERTY:\s*(.+)", re.I),
        "loan_amount": re.compile(r"Loan Amount.*?\$?([\d,]+)", re.I | re.S),
        "interest_rate": re.compile(r"Interest Rate.*?([\d.]+)%", re.I),
        "monthly_payment": re.compile(r"Monthly Payment.*?\$?([\d,]+)", re.I | re.S),
        "closing_cash": re.compile(r"(?:Cash to Close|Total Closing Costs).*?\$?([\d,]+)", re.I | re.S),
        "closing_date": re.compile(r"Closing Date:\s*(.+)", re.I),
    }.items():
        val = _money(pattern, text) if any(x in key for x in ("amount", "payment", "cash")) else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_employment_verification(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "employee_name": re.compile(r"Employee Name:\s*(.+)", re.I),
        "employer_name": re.compile(r"Employer Name:\s*(.+)", re.I),
        "employer_phone": re.compile(r"Employer Phone:\s*(.+)", re.I),
        "position": re.compile(r"Position/Title:\s*(.+)", re.I),
        "employment_start": re.compile(r"Date of Employment:\s*(.+)", re.I),
        "salary": re.compile(r"(?:Current |Annual )?Salary|Wages:\s*\$?([\d,]+)", re.I),
        "hours_per_week": re.compile(r"Hours.*Week:\s*(\d+)", re.I),
        "verified": re.compile(r"Verified by:\s*(.+)", re.I),
        "verification_date": re.compile(r"Verification Date:\s*(.+)", re.I),
    }.items():
        val = _money(pattern, text) if key == "salary" else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_hazard_insurance(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "insured_name": re.compile(r"Insured Name|Named Insured:\s*(.+)", re.I),
        "property_address": re.compile(r"Property(?: Location)?:\s*(.+)", re.I),
        "policy_number": re.compile(r"Policy Number:\s*(\S+)", re.I),
        "effective_date": re.compile(r"Effective Date:\s*(.+)", re.I),
        "expiration_date": re.compile(r"Expiration Date:\s*(.+)", re.I),
        "coverage_a": re.compile(r"Cov[^:]*A[^:]*:\s*\$?([\d,]+)", re.I),
        "premium": re.compile(r"(?:Total |Annual )?Premium:\s*\$?([\d,]+)", re.I),
        "deductible": re.compile(r"Deductible:\s*\$?([\d,]+)", re.I),
    }.items():
        val = _money(pattern, text) if any(x in key for x in ("coverage", "premium", "deductible")) else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_property_tax(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "property_address": re.compile(r"Property Address|Situs:\s*(.+)", re.I),
        "parcel_id": re.compile(r"(?:Parcel|Parcel ID|APN|PIN):\s*(\S+)", re.I),
        "tax_year": re.compile(r"Tax (?:Year|Period):\s*(\d{4})", re.I),
        "assessed_value": re.compile(r"Assessed Value:\s*\$?([\d,]+)", re.I),
        "tax_amount": re.compile(r"(?:Total |Annual )?Tax(?:es)? (?:Due|Amount):\s*\$?([\d,]+)", re.I),
        "paid_date": re.compile(r"Paid (?:Date|On):\s*(.+)", re.I),
        "due_date": re.compile(r"Due Date:\s*(.+)", re.I),
    }.items():
        val = _money(pattern, text) if any(x in key for x in ("value", "amount")) else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_pre_approval(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "borrower_name": re.compile(r"Borrower(?: Name)?:\s*(.+)", re.I),
        "pre_approved_amount": re.compile(r"Pre.?Approved (?:Loan )?Amount:\s*\$?([\d,]+)", re.I),
        "program": re.compile(r"Loan Program|Product:\s*(.{5,40})", re.I),
        "expiration_date": re.compile(r"Expiration Date:\s*(.+)", re.I),
        "interest_rate": re.compile(r"Interest Rate:\s*([\d.]+)%?", re.I),
        "property_address": re.compile(r"Property Address:\s*(.+)", re.I),
    }.items():
        val = _money(pattern, text) if any(x in key for x in ("amount",)) else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_generic(text: str) -> dict[str, list[ExtractedMortgageField]]:
    """Fallback: extract labeled key-value pairs common across mortgage docs."""
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for match in re.finditer(r"^([A-Za-z][A-Za-z /]+):\s*(.+)$", text, re.M):
        key = match.group(1).strip().lower().replace(" ", "_")
        val = match.group(2).strip()
        if len(key) < 40 and len(val) < 200:
            fields.setdefault(key, []).extend(_field(key, val, confidence=0.6))
    return fields


EXTRACTOR_MAP: dict[MortgageDocumentType, Callable[[str], dict[str, list[ExtractedMortgageField]]]] = {
    MortgageDocumentType.W2: extract_w2,
    MortgageDocumentType.PAY_STUB: extract_pay_stub,
    MortgageDocumentType.TAX_RETURN_1040: extract_tax_return_1040,
    MortgageDocumentType.TAX_RETURN_1065: extract_tax_return_1040,
    MortgageDocumentType.PROFIT_LOSS: extract_tax_return_1040,
    MortgageDocumentType.SCHEDULE_C: extract_tax_return_1040,
    MortgageDocumentType.CREDIT_REPORT: extract_credit_report,
    MortgageDocumentType.BANK_STATEMENT: extract_bank_statement,
    MortgageDocumentType.INVESTMENT_STATEMENT: extract_bank_statement,
    MortgageDocumentType.RETIREMENT_401K: extract_bank_statement,
    MortgageDocumentType.RESIDENTIAL_APPRAISAL: lambda t: extract_appraisal(t, commercial=False),
    MortgageDocumentType.COMMERCIAL_APPRAISAL: lambda t: extract_appraisal(t, commercial=True),
    MortgageDocumentType.PURCHASE_AGREEMENT: extract_purchase_agreement,
    MortgageDocumentType.GIFT_LETTER: extract_gift_letter,
    MortgageDocumentType.BUSINESS_CREDIT_REPORT: extract_business_credit,
    MortgageDocumentType.RENT_ROLL: extract_rent_roll,
    MortgageDocumentType.OPERATING_STATEMENT: extract_operating_statement,
    MortgageDocumentType.LOAN_APPLICATION_1003: extract_form_1003,
    MortgageDocumentType.UNIFORM_RESIDENTIAL_LOAN_APPLICATION: extract_form_1003,
    MortgageDocumentType.PRE_APPROVAL_LETTER: extract_pre_approval,
    MortgageDocumentType.TITLE_COMMITMENT: extract_title_commitment,
    MortgageDocumentType.TITLE_PRELIMINARY_REPORT: extract_title_commitment,
    MortgageDocumentType.FLOOD_ZONE_DETERMINATION: extract_flood_cert,
    MortgageDocumentType.FEMA_FLOOD_CERT: extract_flood_cert,
    MortgageDocumentType.VERIFICATION_OF_EMPLOYMENT: extract_employment_verification,
    MortgageDocumentType.VOE: extract_employment_verification,
    MortgageDocumentType.VERIFICATION_OF_DEPOSIT: extract_bank_statement,
    MortgageDocumentType.VOD: extract_bank_statement,
    MortgageDocumentType.HAZARD_INSURANCE_DECLARATION: extract_hazard_insurance,
    MortgageDocumentType.HAZARD_INSURANCE: extract_hazard_insurance,
    MortgageDocumentType.PROPERTY_TAX_BILL: extract_property_tax,
    MortgageDocumentType.PROPERTY_TAX_RECEIPT: extract_property_tax,
    MortgageDocumentType.UNDERWRITING_APPROVAL_MEMO: extract_uw_approval_memo,
    MortgageDocumentType.UW_APPROVAL_MEMO: extract_uw_approval_memo,
    MortgageDocumentType.CLOSING_DISCLOSURE: extract_closing_disclosure,
    MortgageDocumentType.TRID_CLOSING_DISCLOSURE: extract_closing_disclosure,
    MortgageDocumentType.LOAN_ESTIMATE: extract_form_1003,
    MortgageDocumentType.PAYOFF_STATEMENT: extract_property_tax,
    MortgageDocumentType.RENTAL_HISTORY: extract_property_tax,
    MortgageDocumentType.MORTGAGE_STATEMENT: extract_property_tax,
}


def extract_fields(doc_type: MortgageDocumentType, text: str) -> dict[str, list[ExtractedMortgageField]]:
    extractor = EXTRACTOR_MAP.get(doc_type, extract_generic)
    fields = extractor(text)
    if doc_type == MortgageDocumentType.UNKNOWN or len(fields) < 2:
        generic = extract_generic(text)
        for key, val in generic.items():
            fields.setdefault(key, []).extend(val)
    return fields
