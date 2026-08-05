"""Fannie Mae / Freddie Mac / HMDA loan-level mappers → mortgage_default_risk features.

Place downloaded files under ``external_data/mortgage/``:

Fannie Mae Single-Family Loan Performance (pipe-delimited):
  external_data/mortgage/fannie/Acquisition_YYYYQn.txt
  external_data/mortgage/fannie/Performance_YYYYQn.txt

Freddie Mac SFLLD (pipe-delimited):
  external_data/mortgage/freddie/historical_data_YYYY.txt
  external_data/mortgage/freddie/historical_data_time_YYYY.txt
  (or sample_orig_YYYY.txt / sample_svcg_YYYY.txt)

HMDA LAR CSV:
  external_data/mortgage/hmda/*.csv

Gold-standard default labels come from GSE performance (90+ DPD / REO / charge-off).
HMDA is used only when GSE files are absent (action_taken denial as weak proxy).
"""

from __future__ import annotations

import csv
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from insureflow.ml.features import MORTGAGE_FEATURE_NAMES

logger = logging.getLogger(__name__)

# Fannie Acquisition (common public layout — 25 pipe fields, 0-index)
# See Fannie Mae Single-Family Loan Performance Data glossary.
_FANNIE_ACQ = {
    "loan_id": 0,
    "orig_channel": 1,
    "seller": 2,
    "orig_rate": 3,
    "orig_upb": 4,
    "orig_term": 5,
    "orig_date": 6,
    "first_pay": 7,
    "ltv": 8,
    "cltv": 9,
    "num_borrowers": 10,
    "dti": 11,
    "credit_score": 12,
    "first_time": 13,
    "loan_purpose": 14,
    "property_type": 15,
    "num_units": 16,
    "occupancy": 17,
    "state": 18,
    "zip3": 19,
    "mi_pct": 20,
    "product": 21,
    "co_credit": 22,
    "mort_insurance": 23,
    "relo": 24,
}

# Freddie origination sample layout (pipe) — similar public fields
_FREDDIE_ORIG = {
    "credit_score": 0,
    "first_time": 1,
    "maturity_date": 2,
    "msa": 3,
    "mi_pct": 4,
    "units": 5,
    "occupancy": 6,
    "cltv": 7,
    "dti": 8,
    "upb": 9,
    "ltv": 10,
    "interest_rate": 11,
    "channel": 12,
    "prepay_penalty": 13,
    "amort_type": 14,
    "state": 15,
    "property_type": 16,
    "zip3": 17,
    "loan_id": 18,
    "loan_purpose": 19,
    "term": 20,
    "num_borrowers": 21,
    "seller": 22,
    "servicer": 23,
}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "" or str(value).strip() in {"", "NA", "N/A", "C", "999", "9999"}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _empty() -> dict[str, Any]:
    return {n: 0.0 for n in MORTGAGE_FEATURE_NAMES}


def _row_from_origination(
    *,
    credit: float,
    dti: float,
    ltv: float,
    upb: float,
    term_months: float,
    rate: float,
    target: float,
) -> dict[str, Any]:
    credit = float(np.clip(credit if credit > 0 else 700.0, 500, 850))
    dti = float(np.clip(dti if dti > 0 else 35.0, 10, 65))
    ltv = float(np.clip(ltv if ltv > 0 else 80.0, 40, 100))
    upb = max(upb, 50_000.0)
    # Approximate income from DTI and P&I when income is not on the file
    r = max(rate, 1.0) / 100.0 / 12.0
    n = max(term_months, 12.0)
    if r > 0:
        p_and_i = upb * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    else:
        p_and_i = upb / n
    annual_pi = p_and_i * 12.0
    income = max(annual_pi / max(dti / 100.0, 0.05), 25_000.0)
    reserves = income * 0.1
    row = _empty()
    row.update(
        {
            "credit_score": credit,
            "dti_ratio": dti,
            "ltv_ratio": ltv,
            "loan_amount": upb,
            "annual_income": income,
            "reserves": reserves,
            "employment_years": 5.0,
            "utilization_rate": float(np.clip(dti * 1.2, 5, 95)),
            "loan_to_income": upb / max(income, 1.0),
            "reserves_to_loan": reserves / max(upb, 1.0),
            "utilization_norm": float(np.clip(dti / 100.0, 0, 1)),
            "income_stability": 0.7,
            "target": float(target),
        }
    )
    return row


def _is_default_perf_code(delq: str, zero_bal: str) -> bool:
    d = (delq or "").strip()
    z = (zero_bal or "").strip()
    # Fannie/Freddie: delinquency status 3+ = 90 DPD; zero balance 3=short sale, 9=REO, 2/6 charge-off variants
    try:
        if d not in {"", "XX", "0", "1", "2"} and int(float(d)) >= 3:
            return True
    except ValueError:
        if d.upper() in {"F", "R", "REO"}:
            return True
    if z in {"2", "3", "6", "9", "15", "16"}:
        return True
    return False


def _iter_pipe_rows(path: Path) -> Iterable[list[str]]:
    with path.open(encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield line.split("|")


def map_fannie_loan_performance(
    acq_paths: list[Path],
    perf_paths: list[Path],
    *,
    max_rows: int = 25000,
) -> list[dict[str, Any]]:
    """Join Fannie acquisition + performance → labeled mortgage rows."""
    defaults: dict[str, bool] = defaultdict(bool)
    for path in perf_paths:
        if not path.exists():
            continue
        for parts in _iter_pipe_rows(path):
            if len(parts) < 10:
                continue
            loan_id = parts[0]
            # Common layouts: loan_id, period, ..., delq_status (~idx 3-5), zero_bal (~10)
            delq = parts[3] if len(parts) > 3 else ""
            zero = ""
            for idx in (8, 9, 10, 11, 14):
                if len(parts) > idx and parts[idx].strip() in {"2", "3", "6", "9", "15", "16"}:
                    zero = parts[idx].strip()
                    break
            if _is_default_perf_code(delq, zero):
                defaults[loan_id] = True

    rows: list[dict[str, Any]] = []
    for path in acq_paths:
        if not path.exists():
            continue
        for parts in _iter_pipe_rows(path):
            if len(parts) < 13:
                continue
            loan_id = parts[_FANNIE_ACQ["loan_id"]]
            credit = _num(parts[_FANNIE_ACQ["credit_score"]])
            # Co-borrower credit sometimes present
            if credit <= 0 and len(parts) > _FANNIE_ACQ["co_credit"]:
                credit = _num(parts[_FANNIE_ACQ["co_credit"]])
            dti = _num(parts[_FANNIE_ACQ["dti"]])
            ltv = _num(parts[_FANNIE_ACQ["ltv"]]) or _num(parts[_FANNIE_ACQ["cltv"]])
            upb = _num(parts[_FANNIE_ACQ["orig_upb"]])
            term = _num(parts[_FANNIE_ACQ["orig_term"]], 360)
            rate = _num(parts[_FANNIE_ACQ["orig_rate"]], 5.0)
            target = 1.0 if defaults.get(loan_id) else 0.0
            rows.append(
                _row_from_origination(
                    credit=credit,
                    dti=dti,
                    ltv=ltv,
                    upb=upb,
                    term_months=term,
                    rate=rate,
                    target=target,
                )
            )
            if len(rows) >= max_rows:
                return rows
    logger.info("Fannie mapper produced %d rows (defaults=%d)", len(rows), sum(1 for r in rows if r["target"] >= 0.5))
    return rows


def map_freddie_loan_level(
    orig_paths: list[Path],
    perf_paths: list[Path],
    *,
    max_rows: int = 25000,
) -> list[dict[str, Any]]:
    """Map Freddie origination + monthly performance files."""
    defaults: dict[str, bool] = defaultdict(bool)
    for path in perf_paths:
        if not path.exists():
            continue
        for parts in _iter_pipe_rows(path):
            if len(parts) < 5:
                continue
            loan_id = parts[0]
            delq = parts[3] if len(parts) > 3 else ""
            zero = parts[8] if len(parts) > 8 else (parts[9] if len(parts) > 9 else "")
            if _is_default_perf_code(delq, zero):
                defaults[loan_id] = True

    rows: list[dict[str, Any]] = []
    for path in orig_paths:
        if not path.exists():
            continue
        for parts in _iter_pipe_rows(path):
            if len(parts) < 19:
                continue
            loan_id = parts[_FREDDIE_ORIG["loan_id"]] if len(parts) > _FREDDIE_ORIG["loan_id"] else parts[0]
            credit = _num(parts[_FREDDIE_ORIG["credit_score"]])
            dti = _num(parts[_FREDDIE_ORIG["dti"]])
            ltv = _num(parts[_FREDDIE_ORIG["ltv"]]) or _num(parts[_FREDDIE_ORIG["cltv"]])
            upb = _num(parts[_FREDDIE_ORIG["upb"]])
            term = _num(parts[_FREDDIE_ORIG["term"]], 360) if len(parts) > _FREDDIE_ORIG["term"] else 360.0
            rate = _num(parts[_FREDDIE_ORIG["interest_rate"]], 5.0)
            target = 1.0 if defaults.get(loan_id) else 0.0
            rows.append(
                _row_from_origination(
                    credit=credit,
                    dti=dti,
                    ltv=ltv,
                    upb=upb,
                    term_months=term,
                    rate=rate,
                    target=target,
                )
            )
            if len(rows) >= max_rows:
                return rows
    logger.info("Freddie mapper produced %d rows", len(rows))
    return rows


def map_hmda_lar(paths: list[Path], *, max_rows: int = 20000) -> list[dict[str, Any]]:
    """Map HMDA LAR CSV — action_taken denial as adverse label (not true default)."""
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8", errors="ignore") as fh:
            reader = csv.DictReader(fh)
            for raw in reader:
                # Skip non-home-purchase / purchased loans when possible
                action = str(raw.get("action_taken") or raw.get("action_taken_type") or "").strip()
                if action not in {"1", "2", "3", "7", "8"}:
                    # Also accept text labels
                    al = action.lower()
                    if al in {"originated", "approved", "loan originated"}:
                        action = "1"
                    elif al in {"denied", "application denied"}:
                        action = "3"
                    else:
                        continue
                # 1=originated, 2=approved not accepted → non-default; 3/7=denied → adverse
                target = 1.0 if action in {"3", "7"} else 0.0
                amount = _num(raw.get("loan_amount") or raw.get("loan_amount_000s"))
                if amount and amount < 1000:  # older HMDA in thousands
                    amount *= 1000.0
                income = _num(raw.get("income") or raw.get("applicant_income_000s"))
                if income and income < 1000:
                    income *= 1000.0
                ltv = _num(raw.get("loan_to_value_ratio") or raw.get("ltv_ratio"))
                dti = _num(raw.get("debt_to_income_ratio") or raw.get("dti"))
                # Credit often absent / exempt in public HMDA
                credit = _num(raw.get("applicant_credit_score") or raw.get("credit_score"))
                if amount <= 0:
                    continue
                rows.append(
                    _row_from_origination(
                        credit=credit or 700.0,
                        dti=dti or 36.0,
                        ltv=ltv or 80.0,
                        upb=amount,
                        term_months=360.0,
                        rate=5.5,
                        target=target,
                    )
                )
                if len(rows) >= max_rows:
                    return rows
    logger.info("HMDA mapper produced %d rows", len(rows))
    return rows


def discover_gse_files(root: Path) -> dict[str, list[Path]]:
    """Find Fannie/Freddie/HMDA files under external_data/mortgage/."""
    root = Path(root)
    found: dict[str, list[Path]] = {
        "fannie_acq": [],
        "fannie_perf": [],
        "freddie_orig": [],
        "freddie_perf": [],
        "hmda": [],
    }
    if not root.exists():
        return found

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if name.endswith((".txt", ".csv")):
            if "acquisition" in name or name.startswith("acq"):
                found["fannie_acq"].append(path)
            elif "performance" in name or name.startswith("perf") or "svcg" in name or "time_" in name:
                if "freddie" in str(path).lower() or "historical_data_time" in name or "sample_svcg" in name:
                    found["freddie_perf"].append(path)
                else:
                    found["fannie_perf"].append(path)
            elif "historical_data" in name or "sample_orig" in name:
                found["freddie_orig"].append(path)
            elif "hmda" in str(path).lower() or "lar" in name:
                if path.suffix.lower() == ".csv":
                    found["hmda"].append(path)
            elif path.suffix.lower() == ".csv" and "hmda" in str(path.parent).lower():
                found["hmda"].append(path)
    return found


def load_gold_standard_mortgage(root: Path, *, max_rows: int = 25000) -> tuple[list[dict[str, Any]], str]:
    """Prefer Fannie → Freddie → HMDA. Returns (rows, source_label)."""
    found = discover_gse_files(root)
    if found["fannie_acq"]:
        rows = map_fannie_loan_performance(found["fannie_acq"], found["fannie_perf"], max_rows=max_rows)
        if rows:
            return rows, "fannie_mae_loan_performance"
    if found["freddie_orig"]:
        rows = map_freddie_loan_level(found["freddie_orig"], found["freddie_perf"], max_rows=max_rows)
        if rows:
            return rows, "freddie_mac_sfll"
    if found["hmda"]:
        rows = map_hmda_lar(found["hmda"], max_rows=max_rows)
        if rows:
            return rows, "hmda_lar_proxy"
    return [], "none"
