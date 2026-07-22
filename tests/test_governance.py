"""Tests for token usage tracker, budget manager, and pipeline telemetry."""

from __future__ import annotations

import json
import tempfile
import threading
from pathlib import Path

import pytest

from insureflow.llm.budget import BudgetExceededError, BudgetManager
from insureflow.llm.tracker import TokenUsageRecord, TokenUsageTracker, estimate_cost
from insureflow.observability.telemetry import PipelineTrace, Span, TelemetryCollector

# ---------------------------------------------------------------------------
# Token Usage Tracker
# ---------------------------------------------------------------------------

class TestEstimateCost:
    def test_gpt4o_cost(self) -> None:
        cost = estimate_cost("gpt-4o", input_tokens=1000, output_tokens=1000)
        assert cost == pytest.approx(0.0125, abs=0.0001)

    def test_gpt4o_mini_cost(self) -> None:
        cost = estimate_cost("gpt-4o-mini", input_tokens=1000, output_tokens=1000)
        assert cost == pytest.approx(0.00075, abs=0.0001)

    def test_unknown_model_defaults_to_gpt4o(self) -> None:
        cost = estimate_cost("unknown-model", input_tokens=1000, output_tokens=1000)
        assert cost == pytest.approx(0.0125, abs=0.0001)

    def test_zero_tokens(self) -> None:
        cost = estimate_cost("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_input_only(self) -> None:
        cost = estimate_cost("gpt-4o", input_tokens=2000, output_tokens=0)
        assert cost == pytest.approx(0.005, abs=0.0001)


class TestTokenUsageRecord:
    def test_to_dict(self) -> None:
        record = TokenUsageRecord(
            model="gpt-4o",
            tier="expensive",
            input_tokens=100,
            output_tokens=50,
            cost=0.001,
            agent="uw_decision",
            bundle_id="b-123",
            user_id="user-1",
        )
        d = record.to_dict()
        assert d["model"] == "gpt-4o"
        assert d["tier"] == "expensive"
        assert d["input_tokens"] == 100
        assert d["output_tokens"] == 50
        assert d["total_tokens"] == 150
        assert d["cost"] == 0.001
        assert d["agent"] == "uw_decision"
        assert d["bundle_id"] == "b-123"
        assert d["user_id"] == "user-1"
        assert "timestamp" in d


class TestTokenUsageTracker:
    def test_record_and_totals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "expensive", 100, 50, agent="agent1")
            tracker.record("gpt-4o-mini", "cheap", 200, 100, agent="agent2")
            totals = tracker.get_session_totals()
            assert totals["request_count"] == 2
            assert totals["input_tokens"] == 300
            assert totals["output_tokens"] == 150
            assert totals["total_tokens"] == 450
            assert totals["total_cost"] > 0

    def test_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.jsonl"
            tracker = TokenUsageTracker(persist_path=path)
            tracker.record("gpt-4o", "default", 100, 50)
            assert path.exists()
            lines = path.read_text().strip().split("\n")
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["model"] == "gpt-4o"

    def test_get_by_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "expensive", 100, 50)
            tracker.record("gpt-4o", "expensive", 200, 100)
            tracker.record("gpt-4o-mini", "cheap", 50, 25)
            by_model = tracker.get_by_model()
            assert by_model["gpt-4o"]["count"] == 2
            assert by_model["gpt-4o"]["input_tokens"] == 300
            assert by_model["gpt-4o-mini"]["count"] == 1

    def test_get_by_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 100, 50, agent="extraction")
            tracker.record("gpt-4o", "default", 200, 100, agent="extraction")
            tracker.record("gpt-4o", "default", 100, 50, agent="decision")
            by_agent = tracker.get_by_agent()
            assert by_agent["extraction"]["count"] == 2
            assert by_agent["decision"]["count"] == 1

    def test_get_by_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 100, 50, user_id="u1")
            tracker.record("gpt-4o", "default", 100, 50, user_id="u2")
            by_user = tracker.get_by_user()
            assert by_user["u1"]["count"] == 1
            assert by_user["u2"]["count"] == 1

    def test_get_records_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            for _ in range(10):
                tracker.record("gpt-4o", "default", 10, 5)
            records = tracker.get_records(limit=3)
            assert len(records) == 3

    def test_reset_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 100, 50)
            tracker.reset_session()
            totals = tracker.get_session_totals()
            assert totals["request_count"] == 0
            assert totals["total_tokens"] == 0

    def test_thread_safety(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")

            def record_many() -> None:
                for _ in range(50):
                    tracker.record("gpt-4o", "default", 10, 5)

            threads = [threading.Thread(target=record_many) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            totals = tracker.get_session_totals()
            assert totals["request_count"] == 200


# ---------------------------------------------------------------------------
# Budget Manager
# ---------------------------------------------------------------------------

class TestBudgetManager:
    def test_no_limits_always_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            mgr = BudgetManager(daily_limit=0, monthly_limit=0, tracker=tracker)
            status = mgr.check_budget()
            assert status["budget_exceeded"] is False

    def test_daily_limit_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 5000, 2000)
            mgr = BudgetManager(daily_limit=0.01, monthly_limit=0, hard_stop=False, tracker=tracker)
            status = mgr.check_budget()
            assert status["budget_exceeded"] is True
            assert status["daily_spent"] > 0

    def test_monthly_limit_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 5000, 2000)
            mgr = BudgetManager(daily_limit=0, monthly_limit=0.01, hard_stop=False, tracker=tracker)
            status = mgr.check_budget()
            assert status["budget_exceeded"] is True

    def test_enforce_raises_on_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 5000, 2000)
            mgr = BudgetManager(daily_limit=0.01, monthly_limit=0, hard_stop=True, tracker=tracker)
            with pytest.raises(BudgetExceededError) as exc_info:
                mgr.enforce()
            assert exc_info.value.limit_type == "daily"

    def test_enforce_no_raise_when_soft_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 5000, 2000)
            mgr = BudgetManager(daily_limit=0.01, monthly_limit=0, hard_stop=False, tracker=tracker)
            mgr.enforce()

    def test_alert_callback_fires(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 5000, 2000)
            alerts: list[tuple[str, float, float]] = []
            mgr = BudgetManager(daily_limit=0.01, monthly_limit=0, hard_stop=False, tracker=tracker)
            mgr.add_alert_callback(lambda t, c, limit: alerts.append((t, c, limit)))
            mgr.check_budget()
            assert len(alerts) >= 1
            assert alerts[0][0] == "daily_limit_exceeded"

    def test_alert_fires_only_once_per_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 5000, 2000)
            alerts: list[tuple[str, float, float]] = []
            mgr = BudgetManager(daily_limit=0.01, monthly_limit=0, hard_stop=False, tracker=tracker)
            mgr.add_alert_callback(lambda t, c, limit: alerts.append((t, c, limit)))
            mgr.check_budget()
            mgr.check_budget()
            assert len(alerts) == 1

    def test_status_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            mgr = BudgetManager(daily_limit=10.0, monthly_limit=100.0, tracker=tracker)
            status = mgr.check_budget()
            assert status["daily_limit"] == 10.0
            assert status["monthly_limit"] == 100.0
            assert status["daily_spent"] == 0.0
            assert status["monthly_spent"] == 0.0
            assert status["daily_remaining"] == 10.0
            assert status["monthly_remaining"] == 100.0

    def test_reset_alerts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 5000, 2000)
            mgr = BudgetManager(daily_limit=0.01, monthly_limit=0, hard_stop=False, tracker=tracker)
            mgr.check_budget()
            mgr.reset_alerts()
            alerts: list[tuple[str, float, float]] = []
            mgr.add_alert_callback(lambda t, c, limit: alerts.append((t, c, limit)))
            mgr.check_budget()
            assert len(alerts) == 1


# ---------------------------------------------------------------------------
# Pipeline Telemetry
# ---------------------------------------------------------------------------

class TestSpan:
    def test_basic_lifecycle(self) -> None:
        span = Span(trace_id="t1", name="extract", layer="ingestion")
        assert span.trace_id == "t1"
        assert span.name == "extract"
        assert span.layer == "ingestion"
        assert span.status == "OK"
        span.set_attribute("doc_type", "acord")
        assert span.attributes["doc_type"] == "acord"
        span.add_event("start", {"info": "beginning"})
        assert len(span.events) == 1
        span.finish()
        assert span.duration_ms >= 0
        assert span.end_time > 0

    def test_to_dict(self) -> None:
        span = Span(trace_id="t1", name="parse", layer="parser")
        span.finish()
        d = span.to_dict()
        assert d["trace_id"] == "t1"
        assert d["name"] == "parse"
        assert d["layer"] == "parser"
        assert d["status"] == "OK"
        assert "duration_ms" in d


class TestPipelineTrace:
    def test_basic_trace(self) -> None:
        trace = PipelineTrace(bundle_id="b-1")
        with trace.span("ingest", "ingestion"):
            pass
        with trace.span("extract", "extraction"):
            pass
        trace.finish()
        assert len(trace.spans) == 2
        assert trace.bundle_id == "b-1"
        assert trace.duration_ms >= 0

    def test_nested_spans(self) -> None:
        trace = PipelineTrace(bundle_id="b-2")
        with trace.span("outer", "pipeline"):
            with trace.span("inner", "agent"):
                pass
        trace.finish()
        assert len(trace.spans) == 2
        assert trace.spans[1].parent_span_id == trace.spans[0].span_id

    def test_exception_in_span(self) -> None:
        trace = PipelineTrace(bundle_id="b-3")
        with pytest.raises(ValueError):
            with trace.span("failing", "agent"):
                raise ValueError("boom")
        trace.finish()
        assert trace.spans[0].status == "ERROR"
        assert trace.spans[0].attributes["error.type"] == "ValueError"

    def test_layer_latencies(self) -> None:
        trace = PipelineTrace(bundle_id="b-4")
        with trace.span("s1", "layer_a"):
            pass
        with trace.span("s2", "layer_a"):
            pass
        with trace.span("s3", "layer_b"):
            pass
        trace.finish()
        latencies = trace.get_layer_latencies()
        assert latencies["layer_a"]["count"] == 2
        assert latencies["layer_b"]["count"] == 1

    def test_to_dict(self) -> None:
        trace = PipelineTrace(bundle_id="b-5", user_id="u-1")
        with trace.span("step", "pipeline"):
            pass
        trace.finish()
        d = trace.to_dict()
        assert d["bundle_id"] == "b-5"
        assert d["user_id"] == "u-1"
        assert d["span_count"] == 1
        assert "spans" in d
        assert "layer_latencies" in d

    def test_auto_generated_trace_id(self) -> None:
        trace = PipelineTrace()
        assert len(trace.trace_id) == 32


class TestTelemetryCollector:
    def test_start_and_finish_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            collector = TelemetryCollector(persist_path=Path(tmp) / "telemetry.jsonl")
            trace = collector.start_trace(bundle_id="b-1")
            with trace.span("step1", "ingestion"):
                pass
            summary = collector.finish_trace(trace)
            assert summary["bundle_id"] == "b-1"
            assert summary["span_count"] == 1

    def test_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "telemetry.jsonl"
            collector = TelemetryCollector(persist_path=path)
            trace = collector.start_trace(bundle_id="b-2")
            with trace.span("s1", "layer"):
                pass
            collector.finish_trace(trace)
            assert path.exists()
            lines = path.read_text().strip().split("\n")
            assert len(lines) == 1

    def test_aggregate_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            collector = TelemetryCollector(persist_path=Path(tmp) / "telemetry.jsonl")
            for _ in range(3):
                trace = collector.start_trace()
                with trace.span("s1", "extraction"):
                    pass
                collector.finish_trace(trace)
            stats = collector.get_aggregate_stats()
            assert stats["extraction"]["total_calls"] == 3
            assert stats["extraction"]["avg_latency_ms"] >= 0

    def test_get_recent_traces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            collector = TelemetryCollector(persist_path=Path(tmp) / "telemetry.jsonl")
            for i in range(5):
                trace = collector.start_trace(bundle_id=f"b-{i}")
                with trace.span("s", "layer"):
                    pass
                collector.finish_trace(trace)
            recent = collector.get_recent_traces(limit=2)
            assert len(recent) == 2
            assert recent[0]["bundle_id"] == "b-3"

    def test_concurrent_traces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            collector = TelemetryCollector(persist_path=Path(tmp) / "telemetry.jsonl")

            def run_trace() -> None:
                trace = collector.start_trace()
                with trace.span("s", "layer"):
                    pass
                collector.finish_trace(trace)

            threads = [threading.Thread(target=run_trace) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            stats = collector.get_aggregate_stats()
            assert stats["layer"]["total_calls"] == 5
