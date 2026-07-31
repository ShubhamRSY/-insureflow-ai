"""ZTA reporting — per-job report and process-wide statistics.

The reporter records every routing decision a job makes so the final result can
answer "how many tokens did we *not* spend?" and "which tasks genuinely needed
an LLM?".  A process-wide counter tracks the same numbers across all jobs for
the ``/api/zta/status`` endpoint.
"""

from __future__ import annotations

import threading
from typing import Any

from insureflow.zta.models import RouteContext, RouteResult, ZtaTask
from insureflow.zta.router import ZeroTokenRouter, get_router

_ACCUMULATOR_LOCK = threading.Lock()
_ACCUMULATOR: dict[str, Any] = {
    "jobs": 0,
    "tasks": 0,
    "deterministic": 0,
    "llm": 0,
    "escalate_human": 0,
    "skip": 0,
    "tokens_saved_est": 0,
    "tokens_used_est": 0,
}


def get_zta_stats() -> dict[str, Any]:
    """Process-wide ZTA counters (thread-safe snapshot)."""
    with _ACCUMULATOR_LOCK:
        return {k: v for k, v in _ACCUMULATOR.items()}


class ZtaReporter:
    """Accumulates routing decisions for a single job/request."""

    def __init__(self, router: ZeroTokenRouter | None = None) -> None:
        self.router = router or get_router()
        self.router.reset_job()
        self.decisions: list[RouteResult] = []

    def route(self, task: ZtaTask, ctx: RouteContext | dict[str, Any] | None = None) -> RouteResult:
        result = self.router.route(task, ctx)
        self.decisions.append(result)
        return result

    def record(self, result: RouteResult) -> None:
        self.decisions.append(result)

    def report(self) -> dict[str, Any]:
        totals: dict[str, int] = {
            "tasks": len(self.decisions),
            "deterministic": 0,
            "llm": 0,
            "escalate_human": 0,
            "skip": 0,
            "tokens_saved_est": 0,
            "tokens_used_est": 0,
        }
        for d in self.decisions:
            totals[d.decision.value] += 1
            totals["tokens_saved_est"] += d.tokens_saved_est
            totals["tokens_used_est"] += d.tokens_used_est

        with _ACCUMULATOR_LOCK:
            _ACCUMULATOR["jobs"] += 1
            _ACCUMULATOR["tasks"] += totals["tasks"]
            for key in ("deterministic", "llm", "escalate_human", "skip", "tokens_saved_est", "tokens_used_est"):
                _ACCUMULATOR[key] += totals[key]

        return {
            "policy": "Use AI only when you must. Everything else, solve deterministically.",
            "mode": self.router.config.mode,
            "config": self.router.config.to_dict(),
            "tasks": [d.to_dict() for d in self.decisions],
            "totals": totals,
        }
