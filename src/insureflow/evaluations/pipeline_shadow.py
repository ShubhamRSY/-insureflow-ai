"""Shadow pipeline evaluations — stored in audit only, never shown on broker-facing UI."""

from __future__ import annotations

from typing import Any


def _score_rating_band(indicated: float, tiv: float, line: str) -> dict[str, Any]:
    """Check premium is within actuarial reasonableness band for exposure."""
    if indicated <= 0 or tiv <= 0:
        return {"score": 0.0, "passed": False, "reason": "missing premium or exposure"}
    rate = indicated / tiv
    low, high = 0.0015, 0.012
    if "liability" in line or "general" in line:
        low, high = 0.0003, 0.004
    if "workers" in line or "comp" in line:
        low, high = 0.002, 0.025
    passed = low <= rate <= high
    mid = (low + high) / 2
    score = max(0.0, 1.0 - abs(rate - mid) / max(mid, 1e-9))
    return {
        "score": round(min(score, 1.0), 4),
        "passed": passed,
        "implied_rate": round(rate, 6),
        "band": [low, high],
    }


def _score_decision_alignment(ai_decision: str, eligible: bool, premium: float) -> dict[str, Any]:
    decision = (ai_decision or "").lower()
    passed = True
    reasons: list[str] = []
    if decision in ("decline", "refer") and eligible and premium > 0:
        passed = False
        reasons.append("eligible quote with decline/refer decision")
    if decision == "accept" and not eligible:
        passed = False
        reasons.append("accept on ineligible quote")
    return {"score": 1.0 if passed else 0.35, "passed": passed, "reasons": reasons}


def _score_data_quality(checklist: dict[str, Any] | None, recon_count: int) -> dict[str, Any]:
    completeness = float((checklist or {}).get("completeness_pct") or 0)
    missing = len((checklist or {}).get("missing") or [])
    recon_penalty = min(recon_count * 0.08, 0.4)
    score = max(0.0, min(1.0, completeness / 100.0 - recon_penalty))
    passed = completeness >= 60.0 and recon_count <= 3
    return {
        "score": round(score, 4),
        "passed": passed,
        "completeness_pct": completeness,
        "missing_docs": missing,
        "reconciliation_conflicts": recon_count,
    }


def run_shadow_eval(
    *,
    summary: dict[str, Any],
    quote: dict[str, Any] | Any,
    memo: dict[str, Any] | Any,
) -> dict[str, Any]:
    """Run backend quality evals; persist to audit — not returned to standard job API."""
    if hasattr(quote, "adjusted_premium"):
        indicated = float(quote.adjusted_premium or 0)
        eligible = bool(getattr(quote, "eligible", True))
    else:
        indicated = float((quote or {}).get("adjusted_premium") or (summary.get("quote") or {}).get("adjusted_premium") or 0)
        eligible = bool((quote or {}).get("eligible", True))

    if hasattr(memo, "decision"):
        ai_decision = memo.decision.value if hasattr(memo.decision, "value") else str(memo.decision)
    else:
        ai_decision = str((memo or {}).get("decision") or summary.get("ai_decision") or "")

    line = str(summary.get("insurance_line") or "")
    tiv = float(summary.get("tiv") or 0)
    checklist = summary.get("document_checklist")
    recon = int(summary.get("reconciliation_discrepancies") or 0)

    rating = _score_rating_band(indicated, tiv, line)
    decision = _score_decision_alignment(ai_decision, eligible, indicated)
    data_q = _score_data_quality(checklist, recon)

    scores = [rating["score"], decision["score"], data_q["score"]]
    overall = round(sum(scores) / len(scores), 4) if scores else 0.0
    overall_pass = all(x.get("passed") for x in (rating, decision, data_q))

    return {
        "version": "1.0",
        "overall_score": overall,
        "overall_pass": overall_pass,
        "tasks": {
            "rating_reasonableness": rating,
            "decision_alignment": decision,
            "data_quality": data_q,
        },
        "bundle_id": summary.get("bundle_id"),
        "insurance_line": line,
        "indicated_premium": indicated,
    }
