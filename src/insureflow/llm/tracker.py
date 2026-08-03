"""Token usage tracking and cost calculation for LLM calls."""

from __future__ import annotations

import json
import logging
import os
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Approximate pricing per 1K tokens (USD) — update as pricing changes.
# "cached" is the provider's cached-input (prompt cache hit) rate; when a model
# has no cache discount it equals the plain input rate. Prices are native-token
# rates as listed by providers (mirrors Artificial Analysis pricing convention).
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "cached": 0.00125, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "cached": 0.000075, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "cached": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "cached": 0.0005, "output": 0.0015},
    "claude-sonnet-4-20250514": {"input": 0.003, "cached": 0.0003, "output": 0.015},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "cached": 0.0003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "cached": 0.000025, "output": 0.00125},
}

# Artificial Analysis blended-price mix: 7:2:1 cache-hit : input : output tokens.
BLENDED_MIX = {"cached": 7.0, "input": 2.0, "output": 1.0}


def get_model_pricing(model: str) -> dict[str, float]:
    """Per-1K-token {input, cached, output} USD pricing for a model (gpt-4o fallback)."""
    pricing = MODEL_PRICING.get(model) or MODEL_PRICING.get("gpt-4o", {"input": 0.0, "cached": 0.0, "output": 0.0})
    return {
        "input": float(pricing.get("input", 0.0)),
        "cached": float(pricing.get("cached", pricing.get("input", 0.0))),
        "output": float(pricing.get("output", 0.0)),
    }


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost in USD for a call with input + output tokens (no cache hits)."""
    pricing = get_model_pricing(model)
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000


def estimate_cost_full(model: str, input_tokens: int = 0, cached_tokens: int = 0, output_tokens: int = 0) -> float:
    """Cost in USD accounting for cached-input (prompt cache hits) + fresh input + output tokens."""
    pricing = get_model_pricing(model)
    return (input_tokens * pricing["input"] + cached_tokens * pricing["cached"] + output_tokens * pricing["output"]) / 1000


def blended_price_per_1k(model: str) -> float:
    """AA-style blended price per 1K tokens: (7*cached + 2*input + 1*output) / 10."""
    pricing = get_model_pricing(model)
    total_mix = sum(BLENDED_MIX.values())
    return (BLENDED_MIX["cached"] * pricing["cached"] + BLENDED_MIX["input"] * pricing["input"] + BLENDED_MIX["output"] * pricing["output"]) / total_mix


class TokenUsageRecord:
    __slots__ = ("timestamp", "model", "tier", "input_tokens", "cached_tokens", "output_tokens", "cost", "agent", "bundle_id", "user_id")

    def __init__(
        self,
        model: str,
        tier: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        agent: str = "",
        bundle_id: str = "",
        user_id: str = "",
        cached_tokens: int = 0,
    ) -> None:
        self.timestamp = datetime.now(tz=timezone.utc)
        self.model = model
        self.tier = tier
        self.input_tokens = input_tokens
        self.cached_tokens = cached_tokens
        self.output_tokens = output_tokens
        self.cost = cost
        self.agent = agent
        self.bundle_id = bundle_id
        self.user_id = user_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "model": self.model,
            "tier": self.tier,
            "input_tokens": self.input_tokens,
            "cached_tokens": self.cached_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.cached_tokens + self.output_tokens,
            "cost": round(self.cost, 6),
            "agent": self.agent,
            "bundle_id": self.bundle_id,
            "user_id": self.user_id,
        }


class TokenUsageTracker:
    """Thread-safe token usage tracker with persistence and aggregation."""

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._records: list[TokenUsageRecord] = []
        self._persist_path = persist_path or Path(os.getenv("TOKEN_USAGE_PATH", "./audit_logs/token_usage.jsonl"))
        self._session_input_tokens = 0
        self._session_cached_tokens = 0
        self._session_output_tokens = 0
        self._session_cost = 0.0

    def record(
        self,
        model: str,
        tier: str,
        input_tokens: int,
        output_tokens: int,
        agent: str = "",
        bundle_id: str = "",
        user_id: str = "",
        cached_tokens: int = 0,
    ) -> TokenUsageRecord:
        cost = estimate_cost_full(model, input_tokens=input_tokens, cached_tokens=cached_tokens, output_tokens=output_tokens)
        entry = TokenUsageRecord(
            model=model,
            tier=tier,
            input_tokens=max(0, input_tokens),
            cached_tokens=max(0, cached_tokens),
            output_tokens=max(0, output_tokens),
            cost=max(0.0, cost),
            agent=agent,
            bundle_id=bundle_id,
            user_id=user_id,
        )
        with self._lock:
            self._records.append(entry)
            self._session_input_tokens += max(0, input_tokens)
            self._session_cached_tokens += max(0, cached_tokens)
            self._session_output_tokens += max(0, output_tokens)
            self._session_cost += max(0.0, cost)
            self._persist(entry)
        return entry

    def _persist(self, entry: TokenUsageRecord) -> None:
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), default=str) + "\n")
        except OSError:
            logger.debug("Failed to persist token usage record", exc_info=True)

    def get_session_totals(self) -> dict[str, Any]:
        with self._lock:
            return {
                "input_tokens": self._session_input_tokens,
                "cached_tokens": self._session_cached_tokens,
                "output_tokens": self._session_output_tokens,
                "total_tokens": self._session_input_tokens + self._session_cached_tokens + self._session_output_tokens,
                "total_cost": round(self._session_cost, 6),
                "request_count": len(self._records),
            }

    def get_by_model(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            by_model: dict[str, dict[str, Any]] = defaultdict(lambda: {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "cost": 0.0, "count": 0})
            for r in self._records:
                by_model[r.model]["input_tokens"] += r.input_tokens
                by_model[r.model]["cached_tokens"] += r.cached_tokens
                by_model[r.model]["output_tokens"] += r.output_tokens
                by_model[r.model]["cost"] += r.cost
                by_model[r.model]["count"] += 1
            return {k: {**v, "cost": round(v["cost"], 6)} for k, v in by_model.items()}

    def get_by_agent(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            by_agent: dict[str, dict[str, Any]] = defaultdict(lambda: {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "cost": 0.0, "count": 0})
            for r in self._records:
                agent = r.agent or "unknown"
                by_agent[agent]["input_tokens"] += r.input_tokens
                by_agent[agent]["cached_tokens"] += r.cached_tokens
                by_agent[agent]["output_tokens"] += r.output_tokens
                by_agent[agent]["cost"] += r.cost
                by_agent[agent]["count"] += 1
            return {k: {**v, "cost": round(v["cost"], 6)} for k, v in by_agent.items()}

    def get_by_user(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            by_user: dict[str, dict[str, Any]] = defaultdict(lambda: {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "cost": 0.0, "count": 0})
            for r in self._records:
                uid = r.user_id or "anonymous"
                by_user[uid]["input_tokens"] += r.input_tokens
                by_user[uid]["cached_tokens"] += r.cached_tokens
                by_user[uid]["output_tokens"] += r.output_tokens
                by_user[uid]["cost"] += r.cost
                by_user[uid]["count"] += 1
            return {k: {**v, "cost": round(v["cost"], 6)} for k, v in by_user.items()}

    def get_records(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._records[-limit:]]

    def reset_session(self) -> None:
        with self._lock:
            self._records.clear()
            self._session_input_tokens = 0
            self._session_cached_tokens = 0
            self._session_output_tokens = 0
            self._session_cost = 0.0


# Global singleton
_token_tracker: Optional[TokenUsageTracker] = None


def get_token_tracker() -> TokenUsageTracker:
    global _token_tracker
    if _token_tracker is None:
        _token_tracker = TokenUsageTracker()
    return _token_tracker
