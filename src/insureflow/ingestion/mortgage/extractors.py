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


# An appraisal states a value once per approach and then states the
# reconciled conclusion. The conclusion is the opinion of value; the
# per-approach figures are intermediate arithmetic. These are tried in
# order so the conclusion wins, falling back through the older wordings.
_APPRAISAL_CONCLUSIVE_VALUE_PATTERNS = (
    re.compile(r"FINAL APPRAISED VALUE[:\s]*\$?\s*([\d,]+(?:\.\d+)?)", re.I),
    re.compile(r"\bFINAL VALUE[:\s]*\$?\s*([\d,]+(?:\.\d+)?)", re.I),
    re.compile(r"\bRECONCILED VALUE[:\s]*\$?\s*([\d,]+(?:\.\d+)?)", re.I),
    re.compile(r"OPINION OF MARKET VALUE[:\s]*\$?\s*([\d,]+(?:\.\d+)?)", re.I),
    re.compile(r"\bAPPRAISED VALUE[:\s]*\$?\s*([\d,]+(?:\.\d+)?)", re.I),
)

# NOI is a figure that must sit next to its own label. `[^\n$]` keeps the
# pattern on one line and forbids skipping past a currency symbol, which
# is how "Stabilized Net Operating Income (NOI):" followed by "Potential
# Gross Income (100% occ) $273,600" used to report gross income as NOI.
_APPRAISAL_NOI_PATTERNS = (
    re.compile(r"^[ \t]*(?:Stabilized|Adjusted|Actual)[ \t]+NOI\b[^\n$]*\$[ \s]*([\d,]+(?:\.\d+)?)", re.I | re.M),
    re.compile(r"^[ \t]*NOI\b[^\n$]*\$[ \s]*([\d,]+(?:\.\d+)?)", re.I | re.M),
    re.compile(r"Net Operating Income[ \t]*\(?NOI\)?[^\n$]*\$[ \s]*([\d,]+(?:\.\d+)?)", re.I),
    re.compile(r"^[ \t]*(?:Stabilized|Adjusted|Actual)?[ \t]*Net Operating Income\b[^\n$]*\$[ \s]*([\d,]+(?:\.\d+)?)", re.I | re.M),
)


def _first_match(patterns: tuple[re.Pattern[str], ...], text: str) -> tuple[str, str]:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip(), pattern.pattern
    return "", ""


def _address(text: str, label: str = "Property Address") -> str:
    """The address on one label's line, minus any columnar padding after it."""
    match = re.search(rf"{label}:[ \t]*([^\n]+)", text, re.I)
    if not match:
        return ""
    line = re.split(r"[ \t]{2,}", match.group(1).strip(), maxsplit=1)[0]
    return line.strip()


def extract_appraisal(text: str, commercial: bool = False) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "appraised_value": re.compile(
            r"(?:Opinion of Market Value|Final Reconciled Value|Indicated Value|Appraised Value).*?\$\s*([\d,]+)",
            re.I | re.S,
        ),
        "appraisal_date": re.compile(r"Appraisal Date:\s*(.+)", re.I),
        "cap_rate": re.compile(r"(?:Cap Rate|Capitalization Rate)[^%\n]*?([\d.]+)\s*%", re.I),
    }.items():
        val = _money(pattern, text) if key == "appraised_value" else _first(pattern, text)
        fields[key] = _field(key, val.replace("\n", " ").strip())

    # Capture the address line only. The old pattern ran to end-of-file and
    # pulled the whole 4,500-character report in as the property address.
    fields["property_address"] = _field("property_address", _address(text))

    noi, noi_pattern = _first_match(_APPRAISAL_NOI_PATTERNS, text)
    fields["noi"] = _field("noi", noi, context=f"matched {noi_pattern}" if noi_pattern else "")

    # A commercial report's conclusion is the reconciled figure. Preferring
    # it stops "Indicated Value - Income Approach: $311,644 / 0.0775 = ..."
    # from being read as the property being worth $311,644.
    conclusion, conclusion_pattern = _first_match(_APPRAISAL_CONCLUSIVE_VALUE_PATTERNS, text)
    fields["final_appraised_value"] = _field("final_appraised_value", conclusion, context=f"matched {conclusion_pattern}" if conclusion_pattern else "")
    if commercial and conclusion:
        fields["appraised_value"] = _field(
            "appraised_value",
            conclusion,
            confidence=0.95,
            context=f"reconciled value conclusion, matched {conclusion_pattern}",
        )

    fields["property_type"] = _field("property_type", "commercial" if commercial else "residential")
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


def extract_business_debt_schedule(text: str) -> dict[str, list[ExtractedMortgageField]]:
    """Pull the debt-service facts a commercial DSCR needs.

    Two numbers matter and they are easy to conflate:

    * the **subject loan's** monthly P&I — the note secured by the property
      being underwritten. This is the denominator of a conventional
      commercial DSCR.
    * the **total** scheduled monthly debt service across every note on the
      schedule. A stricter view that some credit policies run as a stress
      test; captured separately so it never silently replaces the first.

    The subject note is identified as the one whose section mentions a
    real-estate mortgage / deed of trust. If the schedule has exactly one
    scheduled payment it is the subject loan by definition.
    """
    fields: dict[str, list[ExtractedMortgageField]] = {}

    # Each "═══ n. NAME" block is one debt; keep the block text so the
    # collateral type can be inspected per note.
    blocks = re.split(r"═{3,}\s*\d+\.\s*", text)
    subject_monthly = 0.0
    subject_name = ""
    total_monthly = 0.0
    for block in blocks[1:]:
        payment = re.search(r"Monthly Payment(?:\s*\(P&I\))?:\s*\$?\s*([\d,]+(?:\.\d+)?)", block, re.I)
        if not payment:
            payment = re.search(r"Monthly Payment:\s*\$?\s*([\d,]+(?:\.\d+)?)", block, re.I)
        if not payment:
            continue
        amount = float(payment.group(1).replace(",", ""))
        total_monthly += amount
        is_real_estate = re.search(r"real estate|mortgage|deed of trust|commercial real estate", block, re.I) is not None
        if is_real_estate and not subject_monthly:
            subject_monthly = amount
            heading = re.search(r"([A-Z][A-Za-z0-9 .&'-]{4,60}?)\s*(?:\n\s*\n|═)", block)
            subject_name = heading.group(1).strip() if heading else ""

    # Fall back to the only scheduled payment when no note is flagged as
    # real estate (short schedules, or a lender that omits the header).
    if not subject_monthly and total_monthly:
        subject_monthly = total_monthly

    fields["subject_loan_monthly_debt_service"] = _field("subject_loan_monthly_debt_service", f"{subject_monthly:.2f}")
    fields["total_monthly_debt_service"] = _field("total_monthly_debt_service", f"{total_monthly:.2f}")
    fields["subject_loan_name"] = _field("subject_loan_name", subject_name, confidence=0.7)

    for key, pattern in {
        "total_indebtedness": re.compile(r"TOTAL INDEBTEDNESS:\s*\$?\s*([\d,]+(?:\.\d+)?)", re.I),
        "total_real_estate_debt": re.compile(r"Total Real Estate Debt:\s*\$?\s*([\d,]+(?:\.\d+)?)", re.I),
        "paydex_score": re.compile(r"D&B PAYDEX Score:\s*(\d+)", re.I),
        # Debt yield and LTV both need the loan amount. A debt schedule
        # states it, and it is the best available figure when the pipeline
        # is run without an explicit loan amount.
        "original_loan_amount": re.compile(r"Original Loan Amount:\s*\$?\s*([\d,]+(?:\.\d+)?)", re.I),
        "current_principal_balance": re.compile(r"Current Principal Balance:\s*\$?\s*([\d,]+(?:\.\d+)?)", re.I),
    }.items():
        fields[key] = _field(key, _money(pattern, text))

    # The subject note's own principal balance, not the entity's aggregate.
    if subject_monthly:
        for block in blocks[1:]:
            if not re.search(r"real estate|mortgage|deed of trust|commercial real estate", block, re.I):
                continue
            balance = re.search(r"Current Principal Balance:\s*\$?\s*([\d,]+(?:\.\d+)?)", block, re.I)
            if balance:
                fields["subject_loan_principal_balance"] = _field("subject_loan_principal_balance", balance.group(1))
                break

    # Explicit "no personal guarantees" is a real credit positive and worth
    # carrying as a fact rather than re-deriving from free text downstream.
    fields["personal_guarantees"] = _field(
        "personal_guarantees",
        "none" if re.search(r"Loan Guarantees\s*\(Personal\):\s*NONE", text, re.I) else "",
        confidence=0.8,
    )
    return fields


# A money amount as it appears in a financial statement: optional currency
# symbol, optional wrapping parens for negatives, thousands separators.
_STATEMENT_MONEY = re.compile(r"\(?-?\$\s*[\d,]+(?:\.\d{1,2})?\)?|[\d,]+\.\d{1,2}")

# Percentages share the same digits as dollars ("-2.9%" is not $2.90), so
# they are removed before money is scanned. Letting the money pattern match
# its digits is how a ratio silently becomes a dollar figure.
_PERCENT_TOKEN = re.compile(r"-?\d+(?:\.\d+)?\s*%")


def _parse_amount(token: str) -> float:
    """Parse a statement money token. Parenthesised values are negative."""
    text = token.strip()
    negative = text.startswith("(") and text.endswith(")")
    cleaned = re.sub(r"[^\d.]", "", text)
    if not cleaned:
        return 0.0
    value = float(cleaned)
    return -value if negative else value


def _amounts_on_line(line: str) -> list[float]:
    """Every money amount on a line, in order, with parens read as negative."""
    without_percentages = _PERCENT_TOKEN.sub(" ", line)
    return [_parse_amount(tok) for tok in _STATEMENT_MONEY.findall(without_percentages)]


def pick_most_recent(amounts: list[float]) -> tuple[float | None, str]:
    """Choose the most recent period's figure from a statement line.

    A lender's operating statement lays a line out as
    ``PRIOR | CURRENT | VARIANCE | %``, so when more than one amount
    appears the **second** is the current year. A single-amount line needs
    no interpretation. Returns ``(value, explanation)``; the caller is
    expected to record the explanation so a reviewer can see which column
    was used and what the alternatives were.
    """
    if not amounts:
        return None, "no amounts on line"
    if len(amounts) == 1:
        return amounts[0], "single amount on line"
    return amounts[1], f"assumed prior|current|variance layout, took column 2 of {len(amounts)}: {amounts}"


def _labelled_amount(text: str, label: re.Pattern[str]) -> tuple[float | None, str]:
    """First line matching ``label``, with its most recent amount."""
    for line in text.splitlines():
        if not label.search(line):
            continue
        value, why = pick_most_recent(_amounts_on_line(line))
        if value is not None:
            return value, f"{label.pattern!r} | {why} | line: {line.strip()[:160]}"
    return None, ""


def extract_operating_statement(text: str) -> dict[str, list[ExtractedMortgageField]]:
    """Annual operating statement: NOI, debt service, DSCR, occupancy.

    The earlier regexes here were written for a single-column statement
    ("Net Operating Income $X") and matched nothing at all against the
    multi-column statements lenders actually send, so NOI, DSCR and EGI
    all extracted empty and the commercial DSCR rule silently passed on
    every deal. These read the labelled row and pick the current-year
    column instead, recording the column choice in ``context`` so the
    underwriting file shows exactly which figure was used.
    """
    fields: dict[str, list[ExtractedMortgageField]] = {}

    noi_labels = [
        re.compile(r"^\s*(?:Net Operating Income|NOI)\b", re.I),
        re.compile(r"Net Operating Income", re.I),
    ]
    for label in noi_labels:
        noi, context = _labelled_amount(text, label)
        if noi is not None:
            fields["noi"] = _field("noi", f"{noi:.2f}", confidence=0.85, context=context)
            break

    egi, egi_context = _labelled_amount(text, re.compile(r"^\s*(?:Effective Gross Income|EGI)\b", re.I))
    fields["effective_gross_income"] = _field("effective_gross_income", f"{egi:.2f}" if egi is not None else "", context=egi_context)

    # Total operating expenses let NOI be rebuilt from EGI when the NOI row
    # itself is missing or garbled.
    opex, opex_context = _labelled_amount(text, re.compile(r"^\s*(?:Total Operating Expenses|TOTAL EXPENSES)\b", re.I))
    fields["total_operating_expenses"] = _field("total_operating_expenses", f"{opex:.2f}" if opex is not None else "", context=opex_context)

    # "DSCR (Debt Service Coverage Ratio): 1.12x" — the parenthetical
    # expansion sits between the label and the number.
    dscr = _first(re.compile(r"\bDSCR\b[^0-9\n]{0,48}?([\d]+\.?\d*)\s*x", re.I), text)
    fields["dscr"] = _field("dscr", dscr, confidence=0.9, context="stated on the statement, not derived")

    # "(P&I Monthly $11,848.40)" — the subject loan's monthly payment,
    # which annualises to the DSCR denominator.
    monthly = _first(re.compile(r"P&I Monthly\s*\$?\s*([\d,]+(?:\.\d+)?)", re.I), text)
    fields["subject_loan_monthly_debt_service"] = _field("subject_loan_monthly_debt_service", monthly, context="stated as P&I Monthly on the operating statement")

    occupancy = _first(re.compile(r"Occupancy(?:\s+Cost\s+Ratio)?[^0-9\n]{0,48}?([\d]+\.?\d*)\s*%", re.I), text)
    fields["occupancy_cost_ratio"] = _field("occupancy_cost_ratio", occupancy)
    vacancy = _first(re.compile(r"Vacancy Rate:[^0-9\n]{0,48}?([\d]+\.?\d*)\s*%", re.I), text)
    fields["vacancy_rate"] = _field("vacancy_rate", vacancy)
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


def extract_identity_document(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "full_name": re.compile(r"(?:Full Name|Name|Cardholder):\s*(.+)", re.I),
        "document_number": re.compile(r"(?:Document|Passport|ID|Alien|A-)(?: Number|#):\s*(\S+)", re.I),
        "date_of_birth": re.compile(r"(?:Date of Birth|DOB):\s*(.+)", re.I),
        "ssn": re.compile(r"(?:SSN|Social Security(?: Number)?):\s*(\d{3}-\d{2}-\d{4})", re.I),
        "expiration_date": re.compile(r"Expiration(?: Date)?:\s*(.+)", re.I),
        "issuing_country": re.compile(r"(?:Issuing Country|Nationality|Country):\s*(.+)", re.I),
        "status": re.compile(r"(?:Immigration Status|Visa Type|Class):\s*(.+)", re.I),
    }.items():
        fields[key] = _field(key, _first(pattern, text))
    return fields


def extract_other_income(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "recipient_name": re.compile(r"(?:Recipient|Payee|Beneficiary|Taxpayer)(?: Name)?:\s*(.+)", re.I),
        "payer_name": re.compile(r"(?:Payer|Payor|Partnership|Plan)(?: Name)?:\s*(.+)", re.I),
        "tax_year": re.compile(r"(?:Tax Year|Calendar Year):\s*(\d{4})", re.I),
        "amount": re.compile(
            r"(?:Gross Distribution|Box 1|Ordinary Income|Monthly Benefit|Award Amount|Payment Amount):\s*\$?([\d,]+(?:\.\d+)?)",
            re.I,
        ),
        "monthly_amount": re.compile(r"Monthly (?:Amount|Benefit|Payment):\s*\$?([\d,]+(?:\.\d+)?)", re.I),
        "start_date": re.compile(r"(?:Start|Effective|Award) Date:\s*(.+)", re.I),
        "ein": re.compile(r"(?:EIN|Employer ID):\s*(\S+)", re.I),
    }.items():
        val = _money(pattern, text) if "amount" in key else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_support_order(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "payee": re.compile(r"(?:Payee|Obligee|Recipient):\s*(.+)", re.I),
        "payor": re.compile(r"(?:Payor|Obligor|Payer):\s*(.+)", re.I),
        "monthly_amount": re.compile(r"(?:Monthly|Court.?Ordered) (?:Amount|Support|Alimony):\s*\$?([\d,]+(?:\.\d+)?)", re.I),
        "case_number": re.compile(r"Case(?: Number|#):\s*(\S+)", re.I),
        "order_date": re.compile(r"(?:Order|Decree) Date:\s*(.+)", re.I),
        "months_received": re.compile(r"(?:Months Received|Payment History Months):\s*(\d+)", re.I),
    }.items():
        val = _money(pattern, text) if "amount" in key else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_earnest_money(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "payer_name": re.compile(r"(?:Payer|From|Buyer):\s*(.+)", re.I),
        "amount": re.compile(r"(?:Amount|Wire Amount|Deposit):\s*\$?([\d,]+(?:\.\d+)?)", re.I),
        "cleared_date": re.compile(r"(?:Cleared|Posted|Wire) Date:\s*(.+)", re.I),
        "reference": re.compile(r"(?:Confirmation|Reference|Check)(?: Number|#):\s*(\S+)", re.I),
        "escrow_agent": re.compile(r"(?:Escrow|Title)(?: Company| Agent)?:\s*(.+)", re.I),
        "property_address": re.compile(r"Property(?: Address)?:\s*(.+)", re.I),
    }.items():
        val = _money(pattern, text) if key == "amount" else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_hoa_questionnaire(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "hoa_name": re.compile(r"(?:HOA|Association) Name:\s*(.+)", re.I),
        "monthly_dues": re.compile(r"(?:Monthly |HOA )?Dues:\s*\$?([\d,]+(?:\.\d+)?)", re.I),
        "special_assessment": re.compile(r"Special Assessment:\s*\$?([\d,]+(?:\.\d+)?)", re.I),
        "units": re.compile(r"(?:Number of )?Units:\s*(\d+)", re.I),
        "litigation": re.compile(r"(?:Pending )?Litigation:\s*(Yes|No)", re.I),
        "insurance_master": re.compile(r"Master (?:Policy|Insurance):\s*(Yes|No|.+)", re.I),
        "property_address": re.compile(r"(?:Property|Condo) Address:\s*(.+)", re.I),
    }.items():
        val = _money(pattern, text) if any(x in key for x in ("dues", "assessment")) else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_bankruptcy_judgment(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "case_number": re.compile(r"Case(?: Number|#):\s*(\S+)", re.I),
        "court": re.compile(r"Court:\s*(.+)", re.I),
        "filing_date": re.compile(r"Filing Date:\s*(.+)", re.I),
        "discharge_date": re.compile(r"Discharge(?: Date)?:\s*(.+)", re.I),
        "chapter": re.compile(r"Chapter:\s*(\d+)", re.I),
        "judgment_amount": re.compile(r"(?:Judgment |Claim )?Amount:\s*\$?([\d,]+(?:\.\d+)?)", re.I),
        "party_name": re.compile(r"(?:Debtor|Defendant|Plaintiff):\s*(.+)", re.I),
    }.items():
        val = _money(pattern, text) if "amount" in key else _first(pattern, text)
        fields[key] = _field(key, val)
    return fields


def extract_landlord_verification(text: str) -> dict[str, list[ExtractedMortgageField]]:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    for key, pattern in {
        "tenant_name": re.compile(r"Tenant(?: Name)?:\s*(.+)", re.I),
        "landlord_name": re.compile(r"Landlord(?: Name)?:\s*(.+)", re.I),
        "landlord_phone": re.compile(r"Landlord Phone:\s*(.+)", re.I),
        "monthly_rent": re.compile(r"Monthly Rent:\s*\$?([\d,]+(?:\.\d+)?)", re.I),
        "occupancy_start": re.compile(r"(?:Lease Start|Occupancy Start|Moved In):\s*(.+)", re.I),
        "on_time_payments": re.compile(r"(?:On.?Time|Timely) Payments:\s*(Yes|No|.+)", re.I),
        "property_address": re.compile(r"(?:Rental |Property )?Address:\s*(.+)", re.I),
    }.items():
        val = _money(pattern, text) if "rent" in key else _first(pattern, text)
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
    MortgageDocumentType.BUSINESS_DEBT_SCHEDULE: extract_business_debt_schedule,
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
    MortgageDocumentType.HOMEOWNERS_INSURANCE: extract_hazard_insurance,
    MortgageDocumentType.PROPERTY_TAX_BILL: extract_property_tax,
    MortgageDocumentType.PROPERTY_TAX_RECEIPT: extract_property_tax,
    MortgageDocumentType.UNDERWRITING_APPROVAL_MEMO: extract_uw_approval_memo,
    MortgageDocumentType.UW_APPROVAL_MEMO: extract_uw_approval_memo,
    MortgageDocumentType.CLOSING_DISCLOSURE: extract_closing_disclosure,
    MortgageDocumentType.TRID_CLOSING_DISCLOSURE: extract_closing_disclosure,
    MortgageDocumentType.LOAN_ESTIMATE: extract_form_1003,
    MortgageDocumentType.PAYOFF_STATEMENT: extract_property_tax,
    MortgageDocumentType.RENTAL_HISTORY: extract_landlord_verification,
    MortgageDocumentType.RENTAL_HISTORY_LETTER: extract_landlord_verification,
    MortgageDocumentType.MORTGAGE_STATEMENT: extract_property_tax,
    MortgageDocumentType.GOVERNMENT_ID: extract_identity_document,
    MortgageDocumentType.PASSPORT: extract_identity_document,
    MortgageDocumentType.SSN_CARD: extract_identity_document,
    MortgageDocumentType.SSN_VERIFICATION: extract_identity_document,
    MortgageDocumentType.RESIDENCY_DOCUMENT: extract_identity_document,
    MortgageDocumentType.PERMANENT_RESIDENT_CARD: extract_identity_document,
    MortgageDocumentType.VISA_DOCUMENT: extract_identity_document,
    MortgageDocumentType.FORM_K1: extract_other_income,
    MortgageDocumentType.SSA_1099: extract_other_income,
    MortgageDocumentType.FORM_1099_R: extract_other_income,
    MortgageDocumentType.SOCIAL_SECURITY_AWARD: extract_other_income,
    MortgageDocumentType.CHILD_SUPPORT_ORDER: extract_support_order,
    MortgageDocumentType.ALIMONY_DOCUMENTATION: extract_support_order,
    MortgageDocumentType.EARNEST_MONEY_RECEIPT: extract_earnest_money,
    MortgageDocumentType.CONDO_HOA_QUESTIONNAIRE: extract_hoa_questionnaire,
    MortgageDocumentType.HOA_STATEMENT: extract_hoa_questionnaire,
    MortgageDocumentType.BANKRUPTCY_DISCHARGE: extract_bankruptcy_judgment,
    MortgageDocumentType.JUDGMENT_DOCUMENT: extract_bankruptcy_judgment,
    MortgageDocumentType.LANDLORD_VERIFICATION: extract_landlord_verification,
    MortgageDocumentType.DIVORCE_DECREE: extract_support_order,
}


def extract_fields(doc_type: MortgageDocumentType, text: str) -> dict[str, list[ExtractedMortgageField]]:
    extractor = EXTRACTOR_MAP.get(doc_type, extract_generic)
    fields = extractor(text)
    if doc_type == MortgageDocumentType.UNKNOWN or len(fields) < 2:
        generic = extract_generic(text)
        for key, val in generic.items():
            fields.setdefault(key, []).extend(val)
    return fields
