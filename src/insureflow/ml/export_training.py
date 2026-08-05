"""Export labeled training rows from persisted underwriting outcomes → ml_data/.

Scans audit_logs for:
- insurance (pipeline_summary.json + submission_bundle.json under realworld-test/,
  e2e-org/, demo/, default/) → labeled rows for loss_prediction / premium_optimizer
- mortgage (mortgage_bundle.json + mortgage_memo.json under demo-mort-* / e2e-mort-*)
  → labeled rows for mortgage_default_risk
- lending (lending/*.json) if present → labeled rows for lending_default_risk

Column order follows the target model's feature schema so the rows can be consumed
directly by ``load_training_csv`` / ``train_all_models``. Models without any labeled
outcome data (fraud_detection, churn_prediction) intentionally produce no CSV so the
production training pipeline leaves them on their deterministic fallbacks.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

from insureflow.ml.features import CONSTRUCTION_MAP, OCCUPANCY_MAP, encode_categorical, get_model_feature_names

logger = logging.getLogger(__name__)


from insureflow.decisions import ml_binary_target


def _target_from_decision(decision: str) -> float:
    return ml_binary_target(decision)

def _empty_row(feature_names: list[str]) -> dict[str, Any]:
    return {name: 0.0 for name in feature_names}


def _as_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: Any) -> int:
    return int(_as_float(value))


def _normalize_construction(value: Any) -> str:
    text = (value or "").lower()
    if any(k in text for k in ("fire resistive", "fire-resistive", "fire_resistive")):
        return "fire_resistive"
    if any(k in text for k in ("steel", "pre-engineered metal", "metal")):
        return "steel_frame"
    if "masonry" in text:
        return "masonry"
    if any(k in text for k in ("non-combustible", "noncombustible")):
        return "noncombustible"
    if "concrete" in text:
        return "reinforced_concrete"
    if "modular" in text:
        return "modular"
    if "manufactured" in text:
        return "manufactured"
    if "frame" in text:
        return "frame"
    return ""


def _normalize_occupancy(value: Any) -> str:
    text = (value or "").lower()
    if any(k in text for k in ("warehouse", "storage", "distribution")):
        return "warehouse"
    if "retail" in text:
        return "retail"
    if "manufacturing" in text or "industrial" in text:
        return "manufacturing"
    if "office" in text:
        return "office"
    if any(k in text for k in ("residential", "apartment", "dwelling")):
        return "residential"
    if any(k in text for k in ("mixed", "flex")):
        return "mixed_use"
    if "institutional" in text or "school" in text or "church" in text:
        return "institutional"
    if "agricultural" in text or "farm" in text:
        return "agricultural"
    return ""


def _latest_loss_ratio(financial: dict[str, Any]) -> float:
    ratios = (financial.get("loss_run") or {}).get("loss_ratios") or {}
    if not isinstance(ratios, dict) or not ratios:
        return 0.0
    latest = 0.0
    for _year, value in ratios.items():
        ratio = _as_float(value) / 100.0
        if ratio > 0.0:
            latest = max(latest, ratio)
    return min(max(latest, 0.0), 3.0)


def _insurance_row(summary: dict[str, Any], bundle: dict[str, Any], feature_names: list[str], target: float) -> dict[str, Any]:
    """Build a DEFAULT_FEATURE_NAMES row from a submission bundle + pipeline summary."""
    structured = bundle.get("structured") or {}
    financial = structured.get("financial") or {}
    loss_run = financial.get("loss_run") or {}
    locations = structured.get("locations") or [{}]
    loc = locations[0] if locations else {}
    coverages = structured.get("coverages") or []
    sov = structured.get("schedule_of_values") or []
    quote = summary.get("quote") or {}
    summary_tiv = _as_float(summary.get("tiv"))
    quote_tiv = _as_float(quote.get("tiv"))
    sov_total = _as_float(sov[0].get("total_value")) if sov and isinstance(sov[0], dict) else 0.0
    building_value = _as_float(loc.get("building_value"))
    contents_value = _as_float(loc.get("contents_value"))

    tiv = summary_tiv or quote_tiv or sov_total or (building_value + contents_value)
    premium = sum(_as_float(c.get("premium")) for c in coverages if isinstance(c, dict))
    revenue = _as_float(financial.get("annual_revenue"))
    prior_claims_count = _as_float(loss_run.get("total_claims"))
    prior_claims_total = _as_float(loss_run.get("total_incurred")) or _as_float(loss_run.get("total_paid"))
    loss_ratio = _latest_loss_ratio(financial)
    if loss_ratio <= 0.0 and tiv > 0.0:
        loss_ratio = min(max(prior_claims_total / tiv, 0.0), 3.0)
    year_built = _as_int(loc.get("year_built"))
    current_year = 2026
    property_age = max(current_year - year_built, 0) if year_built > 0 else 0.0
    square_footage = _as_float(loc.get("square_footage"))
    construction = encode_categorical(_normalize_construction(loc.get("construction_type")), CONSTRUCTION_MAP)
    occupancy = encode_categorical(_normalize_occupancy(loc.get("building_occupancy")), OCCUPANCY_MAP)
    protection = _as_int(loc.get("protection_class"))

    employees = 0.0
    years_in_business = 0.0
    revenue_per_employee = revenue / max(employees, 1.0)
    claims_per_year = prior_claims_count / max(years_in_business, 1.0)
    tiv_to_revenue = tiv / max(revenue, 1.0) if revenue > 0.0 else 0.0
    premium_to_tiv = premium / max(tiv, 1.0)
    risk_score_raw = loss_ratio * 0.3 + (1 - min(0.0 / 850, 1.0)) * 0.2 + min(prior_claims_count / 10, 1.0) * 0.2 + min(0.0 / 5, 1.0) * 0.15 + (1 - min(years_in_business / 30, 1.0)) * 0.15

    row = _empty_row(feature_names)
    row.update(
        {
            "revenue": revenue,
            "employees": employees,
            "years_in_business": years_in_business,
            "prior_claims_count": prior_claims_count,
            "prior_claims_total": prior_claims_total,
            "tiv": tiv,
            "requested_premium": premium,
            "loss_ratio": loss_ratio,
            "credit_score": 0.0,
            "property_age": property_age,
            "construction_type": float(construction),
            "occupancy_type": float(occupancy),
            "protection_class": float(protection),
            "year_built": float(year_built),
            "square_footage": square_footage,
            "revenue_per_employee": revenue_per_employee,
            "claims_per_year": claims_per_year,
            "tiv_to_revenue": tiv_to_revenue,
            "premium_to_tiv": premium_to_tiv,
            "risk_score_raw": risk_score_raw,
        }
    )
    row["target"] = target
    return row


def _insurance_target(summary: dict[str, Any], model_type: str, bundle: dict[str, Any]) -> float | None:
    """Derive the model-specific target from a summary + bundle, or None if unavailable."""
    if model_type == "premium_optimizer":
        quote = summary.get("quote") or {}
        target = _as_float(quote.get("adjusted_premium")) or _as_float(quote.get("base_premium"))
        if target <= 0.0:
            structured = bundle.get("structured") or {}
            target = sum(_as_float(c.get("premium")) for c in structured.get("coverages") or [] if isinstance(c, dict))
        return target if target > 0.0 else None

    # loss_prediction — prefer per-submission expected loss proxies over a single
    # copied loss-run total (demo audits often stamp the same incurred on every file).
    structured = bundle.get("structured") or {}
    financial = structured.get("financial") or {}
    loss_run = financial.get("loss_run") or {}
    quote = summary.get("quote") or {}
    tiv = (
        _as_float(summary.get("tiv"))
        or _as_float(quote.get("tiv"))
        or _as_float((structured.get("schedule_of_values") or [{}])[0].get("total_value") if structured.get("schedule_of_values") else 0)
    )
    ratio = _latest_loss_ratio(financial)
    premium = _as_float(quote.get("adjusted_premium")) or _as_float(quote.get("base_premium"))
    incurred = _as_float(loss_run.get("total_incurred")) or _as_float(loss_run.get("total_paid"))
    claims = _as_float(loss_run.get("total_claims"))

    # Expected loss ≈ LR * TIV when we have both; else premium * LR; else incurred / years
    if ratio > 0.0 and tiv > 0.0:
        return ratio * tiv
    if ratio > 0.0 and premium > 0.0:
        return premium * max(ratio, 0.5)
    if incurred > 0.0 and claims > 1.0:
        return incurred / claims  # severity proxy — more diverse than raw incurred
    if incurred > 0.0:
        return incurred
    if premium > 0.0:
        return premium * 0.65  # technical loss proxy from priced premium
    return None


def _mortgage_row(record: dict[str, Any], feature_names: list[str], target: float) -> dict[str, Any]:
    """Build a MORTGAGE_FEATURE_NAMES row from a mortgage bundle + memo."""
    bundle = record.get("bundle") or {}
    memo = record.get("memo") or {}
    credit = bundle.get("credit") or {}
    income = bundle.get("income") or {}
    assets = bundle.get("assets") or {}
    collateral = bundle.get("collateral") or {}

    credit_score = _as_float(credit.get("credit_score"))
    dti_ratio = _as_float(memo.get("dti_ratio"))
    ltv_ratio = _as_float(memo.get("ltv_ratio")) or _as_float(collateral.get("ltv"))
    appraised = _as_float(collateral.get("appraised_value"))
    loan_amount = _as_float(record.get("loan_amount")) or (appraised * (ltv_ratio / 100.0) if ltv_ratio > 0.0 else 0.0)
    annual_income = _as_float(income.get("adjusted_gross_income")) or _as_float(income.get("total_income")) or _as_float(income.get("annual_wages"))
    reserves = _as_float(assets.get("total_liquid_assets"))
    utilization_rate = _as_float(credit.get("utilization_rate"))
    derogatory_marks = float(len(credit.get("derogatory_flags") or [])) if isinstance(credit.get("derogatory_flags"), list) else 0.0

    row = _empty_row(feature_names)
    row.update(
        {
            "credit_score": credit_score,
            "dti_ratio": dti_ratio,
            "ltv_ratio": ltv_ratio,
            "loan_amount": loan_amount,
            "annual_income": annual_income,
            "reserves": reserves,
            "self_employment_income": _as_float(income.get("self_employment_income")),
            "utilization_rate": utilization_rate,
            "derogatory_marks": derogatory_marks,
            "loan_to_income": loan_amount / max(annual_income, 1.0),
            "reserves_to_loan": reserves / max(loan_amount, 1.0),
            "utilization_norm": min(max(utilization_rate, 0.0), 100.0) / 100.0,
        }
    )
    row["target"] = target
    return row


def _mortgage_target(memo: dict[str, Any], bundle: dict[str, Any] | None = None) -> float:
    """Label mortgage default risk from decision, else from credit risk factors.

    Demo audits often stamp every file ``refer`` with the same risk_score — in that
    case derive a binary label from DTI / LTV / credit so exported CSVs are not
    single-class degenerate.
    """
    from insureflow.decisions import DecisionOutcome, ml_binary_target, normalize_decision

    outcome = normalize_decision(memo.get("decision"))
    if outcome in {DecisionOutcome.DECLINE, DecisionOutcome.ACCEPT, DecisionOutcome.CONDITIONAL_ACCEPT}:
        return ml_binary_target(outcome)

    risk_score = _as_float(memo.get("risk_score"))
    if risk_score >= 0.5:
        return 1.0

    credit = (bundle or {}).get("credit") or {}
    credit_score = _as_float(credit.get("credit_score"))
    dti = _as_float(memo.get("dti_ratio"))
    ltv = _as_float(memo.get("ltv_ratio"))
    score = 0.0
    if credit_score and credit_score < 620:
        score += 0.35
    elif credit_score and credit_score < 680:
        score += 0.15
    if dti > 43:
        score += 0.25
    if ltv > 90:
        score += 0.20
    elif ltv > 80:
        score += 0.10
    if score >= 0.35:
        return 1.0
    if risk_score > 0.0:
        return 0.0
    return 0.5


def _lending_row(payload: dict[str, Any], feature_names: list[str]) -> dict[str, Any]:
    result = payload.get("result") or {}
    app = payload.get("application") or {}
    fin = (app.get("financials") or [{}])[0] if isinstance(app.get("financials"), list) else {}
    fin_data = app.get("financial_data") or {}
    analysis = result.get("credit_analysis") or {}

    row = _empty_row(feature_names)
    row["loan_segment_business"] = 1.0 if payload.get("application_type") == "business" else 0.0
    row["credit_score"] = float(fin_data.get("credit_score") or ((app.get("guarantors") or [{}])[0].get("credit_score") or 0))
    row["dti_ratio"] = float(analysis.get("debt_to_income_ratio") or 0)
    row["annual_income"] = float(fin.get("annual_revenue") or fin_data.get("annual_income") or 0)
    row["loan_amount"] = float(app.get("requested_amount") or 0)
    row["years_in_business"] = float(app.get("years_in_business") or 0)
    row["employment_years"] = float(fin_data.get("employment_years") or 0)
    row["dscr"] = float(analysis.get("dscr") or 0)
    row["current_ratio"] = float(analysis.get("liquidity_ratio") or 0)
    row["leverage_ratio"] = float(analysis.get("leverage_ratio") or 0)
    row["profit_margin"] = float(analysis.get("profitability_score") or 0)
    row["debt_service"] = float(fin.get("debt_service") or 0)
    row["ebitda"] = float(fin.get("ebitda") or 0)
    row["total_assets"] = float(fin.get("total_assets") or fin_data.get("total_assets") or 0)
    row["total_liabilities"] = float(fin.get("total_liabilities") or fin_data.get("total_liabilities") or 0)
    row["bankruptcies"] = float(fin_data.get("bankruptcies_last_7_years") or 0)
    row["foreclosures"] = float(fin_data.get("foreclosures_last_7_years") or 0)
    return row


def _iter_insurance_dir(path: Path) -> dict[str, Any] | None:
    """Load (summary, bundle) for an insurance audit dir, or None if unreadable."""
    summary_path = path / "pipeline_summary.json"
    bundle_path = path / "submission_bundle.json"
    if not summary_path.exists() or not bundle_path.exists():
        return None
    try:
        raw = summary_path.read_text(encoding="utf-8")
        if raw.startswith("ENC:v1:"):
            return None
        summary = json.loads(raw)
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(summary, dict) or not isinstance(bundle, dict):
        return None
    return {"summary": summary, "bundle": bundle}


def _iter_mortgage_dir(path: Path) -> dict[str, Any] | None:
    """Load (bundle, memo) for a mortgage audit dir, or None if unreadable."""
    bundle_path = path / "mortgage_bundle.json"
    memo_path = path / "mortgage_memo.json"
    if not bundle_path.exists():
        return None
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        memo = json.loads(memo_path.read_text(encoding="utf-8")) if memo_path.exists() else {}
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(bundle, dict):
        return None
    return {"bundle": bundle, "memo": memo if isinstance(memo, dict) else {}}


def export_from_audit_logs(
    audit_root: Path | str | None = None,
    *,
    out_path: Path | str | None = None,
    model_type: str = "loss_prediction",
) -> dict[str, Any]:
    """Scan audit logs and write a labeled training CSV for the requested model."""
    root = Path(audit_root or Path.cwd() / "audit_logs")
    dest = Path(out_path or Path.cwd() / "ml_data" / f"{model_type}.csv")
    dest.parent.mkdir(parents=True, exist_ok=True)

    if model_type in {"fraud_detection", "churn_prediction"}:
        return {
            "ok": False,
            "rows": 0,
            "path": str(dest),
            "model_type": model_type,
            "message": f"No labeled outcome data available for {model_type} — model stays on deterministic fallback",
        }

    feature_names = get_model_feature_names(model_type)
    rows: list[dict[str, Any]] = []
    skipped = 0

    if not root.exists():
        return {"ok": False, "rows": 0, "path": str(dest), "model_type": model_type, "message": f"Audit root not found: {root}"}

    if model_type == "mortgage_default_risk":
        for path in sorted(root.iterdir()):
            if not path.is_dir() or not (path.name.startswith("demo-mort") or path.name.startswith("e2e-mort")):
                continue
            record = _iter_mortgage_dir(path)
            if record is None:
                continue
            row = _mortgage_row(record, feature_names, _mortgage_target(record["memo"], record.get("bundle")))
            rows.append(row)
    elif model_type == "lending_default_risk":
        candidates: list[Path] = []
        lending_dir = root / "lending"
        if lending_dir.exists():
            candidates.extend(sorted(lending_dir.glob("*.json")))
        # Also pick up demo/lp lending pipeline payloads under org folders
        for path in sorted(root.rglob("*.json")):
            name = path.name.lower()
            parent = path.parent.name.lower()
            if "lend" in name or parent.startswith("demo-lend") or parent.startswith("lp-lend"):
                if path not in candidates:
                    candidates.append(path)
        for path in candidates:
            try:
                raw = path.read_text(encoding="utf-8")
                if not raw.strip() or raw.startswith("ENC:v1:"):
                    continue
                payload = json.loads(raw)
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(payload, dict):
                continue
            # Skip analytics-only stubs with no application/financials
            if not (payload.get("application") or payload.get("result") or payload.get("financials")):
                continue
            decision = (payload.get("result") or {}).get("decision") or payload.get("decision") or ""
            row = _lending_row(payload, feature_names)
            row["target"] = _target_from_decision(decision)
            rows.append(row)
    else:
        # loss_prediction / premium_optimizer
        for path in sorted(root.rglob("pipeline_summary.json")):
            if "mort" in path.name and "mort" in path.parent.name:
                continue
            record = _iter_insurance_dir(path.parent)
            if record is None:
                continue
            target = _insurance_target(record["summary"], model_type, record["bundle"])
            if target is None:
                skipped += 1
                continue
            row = _insurance_row(record["summary"], record["bundle"], feature_names, target)
            rows.append(row)

    if not rows:
        return {"ok": False, "rows": 0, "path": str(dest), "model_type": model_type, "message": "No audit outcomes found to export"}

    fieldnames = feature_names + ["target"]
    with dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, 0.0) for k in fieldnames})

    logger.info("Exported %d training rows → %s", len(rows), dest)
    return {"ok": True, "rows": len(rows), "path": str(dest), "model_type": model_type, "skipped_no_target": skipped}
