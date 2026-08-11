"""Financial statement parser (balance sheet / income statement / tax return).

Commercial insurance submissions routinely include the insured's financial
statements (audited or compiled) as supporting evidence of financial capacity.
Before this parser, financial documents were classified but the line items were
never extracted — ``FinancialData`` held only revenue/assets that happened to be
available from the ACORD/JSON structured path.

This parser extracts the classic balance-sheet and income-statement line items
from both labelled blocks ("Total Assets ... 1,234,567") and tabular exports
("| Total Assets | 1,234,567 | 1,100,000 |"), plus statement type, period end,
fiscal year, and audit status. The line items populate the ``FinancialData``
model (via :meth:`parse_structured`) and the per-field extracted-fields map (via
:meth:`parse`) so the financial-condition grader can consume either form.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Optional

from insureflow.ingestion.base import BaseParser
from insureflow.models.submissions import ExtractedChunk, ExtractedField, FinancialData, UnstructuredSubmission

# Normalized field key → (display label regex alternatives). Order matters:
# longer/more-specific labels first so "total assets" wins over "assets".
_FIELD_LABELS: dict[str, list[str]] = {
    "annual_revenue": [
        r"total\s+revenue",
        r"gross\s+revenue",
        r"gross\s+sales",
        r"net\s+sales",
        r"annual\s+revenue",
        r"total\s+sales",
        r"(?<!net\s)(?<!total\s)revenue\b",
        r"gross\s+receipts",
        r"business\s+receipts",
    ],
    "total_assets": [r"total\s+assets"],
    "current_assets": [r"total\s+current\s+assets", r"current\s+assets"],
    "cash_and_equivalents": [
        r"cash\s+(?:and\s+|&)\s*cash\s+equivalents",
        r"cash\s+on\s+hand",
        r"\bcash\b",
    ],
    "accounts_receivable": [r"accounts\s+receivable", r"trade\s+receivables?", r"receivables?\b"],
    "inventory": [r"\binventory\b"],
    "total_liabilities": [r"total\s+liabilities"],
    "current_liabilities": [r"total\s+current\s+liabilities", r"current\s+liabilities"],
    "long_term_debt": [r"long[- ]term\s+debt", r"notes\s+payable"],
    "shareholder_equity": [r"shareholders?[`']?s?\s+equity", r"stockholders?[`']?s?\s+equity", r"owner(?:'s)?\s+equity"],
    "total_equity": [r"total\s+equity", r"total\s+(?:stock|share)holders[`']?\s+equity"],
    "net_income": [
        r"net\s+income\s*\(\s*loss\s*\)",
        r"net\s+loss\s*\(\s*income\s*\)",
        r"net\s+income\s*\(\s*income\s*\)",
        r"net\s+income",
        r"net\s+earnings",
        r"net\s+profit",
        r"income\s+(?:after|before)\s+taxes?",
        r"profit\s+(?:after|before)\s+tax",
        r"net\s+loss",
    ],
    "gross_profit": [r"gross\s+profit"],
    "operating_income": [r"income\s+from\s+operations", r"operating\s+income", r"operating\s+profit", r"\bebit\b"],
    "ebitda": [r"\bebitda\b"],
    "payroll": [
        r"(?:total|annual|estimated)?\s*(?:annual\s+)?payroll",
        r"wages?\s+(?:paid|expense)?\b",
        r"salaries?\b",
    ],
}

# Filler between the label and the amount must not contain digits, currency
# markers, or parens so the greedy match cannot swallow part of the number. A
# separator dash only counts when it is not directly followed by a digit (that
# case is the negative sign, captured inside the money group).
_FIELD_RE: dict[str, re.Pattern[str]] = {
    key: re.compile(
        rf"(?i)(?:^|\n)\s*(?:[\|]?\s*)?(?:{'|'.join(labels)})"
        rf"[^0-9$€£(\-\n]*(?:[:\-–](?![\d]))?[^0-9$€£(\-\n]*"
        rf"(\(?\s*[$€£]?\s*-?[\d,]+(?:\.\d{{1,2}})?\s*\)?)"
    )
    for key, labels in _FIELD_LABELS.items()
}

_MONEY_RE = re.compile(r"^\(?\s*[$€£]?\s*-?\s*([\d,]+(?:\.\d{1,2})?)\s*\)?$")
_SEPARATOR_RE = re.compile(r"^[\s|\-_:+.,=~]+$")

_DATE_RE = re.compile(
    r"(?i)(?:as\s+of|at\s+for|for\s+(?:the\s+)?(?:period\s+ended|year\s+ended|twelve\s+months\s+ended))"
    r"[:\s]+([A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})"
)
_FISCAL_YEAR_RE = re.compile(r"(?i)(?:fiscal\s+year|year\s+ended|tax\s+year)[:\s]+.*?(\b(?:19|20)\d{2}\b)")
_STANDALONE_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def _parse_money(raw: str) -> Optional[float]:
    raw = raw.strip()
    negative = (raw.startswith("(") and raw.endswith(")")) or raw.startswith("-")
    m = _MONEY_RE.match(raw)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    return -value if negative else value


class FinancialStatementParser(BaseParser):
    """Parse balance-sheet / income-statement / tax-return documents.

    ``parse()`` returns an :class:`UnstructuredSubmission` whose
    ``extracted_fields`` map holds the normalized line-item keys used by the
    financial-condition grader. ``parse_structured()`` returns the rich
    :class:`FinancialData` model.
    """

    def parse(self, raw_text: str, submission_id: str) -> UnstructuredSubmission:
        figures, confidence = self._extract_figures_with_confidence(raw_text)
        meta = self._extract_metadata(raw_text)

        submission = UnstructuredSubmission(
            submission_id=submission_id,
            source="financial_statement",
            document_type="financial_statement",
            raw_text=raw_text,
            processed_at=datetime.now(timezone.utc),
        )

        submission.extracted_fields = {}
        for key, value in figures.items():
            submission.extracted_fields[key] = [
                ExtractedField(
                    field_name=key,
                    value=str(value),
                    confidence=confidence,
                    context=f"{key} from financial statement",
                )
            ]
        for key, value in meta.items():
            submission.extracted_fields[key] = [
                ExtractedField(
                    field_name=key,
                    value=str(value),
                    confidence=confidence,
                    context=f"{key} from financial statement",
                )
            ]

        submission.chunks = [ExtractedChunk(chunk_index=0, text=raw_text, start_char=0, end_char=len(raw_text))]
        return submission

    def parse_structured(self, raw_text: str) -> FinancialData:
        figures, _ = self._extract_figures_with_confidence(raw_text)
        meta = self._extract_metadata(raw_text)

        data = FinancialData()
        for key, value in figures.items():
            setattr(data, key, value)

        statement_type = meta.get("statement_type")
        if statement_type:
            data.statement_type = str(statement_type)
        if meta.get("as_of_date"):
            data.as_of_date = str(meta["as_of_date"])
        if meta.get("fiscal_year"):
            data.fiscal_year = str(meta["fiscal_year"])
        if meta.get("audit_type"):
            data.audit_type = str(meta["audit_type"])
            data.is_audited = meta["audit_type"] == "audited"

        # Keep the legacy field in sync for callers that read total_asset_value.
        if data.total_assets is not None and data.total_asset_value is None:
            data.total_asset_value = data.total_assets

        return data

    # ── Extraction ─────────────────────────────────────────────────────────
    def _extract_figures_with_confidence(self, text: str) -> tuple[dict[str, float], float]:
        figures: dict[str, float] = {}
        lines = text.split("\n")

        for line in lines:
            for key, value in self._line_value(line):
                figures.setdefault(key, value)

        if not figures:
            return figures, 0.6

        conf = 0.85
        if re.search(r"(?i)balance\s+sheet", text):
            conf += 0.05
        if re.search(r"(?i)(income\s+statement|profit\s+and\s+loss)", text):
            conf += 0.05
        if re.search(r"(?i)(audited|independent\s+auditor|review\s+report|compil)", text):
            conf += 0.05
        return figures, round(min(conf, 0.95), 2)

    def _line_value(self, line: str) -> list[tuple[str, float]]:
        """Return (key, value) pairs found on a single line.

        Handles both tabular rows ("| Total Assets | 1,234,567 | 1,100,000 |",
        taking the first numeric cell) and labelled blocks
        ("Total Assets 1,234,567" / "Total Assets: $1,234,567").
        """
        results: list[tuple[str, float]] = []
        stripped = line.strip()
        if not stripped or _SEPARATOR_RE.match(stripped):
            return results

        if "|" in stripped:
            cells = [c.strip() for c in stripped.split("|")]
            cells = [c for c in cells if c]
            if not cells or len(cells) < 2:
                return results
            label_cell = cells[0]
            value_cell = next((c for c in cells[1:] if _MONEY_RE.match(c.strip().replace(",", ""))), None)
            if value_cell is None:
                return results
            value = _parse_money(value_cell)
            if value is None:
                return results
            for key, value_patterns in _FIELD_LABELS.items():
                if any(re.search(rf"(?i)\b(?:{label})\b", label_cell) for label in value_patterns):
                    results.append((key, value))
                    break
            return results

        for key in _FIELD_LABELS:
            match = _FIELD_RE[key].search(line)
            if match:
                value = _parse_money(match.group(1))
                if value is not None:
                    results.append((key, value))
        return results

    def _extract_metadata(self, text: str) -> dict[str, Any]:
        meta: dict[str, Any] = {}

        types: list[str] = []
        if re.search(r"(?i)\bbalance\s+sheet\b", text):
            types.append("balance_sheet")
        if re.search(r"(?i)(income\s+statement|profit\s+and\s+loss|profit\s+&\s+loss|statement\s+of\s+operations|\bp\s*&\s*l\b)", text):
            types.append("income_statement")
        if re.search(r"(?i)(statement\s+of\s+cash\s+flows|cash\s+flow\s+statement)", text):
            types.append("cash_flow")
        if re.search(r"(?i)(tax\s+return|form\s+1120|1120[s\-]|corporate\s+tax\s+return|1040)", text):
            types.append("tax_return")
        if types:
            meta["statement_type"] = "combined" if len(types) > 1 else types[0]

        audit: Optional[str] = None
        if re.search(r"(?i)(independent\s+auditor[`']?s?\s+report|opinion\s+on\s+the\s+financial|audited|in\s+our\s+opinion)", text):
            audit = "audited"
        elif re.search(r"(?i)(review\s+report|reviewed\s+by|limited\s+review)", text):
            audit = "reviewed"
        elif re.search(r"(?i)(compilation\s+report|compiled\s+by|accountants?\s+compilation)", text):
            audit = "compiled"
        elif re.search(r"(?i)(unaudited|internal\s+use\s+only|management\s+prepared|not\s+audited)", text):
            audit = "internal"
        if audit:
            meta["audit_type"] = audit

        date_match = _DATE_RE.search(text)
        if date_match:
            raw_date = date_match.group(1).replace(",", "").strip()
            try:
                parsed = self._parse_period_date(raw_date)
                if parsed:
                    meta["as_of_date"] = parsed.isoformat()
                    meta["fiscal_year"] = str(parsed.year)
            except (ValueError, TypeError):
                pass
        if "fiscal_year" not in meta:
            fy_match = _FISCAL_YEAR_RE.search(text)
            if fy_match:
                meta["fiscal_year"] = fy_match.group(1)
            else:
                years = [y for y in _STANDALONE_YEAR_RE.findall(text) if int(y) > 2015]
                if years:
                    meta["fiscal_year"] = max(years)

        return meta

    @staticmethod
    def _parse_period_date(raw: str) -> Optional[date]:
        raw = raw.strip().replace(",", "")
        if raw.isdigit() and len(raw) == 4:
            return date(int(raw), 12, 31)
        normalized = raw.replace("/", "-")
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%b %d %Y", "%B %d %Y", "%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(normalized, fmt).date()
            except ValueError:
                continue
        try:
            parts = [int(p) for p in normalized.split("-")]
            if len(parts) == 3:
                year = parts[2] if parts[2] >= 1000 else 2000 + parts[2]
                return date(year, parts[1], parts[0]) if parts[0] > 12 else date(year, parts[0], parts[1])
        except (ValueError, TypeError):
            pass
        return None
