"""Tests for cached-token pricing, blended price, and tracker cached aggregation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from insureflow.llm.tracker import (
    BLENDED_MIX,
    TokenUsageTracker,
    blended_price_per_1k,
    estimate_cost_full,
    get_model_pricing,
)


class TestGetModelPricing:
    def test_gpt4o_prices(self) -> None:
        p = get_model_pricing("gpt-4o")
        assert p["input"] == pytest.approx(0.0025)
        assert p["cached"] == pytest.approx(0.00125)
        assert p["output"] == pytest.approx(0.01)

    def test_model_without_cache_discount_defaults_to_input(self) -> None:
        p = get_model_pricing("gpt-4-turbo")
        assert p["cached"] == p["input"]

    def test_unknown_model_falls_back_to_gpt4o(self) -> None:
        p = get_model_pricing("totally-unknown")
        assert p["input"] == pytest.approx(0.0025)


class TestEstimateCostFull:
    def test_cached_tokens_cheaper(self) -> None:
        fresh = estimate_cost_full("gpt-4o", input_tokens=1000, cached_tokens=0, output_tokens=0)
        cached = estimate_cost_full("gpt-4o", input_tokens=0, cached_tokens=1000, output_tokens=0)
        assert cached < fresh
        assert fresh == pytest.approx(0.0025, abs=1e-6)
        assert cached == pytest.approx(0.00125, abs=1e-6)

    def test_combined(self) -> None:
        cost = estimate_cost_full("gpt-4o", input_tokens=100, cached_tokens=100, output_tokens=100)
        assert cost == pytest.approx((100 * 0.0025 + 100 * 0.00125 + 100 * 0.01) / 1000, abs=1e-6)

    def test_backward_compatible_with_estimate_cost(self) -> None:
        # estimate_cost_full with no cached tokens equals the old signature
        assert estimate_cost_full("gpt-4o-mini", input_tokens=1000, output_tokens=1000) == pytest.approx((1000 * 0.00015 + 1000 * 0.0006) / 1000, abs=1e-6)


class TestBlendedPrice:
    def test_blended_price_gpt4o(self) -> None:
        p = get_model_pricing("gpt-4o")
        expected = (BLENDED_MIX["cached"] * p["cached"] + BLENDED_MIX["input"] * p["input"] + BLENDED_MIX["output"] * p["output"]) / sum(BLENDED_MIX.values())
        assert blended_price_per_1k("gpt-4o") == pytest.approx(expected, abs=1e-9)

    def test_blended_price_between_input_and_output(self) -> None:
        blended = blended_price_per_1k("gpt-4o-mini")
        p = get_model_pricing("gpt-4o-mini")
        assert p["cached"] <= blended <= p["output"]


class TestTrackerCachedAggregation:
    def test_record_with_cached_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 100, 50, cached_tokens=200)
            totals = tracker.get_session_totals()
            assert totals["input_tokens"] == 100
            assert totals["cached_tokens"] == 200
            assert totals["output_tokens"] == 50
            assert totals["total_tokens"] == 350

    def test_get_by_model_includes_cached(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 100, 50, cached_tokens=300)
            by_model = tracker.get_by_model()["gpt-4o"]
            assert by_model["cached_tokens"] == 300
            assert by_model["count"] == 1

    def test_cost_reflects_cached_discount(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracker = TokenUsageTracker(persist_path=Path(tmp) / "usage.jsonl")
            tracker.record("gpt-4o", "default", 1000, 0, cached_tokens=0)
            fresh_cost = tracker.get_session_totals()["total_cost"]
            tracker.reset_session()
            tracker.record("gpt-4o", "default", 0, 0, cached_tokens=1000)
            cached_cost = tracker.get_session_totals()["total_cost"]
            assert cached_cost < fresh_cost
