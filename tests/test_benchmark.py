"""Tests for the Artificial Analysis-style performance / price benchmark harness."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from evaluations.benchmark import (
    BENCHMARK_PROMPTS,
    INTELLIGENCE_INDEX_WEIGHTS,
    REASONING_TOKENS_FALLBACK,
    BenchmarkPrompt,
    PerCallTiming,
    aggregate_timings,
    benchmark_prompts,
    cost_per_task,
    count_openai_tokens,
    measure_call,
    run_benchmark,
    seed_demo_benchmark,
)
from insureflow.llm.client import LLMClient, StreamChunk


class FakeLLMClient:
    """Records usage but streams deterministic deltas with real timing."""

    def __init__(self, model: str = "gpt-4o", delay: float = 0.01, with_reasoning: bool = True) -> None:
        self.model = model
        self.delay = delay
        self.with_reasoning = with_reasoning
        self.calls: list[tuple[str, str]] = []

    def stream(self, system_prompt: str, user_prompt: str):
        self.calls.append((system_prompt, user_prompt))
        time.sleep(self.delay)
        if self.with_reasoning:
            yield StreamChunk(reasoning="Let me think about this step by step.")
        for word in ["The", " answer", " is", " correct", "."]:
            time.sleep(self.delay)
            yield StreamChunk(text=word)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return "The answer is correct."


@pytest.fixture
def prompt() -> BenchmarkPrompt:
    return BENCHMARK_PROMPTS[0]


def test_count_openai_tokens() -> None:
    assert count_openai_tokens("") == 0
    n = count_openai_tokens("The quick brown fox jumps over the lazy dog.")
    assert n > 0


def test_measure_call_streaming_metrics(prompt: BenchmarkPrompt) -> None:
    client = FakeLLMClient(delay=0.01)
    timing = measure_call(client, prompt)
    assert timing.error is None
    assert timing.ttft_s is not None and timing.ttft_s > 0
    assert timing.first_answer_s is not None and timing.first_answer_s >= timing.ttft_s
    assert timing.output_speed_tok_s is not None and timing.output_speed_tok_s > 0
    assert timing.total_response_time_100_s is not None and timing.total_response_time_100_s > 0
    assert timing.e2e_s is not None and timing.e2e_s >= timing.first_answer_s
    assert timing.output_tokens > 0
    assert timing.reasoning_tokens > 0  # reasoning content was streamed


def test_measure_call_without_reasoning(prompt: BenchmarkPrompt) -> None:
    client = FakeLLMClient(delay=0.0, with_reasoning=False)
    timing = measure_call(client, prompt)
    assert timing.reasoning_tokens == 0
    assert timing.first_answer_s is not None


def test_measure_call_error_path(prompt: BenchmarkPrompt) -> None:
    class BrokenClient:
        def stream(self, system_prompt: str, user_prompt: str):
            raise RuntimeError("boom")

    timing = measure_call(BrokenClient(), prompt)  # type: ignore[arg-type]
    assert timing.error is not None
    assert timing.output_tokens == 0


def test_aggregate_timings() -> None:
    timings = [
        PerCallTiming(
            prompt_id="a", category="coding", ttft_s=0.5, first_answer_s=1.0,
            output_speed_tok_s=20.0, total_response_time_100_s=5.5, e2e_s=6.0,
            input_tokens=100, cached_tokens=0, output_tokens=50, reasoning_tokens=0,
        ),
        PerCallTiming(
            prompt_id="b", category="math", ttft_s=1.5, first_answer_s=2.0,
            output_speed_tok_s=10.0, total_response_time_100_s=11.5, e2e_s=12.0,
            input_tokens=200, cached_tokens=0, output_tokens=100, reasoning_tokens=0,
        ),
    ]
    agg = aggregate_timings(timings)
    assert agg["calls"] == 2
    assert agg["errors"] == 0
    assert agg["time_to_first_token_s"]["avg"] == pytest.approx(1.0)
    assert agg["output_speed_tokens_per_s"]["avg"] == pytest.approx(15.0)
    assert agg["total_response_time_100_tokens_s"]["avg"] == pytest.approx(8.5)
    # reasoning unmeasured → 2k fallback per AA
    assert agg["average_reasoning_tokens"] == REASONING_TOKENS_FALLBACK
    assert agg["reasoning_tokens_source"] == "assumed_2k_fallback"


def test_aggregate_timings_measured_reasoning() -> None:
    timings = [
        PerCallTiming(
            prompt_id="a", category="coding", ttft_s=0.5, first_answer_s=5.0,
            output_speed_tok_s=20.0, total_response_time_100_s=5.5, e2e_s=6.0,
            input_tokens=100, cached_tokens=0, output_tokens=50, reasoning_tokens=1200,
        )
    ]
    agg = aggregate_timings(timings)
    assert agg["average_reasoning_tokens"] == 1200
    assert agg["reasoning_tokens_source"] == "measured"


def test_cost_per_task_weighted(prompt: BenchmarkPrompt) -> None:
    timings = [
        PerCallTiming(
            prompt_id="a", category="coding", ttft_s=None, first_answer_s=None,
            output_speed_tok_s=None, total_response_time_100_s=None, e2e_s=None,
            input_tokens=1000, cached_tokens=0, output_tokens=1000,
            reasoning_tokens=0,
        )
    ]
    result = cost_per_task(timings, model="gpt-4o")
    assert result["ok"] is True
    # gpt-4o: 1000*0.0025 + 1000*0.01 = 0.0125 USD, weight coding = 0.20
    expected = (0.20 * 0.0125) / 1
    assert result["cost_per_task_usd"] == pytest.approx(expected, abs=1e-6)
    assert result["total_tasks"] == 1
    assert result["by_category"]["coding"]["tasks"] == 1


def test_cost_per_task_cached_tokens() -> None:
    timings = [
        PerCallTiming(
            prompt_id="a", category="math", ttft_s=None, first_answer_s=None,
            output_speed_tok_s=None, total_response_time_100_s=None, e2e_s=None,
            input_tokens=0, cached_tokens=1000, output_tokens=0,
            reasoning_tokens=0,
        )
    ]
    result = cost_per_task(timings, model="gpt-4o")
    # cached rate 0.00125/1K → 0.00125 * weight(math=0.15)
    expected = (0.15 * 0.00125) / 1
    assert result["cost_per_task_usd"] == pytest.approx(expected, abs=1e-6)


def test_run_benchmark_with_fake_client() -> None:
    result = run_benchmark(
        model="gpt-4o",
        client=FakeLLMClient(delay=0.0),  # type: ignore[arg-type]
        categories=["coding", "math"],
        output_path=None,
    )
    assert result["ok"] is True
    assert result["model"] == "gpt-4o"
    # 2 prompts per category (coding_001/002, math_001/002)
    assert result["metrics"]["calls"] == 4
    assert result["metrics"]["errors"] == 0
    assert result["cost_per_task"]["total_tasks"] == 4
    assert result["blended_price_per_1k_usd"] > 0
    assert "per_call" in result
    assert "methodology" in result


def test_run_benchmark_output_path(tmp_path: Path) -> None:
    out = tmp_path / "bench.json"
    result = run_benchmark(
        model="gpt-4o",
        client=FakeLLMClient(delay=0.0),  # type: ignore[arg-type]
        categories=["science"],
        output_path=str(out),
    )
    assert out.exists()
    assert result["metrics"]["calls"] == 1


def test_benchmark_prompts_filter() -> None:
    all_prompts = benchmark_prompts()
    assert len(all_prompts) == len(BENCHMARK_PROMPTS)
    coding = benchmark_prompts(categories=["coding"])
    assert all(p.category == "coding" for p in coding)
    assert set(BENCHMARK_PROMPTS) == set(all_prompts)


def test_intelligence_index_weights() -> None:
    assert set(INTELLIGENCE_INDEX_WEIGHTS) == {"general_knowledge", "coding", "math", "science", "commercial_insurance", "personal_lines"}
    assert abs(sum(INTELLIGENCE_INDEX_WEIGHTS.values()) - 1.0) < 1e-9
    # every default prompt maps to a weight
    cats = {p.category for p in BENCHMARK_PROMPTS}
    assert cats <= set(INTELLIGENCE_INDEX_WEIGHTS)


def test_seed_demo_benchmark(tmp_path: Path) -> None:
    from evaluations.trend_store import EvalTrendStore

    store = EvalTrendStore(path=tmp_path / "trends.jsonl")
    demo = seed_demo_benchmark(store)
    assert demo["demo"] is True
    rows = store.list_rows(suite="perf_benchmark")
    assert len(rows) == 1
    assert rows[0]["metadata"]["cost_per_task_usd"] == demo["cost_per_task"]["cost_per_task_usd"]
    assert seed_demo_benchmark(store) == {}
    assert len(store.list_rows(suite="perf_benchmark")) == 1


def test_streaming_used_via_llm_client_interface(prompt: BenchmarkPrompt) -> None:
    """LLMClient exposes the stream() generator the benchmark relies on."""
    client = LLMClient(model_tier="default")
    assert hasattr(client, "stream")
    assert hasattr(client, "complete")
