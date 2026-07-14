"""Quality gates / metric thresholds for automated eval flagging.

Cadence: mostly **automated jobs** (CI + nightly/weekly GitHub Actions).
HITL reviews are scheduled human work with documented frequency — not ad-hoc only.

When a metric breaches its threshold → status = fail (block) or warn (flag).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class GateSeverity(str, Enum):
    BLOCK = "block"  # fails the run / blocks deploy verdict
    FLAG = "flag"  # warning — investigate, do not auto-block


@dataclass(frozen=True)
class MetricThreshold:
    metric: str
    description: str
    direction: str  # min = must be >= threshold; max = must be <= threshold
    threshold: float
    severity: GateSeverity
    category: str  # field_extraction | rag | hitl | safety


# Canonical thresholds used across report, cadence SLAs, and CI flagging
QUALITY_GATES: list[MetricThreshold] = [
    MetricThreshold(
        metric="precision",
        description="Field extraction precision on golden set",
        direction="min",
        threshold=0.85,
        severity=GateSeverity.BLOCK,
        category="field_extraction",
    ),
    MetricThreshold(
        metric="recall",
        description="Field extraction recall on golden set",
        direction="min",
        threshold=0.90,
        severity=GateSeverity.BLOCK,
        category="field_extraction",
    ),
    MetricThreshold(
        metric="hallucination_rate",
        description="1 - recall proxy for missing/invented fields",
        direction="max",
        threshold=0.05,
        severity=GateSeverity.BLOCK,
        category="field_extraction",
    ),
    MetricThreshold(
        metric="ragas_quality_score",
        description="Average of faithfulness + relevancy + context precision/recall",
        direction="min",
        threshold=0.80,
        severity=GateSeverity.BLOCK,
        category="rag",
    ),
    MetricThreshold(
        metric="faithfulness",
        description="Ragas faithfulness (answer grounded in retrieved context)",
        direction="min",
        threshold=0.80,
        severity=GateSeverity.FLAG,
        category="rag",
    ),
    MetricThreshold(
        metric="answer_relevancy",
        description="Ragas answer relevancy",
        direction="min",
        threshold=0.75,
        severity=GateSeverity.FLAG,
        category="rag",
    ),
    MetricThreshold(
        metric="context_precision",
        description="Ragas context precision (retrieved chunks are useful)",
        direction="min",
        threshold=0.70,
        severity=GateSeverity.FLAG,
        category="rag",
    ),
    MetricThreshold(
        metric="context_recall",
        description="Ragas context recall (needed facts retrieved)",
        direction="min",
        threshold=0.70,
        severity=GateSeverity.FLAG,
        category="rag",
    ),
    MetricThreshold(
        metric="hitl_agree_rate",
        description="Share of human reviews that agree with AI decision",
        direction="min",
        threshold=0.80,
        severity=GateSeverity.FLAG,
        category="hitl",
    ),
    MetricThreshold(
        metric="hitl_case_pass_rate",
        description="Share of human rubric reviews that pass all dimension thresholds",
        direction="min",
        threshold=0.80,
        severity=GateSeverity.BLOCK,
        category="hitl",
    ),
    MetricThreshold(
        metric="giskard_high_severity_issues",
        description="High-severity issues from Giskard safety scan",
        direction="max",
        threshold=0.0,
        severity=GateSeverity.FLAG,
        category="safety",
    ),
]


def apply_quality_gates(metrics: dict[str, Any]) -> dict[str, Any]:
    """Compare observed metrics to thresholds and return flags.

    metrics keys should match MetricThreshold.metric names where available.
    Missing metrics are reported as 'skipped' (not a fail).
    """
    results: list[dict[str, Any]] = []
    blocks = 0
    flags = 0
    passes = 0
    skipped = 0

    for gate in QUALITY_GATES:
        raw = metrics.get(gate.metric)
        if raw is None or raw == "N/A":
            results.append(
                {
                    "metric": gate.metric,
                    "status": "skipped",
                    "threshold": gate.threshold,
                    "observed": None,
                    "severity": gate.severity.value,
                    "description": gate.description,
                    "category": gate.category,
                }
            )
            skipped += 1
            continue

        try:
            observed = float(raw)
        except (TypeError, ValueError):
            results.append(
                {
                    "metric": gate.metric,
                    "status": "skipped",
                    "threshold": gate.threshold,
                    "observed": raw,
                    "severity": gate.severity.value,
                    "description": gate.description,
                    "category": gate.category,
                    "note": "non-numeric",
                }
            )
            skipped += 1
            continue

        ok = observed >= gate.threshold if gate.direction == "min" else observed <= gate.threshold
        if ok:
            status = "pass"
            passes += 1
        elif gate.severity == GateSeverity.BLOCK:
            status = "fail"
            blocks += 1
        else:
            status = "flag"
            flags += 1

        results.append(
            {
                "metric": gate.metric,
                "status": status,
                "threshold": gate.threshold,
                "direction": gate.direction,
                "observed": round(observed, 4),
                "severity": gate.severity.value,
                "description": gate.description,
                "category": gate.category,
                "flagged": status in {"fail", "flag"},
            }
        )

    if blocks > 0:
        verdict = "BLOCKED"
    elif flags > 0:
        verdict = "FLAGGED"
    elif passes > 0:
        verdict = "PASS"
    else:
        verdict = "INCOMPLETE"

    return {
        "verdict": verdict,
        "blocks": blocks,
        "flags": flags,
        "passes": passes,
        "skipped": skipped,
        "gates": results,
        "thresholds_reference": [
            {
                "metric": g.metric,
                "threshold": g.threshold,
                "direction": g.direction,
                "severity": g.severity.value,
                "category": g.category,
            }
            for g in QUALITY_GATES
        ],
        "automation": {
            "unit_tests": "automated — every PR/push (GitHub Actions CI)",
            "golden_ragas": "automated — nightly cron (scheduled_evals.yml)",
            "giskard_full_report": "automated — weekly Monday cron",
            "hitl_rubric_reviews": "human on weekly cadence — assisted by APIs; not fully automated scoring",
            "uw_signoff": "human — every submission before bind (hard gate)",
        },
        "interview_summary": (
            f"Mix of automated jobs and human reviews. "
            f"Automated: CI every PR; golden precision/recall + Ragas nightly; Giskard weekly. "
            f"Human: UW sign-off every submission; weekly rubric spot-checks. "
            f"Thresholds: precision≥85% (block), recall≥90% (block), hallucination≤5% (block), "
            f"RAG quality≥80% (block), HITL pass≥80% (block); Ragas component metrics flag below "
            f"faithfulness 80% / relevancy 75% / context P/R 70%. "
            f"Current gate verdict from supplied metrics: {verdict} "
            f"({blocks} blocks, {flags} flags, {passes} passes, {skipped} skipped)."
        ),
    }


def gates_from_report_summary(summary: dict[str, Any], ragas_metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Helper to pull metrics out of generate_report()-style summaries."""
    metrics: dict[str, Any] = {
        "precision": summary.get("precision"),
        "recall": summary.get("recall"),
        "hallucination_rate": summary.get("hallucination_rate"),
        "hitl_agree_rate": summary.get("hitl_agree_rate"),
        "hitl_case_pass_rate": summary.get("hitl_case_pass_rate"),
    }
    qs = summary.get("ragas_quality_score")
    if isinstance(qs, (int, float)):
        metrics["ragas_quality_score"] = qs
    if ragas_metrics:
        for key in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
            payload = ragas_metrics.get(key)
            if isinstance(payload, dict) and "avg" in payload:
                metrics[key] = payload["avg"]
            elif isinstance(payload, (int, float)):
                metrics[key] = payload
    return apply_quality_gates(metrics)


if __name__ == "__main__":
    import json

    demo = apply_quality_gates(
        {
            "precision": 0.91,
            "recall": 0.94,
            "hallucination_rate": 0.03,
            "ragas_quality_score": 0.84,
            "faithfulness": 0.82,
            "answer_relevancy": 0.79,
            "context_precision": 0.72,
            "context_recall": 0.71,
            "hitl_agree_rate": 0.85,
            "hitl_case_pass_rate": 0.82,
            "giskard_high_severity_issues": 0,
        }
    )
    print(json.dumps(demo, indent=2))
