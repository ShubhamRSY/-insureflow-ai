"""Artificial Analysis-style performance and price benchmarking.

Implements the methodology published at https://artificialanalysis.ai/methodology:

  - Time to First Token (TTFT): seconds between sending a request and receiving
    the first token (for reasoning models this is the first reasoning token).
  - Time to First Answer Token: seconds until the first answer token arrives,
    i.e. after any 'thinking' / reasoning phase.
  - Output Speed (output tokens per second): average tokens/sec received after
    the first token.
  - Total Response Time for 100 Output Tokens: synthetic = TTFT + 100 / speed.
  - End-to-End Response Time: full wall-clock time to a complete response.
  - Average Reasoning Tokens: reasoning tokens before the answer (AA assumes
    2k when not measured — see REASONING_TOKENS_FALLBACK).
  - Cost per Task: weighted-average USD cost per Intelligence Index task, using
    input + cached + output token prices weighted per benchmark.
  - Price (Blended): 7:2:1 cache-hit : input : output token mix.

Token counts use OpenAI tokens (tiktoken o200k_base) as the standard unit so
models can be compared fairly, matching AA convention. Prices are native-token
per-1K rates from insureflow.llm.tracker.MODEL_PRICING.

Run: python -m evaluations.benchmark [--output out.json]
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from insureflow.config import settings
from insureflow.llm.client import LLMClient
from insureflow.llm.tracker import blended_price_per_1k, estimate_cost_full, get_model_pricing

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token counting (OpenAI tokens = standard unit across Artificial Analysis)
# ---------------------------------------------------------------------------

_enc: Any = None


def _get_encoder() -> Any:
    """Lazy tiktoken o200k_base encoder; falls back to None (char/4 estimate)."""
    global _enc
    if _enc is not None:
        return _enc
    try:
        import tiktoken

        _enc = tiktoken.get_encoding("o200k_base")
    except Exception:
        logger.warning("tiktoken unavailable — falling back to character-based token estimate")
        _enc = False
    return _enc


def count_openai_tokens(text: str) -> int:
    """Count tokens using OpenAI's o200k_base tokenizer (chars/4 fallback)."""
    if not text:
        return 0
    enc = _get_encoder()
    if enc:
        try:
            return len(enc.encode(text))
        except Exception:
            pass
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Benchmark prompt set (diverse; mirrors AA's multi-category 60-prompt set)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkPrompt:
    prompt_id: str
    category: str  # key into INTELLIGENCE_INDEX_WEIGHTS
    system_prompt: str
    user_prompt: str


# Weight of each benchmark in the Artificial Analysis Intelligence Index.
# Not published exactly by AA — update to mirror the current published index.
# Cost per Task = sum_i w_i * (input_i*p_in + cached_i*p_cache + output_i*p_out) / tasks_i
INTELLIGENCE_INDEX_WEIGHTS: dict[str, float] = {
    "general_knowledge": 0.25,
    "coding": 0.20,
    "math": 0.15,
    "science": 0.10,
    "commercial_insurance": 0.15,
    "personal_lines": 0.15,
}

# AA assumes 2k reasoning tokens when the average is not measured.
REASONING_TOKENS_FALLBACK: int = 2000

# AA's synthetic response-time target
OUTPUT_TOKENS_TARGET: int = 100

PROMPT_TEMPLATE_SYSTEM = "You are a careful, precise assistant. Answer concisely and correctly. Do not include disclaimers. Provide the answer directly."

BENCHMARK_PROMPTS: list[BenchmarkPrompt] = [
    BenchmarkPrompt(
        prompt_id="general_001",
        category="general_knowledge",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt=("What is the difference between an occurrence-based and a claims-made insurance policy? Give a concise definition of each and one example of when each is typically used."),
    ),
    BenchmarkPrompt(
        prompt_id="general_002",
        category="general_knowledge",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt="List the three main financial statements and one sentence on what each one reports.",
    ),
    BenchmarkPrompt(
        prompt_id="general_003",
        category="general_knowledge",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt="In two or three sentences, explain what an insurance deductible is and how a higher deductible affects premium.",
    ),
    BenchmarkPrompt(
        prompt_id="coding_001",
        category="coding",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt=(
            "Write a short Python function that takes a list of insurance claims "
            "(dicts with 'amount' and 'status') and returns the total paid amount for "
            "claims with status 'PAID'. Handle empty input and negative amounts by skipping them."
        ),
    ),
    BenchmarkPrompt(
        prompt_id="coding_002",
        category="coding",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt="Write a SQL query that returns the 10 most recent claims from a table 'claims' ordered by created_at.",
    ),
    BenchmarkPrompt(
        prompt_id="math_001",
        category="math",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt=(
            "An insured has a building valued at $2,500,000 insured on a replacement-cost basis "
            "with an 80% coinsurance clause. A loss of $500,000 occurs. What is the penalty-free "
            "coverage amount and the final loss payment? Show your arithmetic."
        ),
    ),
    BenchmarkPrompt(
        prompt_id="math_002",
        category="math",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt="If a premium is $1,200 annually and the cancellation refund is 90% pro-rata, what refund is due after 3 full months? Show the calculation.",
    ),
    BenchmarkPrompt(
        prompt_id="science_001",
        category="science",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt="Explain in two sentences why a building with a fire sprinkler system generally has a lower property risk profile.",
    ),
    BenchmarkPrompt(
        prompt_id="commercial_001",
        category="commercial_insurance",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt=(
            "A mid-size manufacturer submits a commercial property application. The building is "
            "30 years old, masonry construction, 2 stories, fully sprinklered, protection class 4, "
            "annual revenue $15M, payroll $4.2M. Summarize the key underwriting risk factors you would "
            "flag and why."
        ),
    ),
    BenchmarkPrompt(
        prompt_id="commercial_002",
        category="commercial_insurance",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt="What is a named insured, additional insured, and additional named insured on a commercial policy? Differentiate each.",
    ),
    BenchmarkPrompt(
        prompt_id="commercial_003",
        category="commercial_insurance",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt="List three common commercial general liability exclusions and one sentence explaining each.",
    ),
    BenchmarkPrompt(
        prompt_id="personal_001",
        category="personal_lines",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt="Explain the difference between replacement cost and actual cash value for a home contents claim.",
    ),
    BenchmarkPrompt(
        prompt_id="personal_002",
        category="personal_lines",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt="A driver with a clean record buys a new car. What personal auto coverages would you recommend and why?",
    ),
    BenchmarkPrompt(
        prompt_id="personal_003",
        category="personal_lines",
        system_prompt=PROMPT_TEMPLATE_SYSTEM,
        user_prompt="What is a homeowners policy 'Section II' loss and how does personal liability coverage respond?",
    ),
]


def benchmark_prompts(categories: Iterable[str] | None = None) -> list[BenchmarkPrompt]:
    """Return the benchmark prompt set, optionally filtered by category."""
    cats = set(categories) if categories is not None else None
    return [p for p in BENCHMARK_PROMPTS if cats is None or p.category in cats]


# ---------------------------------------------------------------------------
# Streaming measurement
# ---------------------------------------------------------------------------


@dataclass
class PerCallTiming:
    prompt_id: str
    category: str
    ttft_s: float | None
    first_answer_s: float | None
    output_speed_tok_s: float | None
    total_response_time_100_s: float | None
    e2e_s: float | None
    input_tokens: int
    cached_tokens: int
    output_tokens: int
    reasoning_tokens: int
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "category": self.category,
            "ttft_s": _round(self.ttft_s),
            "first_answer_token_s": _round(self.first_answer_s),
            "output_speed_tokens_per_s": _round(self.output_speed_tok_s),
            "total_response_time_100_tokens_s": _round(self.total_response_time_100_s),
            "e2e_response_time_s": _round(self.e2e_s),
            "input_tokens": self.input_tokens,
            "cached_tokens": self.cached_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "error": self.error,
        }


def _round(v: float | None) -> float | None:
    return round(v, 6) if v is not None else None


def _extract_usage(usage: Any) -> tuple[int, int, int, int]:
    """Return (input_tokens, cached_tokens, output_tokens, reasoning_tokens) from a provider usage object."""
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0
    cached_tokens = 0
    reasoning_tokens = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached_tokens = getattr(details, "cached_tokens", 0) or 0
    comp_details = getattr(usage, "completion_tokens_details", None)
    if comp_details is not None:
        reasoning_tokens = getattr(comp_details, "reasoning_tokens", 0) or 0
    return input_tokens, cached_tokens, output_tokens, reasoning_tokens


def measure_call(
    client: LLMClient,
    prompt: BenchmarkPrompt,
    max_tokens: int | None = None,
) -> PerCallTiming:
    """Stream one prompt through the client and time TTFT / first-answer / speed / E2E.

    Falls back to non-streaming timing if the provider does not support streaming.
    """
    t_start = time.perf_counter()
    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    first_token_s: float | None = None
    first_answer_s: float | None = None
    usage: Any = None

    try:
        for chunk in client.stream(prompt.system_prompt, prompt.user_prompt):
            if chunk.text:
                if first_token_s is None:
                    first_token_s = time.perf_counter() - t_start
                if first_answer_s is None:
                    first_answer_s = time.perf_counter() - t_start
                text_parts.append(chunk.text)
            if chunk.reasoning:
                if first_token_s is None:
                    first_token_s = time.perf_counter() - t_start
                reasoning_parts.append(chunk.reasoning)
            if chunk.usage is not None:
                usage = chunk.usage
        e2e_s = time.perf_counter() - t_start
    except (NotImplementedError, AttributeError):
        # Streaming unsupported — fall back to a single non-streamed call (E2E only).
        e2e_s = time.perf_counter() - t_start
        try:
            client.complete(prompt.system_prompt, prompt.user_prompt)
            e2e_s = time.perf_counter() - t_start
        except Exception as exc:  # pragma: no cover - provider error path
            logger.warning("benchmark prompt %s failed: %s", prompt.prompt_id, exc)
            return PerCallTiming(
                prompt_id=prompt.prompt_id,
                category=prompt.category,
                ttft_s=None,
                first_answer_s=None,
                output_speed_tok_s=None,
                total_response_time_100_s=None,
                e2e_s=e2e_s,
                input_tokens=0,
                cached_tokens=0,
                output_tokens=0,
                reasoning_tokens=0,
                error=str(exc),
            )
    except Exception as exc:  # pragma: no cover - provider error path
        logger.warning("benchmark prompt %s failed: %s", prompt.prompt_id, exc)
        e2e_s = time.perf_counter() - t_start
        return PerCallTiming(
            prompt_id=prompt.prompt_id,
            category=prompt.category,
            ttft_s=first_token_s,
            first_answer_s=first_answer_s,
            output_speed_tok_s=None,
            total_response_time_100_s=None,
            e2e_s=e2e_s,
            input_tokens=0,
            cached_tokens=0,
            output_tokens=0,
            reasoning_tokens=0,
            error=str(exc),
        )

    # Prefer provider usage (native tokens); fall back to OpenAI-token counts.
    if usage is not None:
        input_tokens, cached_tokens, output_tokens, reasoning_tokens = _extract_usage(usage)
    else:
        input_tokens = count_openai_tokens(prompt.system_prompt + "\n" + prompt.user_prompt)
        cached_tokens = 0
        output_tokens = count_openai_tokens("".join(text_parts))
        reasoning_tokens = count_openai_tokens("".join(reasoning_parts))
    if reasoning_tokens == 0 and reasoning_parts:
        reasoning_tokens = count_openai_tokens("".join(reasoning_parts))

    if output_tokens < 1:
        output_tokens = count_openai_tokens("".join(text_parts))

    output_speed_tok_s: float | None = None
    if output_tokens >= 1 and first_token_s is not None and e2e_s - first_token_s > 0:
        output_speed_tok_s = (output_tokens - 1) / (e2e_s - first_token_s)
    total_100_s: float | None = None
    if first_token_s is not None and output_speed_tok_s and output_speed_tok_s > 0:
        total_100_s = first_token_s + OUTPUT_TOKENS_TARGET / output_speed_tok_s

    return PerCallTiming(
        prompt_id=prompt.prompt_id,
        category=prompt.category,
        ttft_s=first_token_s,
        first_answer_s=first_answer_s,
        output_speed_tok_s=output_speed_tok_s,
        total_response_time_100_s=total_100_s,
        e2e_s=e2e_s,
        input_tokens=input_tokens,
        cached_tokens=cached_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
    )


# ---------------------------------------------------------------------------
# Cost per task (weighted by Intelligence Index weights)
# ---------------------------------------------------------------------------


def cost_per_task(
    timings: Iterable[PerCallTiming],
    model: str,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Weighted-average USD cost to complete one Intelligence Index task.

    cost_per_task = sum_i w_i * (input_i*p_in + cached_i*p_cache + output_i*p_out) / tasks_i
    """
    weights = weights or INTELLIGENCE_INDEX_WEIGHTS
    rows = list(timings)
    if not rows:
        return {"ok": False, "error": "no timing rows", "cost_per_task_usd": None}
    total_weighted_cost = 0.0
    by_category: dict[str, dict[str, Any]] = {}
    for r in rows:
        w = weights.get(r.category, 1.0)
        cost = estimate_cost_full(
            model,
            input_tokens=r.input_tokens,
            cached_tokens=r.cached_tokens,
            output_tokens=r.output_tokens,
        )
        total_weighted_cost += w * cost
        cat = by_category.setdefault(
            r.category,
            {"tasks": 0, "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
        )
        cat["tasks"] += 1
        cat["input_tokens"] += r.input_tokens
        cat["cached_tokens"] += r.cached_tokens
        cat["output_tokens"] += r.output_tokens
        cat["cost_usd"] += cost

    for cat in by_category.values():
        cat["cost_per_task_usd"] = round(cat["cost_usd"] / cat["tasks"], 6) if cat["tasks"] else None

    return {
        "ok": True,
        "model": model,
        "total_tasks": len(rows),
        "cost_per_task_usd": round(total_weighted_cost / len(rows), 6),
        "total_cost_usd": round(total_weighted_cost, 6),
        "by_category": by_category,
        "weights": weights,
        "formula": "cost_per_task = sum_i w_i*(in*p_in + cached*p_cache + out*p_out) / tasks_i",
    }


# ---------------------------------------------------------------------------
# Aggregation + full benchmark run
# ---------------------------------------------------------------------------


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _pct(values: list[float], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    idx = min(len(s) - 1, int(p / 100.0 * (len(s) - 1)))
    return s[idx]


def aggregate_timings(timings: list[PerCallTiming]) -> dict[str, Any]:
    """Aggregate per-call timings into AA-style summary metrics."""
    ttft = [t.ttft_s for t in timings if t.ttft_s is not None]
    first_answer = [t.first_answer_s for t in timings if t.first_answer_s is not None]
    speeds = [t.output_speed_tok_s for t in timings if t.output_speed_tok_s is not None]
    total100 = [t.total_response_time_100_s for t in timings if t.total_response_time_100_s is not None]
    e2e = [t.e2e_s for t in timings if t.e2e_s is not None]
    reasoning = [t.reasoning_tokens for t in timings if t.reasoning_tokens]

    avg_speed = _avg(speeds)
    avg_ttft = _avg(ttft)
    # AA: assume 2k reasoning tokens when unmeasured
    avg_reasoning = _avg([float(r) for r in reasoning]) if reasoning else REASONING_TOKENS_FALLBACK

    return {
        "ok": True,
        "calls": len(timings),
        "errors": sum(1 for t in timings if t.error),
        "time_to_first_token_s": {
            "avg": _round(avg_ttft),
            "p50": _round(_pct(ttft, 50)),
            "p95": _round(_pct(ttft, 95)),
        },
        "time_to_first_answer_token_s": {
            "avg": _round(_avg(first_answer)),
            "p50": _round(_pct(first_answer, 50)),
            "p95": _round(_pct(first_answer, 95)),
        },
        "output_speed_tokens_per_s": {
            "avg": _round(avg_speed),
            "p50": _round(_pct(speeds, 50)),
            "p95": _round(_pct(speeds, 95)),
        },
        "total_response_time_100_tokens_s": {
            "avg": _round(_avg(total100)),
            "p50": _round(_pct(total100, 50)),
            "p95": _round(_pct(total100, 95)),
        },
        "e2e_response_time_s": {
            "avg": _round(_avg(e2e)),
            "p50": _round(_pct(e2e, 50)),
            "p95": _round(_pct(e2e, 95)),
        },
        "average_reasoning_tokens": avg_reasoning,
        "reasoning_tokens_source": "measured" if reasoning else "assumed_2k_fallback",
        "total_input_tokens": sum(t.input_tokens for t in timings),
        "total_cached_tokens": sum(t.cached_tokens for t in timings),
        "total_output_tokens": sum(t.output_tokens for t in timings),
        # Synthetic combined metric: total response time for 100 output tokens
        "total_response_time_for_100_output_tokens_s": (_round(avg_ttft + OUTPUT_TOKENS_TARGET / avg_speed) if avg_ttft is not None and avg_speed else None),
    }


def run_benchmark(
    model: str | None = None,
    model_tier: str = "default",
    categories: Iterable[str] | None = None,
    prompts: list[BenchmarkPrompt] | None = None,
    max_tokens: int | None = None,
    client: LLMClient | None = None,
    output_path: str | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run the full performance + price benchmark against the configured model.

    Returns summary metrics, cost-per-task, and per-call timings.
    """
    model = model or settings.llm_model
    client = client or LLMClient(model_tier=model_tier, agent="benchmark")
    prompt_set = prompts or benchmark_prompts(categories)

    timings: list[PerCallTiming] = []
    for p in prompt_set:
        timing = measure_call(client, p, max_tokens=max_tokens)
        timings.append(timing)
        logger.info("[benchmark] %s ttft=%s speed=%s e2e=%s", p.prompt_id, timing.ttft_s, timing.output_speed_tok_s, timing.e2e_s)

    metrics = aggregate_timings(timings)
    cost = cost_per_task(timings, model=model, weights=weights)
    pricing = get_model_pricing(model)

    result: dict[str, Any] = {
        "ok": True,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "model": model,
        "model_tier": model_tier,
        "metrics": metrics,
        "cost_per_task": cost,
        "blended_price_per_1k_usd": blended_price_per_1k(model),
        "pricing_per_1k": pricing,
        "model_metadata": _model_metadata_payload(model),
        "registry_inventory": _registry_inventory_payload(),
        "methodology": (
            "TTFT = time to first (reasoning) token; first_answer = first non-reasoning token; "
            "output_speed = (out_tokens-1)/(e2e-ttft); total_100 = ttft + 100/output_speed; "
            "reasoning tokens measured or 2k fallback; cost per task weighted by Intelligence Index weights."
        ),
        "per_call": [t.to_dict() for t in timings],
    }

    if output_path:
        Path(output_path).write_text(json.dumps(result, indent=2, default=str))
        logger.info("Benchmark results written to %s", output_path)

    return result


def _model_metadata_payload(model: str) -> dict[str, Any]:
    """AA vocabulary for the benchmarked model: creator, open weights, endpoints, system."""
    try:
        from insureflow.llm.model_registry import get_model_metadata

        return get_model_metadata(model).to_dict()
    except Exception:
        return {"model": model, "error": "model_registry unavailable"}


def _registry_inventory_payload() -> dict[str, Any]:
    """AA vocabulary inventory (models, creators, providers, endpoints, systems)."""
    try:
        from insureflow.llm.model_registry import registry_inventory

        return registry_inventory()
    except Exception:
        return {"error": "model_registry unavailable"}


# ---------------------------------------------------------------------------
# Trend-store + demo seeding
# ---------------------------------------------------------------------------


def seed_demo_benchmark(store: Any | None = None) -> dict[str, Any]:
    """Seed a demo benchmark run so dashboards render without an LLM key.

    Idempotent: skips seeding if a ``perf_benchmark`` row already exists.
    """
    from evaluations.trend_store import EvalTrendStore

    store = store or EvalTrendStore()
    if store.list_rows(suite="perf_benchmark"):
        return {}
    demo: dict[str, Any] = {
        "metrics": {
            "time_to_first_token_s": {"avg": 0.42, "p50": 0.38, "p95": 0.61},
            "output_speed_tokens_per_s": {"avg": 48.0, "p50": 45.0, "p95": 61.0},
            "e2e_response_time_s": {"avg": 4.8, "p50": 4.5, "p95": 6.2},
            "average_reasoning_tokens": 2000,
            "total_response_time_100_tokens_s": {"avg": 2.5, "p50": 2.4, "p95": 2.7},
        },
        "cost_per_task": {"cost_per_task_usd": 0.0182, "total_tasks": 14},
        "model": "gpt-4o",
        "ok": True,
        "demo": True,
    }
    store.record("perf_benchmark", demo["metrics"], metadata={"model": demo["model"], "demo": True, "cost_per_task_usd": demo["cost_per_task"]["cost_per_task_usd"]})
    return demo


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out = sys.argv[1] if len(sys.argv) > 1 else "benchmark_results.json"
    res = run_benchmark(output_path=out)
    print(json.dumps(res["metrics"], indent=2, default=str))
    print(json.dumps(res["cost_per_task"], indent=2, default=str))
    print(f"Results written to {out}")
