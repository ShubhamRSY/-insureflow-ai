"""Lending document ingestion — classify + extract fields from raw applications."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from insureflow.lending.models import BusinessFinancialData, BusinessLoanApplication, ConsumerFinancialData, ConsumerLoanApplication, LendingDocumentType, LoanProductType, LoanPurpose

TEXT_SUFFIXES = {".md", ".txt", ".json", ".csv", ".xml", ".html"}
BINARY_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif"}


@dataclass
class LendingDocument:
    filename: str
    content: str
    document_type: LendingDocumentType = LendingDocumentType.LOAN_APPLICATION
    extracted: dict[str, Any] = field(default_factory=dict)
    ocr_engine: str = ""
    extraction_method: str = "regex"


# filename / content hints → document type
_TYPE_HINTS: list[tuple[LendingDocumentType, tuple[str, ...]]] = [
    (LendingDocumentType.TAX_RETURN, ("tax_return", "1040", "1120", "form 1120", "form 1040")),
    (LendingDocumentType.PROFIT_LOSS, ("profit_loss", "p&l", "income statement", "profit and loss")),
    (LendingDocumentType.BALANCE_SHEET, ("balance_sheet", "balance sheet")),
    (LendingDocumentType.CASH_FLOW, ("cash_flow", "cash flow")),
    (LendingDocumentType.BANK_STATEMENT, ("bank_statement", "bank statement", "checking account")),
    (LendingDocumentType.CREDIT_REPORT, ("credit_report", "credit score", "fico", "experian", "equifax")),
    (LendingDocumentType.W2, ("w2", "w-2", "form w-2")),
    (LendingDocumentType.PAY_STUB, ("pay_stub", "paystub", "earnings statement")),
    (LendingDocumentType.DEBT_SCHEDULE, ("debt_schedule", "schedule of debts")),
    (LendingDocumentType.BUSINESS_PLAN, ("business_plan", "business plan")),
    (LendingDocumentType.FINANCIAL_STATEMENT, ("financial_statement", "financials")),
    (LendingDocumentType.COLLATERAL_APPRAISAL, ("appraisal", "collateral")),
    (LendingDocumentType.LOAN_APPLICATION, ("loan_application", "application", "1003", "sba")),
]


def classify_lending_document(filename: str, content: str = "") -> LendingDocumentType:
    blob = f"{filename}\n{content[:4000]}".lower()
    for doc_type, hints in _TYPE_HINTS:
        if any(h in blob for h in hints):
            return doc_type
    return LendingDocumentType.LOAN_APPLICATION


def _money(text: str, *labels: str) -> float | None:
    for label in labels:
        pat = re.compile(
            rf"{re.escape(label)}\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d+)?)",
            re.IGNORECASE,
        )
        m = pat.search(text)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _int_field(text: str, *labels: str) -> int | None:
    for label in labels:
        pat = re.compile(rf"{re.escape(label)}\s*[:=]?\s*(\d{{2,4}})", re.IGNORECASE)
        m = pat.search(text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


def _str_field(text: str, *labels: str) -> str | None:
    for label in labels:
        pat = re.compile(rf"{re.escape(label)}\s*[:=]\s*(.+)", re.IGNORECASE)
        m = pat.search(text)
        if m:
            return m.group(1).strip().split("\n")[0][:120]
    return None


def extract_lending_fields(content: str, doc_type: LendingDocumentType) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    revenue = _money(content, "Annual Revenue", "Revenue", "Gross Revenue", "Total Revenue")
    if revenue is not None:
        fields["annual_revenue"] = revenue
    net = _money(content, "Net Income", "Net Profit", "Profit After Tax")
    if net is not None:
        fields["net_income"] = net
    ebitda = _money(content, "EBITDA")
    if ebitda is not None:
        fields["ebitda"] = ebitda
    assets = _money(content, "Total Assets", "Assets")
    if assets is not None:
        fields["total_assets"] = assets
    liab = _money(content, "Total Liabilities", "Liabilities")
    if liab is not None:
        fields["total_liabilities"] = liab
    debt = _money(content, "Debt Service", "Annual Debt Service", "Monthly Debt")
    if debt is not None:
        fields["debt_service"] = debt
    income = _money(content, "Annual Income", "Gross Income", "Adjusted Gross Income")
    if income is not None:
        fields["annual_income"] = income
    amount = _money(content, "Loan Amount", "Requested Amount", "Amount Requested")
    if amount is not None:
        fields["requested_amount"] = amount
    score = _int_field(content, "Credit Score", "FICO", "FICO Score")
    if score is not None:
        fields["credit_score"] = score
    years = _money(content, "Years in Business", "Years Operating")
    if years is not None:
        fields["years_in_business"] = years
    name = _str_field(content, "Business Name", "Applicant", "Borrower Name", "Legal Name")
    if name:
        fields["business_name"] = name
    industry = _str_field(content, "Industry", "NAICS", "Business Type")
    if industry:
        fields["industry"] = industry
    fields["document_type"] = doc_type.value
    return fields


def _enrich_extraction(
    content: str,
    dtype: LendingDocumentType,
    *,
    source_path: str = "",
    use_llm: bool = True,
) -> dict[str, Any]:
    fields = extract_lending_fields(content, dtype)
    method = "regex"
    if use_llm:
        try:
            from insureflow.lending.llm_extractor import LendingLLMExtractor

            extractor = LendingLLMExtractor()
            if extractor.needs_llm(fields, content):
                llm_fields = extractor.extract(content, dtype, source_path)
                if llm_fields:
                    for key, value in llm_fields.items():
                        if key == "extraction_method":
                            continue
                        if fields.get(key) in (None, "", 0, 0.0):
                            fields[key] = value
                    method = "regex+llm"
        except Exception:  # noqa: BLE001
            pass
    fields["extraction_method"] = method
    return fields


def _read_path_text(path: Path) -> tuple[str, str]:
    """Return (text, ocr_engine)."""
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="replace"), ""
    if suffix in BINARY_SUFFIXES:
        from insureflow.ingestion.ocr import OCRProcessor

        ocr = OCRProcessor(engine="auto")
        result = ocr.extract_text(str(path), submission_id=path.stem)
        engine = getattr(result, "ocr_engine", "") or "ocr"
        return result.raw_text or "", str(engine)
    return "", ""


def load_lending_documents_from_directory(
    directory: str | Path,
    *,
    use_llm: bool = True,
) -> list[LendingDocument]:
    root = Path(directory)
    docs: list[LendingDocument] = []
    if not root.exists():
        return docs
    allowed = TEXT_SUFFIXES | BINARY_SUFFIXES
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        if path.name.startswith("."):
            continue
        content, ocr_engine = _read_path_text(path)
        if not content.strip():
            continue
        dtype = classify_lending_document(path.name, content)
        extracted = _enrich_extraction(content, dtype, source_path=str(path), use_llm=use_llm)
        docs.append(
            LendingDocument(
                filename=str(path.relative_to(root)),
                content=content,
                document_type=dtype,
                extracted=extracted,
                ocr_engine=ocr_engine,
                extraction_method=str(extracted.get("extraction_method") or "regex"),
            )
        )
    return docs


def load_lending_documents_from_payloads(
    payloads: list[dict[str, Any]],
    *,
    use_llm: bool = True,
) -> list[LendingDocument]:
    import base64
    import tempfile

    docs: list[LendingDocument] = []
    for item in payloads:
        filename = str(item.get("filename") or "document.txt")
        encoding = str(item.get("encoding") or "utf-8")
        content = str(item.get("content") or "")
        ocr_engine = ""
        suffix = Path(filename).suffix.lower()
        if encoding == "base64" and suffix in BINARY_SUFFIXES:
            raw = base64.b64decode(content)
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
                tmp.write(raw)
                tmp.flush()
                content, ocr_engine = _read_path_text(Path(tmp.name))
        dtype = classify_lending_document(filename, content)
        extracted = _enrich_extraction(content, dtype, source_path=filename, use_llm=use_llm)
        docs.append(
            LendingDocument(
                filename=filename,
                content=content,
                document_type=dtype,
                extracted=extracted,
                ocr_engine=ocr_engine,
                extraction_method=str(extracted.get("extraction_method") or "regex"),
            )
        )
    return docs


def merge_extracted_fields(docs: list[LendingDocument]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for doc in docs:
        for key, value in doc.extracted.items():
            if key == "document_type":
                continue
            if key not in merged or merged[key] in (None, "", 0, 0.0):
                merged[key] = value
    return merged


def application_from_documents(
    docs: list[LendingDocument],
    *,
    product_type: LoanProductType = LoanProductType.BUSINESS_TERM_LOAN,
    purpose: LoanPurpose = LoanPurpose.OTHER,
    is_business: bool | None = None,
    overrides: dict[str, Any] | None = None,
) -> BusinessLoanApplication | ConsumerLoanApplication:
    """Build a lending application from extracted document fields."""
    merged = merge_extracted_fields(docs)
    if overrides:
        for key, value in overrides.items():
            if value in (None, "", 0, 0.0):
                continue
            dest = "requested_amount" if key == "amount" else key
            # Prefer document-extracted values over form defaults
            if dest in merged and merged[dest] not in (None, "", 0, 0.0):
                continue
            merged[dest] = value

    business = is_business
    if business is None:
        business = product_type.value.startswith(("business_", "commercial_", "construction_", "sba_", "equipment_", "invoice_"))

    app_id = f"lend-{uuid4().hex[:12]}"
    amount = float(merged.get("requested_amount") or 0)

    if business:
        fin = BusinessFinancialData(
            annual_revenue=float(merged.get("annual_revenue") or 0),
            net_income=float(merged.get("net_income") or 0),
            ebitda=float(merged.get("ebitda") or 0),
            debt_service=float(merged.get("debt_service") or 0),
            total_assets=float(merged.get("total_assets") or 0),
            total_liabilities=float(merged.get("total_liabilities") or 0),
        )
        return BusinessLoanApplication(
            application_id=app_id,
            business_name=str(merged.get("business_name") or "Unknown Business"),
            industry=str(merged.get("industry") or ""),
            years_in_business=float(merged.get("years_in_business") or 0),
            product_type=product_type,
            loan_purpose=purpose,
            requested_amount=amount or 100_000,
            requested_term_months=int((overrides or {}).get("term_months") or 12),
            financials=[fin],
        )

    fin_c = ConsumerFinancialData(
        annual_income=float(merged.get("annual_income") or merged.get("annual_revenue") or 0),
        total_monthly_debt=float(merged.get("debt_service") or 0),
        credit_score=int(merged.get("credit_score") or 0),
        employment_years=float(merged.get("years_in_business") or 0),
    )
    return ConsumerLoanApplication(
        application_id=app_id,
        product_type=product_type,
        loan_purpose=purpose,
        requested_amount=amount or 25_000,
        requested_term_months=int((overrides or {}).get("term_months") or 36),
        financial_data=fin_c,
    )
