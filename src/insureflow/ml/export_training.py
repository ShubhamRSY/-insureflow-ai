"""Export labeled training rows from persisted insurance/lending outcomes → ml_data/."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

from insureflow.ml.features import DEFAULT_FEATURE_NAMES

logger = logging.getLogger(__name__)


def _row_from_insurance_summary(summary: dict[str, Any], target: float) -> dict[str, Any]:
    row = {name: 0.0 for name in DEFAULT_FEATURE_NAMES}
    row["tiv"] = float(summary.get("tiv") or summary.get("total_insured_value") or 0)
    row["requested_premium"] = float(summary.get("quoted_premium") or summary.get("premium") or 0)
    row["loss_ratio"] = float(summary.get("loss_ratio") or 0)
    row["prior_claims_count"] = float(summary.get("claim_count") or summary.get("prior_claims_count") or 0)
    row["revenue"] = float(summary.get("revenue") or 0)
    row["years_in_business"] = float(summary.get("years_in_business") or 0)
    row["credit_score"] = float(summary.get("credit_score") or 0)
    row["target"] = target
    return row


def _target_from_decision(decision: str) -> float:
    d = (decision or "").lower()
    if d in {"decline", "declined", "reject"}:
        return 1.0
    if d in {"refer", "referral", "conditional_accept", "suspended"}:
        return 0.5
    if d in {"accept", "approve", "approved", "bind", "bound"}:
        return 0.0
    return 0.5


def export_from_audit_logs(
    audit_root: Path | str | None = None,
    *,
    out_path: Path | str | None = None,
    model_type: str = "loss_prediction",
) -> dict[str, Any]:
    """Scan audit_logs for pipeline summaries and write a training CSV."""
    root = Path(audit_root or Path.cwd() / "audit_logs")
    dest = Path(out_path or Path.cwd() / "ml_data" / f"{model_type}.csv")
    dest.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    if root.exists():
        for path in root.rglob("pipeline_summary.json"):
            try:
                summary = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            decision = str(summary.get("decision") or summary.get("ai_decision") or "")
            rows.append(_row_from_insurance_summary(summary, _target_from_decision(decision)))

        lending_dir = root / "lending"
        if lending_dir.exists():
            for path in lending_dir.glob("*.json"):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                result = payload.get("result") or {}
                app = payload.get("application") or {}
                fin = (app.get("financials") or [{}])[0] if isinstance(app.get("financials"), list) else {}
                row = {name: 0.0 for name in DEFAULT_FEATURE_NAMES}
                row["revenue"] = float(fin.get("annual_revenue") or 0)
                row["requested_premium"] = float(app.get("requested_amount") or 0)
                row["credit_score"] = float(((app.get("financial_data") or {}).get("credit_score")) or 0)
                row["years_in_business"] = float(app.get("years_in_business") or 0)
                row["target"] = _target_from_decision(str(result.get("decision") or ""))
                rows.append(row)

    if not rows:
        return {"ok": False, "rows": 0, "path": str(dest), "message": "No audit outcomes found to export"}

    fieldnames = DEFAULT_FEATURE_NAMES + ["target"]
    with dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, 0.0) for k in fieldnames})

    logger.info("Exported %d training rows → %s", len(rows), dest)
    return {"ok": True, "rows": len(rows), "path": str(dest), "model_type": model_type}
