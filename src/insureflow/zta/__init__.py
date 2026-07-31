"""Zero Token Architecture (ZTA).

Route every pipeline task through a deterministic-first decision layer.  Use an
LLM only when a task genuinely needs one (unstructured/ambiguous docs, memo
generation, vision) and a budget allows it — everything else runs on code,
rules and trained ML models at zero tokens.
"""

from __future__ import annotations

from insureflow.zta.config import ZtaConfig
from insureflow.zta.models import RouteContext, RouteDecision, RouteResult, ZtaTask
from insureflow.zta.report import ZtaReporter, get_zta_stats
from insureflow.zta.router import ZeroTokenRouter, estimate_tokens, get_router

__all__ = [
    "ZtaConfig",
    "ZtaReporter",
    "ZtaTask",
    "RouteContext",
    "RouteDecision",
    "RouteResult",
    "ZeroTokenRouter",
    "estimate_tokens",
    "get_router",
    "get_zta_stats",
]
