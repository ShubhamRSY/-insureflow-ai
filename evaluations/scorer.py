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
            scored.append({
                "case": case.name,
                "status": "error",
                "error": str(exc),
                "precision": 0.0,
                "recall": 0.0,
                "hallucination_rate": 1.0,
            })

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

    if output_path:
        import pathlib
        pathlib.Path(output_path).write_text(json.dumps(summary, indent=2, default=str))

    return scored


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "evaluation_scores.json"
    score_all(out)
    print(f"Scores written to {out}")
