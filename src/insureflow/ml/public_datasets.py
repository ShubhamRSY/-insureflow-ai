"""Map downloaded public datasets → ml_data feature schemas.

Pulled sources (see ``external_data/``):
- Insurance: Kaggle-style ``insurance_claims.csv`` (fraud + claim amounts + premium)
- Lending: SBA FOIA 7(a), UCI German Credit, UCI Default of Credit Card Clients
- Mortgage (priority order):
  1. Fannie Mae / Freddie Mac loan-performance (gold standard) under
     ``external_data/mortgage/`` — see ``gse_mortgage.py``
  2. HMDA LAR (denial proxy) under ``external_data/mortgage/hmda/``
  3. ISLR Default + AER CreditCard proxies
  4. UW-rule seed from ``seed_datasets``
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

import numpy as np

from insureflow.ml.features import (
    DEFAULT_FEATURE_NAMES,
    LENDING_FEATURE_NAMES,
    MORTGAGE_FEATURE_NAMES,
)
from insureflow.ml.seed_datasets import (
    DEFAULT_OUT_DIR,
    _target_diversity_ok,
    _write_csv,
    build_insurance_from_wisconsin,
    build_lending_seed,
    build_mortgage_seed,
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
EXTERNAL = ROOT / "external_data"


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "" or value == "NA":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _empty(names: list[str]) -> dict[str, Any]:
    return {n: 0.0 for n in names}


def map_insurance_claims(path: Path, *, max_rows: int = 5000) -> dict[str, list[dict[str, Any]]]:
    """Map auto insurance claims CSV → loss / fraud / premium / churn rows."""
    if not path.exists():
        return {}
    loss: list[dict[str, Any]] = []
    fraud: list[dict[str, Any]] = []
    premium: list[dict[str, Any]] = []
    churn: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8", errors="ignore") as fh:
        for i, raw in enumerate(csv.DictReader(fh)):
            if i >= max_rows:
                break
            claim = _num(raw.get("total_claim_amount"))
            prem = _num(raw.get("policy_annual_premium"))
            months = _num(raw.get("months_as_customer"))
            age = _num(raw.get("age"), 40)
            deduct = _num(raw.get("policy_deductable"), 500)
            umbrella = _num(raw.get("umbrella_limit"))
            vehicles = _num(raw.get("number_of_vehicles_involved"), 1)
            injuries = _num(raw.get("bodily_injuries"))
            auto_year = _num(raw.get("auto_year"), 2010)
            fraud_y = 1.0 if str(raw.get("fraud_reported", "")).strip().upper() in {"Y", "YES", "1", "TRUE"} else 0.0
            severity = str(raw.get("incident_severity", "")).lower()
            sev_score = 0.9 if "total loss" in severity else 0.6 if "major" in severity else 0.3 if "minor" in severity else 0.5

            tiv = max(claim * 4.0, prem * 80.0, deduct * 50.0, 25_000.0)
            revenue = max(tiv * 0.4, 80_000.0)
            employees = max(3.0, min(200.0, revenue / 120_000.0))
            years = max(months / 12.0, 0.5)
            loss_ratio = min(max(claim / max(tiv, 1.0), 0.01), 3.0)
            credit = float(np.clip(780 - sev_score * 40 - injuries * 15, 500, 850))
            property_age = float(max(2026 - auto_year, 1))
            risk = loss_ratio * 0.35 + (1 - credit / 850) * 0.2 + sev_score * 0.25 + min(vehicles / 5, 1) * 0.1

            base = _empty(DEFAULT_FEATURE_NAMES)
            base.update(
                {
                    "revenue": revenue,
                    "employees": employees,
                    "years_in_business": years,
                    "prior_claims_count": vehicles + injuries,
                    "prior_claims_total": claim * 0.4,
                    "tiv": tiv,
                    "requested_premium": prem if prem > 0 else tiv * 0.005,
                    "loss_ratio": loss_ratio,
                    "credit_score": credit,
                    "property_age": property_age,
                    "year_built": auto_year,
                    "square_footage": max(tiv / 120.0, 800.0),
                    "num_stories": 1.0,
                    "umbrella_limit_proxy": umbrella,  # ignored if not in schema
                    "alarm_system": 1.0 if str(raw.get("police_report_available", "")).upper() == "YES" else 0.0,
                    "prior_cancellations": 0.0,
                    "month_of_binding": float((i % 12) + 1),
                    "quarter": float((i % 4) + 1),
                    "revenue_per_employee": revenue / max(employees, 1.0),
                    "claims_per_year": (vehicles + injuries) / max(years, 1.0),
                    "tiv_to_revenue": tiv / max(revenue, 1.0),
                    "premium_to_tiv": (prem if prem > 0 else tiv * 0.005) / max(tiv, 1.0),
                    "risk_score_raw": risk,
                }
            )
            # drop non-schema keys
            row = {k: base.get(k, 0.0) for k in DEFAULT_FEATURE_NAMES}

            loss.append({**row, "target": max(claim, 1.0)})
            fraud.append({**row, "target": fraud_y})
            premium.append({**row, "target": max(prem, claim * 0.08 + 500.0)})
            # churn proxy: short tenure + severe/fraudulent claim
            churn_y = 1.0 if (months < 24 and (fraud_y or sev_score >= 0.6)) or claim > 80_000 else 0.0
            churn.append({**row, "target": churn_y})

    # balance churn a bit
    pos = [r for r in churn if r["target"] >= 0.5]
    neg = [r for r in churn if r["target"] < 0.5]
    if pos and neg and len(pos) < 30:
        for r in sorted(neg, key=lambda x: x["loss_ratio"], reverse=True)[:40]:
            r["target"] = 1.0
    return {
        "loss_prediction": loss,
        "fraud_detection": fraud,
        "premium_optimizer": premium,
        "churn_prediction": churn,
    }


def map_sba_7a(path: Path, *, max_rows: int = 25000) -> list[dict[str, Any]]:
    """Map SBA FOIA 7(a) loans → lending_default_risk (CHGOFF = default)."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8", errors="ignore") as fh:
        for i, raw in enumerate(csv.DictReader(fh)):
            if i >= max_rows:
                break
            status = str(raw.get("LoanStatus") or "").strip().upper()
            # Keep clear outcomes only
            if status in {"CHGOFF", "CHARGE OFF", "CHARGED OFF"}:
                target = 1.0
            elif status in {"P I F", "PIF", "PAID IN FULL"}:
                target = 0.0
            else:
                continue
            amount = _num(raw.get("GrossApproval"))
            term = _num(raw.get("TermInMonths"), 60)
            rate = _num(raw.get("InitialInterestRate"), 8)
            jobs = _num(raw.get("JobsSupported"), 1)
            age_txt = str(raw.get("BusinessAge") or "").lower()
            years = 10.0
            if "new" in age_txt or "startup" in age_txt or "< 2" in age_txt:
                years = 1.0
            elif "2" in age_txt and "5" in age_txt:
                years = 3.5
            elif "5" in age_txt or "existing" in age_txt:
                years = 8.0
            revenue = max(amount * 2.5, jobs * 80_000.0, 50_000.0)
            # Rough DSCR / leverage proxies from rate, term, size
            annual_debt = amount * (rate / 100.0 + 1.0 / max(term / 12.0, 1.0))
            ebitda = revenue * 0.12
            dscr = ebitda / max(annual_debt, 1.0)
            leverage = amount / max(revenue, 1.0)
            credit = float(np.clip(740 - max(0, rate - 8) * 8 - (40 if years < 2 else 0), 480, 850))
            row = _empty(LENDING_FEATURE_NAMES)
            row.update(
                {
                    "loan_segment_business": 1.0,
                    "credit_score": credit,
                    "dti_ratio": float(np.clip(22 + rate * 1.5 + leverage * 8, 15, 65)),
                    "annual_income": revenue,
                    "loan_amount": amount,
                    "years_in_business": years,
                    "dscr": float(np.clip(dscr, 0.5, 3.0)),
                    "current_ratio": float(np.clip(1.4 - leverage * 0.2, 0.4, 3.0)),
                    "leverage_ratio": float(np.clip(leverage * 3.0, 0.3, 8.0)),
                    "profit_margin": float(np.clip(12 - rate * 0.4, -5, 30)),
                    "debt_service": annual_debt,
                    "ebitda": ebitda,
                    "total_assets": revenue * 1.8,
                    "total_liabilities": amount * 1.1,
                    "bankruptcies": 0.0,
                    "loan_to_income": amount / max(revenue, 1.0),
                    "target": target,
                }
            )
            rows.append(row)
    # Downsample majority class for balance (~20% defaults)
    pos = [r for r in rows if r["target"] >= 0.5]
    neg = [r for r in rows if r["target"] < 0.5]
    if pos and neg:
        rng = np.random.RandomState(47)
        n_neg = min(len(neg), max(len(pos) * 4, 500))
        idx = rng.choice(len(neg), size=n_neg, replace=False)
        rows = pos + [neg[i] for i in idx]
    return rows


def map_german_credit(path: Path) -> list[dict[str, Any]]:
    """Map UCI German Credit (``german.data`` space-separated) → consumer lending rows."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) < 21:
                continue
            # attrs: status duration credit_history purpose amount ... age ... existing_credits ... label
            try:
                duration = float(parts[1])
                amount = float(parts[4])
                age = float(parts[12])
                existing = float(parts[15])
                label = int(parts[-1])
            except ValueError:
                continue
            target = 1.0 if label == 2 else 0.0  # 2 = bad credit
            income = max(amount * 1.8, age * 1500.0, 25_000.0)
            row = _empty(LENDING_FEATURE_NAMES)
            row.update(
                {
                    "loan_segment_business": 0.0,
                    "credit_score": float(np.clip(720 - target * 80 - existing * 20, 480, 850)),
                    "dti_ratio": float(np.clip(20 + duration / 3.0, 15, 60)),
                    "annual_income": income,
                    "loan_amount": amount,
                    "employment_years": float(np.clip(age / 8.0, 0, 35)),
                    "loan_to_income": amount / max(income, 1.0),
                    "bankruptcies": 1.0 if existing >= 3 else 0.0,
                    "target": target,
                }
            )
            rows.append(row)
    return rows


def map_credit_card_default(path: Path, *, max_rows: int = 15000) -> list[dict[str, Any]]:
    """Map UCI Default of Credit Card Clients → consumer lending rows."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8", errors="ignore") as fh:
        reader = csv.DictReader(fh)
        for i, raw in enumerate(reader):
            if i >= max_rows:
                break
            # last column name varies
            target_key = "default payment next month"
            if target_key not in raw:
                target_key = list(raw.keys())[-1]
            target = 1.0 if _num(raw.get(target_key)) >= 1 else 0.0
            limit = _num(raw.get("LIMIT_BAL"), 50000)
            age = _num(raw.get("AGE"), 35)
            pay0 = _num(raw.get("PAY_0"))
            bill = _num(raw.get("BILL_AMT1"))
            pay_amt = _num(raw.get("PAY_AMT1"))
            income = max(limit * 0.6, age * 2000, 30_000)
            util = bill / max(limit, 1.0)
            row = _empty(LENDING_FEATURE_NAMES)
            row.update(
                {
                    "loan_segment_business": 0.0,
                    "credit_score": float(np.clip(760 - max(pay0, 0) * 35 - util * 80, 480, 850)),
                    "dti_ratio": float(np.clip(18 + util * 40, 10, 65)),
                    "annual_income": income,
                    "loan_amount": limit,
                    "employment_years": float(np.clip(age / 6, 0, 35)),
                    "loan_to_income": limit / max(income, 1.0),
                    "current_ratio": float(np.clip(pay_amt / max(bill, 1.0) * 2, 0.2, 3.0)),
                    "bankruptcies": 1.0 if pay0 >= 3 else 0.0,
                    "target": target,
                }
            )
            rows.append(row)
    return rows


def map_public_mortgage_proxies(
    default_csv: Path,
    credit_card_csv: Path,
    *,
    max_rows: int = 12000,
) -> list[dict[str, Any]]:
    """Map public credit-default tables into mortgage feature schema.

    Not Fannie/Freddie loan-level data — used only when GSEs/HMDA are unavailable
    so mortgage models can still be checked on real public credit outcomes.
    """
    rows: list[dict[str, Any]] = []
    if default_csv.exists():
        with default_csv.open(newline="", encoding="utf-8", errors="ignore") as fh:
            for raw in csv.DictReader(fh):
                target = 1.0 if str(raw.get("default", "")).lower() in {"yes", "y", "1", "true"} else 0.0
                balance = _num(raw.get("balance"))
                income = _num(raw.get("income")) * 1000 if _num(raw.get("income")) < 200 else _num(raw.get("income"))
                income = max(income, 20_000)
                student = 1.0 if str(raw.get("student", "")).lower() in {"yes", "y"} else 0.0
                loan = max(balance * 8, income * 2.5)
                ltv = float(np.clip(60 + (balance / max(income, 1)) * 8, 50, 100))
                dti = float(np.clip(25 + student * 8 + (balance / max(income, 1)) * 15, 15, 55))
                credit = float(np.clip(740 - student * 20 - (balance / 500), 500, 850))
                row = _empty(MORTGAGE_FEATURE_NAMES)
                row.update(
                    {
                        "credit_score": credit,
                        "dti_ratio": dti,
                        "ltv_ratio": ltv,
                        "loan_amount": loan,
                        "annual_income": income,
                        "reserves": max(income * 0.15 - balance, 500),
                        "employment_years": 2.0 if student else 8.0,
                        "utilization_rate": float(np.clip(balance / max(income / 12, 1) * 10, 5, 95)),
                        "derogatory_marks": 0.0,
                        "loan_to_income": loan / max(income, 1.0),
                        "reserves_to_loan": max(income * 0.15 - balance, 500) / max(loan, 1.0),
                        "utilization_norm": float(np.clip(balance / max(income, 1), 0, 1)),
                        "income_stability": 0.3 if student else 0.8,
                        "target": target,
                    }
                )
                rows.append(row)

    if credit_card_csv.exists() and len(rows) < max_rows:
        with credit_card_csv.open(newline="", encoding="utf-8", errors="ignore") as fh:
            for raw in csv.DictReader(fh):
                # AER CreditCard: card=yes means approved; use reports>0 + high share as stress → default proxy
                reports = _num(raw.get("reports"))
                income = _num(raw.get("income")) * 10000 if _num(raw.get("income")) < 100 else _num(raw.get("income"))
                income = max(income, 25_000)
                age = _num(raw.get("age"), 35)
                owner = 1.0 if str(raw.get("owner", "")).lower() in {"yes", "y", "1"} else 0.0
                share = _num(raw.get("share"))
                target = 1.0 if reports >= 2 or (reports >= 1 and share > 0.001) else 0.0
                loan = income * (3.5 if owner else 2.0)
                row = _empty(MORTGAGE_FEATURE_NAMES)
                row.update(
                    {
                        "credit_score": float(np.clip(760 - reports * 40, 500, 850)),
                        "dti_ratio": float(np.clip(28 + reports * 5, 15, 55)),
                        "ltv_ratio": 75.0 if owner else 90.0,
                        "loan_amount": loan,
                        "annual_income": income,
                        "reserves": income * (0.2 if owner else 0.05),
                        "employment_years": float(np.clip(age / 5, 0, 35)),
                        "self_employment_income": income * 0.5 if str(raw.get("selfemp", "")).lower() in {"yes", "y"} else 0.0,
                        "utilization_rate": float(np.clip(share * 10000, 5, 95)),
                        "derogatory_marks": reports,
                        "loan_to_income": loan / max(income, 1.0),
                        "reserves_to_loan": (income * (0.2 if owner else 0.05)) / max(loan, 1.0),
                        "utilization_norm": float(np.clip(share * 100, 0, 1)),
                        "income_stability": float(np.clip(age / 50, 0.2, 1.0)),
                        "target": target,
                    }
                )
                rows.append(row)
                if len(rows) >= max_rows:
                    break
    return rows[:max_rows]


def build_from_public_downloads(
    *,
    external_root: Path | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Build ml_data CSVs preferentially from downloaded public datasets."""
    root = Path(external_root or EXTERNAL)
    out = Path(out_dir or DEFAULT_OUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"external_root": str(root), "out_dir": str(out), "models": {}, "sources_used": []}

    # --- Insurance ---
    wi = build_insurance_from_wisconsin(ROOT / "examples" / "insurance" / "real_claims_wisconsin.csv")
    claims_path = root / "insurance" / "insurance_claims.csv"
    pub_ins = map_insurance_claims(claims_path)
    if pub_ins:
        report["sources_used"].append(str(claims_path))
    for mt in ("loss_prediction", "fraud_detection", "premium_optimizer", "churn_prediction"):
        rows = (pub_ins.get(mt) or []) + (wi.get(mt) or [])
        classification = mt in {"fraud_detection", "churn_prediction"}
        n = _write_csv(out / f"{mt}.csv", DEFAULT_FEATURE_NAMES, rows)
        report["models"][mt] = {
            "rows": n,
            "source": "insurance_claims+wisconsin" if pub_ins else "wisconsin_claims",
            "diverse": _target_diversity_ok(rows, classification=classification),
            "path": str(out / f"{mt}.csv"),
        }

    # --- Lending ---
    lend_rows: list[dict[str, Any]] = []
    sba = root / "lending" / "sba_7a_fy2020_sample.csv"
    german = root / "lending" / "german_credit" / "german.data"
    ccd = root / "lending" / "credit_card_default.csv"
    for path, mapper, label in (
        (sba, map_sba_7a, "SBA_FOIA_7a"),
        (german, map_german_credit, "UCI_German_Credit"),
        (ccd, map_credit_card_default, "UCI_CreditCardDefault"),
    ):
        part = mapper(path) if path.exists() else []
        if part:
            lend_rows.extend(part)
            report["sources_used"].append(f"{label}:{path}")
    if not _target_diversity_ok(lend_rows, classification=True):
        lend_rows = lend_rows + build_lending_seed(n_samples=1500)
        report["sources_used"].append("uw_rule_seed_lending_topup")
    n = _write_csv(out / "lending_default_risk.csv", LENDING_FEATURE_NAMES, lend_rows)
    report["models"]["lending_default_risk"] = {
        "rows": n,
        "source": "SBA+German+CreditCardDefault",
        "diverse": _target_diversity_ok(lend_rows, classification=True),
        "path": str(out / "lending_default_risk.csv"),
    }

    # --- Mortgage (GSE/HMDA gold standard first) ---
    from insureflow.ml.gse_mortgage import load_gold_standard_mortgage

    mort_rows, gse_label = load_gold_standard_mortgage(root / "mortgage", max_rows=25000)
    mort_source = gse_label
    mort_note = ""
    if mort_rows:
        report["sources_used"].append(f"gse:{gse_label}")
        mort_note = "Gold-standard GSE/HMDA loan-level labels"
        if not _target_diversity_ok(mort_rows, classification=True):
            # Keep GSE labels; top up volume/class balance with UW-rule seed
            mort_rows = mort_rows + build_mortgage_seed(n_samples=max(200, 60 - len(mort_rows)))
            mort_source = f"{gse_label}+uw_rule_seed_topup"
            mort_note = "GSE/HMDA present but sparse — topped up with UW-rule seed for training volume"
            report["sources_used"].append("uw_rule_seed_mortgage_topup")
    else:
        mort_rows = map_public_mortgage_proxies(
            root / "mortgage" / "Default.csv",
            root / "mortgage" / "CreditCard.csv",
        )
        mort_source = "ISLR_Default+AER_CreditCard_proxy"
        if mort_rows:
            report["sources_used"].append(mort_source)
            mort_note = "Credit-risk proxy — drop Fannie/Freddie/HMDA under external_data/mortgage/ for gold standard"
        if not _target_diversity_ok(mort_rows, classification=True):
            mort_rows = build_mortgage_seed()
            mort_source = "uw_rule_seed"
            report["sources_used"].append(mort_source)
            mort_note = "No GSE/HMDA or proxy files found — using UW-rule seed"
    n = _write_csv(out / "mortgage_default_risk.csv", MORTGAGE_FEATURE_NAMES, mort_rows)
    report["models"]["mortgage_default_risk"] = {
        "rows": n,
        "source": mort_source,
        "diverse": _target_diversity_ok(mort_rows, classification=True),
        "path": str(out / "mortgage_default_risk.csv"),
        "note": mort_note,
    }

    report["ok"] = all(m.get("diverse") and m.get("rows", 0) >= 50 for m in report["models"].values())
    return report
