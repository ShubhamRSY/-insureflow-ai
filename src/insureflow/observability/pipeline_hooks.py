"""Best-effort observability hooks after an insurance pipeline run."""

from __future__ import annotations

from typing import Any


def record_pipeline_observability(summary: dict[str, Any] | None) -> None:
    if not summary:
        return
    try:
        from insureflow.observability.prometheus_metrics import observe_pipeline

        observe_pipeline(summary)
    except Exception:
        pass
    try:
        from insureflow.observability.openobserve import emit_pipeline_trace

        emit_pipeline_trace(summary)
    except Exception:
        pass
