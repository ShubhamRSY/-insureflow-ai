"""Canonical value normalization for extracted fields.

Regex and LLM extraction both return strings. Downstream reconciliation,
triage, and rating consume those values, so they must be comparable: "$750K",
"750,000", and "750000.00" must all collapse to the same canonical form.

Rules are conservative: a value is only rewritten when we are confident of the
target type. Unknown values are returned lightly cleaned (whitespace, stray
dollar signs, trailing punctuation) rather than dropped.
"""

from __future__ import annotations

import re
from datetime import datetime

_AMOUNT_SUFFIX = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
_WORD_SUFFIX = {
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
    "mn": 1_000_000,
    "mm": 1_000_000,
    "bn": 1_000_000_000,
}
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y%m%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%m.%d.%Y",
    "%m/%d/%y",
    "%m-%d-%y",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%y %H:%M:%S",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d %Y",
    "%b %d %Y",
)
_YES = {"y", "yes", "yeah", "true", "1", "yep"}
_NO = {"n", "no", "nope", "false", "0", "none", "n/a", "na"}

_AMOUNT_FIELDS = frozenset(
    {
        "amount",
        "value",
        "premium",
        "tiv",
        "balance",
        "income",
        "limit",
        "benefit",
        "funding",
        "price",
        "cost",
        "asset",
        "revenue",
        "payroll",
        "coverage",
    }
)
_AMOUNT_FIELD_ALIASES = frozenset(
    {
        "face_amount",
        "building_value",
        "contents_value",
        "bi_value",
        "total_insurable_value",
        "outstanding_balance",
        "account_value",
        "rider_benefit",
        "income_amount",
        "funding_amount",
        "annual_income",
        "total_incurred",
        "square_footage",
    }
)
_INTEGER_FIELDS = frozenset(
    {
        "claim_count",
        "number_of_stories",
        "year_built",
        "protection_class",
        "pulse",
        "total_claims",
        "number_of_exits",
        "floor_area_sqft",
    }
)
_NON_NUMERIC_ID_FIELDS = frozenset(
    {
        "naics_code",
        "policy_number",
        "account_number",
        "tax_id",
        "ssn",
        "ein",
        "fein",
        "loan_number",
        "zip",
        "phone",
        "fax",
        "sic_code",
        "naic_code",
        "license_number",
        "serff_tracking",
    }
)


def _clean(raw: str) -> str:
    value = raw.strip()
    value = re.sub(r"[ \t]+", " ", value)
    value = value.strip(".,;:")
    return value


def normalize_amount(raw: str) -> str:
    value = _clean(str(raw))
    if not value:
        return ""
    # Strip leading currency markers: "US$750K", "USD 750K", "₹5,00,000", "Rs. 25,000"
    cleaned = re.sub(r"^\s*(?:usd|us\$|inr|rs\.?|ind|€|£|₹)\s*\$?\s*", "", value, flags=re.IGNORECASE)
    cleaned = cleaned.replace("$", "").replace("₹", "").replace(",", "")
    lowered = cleaned.lower().strip()

    # "$1.2M", "750K", "4.35 million", "12bn"
    m = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*([a-z]+)", lowered)
    if m:
        number = float(m.group(1))
        suffix = m.group(2)
        multiplier = _AMOUNT_SUFFIX.get(suffix) or _WORD_SUFFIX.get(suffix)
        if multiplier:
            number *= multiplier
        elif suffix not in {"thousand", "million", "billion", "mn", "mm", "bn"}:
            # Unknown suffix (e.g. currency code "cad") — keep cleaned raw.
            return value
        return _format_number(number)

    try:
        return _format_number(float(lowered))
    except ValueError:
        return value


def normalize_percent(raw: str) -> str:
    value = _clean(str(raw))
    if not value:
        return ""
    cleaned = value.replace("%", "").replace(",", "").strip()
    try:
        return _format_number(float(cleaned))
    except ValueError:
        return value


def normalize_int(raw: str) -> str:
    value = _clean(str(raw))
    if not value:
        return ""
    cleaned = re.sub(r"[^\d]", "", value)
    if not cleaned:
        return value
    return str(int(cleaned))


def normalize_date(raw: str) -> str:
    value = _clean(str(raw))
    if not value:
        return ""
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def normalize_yesno(raw: str) -> str:
    value = _clean(str(raw)).lower()
    if value in _YES:
        return "yes"
    if value in _NO:
        return "no"
    if value in {"smoker", "non-smoker", "nonsmoker", "non smoker"}:
        return "non-smoker" if "non" in value else "smoker"
    return _clean(str(raw))


def normalize_name(raw: str) -> str:
    return _clean(str(raw))


def _format_number(number: float) -> str:
    if number == int(number):
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def normalize_field(field_name: str, raw: str) -> str:
    """Normalize an extracted value by its canonical field name."""
    if not isinstance(raw, str) or not raw.strip():
        return _clean(str(raw)) if isinstance(raw, str) else str(raw)
    key = field_name.lower()
    if key in _NON_NUMERIC_ID_FIELDS:
        return normalize_name(raw)
    if key in _AMOUNT_FIELD_ALIASES or any(token in key for token in _AMOUNT_FIELDS):
        return normalize_amount(raw)
    if key.endswith("_percent") or "allocation" in key or "percent" in key:
        return normalize_percent(raw)
    if key in _INTEGER_FIELDS or key.endswith("_count"):
        return normalize_int(raw)
    if "date" in key or key == "dob":
        return normalize_date(raw)
    if key in {"smoker_status", "sprinklered", "tobacco_use"} or key.startswith("is_"):
        return normalize_yesno(raw)
    if key in {
        "height",
        "full_name",
        "insured_name",
        "beneficiary",
        "beneficiary_name",
        "beneficiary_relationship",
        "employer",
        "lender",
        "custodian",
        "funding_source",
        "address",
        "occupancy",
        "occupancy_type",
        "construction",
        "construction_type",
        "carrier",
        "broker_name",
        "named_insured",
        "occupation",
    }:
        return normalize_name(raw)
    return _clean(raw)
