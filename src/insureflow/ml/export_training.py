"""Export labeled training rows from persisted underwriting outcomes → ml_data/.

Scans audit_logs for insurance (pipeline_summary.json), lending (lending/*.json),
and mortgage (mortgage/*.jsonl / mortgage bundles) outcomes and writes a labeled
CSV per model type. Column order follows the target model's feature schema so the
rows can be consumed directly by ``load_training_csv`` / ``train_all_models``.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

from insureflow.ml.features import get_model_feature_names

logger = logging.getLogger(__name__)


def _target_from_decision(decision: str) -> float:
    d = (decision or "").lower()
    if d in {"decline", "declined", "reject", "deny", "denied"}:
        return 1.0
    if d in {"refer", "referral", "conditional_accept", "suspended", "suspend"}:
        return 0.5
    if d in {"accept", "approve", "approved", "bind", "bound"}:
        return 0.0
    return 0.5


def _empty_row(feature_names: list[str]) -> dict[str, Any]:
    return {name: 0.0 for name in feature_names}


def _insurance_row(summary: dict[str, Any], feature_names: list[str]) -> dict[str, Any]:
    row = _empty_row(feature_names)
    row["tiv"] = float(summary.get("tiv") or summary.get("total_insured_value") or 0)
    row["requested_premium"] = float(summary.get("quoted_premium") or summary.get("premium") or 0)
    row["loss_ratio"] = float(summary.get("loss_ratio") or 0)
    row["prior_claims_count"] = float(summary.get("claim_count") or summary.get("prior_claims_count") or 0)
    row["revenue"] = float(summary.get("revenue") or 0)
    row["years_in_business"] = float(summary.get("years_in_business") or 0)
    row["credit_score"] = float(summary.get("credit_score") or 0)
    return row


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


def _mortgage_row(record: dict[str, Any], feature_names: list[str]) -> dict[str, Any]:
    memo = record.get("memo") or {}
    bundle = record.get("bundle") or {}
    credit = bundle.get("credit") or {}
    income = bundle.get("income") or {}
    assets = bundle.get("assets") or {}
    collateral = bundle.get("collateral") or {}

    row = _empty_row(feature_names)
    row["credit_score"] = float(credit.get("credit_score") or 0)
    row["dti_ratio"] = float(memo.get("dti_ratio") or 0)
    row["ltv_ratio"] = float(memo.get("ltv_ratio") or collateral.get("ltv") or 0)
    loan_amount = float(record.get("loan_amount") or 0)
    if not loan_amount and collateral.get("appraised_value"):
        loan_amount = collateral["appraised_value"] * (float(row["ltv_ratio"] or 80) / 100.0)
    row["loan_amount"] = loan_amount
    row["annual_income"] = float(income.get("adjusted_gross_income") or income.get("total_income") or 0)
    row["reserves"] = float(assets.get("total_liquid_assets") or 0)
    row["self_employment_income"] = float(income.get("self_employment_income") or 0)
    row["utilization_rate"] = float(credit.get("utilization_rate") or 0)
    row["derogatory_marks"] = float(len(credit.get("derogatory_flags") or []))
    return row


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

    feature_names = get_model_feature_names(model_type)
    rows: list[dict[str, Any]] = []

    if root.exists():
        if model_type == "lending_default_risk":
            lending_dir = root / "lending"
            if lending_dir.exists():
                for path in lending_dir.glob("*.json"):
                    try:
                        payload = json.loads(path.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, OSError):
                        continue
                    decision = (payload.get("result") or {}).get("decision") or ""
                    row = _lending_row(payload, feature_names)
                    row["target"] = _target_from_decision(decision)
                    rows.append(row)
        elif model_type == "mortgage_default_risk":
            for path in root.rglob("mortgage*.jsonl"):
                try:
                    for line in path.read_text(encoding="utf-8").splitlines():
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        if isinstance(record, dict) and (record.get("memo") or record.get("bundle")):
                            row = _mortgage_row(record, feature_names)
                            decision = (record.get("memo") or {}).get("decision") or record.get("decision") or ""
                            row["target"] = _target_from_decision(decision)
                            rows.append(row)
                except (json.JSONDecodeError, OSError):
                    continue
        else:
            for path in root.rglob("pipeline_summary.json"):
                try:
                    summary = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                decision = str(summary.get("decision") or summary.get("ai_decision") or "")
                row = _insurance_row(summary, feature_names)
                row["target"] = _target_from_decision(decision)
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
    return {"ok": True, "rows": len(rows), "path": str(dest), "model_type": model_type}
