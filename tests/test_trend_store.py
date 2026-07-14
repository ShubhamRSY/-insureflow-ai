"""Tests for eval trend store (time-series for dashboards)."""

from __future__ import annotations

from pathlib import Path

from evaluations.trend_store import EvalTrendStore, seed_demo_trends


def test_trend_store_record_and_series(tmp_path: Path) -> None:
    store = EvalTrendStore(tmp_path / "trends.jsonl")
    store.record("golden_nightly", {"precision": 0.9, "recall": 0.92})
    store.record("golden_nightly", {"precision": 0.91, "recall": 0.93})
    store.record("weekly", {"precision": 0.88})

    rows = store.list(suite="golden_nightly")
    assert len(rows) == 2
    series = store.series("precision", suite="golden_nightly")
    assert len(series) == 2
    assert series[0]["value"] == 0.9
    assert series[1]["value"] == 0.91


def test_seed_demo_trends(tmp_path: Path) -> None:
    store = EvalTrendStore(tmp_path / "trends.jsonl")
    n = seed_demo_trends(store)
    assert n == 5
    assert seed_demo_trends(store) == 0  # idempotent when data exists
    payload = store.dashboard_payload()
    assert payload["points"] == 5
    assert len(payload["series"]["precision"]) == 5
    assert "visualization" in payload
