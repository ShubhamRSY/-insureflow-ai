"""RAG retrieval config: top-k, over-fetch, re-ranking, fallback chain.

Defaults (interview-ready):
- final ``top_k`` = **5** (pipeline synthesis often uses **3**)
- over-fetch ``fetch_k`` = **15** (3× top_k) before re-rank
- re-rank: score fusion (vector sim + keyword overlap) + light MMR diversify
- min vector similarity gate; below that → fallback ladder
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalConfig:
    """Tunable retrieval knobs (also logged on MLflow RAG experiments)."""

    top_k: int = 5
    fetch_k: int = 15  # candidates pulled before re-rank
    pipeline_top_k: int = 3  # tighter budget for live agent synthesis
    min_vector_score: float = 0.12  # below → treat vector as miss
    rerank_vector_weight: float = 0.65
    rerank_keyword_weight: float = 0.35
    mmr_lambda: float = 0.7  # 1.0 = pure relevance, 0.0 = pure diversity
    kg_depth: int = 2
    kg_max_facts: int = 12
    enable_rerank: bool = True
    enable_keyword_fallback: bool = True
    enable_kg_fallback: bool = True

    @classmethod
    def from_env(cls) -> RetrievalConfig:
        def _i(name: str, default: int) -> int:
            raw = os.getenv(name, "").strip()
            return int(raw) if raw else default

        def _f(name: str, default: float) -> float:
            raw = os.getenv(name, "").strip()
            return float(raw) if raw else default

        def _b(name: str, default: bool) -> bool:
            raw = os.getenv(name, "").strip().lower()
            if not raw:
                return default
            return raw in {"1", "true", "yes", "on"}

        top_k = _i("RAG_TOP_K", 5)
        return cls(
            top_k=top_k,
            fetch_k=_i("RAG_FETCH_K", max(15, top_k * 3)),
            pipeline_top_k=_i("RAG_PIPELINE_TOP_K", 3),
            min_vector_score=_f("RAG_MIN_VECTOR_SCORE", 0.12),
            rerank_vector_weight=_f("RAG_RERANK_VECTOR_WEIGHT", 0.65),
            rerank_keyword_weight=_f("RAG_RERANK_KEYWORD_WEIGHT", 0.35),
            mmr_lambda=_f("RAG_MMR_LAMBDA", 0.7),
            kg_depth=_i("RAG_KG_DEPTH", 2),
            kg_max_facts=_i("RAG_KG_MAX_FACTS", 12),
            enable_rerank=_b("RAG_ENABLE_RERANK", True),
            enable_keyword_fallback=_b("RAG_ENABLE_KEYWORD_FALLBACK", True),
            enable_kg_fallback=_b("RAG_ENABLE_KG_FALLBACK", True),
        )


def tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", text.lower()) if t}


DEFAULT_RETRIEVAL = RetrievalConfig.from_env()
