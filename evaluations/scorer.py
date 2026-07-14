from __future__ import annotations

import json
import logging
from typing import Any

from evaluations.golden_dataset import golden_dataset
from evaluations.runner import run_case

logger = logging.getLogger(__name__)


def compute_precision(actual: Any, expected: Any, tolerance: float = 0.05) -> float:
    if expected is None:
        return 1.0
    if actual is None:
        return 0.0
    if isinstance(expected, (int, float)):
        if expected == 0:
            return 1.0
        return max(0.0, 1.0 - abs(float(actual) - float(expected)) / float(expected))
    if isinstance(expected, bool):
        return 1.0 if actual == expected else 0.0
    if isinstance(expected, str):
        return 1.0 if str(actual).strip().lower() == expected.strip().lower() else 0.0
    return 1.0 if actual == expected else 0.0


def compute_recall(found: int, expected: int) -> float:
    if expected == 0:
        return 1.0
    return min(1.0, found / expected)


FIELD_KEYS = [
    ("insured_name", "Named insured"),
    ("construction", "Construction type"),
    ("occupancy", "Occupancy type"),
    ("protection_class", "Protection class"),
    ("square_footage", "Square footage"),
    ("stories", "Number of stories"),
    ("naics", "NAICS code"),
    ("revenue", "Annual revenue"),
    ("payroll", "Payroll"),
]


def score_case(case_result: dict[str, Any], tolerance: float = 0.05) -> dict[str, Any]:
    actual = case_result.get("actual", {})
    expected = case_result.get("expected", {})

    field_scores: dict[str, float] = {}
    for key, label in FIELD_KEYS:
        a = actual.get(key)
        e = expected.get(key)
        field_scores[key] = compute_precision(a, e, tolerance)

    precision = sum(field_scores.values()) / max(len(field_scores), 1)
    recall = compute_recall(
        sum(1 for v in field_scores.values() if v >= 0.5),
        sum(1 for k in field_scores if expected.get(k) is not None),
    )
    hallucination_rate = 1.0 - recall

    return {
        "case": case_result.get("case", "unknown"),
        "status": case_result.get("status"),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "field_scores": {k: round(v, 4) for k, v in field_scores.items()},
    }


def score_all(output_path: str | None = None) -> list[dict[str, Any]]:
    cases = golden_dataset()
    scored: list[dict[str, Any]] = []

    for case in cases:
        try:
            result = run_case(case)
            s = score_case(result)
            scored.append(s)
        except Exception as exc:
            scored.append(
                {
                    "case": case.name,
                    "status": "error",
                    "error": str(exc),
                    "precision": 0.0,
                    "recall": 0.0,
                    "hallucination_rate": 1.0,
                }
            )

    avg_precision = sum(s["precision"] for s in scored) / max(len(scored), 1)
    avg_recall = sum(s["recall"] for s in scored) / max(len(scored), 1)
    avg_hallucination = sum(s["hallucination_rate"] for s in scored) / max(len(scored), 1)

    summary = {
        "total_cases": len(scored),
        "avg_precision": round(avg_precision, 4),
        "avg_recall": round(avg_recall, 4),
        "avg_hallucination_rate": round(avg_hallucination, 4),
        "results": scored,
    }

    try:
        from evaluations.quality_gates import apply_quality_gates

        gates = apply_quality_gates(
            {
                "precision": avg_precision,
                "recall": avg_recall,
                "hallucination_rate": avg_hallucination,
            }
        )
        summary["quality_gates"] = gates
        summary["gate_verdict"] = gates["verdict"]
        if gates["verdict"] == "BLOCKED":
            logger.error("QUALITY GATE BLOCKED: %s", [g for g in gates["gates"] if g["status"] == "fail"])
        elif gates["verdict"] == "FLAGGED":
            logger.warning("QUALITY GATE FLAGGED: %s", [g for g in gates["gates"] if g["status"] == "flag"])
    except Exception as exc:
        logger.warning("Quality gates skipped: %s", exc)

    try:
        from evaluations.trend_store import EvalTrendStore

        EvalTrendStore().record(
            "golden_scorer",
            {
                "precision": avg_precision,
                "recall": avg_recall,
                "hallucination_rate": avg_hallucination,
            },
            metadata={"total_cases": len(scored)},
        )
    except Exception as exc:
        logger.warning("Trend store append skipped: %s", exc)

    try:
        from evaluations.drift import detect_drift, log_drift_event, maybe_open_regression_experiment

        drift = detect_drift(
            {
                "precision": avg_precision,
                "recall": avg_recall,
                "hallucination_rate": avg_hallucination,
            }
        )
        summary["drift"] = drift.to_dict()
        if drift.status.value != "none":
            log_drift_event(drift)
            logger.warning("MODEL/AGENT DRIFT: %s — %s", drift.status.value, drift.interview_summary)
            exp = maybe_open_regression_experiment(drift)
            if exp:
                summary["drift"]["regression_experiment"] = {"run_id": exp.get("run_id"), "name": exp.get("name")}
    except Exception as exc:
        logger.warning("Drift detection skipped: %s", exc)

    try:
        from evaluations.cloud_tracker import get_tracker

        cloud = get_tracker().log_case_scores(scored)
        summary["cloud_tracking"] = {
            "enabled": cloud.enabled,
            "provider": cloud.provider,
            "project": cloud.project,
            "run_id": cloud.run_id,
            "url": cloud.url,
            "local_path": cloud.local_path,
            "error": cloud.error,
        }
    except Exception as exc:
        logger.warning("Cloud tracking skipped: %s", exc)
        summary["cloud_tracking"] = {"enabled": False, "error": str(exc)}

    if output_path:
        import pathlib

        pathlib.Path(output_path).write_text(json.dumps(summary, indent=2, default=str))

    return scored


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "evaluation_scores.json"
    score_all(out)
    print(f"Scores written to {out}")
