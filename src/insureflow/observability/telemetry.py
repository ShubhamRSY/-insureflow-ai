"""Pipeline telemetry — span-based end-to-end latency tracing across all layers."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)


class Span:
    """A single unit of work within a pipeline trace."""

    __slots__ = (
        "trace_id",
        "span_id",
        "parent_span_id",
        "name",
        "layer",
        "start_time",
        "end_time",
        "status",
        "attributes",
        "events",
    )

    def __init__(
        self,
        trace_id: str,
        name: str,
        layer: str,
        parent_span_id: Optional[str] = None,
    ) -> None:
        self.trace_id = trace_id
        self.span_id = uuid.uuid4().hex[:16]
        self.parent_span_id = parent_span_id
        self.name = name
        self.layer = layer
        self.start_time = time.monotonic()
        self.end_time: float = 0.0
        self.status = "OK"
        self.attributes: dict[str, Any] = {}
        self.events: list[dict[str, Any]] = []

    @property
    def duration_ms(self) -> float:
        if self.end_time <= 0:
            return (time.monotonic() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[dict[str, Any]] = None) -> None:
        self.events.append(
            {
                "name": name,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "attributes": attributes or {},
            }
        )

    def finish(self, status: str = "OK") -> None:
        self.end_time = time.monotonic()
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "layer": self.layer,
            "start_time": datetime.fromtimestamp(self.start_time, tz=timezone.utc).isoformat(),
            "duration_ms": round(self.duration_ms, 3),
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
        }


class PipelineTrace:
    """A complete trace of a pipeline request across all layers."""

    def __init__(self, trace_id: Optional[str] = None, bundle_id: str = "", user_id: str = "") -> None:
        self.trace_id = trace_id or uuid.uuid4().hex
        self.bundle_id = bundle_id
        self.user_id = user_id
        self.spans: list[Span] = []
        self.start_time = time.monotonic()
        self.end_time: float = 0.0
        self._span_stack: list[Span] = []
        self._layer_latencies: dict[str, list[float]] = {}

    @property
    def duration_ms(self) -> float:
        if self.end_time <= 0:
            return (time.monotonic() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def start_span(self, name: str, layer: str) -> Span:
        parent_id = self._span_stack[-1].span_id if self._span_stack else None
        span = Span(self.trace_id, name, layer, parent_id)
        self.spans.append(span)
        self._span_stack.append(span)
        return span

    def finish_span(self, span: Span, status: str = "OK") -> None:
        span.finish(status)
        if span in self._span_stack:
            self._span_stack.remove(span)
        self._layer_latencies.setdefault(span.layer, []).append(span.duration_ms)

    @contextmanager
    def span(self, name: str, layer: str) -> Generator[Span, None, None]:
        s = self.start_span(name, layer)
        try:
            yield s
            self.finish_span(s, "OK")
        except Exception as exc:
            s.set_attribute("error.type", type(exc).__name__)
            s.set_attribute("error.message", str(exc))
            self.finish_span(s, "ERROR")
            raise

    def finish(self) -> None:
        self.end_time = time.monotonic()

    def get_layer_latencies(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for layer, durations in self._layer_latencies.items():
            result[layer] = {
                "count": len(durations),
                "total_ms": round(sum(durations), 3),
                "avg_ms": round(sum(durations) / len(durations), 3),
                "min_ms": round(min(durations), 3),
                "max_ms": round(max(durations), 3),
            }
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "bundle_id": self.bundle_id,
            "user_id": self.user_id,
            "total_duration_ms": round(self.duration_ms, 3),
            "span_count": len(self.spans),
            "layer_latencies": self.get_layer_latencies(),
            "spans": [s.to_dict() for s in self.spans],
            "completed_at": datetime.now(tz=timezone.utc).isoformat(),
        }


class TelemetryCollector:
    """Collects and persists pipeline traces for analysis."""

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._active_traces: dict[str, PipelineTrace] = {}
        self._completed_traces: list[dict[str, Any]] = []
        self._persist_path = persist_path or Path(os.getenv("TELEMETRY_PATH", "./audit_logs/telemetry.jsonl"))
        self._layer_totals: dict[str, dict[str, float]] = {}

    def start_trace(self, bundle_id: str = "", user_id: str = "") -> PipelineTrace:
        trace = PipelineTrace(bundle_id=bundle_id, user_id=user_id)
        with self._lock:
            self._active_traces[trace.trace_id] = trace
        return trace

    def finish_trace(self, trace: PipelineTrace) -> dict[str, Any]:
        trace.finish()
        summary = trace.to_dict()
        with self._lock:
            self._active_traces.pop(trace.trace_id, None)
            self._completed_traces.append(summary)
            for layer, stats in trace.get_layer_latencies().items():
                if layer not in self._layer_totals:
                    self._layer_totals[layer] = {"total_ms": 0, "count": 0}
                self._layer_totals[layer]["total_ms"] += stats["total_ms"]
                self._layer_totals[layer]["count"] += stats["count"]
            self._persist(summary)
        return summary

    def _persist(self, summary: dict[str, Any]) -> None:
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(summary, default=str) + "\n")
        except OSError:
            logger.debug("Failed to persist telemetry trace", exc_info=True)

    def get_aggregate_stats(self) -> dict[str, Any]:
        with self._lock:
            result: dict[str, Any] = {}
            for layer, totals in self._layer_totals.items():
                avg = totals["total_ms"] / totals["count"] if totals["count"] > 0 else 0
                result[layer] = {
                    "total_calls": int(totals["count"]),
                    "total_latency_ms": round(totals["total_ms"], 3),
                    "avg_latency_ms": round(avg, 3),
                }
            return result

    def get_recent_traces(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return self._completed_traces[-limit:]


_collector: Optional[TelemetryCollector] = None


def get_telemetry_collector() -> TelemetryCollector:
    global _collector
    if _collector is None:
        _collector = TelemetryCollector()
    return _collector
