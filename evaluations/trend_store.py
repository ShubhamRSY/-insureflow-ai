"""Time-series store for eval / agent performance trends (visualization source)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

DEFAULT_TREND_PATH = Path(os.getenv("EVAL_TREND_PATH", "./evaluation_trends/trends.jsonl"))


class EvalTrendStore:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or DEFAULT_TREND_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, suite: str, metrics: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        row = {
            "id": f"trend-{uuid4().hex[:10]}",
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "suite": suite,
            "metrics": metrics,
            "metadata": metadata or {},
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
        return row

    def list(self, suite: str | None = None, limit: int = 90) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if suite and row.get("suite") != suite:
                continue
            rows.append(row)
        return rows[-limit:]

    def series(self, metric: str, suite: str | None = None, limit: int = 90) -> list[dict[str, Any]]:
        out = []
        for row in self.list(suite=suite, limit=limit):
            val = (row.get("metrics") or {}).get(metric)
            if val is None:
                continue
            try:
                out.append({"ts": row["ts"], "suite": row.get("suite"), "value": float(val)})
            except (TypeError, ValueError):
                continue
        return out

    def dashboard_payload(self) -> dict[str, Any]:
        rows = self.list(limit=120)
        suites = sorted({r.get("suite", "") for r in rows if r.get("suite")})
        # Build multi-metric series for charts
        chart_metrics = [
            "precision",
            "recall",
            "hallucination_rate",
            "ragas_quality_score",
            "hitl_case_pass_rate",
            "avg_agent_error_rate",
            "avg_agent_latency_ms",
        ]
        series = {m: self.series(m, limit=90) for m in chart_metrics}
        latest = rows[-1] if rows else None
        return {
            "points": len(rows),
            "suites": suites,
            "latest": latest,
            "series": series,
            "visualization": "frontend /evaluations page — Recharts line/bar trends",
            "automation": "Scorer + nightly CI append points; agent log analyzer appends latency/error rates",
        }


def seed_demo_trends(store: EvalTrendStore | None = None) -> int:
    """Seed a short trend history so charts render without waiting for nights."""
    store = store or EvalTrendStore()
    if store.list():
        return 0
    demo = [
        {"precision": 0.82, "recall": 0.88, "hallucination_rate": 0.08, "ragas_quality_score": 0.76, "hitl_case_pass_rate": 0.72, "avg_agent_error_rate": 0.04, "avg_agent_latency_ms": 780},
        {"precision": 0.86, "recall": 0.91, "hallucination_rate": 0.05, "ragas_quality_score": 0.81, "hitl_case_pass_rate": 0.78, "avg_agent_error_rate": 0.03, "avg_agent_latency_ms": 720},
        {"precision": 0.89, "recall": 0.93, "hallucination_rate": 0.04, "ragas_quality_score": 0.84, "hitl_case_pass_rate": 0.83, "avg_agent_error_rate": 0.02, "avg_agent_latency_ms": 690},
        {"precision": 0.91, "recall": 0.94, "hallucination_rate": 0.03, "ragas_quality_score": 0.86, "hitl_case_pass_rate": 0.88, "avg_agent_error_rate": 0.018, "avg_agent_latency_ms": 650},
        {"precision": 0.92, "recall": 0.95, "hallucination_rate": 0.025, "ragas_quality_score": 0.87, "hitl_case_pass_rate": 0.90, "avg_agent_error_rate": 0.015, "avg_agent_latency_ms": 630},
    ]
    for i, m in enumerate(demo):
        store.record("golden_nightly", m, metadata={"seed": True, "day_offset": i - len(demo) + 1})
    return len(demo)
