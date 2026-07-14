"""Re-ranking for RAG candidates: score fusion + MMR diversification.

Default path (no GPU / no cross-encoder dependency):
1. Over-fetch ``fetch_k`` from the vector store
2. Fuse vector similarity with lexical keyword overlap
3. Apply MMR so we don't return near-duplicate guidelines
4. Keep final ``top_k``

Optional: if ``sentence_transformers`` is installed and
``RAG_CROSS_ENCODER_MODEL`` is set, use a cross-encoder as a final pass.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from insureflow.rag.retrieval_config import RetrievalConfig, tokenize

if TYPE_CHECKING:
    from insureflow.rag.guidelines import Guideline

logger = logging.getLogger(__name__)


def keyword_overlap_score(query: str, guideline: Guideline) -> float:
    q = tokenize(query)
    if not q:
        return 0.0
    blob = f"{guideline.title} {guideline.content} {' '.join(guideline.keywords)}"
    doc = tokenize(blob)
    if not doc:
        return 0.0
    return len(q & doc) / len(q)


def fuse_scores(
    vector_score: float,
    keyword_score: float,
    cfg: RetrievalConfig,
) -> float:
    total = cfg.rerank_vector_weight * float(vector_score) + cfg.rerank_keyword_weight * float(keyword_score)
    return float(total)


def mmr_select(
    scored: list[tuple[Guideline, float]],
    query: str,
    top_k: int,
    lambda_mult: float,
) -> list[tuple[Guideline, float]]:
    """Maximal Marginal Relevance over fused scores (token Jaccard as similarity)."""
    if not scored:
        return []
    remaining = list(scored)
    selected: list[tuple[Guideline, float]] = []
    q_tokens = tokenize(query)

    def _doc_tokens(g: Guideline) -> set[str]:
        return set(tokenize(f"{g.title} {g.content}"))

    while remaining and len(selected) < top_k:
        best_idx = 0
        best_mmr = float("-inf")
        for i, (g, rel) in enumerate(remaining):
            if not selected:
                mmr = rel
            else:
                g_tok = _doc_tokens(g)
                max_sim = 0.0
                for sg, _ in selected:
                    s_tok = _doc_tokens(sg)
                    union = g_tok | s_tok
                    sim = (len(g_tok & s_tok) / len(union)) if union else 0.0
                    if q_tokens:
                        # mild query-aware penalty already baked into rel
                        pass
                    max_sim = max(max_sim, sim)
                mmr = lambda_mult * rel - (1.0 - lambda_mult) * max_sim
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = i
        selected.append(remaining.pop(best_idx))
    return selected


def _cross_encoder_rerank(
    query: str,
    candidates: list[tuple[Guideline, float]],
    top_k: int,
) -> list[tuple[Guideline, float]] | None:
    model_name = os.getenv("RAG_CROSS_ENCODER_MODEL", "").strip()
    if not model_name or not candidates:
        return None
    try:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(model_name)
        pairs = [(query, f"{g.title}. {g.content}") for g, _ in candidates]
        scores = model.predict(pairs)
        ranked = sorted(
            zip((g for g, _ in candidates), scores),
            key=lambda x: float(x[1]),
            reverse=True,
        )
        return [(g, float(s)) for g, s in ranked[:top_k]]
    except Exception as exc:
        logger.debug("Cross-encoder re-rank unavailable: %s", exc)
        return None


def rerank(
    query: str,
    candidates: list[tuple[Guideline, float]],
    top_k: int,
    cfg: RetrievalConfig | None = None,
) -> list[tuple[Guideline, float]]:
    """Re-rank vector hits → fused score → MMR → optional cross-encoder."""
    cfg = cfg or RetrievalConfig.from_env()
    if not candidates:
        return []
    if not cfg.enable_rerank:
        return candidates[:top_k]

    fused: list[tuple[Guideline, float]] = []
    for g, vec_s in candidates:
        kw = keyword_overlap_score(query, g)
        fused.append((g, fuse_scores(vec_s, kw, cfg)))
    fused.sort(key=lambda x: x[1], reverse=True)

    mmr_out = mmr_select(fused, query, top_k=min(top_k * 2, len(fused)), lambda_mult=cfg.mmr_lambda)
    ce = _cross_encoder_rerank(query, mmr_out, top_k=top_k)
    if ce is not None:
        return ce
    return mmr_out[:top_k]
