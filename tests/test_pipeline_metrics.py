"""Tests for pipeline business metrics — fill rate, override rate, cycle time."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

from insureflow.analytics.metrics import (
    CycleTimeTracker,
    FillRateTracker,
    OverrideRateTracker,
    PipelineMetrics,
)

# ---------------------------------------------------------------------------
# Fill Rate Tracker
# ---------------------------------------------------------------------------

class TestFillRateTracker:
    def _make_tracker(self, tmp: str) -> FillRateTracker:
        return FillRateTracker(persist_path=Path(tmp) / "fill_rate.jsonl")

    def test_record_field_filled(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        tracker.record_field("naics_code", filled=True, bundle_id="b-1")
        rate = tracker.get_fill_rate("naics_code")
        assert rate["filled"] == 1
        assert rate["fill_rate"] == 1.0

    def test_record_field_empty(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        tracker.record_field("naics_code", filled=False, bundle_id="b-1")
        rate = tracker.get_fill_rate("naics_code")
        assert rate["empty"] == 1
        assert rate["fill_rate"] == 0.0

    def test_mixed_fill_rate(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        for i in range(8):
            tracker.record_field("naics_code", filled=True, bundle_id=f"b-{i}")
        for i in range(2):
            tracker.record_field("naics_code", filled=False, bundle_id=f"b-{i+8}")
        rate = tracker.get_fill_rate("naics_code")
        assert rate["total"] == 10
        assert rate["filled"] == 8
        assert rate["fill_rate"] == 0.8

    def test_fill_rates_by_field(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        tracker.record_field("naics_code", filled=True, bundle_id="b-1")
        tracker.record_field("state", filled=False, bundle_id="b-1")
        by_field = tracker.get_fill_rates_by_field()
        assert by_field["naics_code"]["fill_rate"] == 1.0
        assert by_field["state"]["fill_rate"] == 0.0

    def test_fill_rates_by_agent(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        tracker.record_field("f1", filled=True, agent="agent_a")
        tracker.record_field("f2", filled=False, agent="agent_a")
        tracker.record_field("f1", filled=True, agent="agent_b")
        by_agent = tracker.get_fill_rates_by_agent()
        assert by_agent["agent_a"]["fill_rate"] == 0.5
        assert by_agent["agent_b"]["fill_rate"] == 1.0

    def test_empty_critical_fields(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        tracker.record_field("naics_code", filled=False, bundle_id="b-1")
        tracker.record_field("naics_code", filled=False, bundle_id="b-2")
        tracker.record_field("naics_code", filled=True, bundle_id="b-3")
        empty = tracker.get_empty_critical_fields()
        naics = [e for e in empty if e["field"] == "naics_code"]
        assert len(naics) == 1
        assert naics[0]["empty_count"] == 2

    def test_record_bundle_fields(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        fields = {
            "named_insured": "ACME Corp",
            "naics_code": "722",
            "state": "FL",
            "tiv": 500000,
            "effective_date": "",
            "coverage_type": "Property",
        }
        tracker.record_bundle_fields("b-1", fields, agent="merge")
        rate = tracker.get_fill_rate()
        assert rate["total"] > 0
        assert rate["filled"] >= 4

    def test_persistence(self, tmp_path: Any) -> None:
        path = Path(tmp_path) / "fill_rate.jsonl"
        tracker = FillRateTracker(persist_path=path)
        tracker.record_field("test", filled=True, bundle_id="b-1")
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1

    def test_no_records_returns_zero(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        rate = tracker.get_fill_rate("nonexistent")
        assert rate["fill_rate"] == 0.0
        assert rate["total"] == 0


# ---------------------------------------------------------------------------
# Override Rate Tracker
# ---------------------------------------------------------------------------

class TestOverrideRateTracker:
    def _make_tracker(self, tmp: str) -> OverrideRateTracker:
        return OverrideRateTracker(persist_path=Path(tmp) / "override_rate.jsonl")

    def test_agreement(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        record = tracker.record_sign_off(
            bundle_id="b-1",
            ai_decision="approve",
            human_decision="approve",
            signed_by="uw1",
        )
        assert record.is_override is False
        rate = tracker.get_override_rate()
        assert rate["overrides"] == 0
        assert rate["override_rate"] == 0.0

    def test_override_upgrade(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        record = tracker.record_sign_off(
            bundle_id="b-1",
            ai_decision="refer",
            human_decision="approve",
            signed_by="uw1",
        )
        assert record.is_override is True
        assert record.override_type == "upgrade"

    def test_override_downgrade(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        record = tracker.record_sign_off(
            bundle_id="b-1",
            ai_decision="approve",
            human_decision="decline",
            signed_by="uw1",
        )
        assert record.is_override is True
        assert record.override_type == "downgrade"

    def test_override_rate_calculation(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        for i in range(7):
            tracker.record_sign_off(bundle_id=f"b-{i}", ai_decision="approve", human_decision="approve", signed_by="uw1")
        for i in range(3):
            tracker.record_sign_off(bundle_id=f"b-{i+7}", ai_decision="approve", human_decision="decline", signed_by="uw1")
        rate = tracker.get_override_rate()
        assert rate["total"] == 10
        assert rate["overrides"] == 3
        assert rate["override_rate"] == 0.3

    def test_override_rate_by_agent(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        tracker.record_sign_off(bundle_id="b-1", ai_decision="approve", human_decision="decline", signed_by="uw1")
        tracker.record_sign_off(bundle_id="b-2", ai_decision="approve", human_decision="approve", signed_by="uw1")
        tracker.record_sign_off(bundle_id="b-3", ai_decision="approve", human_decision="approve", signed_by="uw2")
        by_agent = tracker.get_override_rate_by_agent()
        assert by_agent["uw1"]["override_rate"] == 0.5
        assert by_agent["uw2"]["override_rate"] == 0.0

    def test_common_override_reasons(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        for _ in range(3):
            tracker.record_sign_off(
                bundle_id="b-1", ai_decision="approve", human_decision="decline",
                signed_by="uw1", override_reason="Loss ratio too high",
            )
        for _ in range(2):
            tracker.record_sign_off(
                bundle_id="b-2", ai_decision="approve", human_decision="decline",
                signed_by="uw1", override_reason="Missing inspection",
            )
        reasons = tracker.get_common_override_reasons()
        assert reasons[0]["reason"] == "Loss ratio too high"
        assert reasons[0]["count"] == 3

    def test_persistence(self, tmp_path: Any) -> None:
        path = Path(tmp_path) / "override_rate.jsonl"
        tracker = OverrideRateTracker(persist_path=path)
        tracker.record_sign_off(bundle_id="b-1", ai_decision="approve", human_decision="decline")
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# Cycle Time Tracker
# ---------------------------------------------------------------------------

class TestCycleTimeTracker:
    def _make_tracker(self, tmp: str) -> CycleTimeTracker:
        return CycleTimeTracker(persist_path=Path(tmp) / "cycle_time.jsonl")

    def test_basic_pipeline_lifecycle(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        tracker.start_pipeline("b-1")
        tracker.start_stage("b-1", "ingest")
        time.sleep(0.01)
        tracker.finish_stage("b-1", "ingest")
        tracker.start_stage("b-1", "extract")
        time.sleep(0.01)
        tracker.finish_stage("b-1", "extract")
        record = tracker.finish_pipeline("b-1")
        assert record is not None
        assert record.bundle_id == "b-1"
        assert record.total_ms > 0
        assert "ingest" in record.stage_durations
        assert "extract" in record.stage_durations

    def test_auto_finish_previous_stage(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        tracker.start_pipeline("b-1")
        tracker.start_stage("b-1", "ingest")
        time.sleep(0.01)
        tracker.start_stage("b-1", "extract")
        assert "ingest" in tracker._active["b-1"]["stages"]

    def test_stats(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        for i in range(5):
            tracker.start_pipeline(f"b-{i}")
            tracker.start_stage(f"b-{i}", "ingest")
            time.sleep(0.005)
            tracker.finish_stage(f"b-{i}", "ingest")
            tracker.finish_pipeline(f"b-{i}")
        stats = tracker.get_stats()
        assert stats["total_runs"] == 5
        assert stats["avg_cycle_ms"] > 0
        assert stats["completed"] == 5

    def test_get_recent(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        for i in range(3):
            tracker.start_pipeline(f"b-{i}")
            tracker.finish_pipeline(f"b-{i}")
        recent = tracker.get_recent(limit=2)
        assert len(recent) == 2

    def test_persistence(self, tmp_path: Any) -> None:
        path = Path(tmp_path) / "cycle_time.jsonl"
        tracker = CycleTimeTracker(persist_path=path)
        tracker.start_pipeline("b-1")
        tracker.finish_pipeline("b-1")
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1

    def test_finish_without_start_returns_none(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        record = tracker.finish_pipeline("nonexistent")
        assert record is None

    def test_empty_stats(self, tmp_path: Any) -> None:
        tracker = self._make_tracker(str(tmp_path))
        stats = tracker.get_stats()
        assert stats["total_runs"] == 0


# ---------------------------------------------------------------------------
# PipelineMetrics (aggregate)
# ---------------------------------------------------------------------------

class TestPipelineMetrics:
    def test_get_all(self, tmp_path: Any) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            metrics = PipelineMetrics()
            metrics.fill_rate = FillRateTracker(persist_path=Path(tmp) / "fill.jsonl")
            metrics.override_rate = OverrideRateTracker(persist_path=Path(tmp) / "override.jsonl")
            metrics.cycle_time = CycleTimeTracker(persist_path=Path(tmp) / "cycle.jsonl")

            metrics.fill_rate.record_field("test", filled=True)
            metrics.override_rate.record_sign_off("b-1", "approve", "decline")
            metrics.cycle_time.start_pipeline("b-1")
            metrics.cycle_time.finish_pipeline("b-1")

            result = metrics.get_all()
            assert "fill_rate" in result
            assert "override_rate" in result
            assert "cycle_time" in result
            assert result["fill_rate"]["filled"] == 1
            assert result["override_rate"]["overrides"] == 1
