from __future__ import annotations

from insureflow.ingestion.classifier import DocumentClassifier
from insureflow.ingestion.financial_parser import FinancialStatementParser
from insureflow.ingestion.loader import SubmissionLoader
from insureflow.models.submissions import DocumentType

BALANCE_SHEET = """ACME MANUFACTURING CO.
Balance Sheet as of December 31, 2023

| Balance Sheet | Amount |
|---|---|
| Cash and Cash Equivalents | 1,250,000 |
| Accounts Receivable | 800,000 |
| Inventory | 2,100,000 |
| Total Current Assets | 4,150,000 |
| Total Assets | 12,600,000 |
| Current Liabilities | 2,400,000 |
| Long Term Debt | 3,100,000 |
| Total Liabilities | 6,500,000 |
| Shareholder's Equity | 6,100,000 |

The accompanying Independent Auditor's Report was issued.
"""

INCOME_STATEMENT = """ACME MANUFACTURING CO.
Income Statement for Year Ended December 31, 2023
Gross Profit 5,200,000
Operating Income 1,800,000
EBITDA 2,100,000
Net Income 1,100,000
Total Assets 12,600,000
"""

TAX_RETURN = """ACME MANUFACTURING CO.
Form 1120 Corporate Tax Return, Tax Year 2023
Total Assets 12,600,000
Net Income (Loss) -45,500
"""


class TestFinancialStatementParser:
    def test_parse_structured_balance_sheet(self) -> None:
        data = FinancialStatementParser().parse_structured(BALANCE_SHEET)
        assert data.statement_type == "balance_sheet"
        assert data.as_of_date == "2023-12-31"
        assert data.fiscal_year == "2023"
        assert data.cash_and_equivalents == 1250000.0
        assert data.accounts_receivable == 800000.0
        assert data.inventory == 2100000.0
        assert data.current_assets == 4150000.0
        assert data.total_assets == 12600000.0
        assert data.current_liabilities == 2400000.0
        assert data.long_term_debt == 3100000.0
        assert data.total_liabilities == 6500000.0
        assert data.shareholder_equity == 6100000.0
        assert data.total_asset_value == 12600000.0

    def test_parse_structured_income_statement(self) -> None:
        data = FinancialStatementParser().parse_structured(INCOME_STATEMENT)
        assert data.statement_type == "income_statement"
        assert data.gross_profit == 5200000.0
        assert data.operating_income == 1800000.0
        assert data.ebitda == 2100000.0
        assert data.net_income == 1100000.0

    def test_parse_structured_tax_return(self) -> None:
        data = FinancialStatementParser().parse_structured(TAX_RETURN)
        assert data.statement_type == "tax_return"
        assert data.net_income == -45500.0

    def test_audit_status_detection(self) -> None:
        data = FinancialStatementParser().parse_structured(BALANCE_SHEET)
        assert data.is_audited is True
        assert data.audit_type == "audited"

        reviewed = BALANCE_SHEET.replace("Independent Auditor's Report", "Independent Review Report")
        assert FinancialStatementParser().parse_structured(reviewed).audit_type == "reviewed"

    def test_parse_unstructured(self) -> None:
        parsed = FinancialStatementParser().parse(BALANCE_SHEET, "fin-1")
        assert parsed.submission_id == "fin-1"
        assert parsed.document_type == "financial_statement"
        assert parsed.source == "financial_statement"
        assert parsed.extracted_fields["total_assets"][0].value == "12600000.0"

    def test_confidence_bounds(self) -> None:
        parsed = FinancialStatementParser().parse(BALANCE_SHEET, "fin-2")
        for fields in parsed.extracted_fields.values():
            for field in fields:
                assert 0.0 <= field.confidence <= 1.0


class TestFinancialClassifier:
    def test_classifies_balance_sheet(self) -> None:
        assert DocumentClassifier.classify(BALANCE_SHEET, "doc-1") == DocumentType.FINANCIAL_STATEMENT

    def test_classifies_income_statement(self) -> None:
        assert DocumentClassifier.classify(INCOME_STATEMENT, "doc-1") == DocumentType.FINANCIAL_STATEMENT

    def test_classifies_tax_return(self) -> None:
        assert DocumentClassifier.classify(TAX_RETURN, "doc-1") == DocumentType.FINANCIAL_STATEMENT


class TestLoaderFinancialIntegration:
    def test_load_bundle_financial_statements(self) -> None:
        bundle = SubmissionLoader().load_bundle(
            bundle_id="fin-bundle-1",
            financial_statements=[BALANCE_SHEET, INCOME_STATEMENT],
        )
        assert len(bundle.unstructured) == 2
        assert bundle.structured is not None
        assert bundle.structured.financial is not None
        assert bundle.structured.financial.total_assets == 12600000.0
        assert bundle.structured.financial.net_income == 1100000.0

    def test_load_bundle_auto_classified(self) -> None:
        bundle = SubmissionLoader().load_bundle(
            bundle_id="fin-bundle-2",
            raw_docs=[BALANCE_SHEET],
            auto_classify=True,
        )
        assert bundle.structured is not None
        assert bundle.structured.financial is not None
        assert bundle.structured.financial.shareholder_equity == 6100000.0
