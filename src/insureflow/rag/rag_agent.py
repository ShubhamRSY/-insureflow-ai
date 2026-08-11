"""Hybrid retrieval: vector guideline RAG + re-rank + fallback ladder + knowledge graph."""

from __future__ import annotations

import logging
from typing import Any, Optional

from insureflow.rag.guidelines import (
    Guideline,
    builtin_carrier_appetite_rules,
    builtin_guidelines,
)
from insureflow.rag.knowledge_graph import get_knowledge_graph
from insureflow.rag.rerank import keyword_overlap_score, rerank
from insureflow.rag.retrieval_config import DEFAULT_RETRIEVAL, RetrievalConfig
from insureflow.rag.vector_store import InMemoryVectorStore, VectorStore

logger = logging.getLogger(__name__)


class RAGAgent:
    """Retrieves underwriting context via vector search, re-rank, and fallbacks."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        use_knowledge_graph: bool = True,
        config: RetrievalConfig | None = None,
    ) -> None:
        self.store = vector_store or InMemoryVectorStore()
        self.use_knowledge_graph = use_knowledge_graph
        self.config = config or DEFAULT_RETRIEVAL
        self._initialized = False

    def ensure_indexed(self) -> None:
        if not self._initialized:
            guidelines = builtin_guidelines()
            appetite = builtin_carrier_appetite_rules()
            active = guidelines.active_as_of() + appetite.active_as_of()
            self.store.index_guidelines(active)
            self._guidelines_cache = list(active)
            self._initialized = True
            logger.info("Indexed %d underwriting guidelines", len(active))

    def _all_guidelines(self) -> list[Guideline]:
        self.ensure_indexed()
        return getattr(self, "_guidelines_cache", [])

    def _keyword_fallback(self, query: str, top_k: int) -> list[tuple[Guideline, float]]:
        """Lexical fallback when vector similarity is below the min gate."""
        scored: list[tuple[Guideline, float]] = []
        for g in self._all_guidelines():
            s = keyword_overlap_score(query, g)
            if s > 0:
                scored.append((g, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search_scored(self, query: str, top_k: int | None = None) -> dict[str, Any]:
        """Vector over-fetch → re-rank → optional keyword fallback."""
        self.ensure_indexed()
        cfg = self.config
        k = top_k if top_k is not None else cfg.top_k
        fetch_k = max(cfg.fetch_k, k)

        raw = self.store.search(query, top_k=fetch_k)
        best_raw = raw[0][1] if raw else 0.0
        source = "vector"
        used_fallback: list[str] = []

        # Gate: if best vector hit is too weak, treat as miss
        if not raw or best_raw < cfg.min_vector_score:
            used_fallback.append("vector_miss")
            if cfg.enable_keyword_fallback:
                kw = self._keyword_fallback(query, top_k=fetch_k)
                if kw:
                    raw = kw
                    source = "keyword_fallback"
                    used_fallback.append("keyword")
                else:
                    raw = []
                    used_fallback.append("keyword_miss")

        ranked = rerank(query, raw, top_k=k, cfg=cfg) if raw else []
        if ranked and source == "vector":
            source = "vector_reranked" if cfg.enable_rerank else "vector"

        return {
            "results": ranked,
            "guidelines": [g for g, _ in ranked],
            "scores": [s for _, s in ranked],
            "source": source,
            "fetch_k": fetch_k,
            "top_k": k,
            "best_raw_vector_score": best_raw,
            "fallbacks_used": used_fallback,
            "rerank_enabled": cfg.enable_rerank,
        }

    def query(self, query: str, top_k: int = 5) -> list[Guideline]:
        guidelines = self.search_scored(query, top_k=top_k)["guidelines"]
        return list(guidelines)

    def retrieve_contexts(
        self,
        query: str,
        top_k: int = 5,
        kg_depth: int | None = None,
        line_of_business: str | None = None,
    ) -> dict[str, Any]:
        """Return structured retrieved contexts used by Ragas / synthesis.

        Fallback ladder when vector is empty / weak:
        1. Keyword overlap over the guideline corpus
        2. Knowledge-graph neighborhood facts
        3. Explicit ``no_context`` marker (agents should not hallucinate guidelines)

        When ``line_of_business`` is set, line-specific guidelines
        (``applies_to_lines``) are preferred and injected if vector miss would
        otherwise return only property/COPE rules.
        """
        self.ensure_indexed()
        cfg = self.config
        depth = kg_depth if kg_depth is not None else cfg.kg_depth
        line = (line_of_business or "").strip().lower()
        # Seed query with line tokens so specialty keywords match
        enriched_query = query
        if line:
            enriched_query = f"{line.replace('_', ' ')} {query}"

        scored = self.search_scored(enriched_query, top_k=top_k)
        guidelines: list[Guideline] = list(scored["guidelines"])
        scores: list[float] = list(scored["scores"])
        fallbacks = list(scored["fallbacks_used"])

        if line:
            line_guides = [g for g in self._all_guidelines() if g.applies_to_lines and line in {x.lower() for x in g.applies_to_lines}]
            have_ids = {g.id for g in guidelines}
            # Prefer / inject line-specific guides at the front
            injected: list[tuple[Guideline, float]] = []
            for g in line_guides:
                if g.id not in have_ids:
                    injected.append((g, 0.99))
                    have_ids.add(g.id)
            if injected:
                fallbacks.append("line_specific_inject")
            merged = injected + list(zip(guidelines, scores))
            # Drop guides that explicitly target a *different* specialty line
            filtered: list[tuple[Guideline, float]] = []
            for g, s in merged:
                targets = {x.lower() for x in (g.applies_to_lines or [])}
                if targets and line not in targets:
                    continue
                filtered.append((g, s))
            if not filtered and merged:
                filtered = merged[:top_k]
            guidelines = [g for g, _ in filtered[:top_k]]
            scores = [s for _, s in filtered[:top_k]]
            scored = {**scored, "guidelines": guidelines, "scores": scores, "top_k": top_k}

        vector_chunks: list[str] = []
        for g, score in zip(guidelines, scores):
            vector_chunks.append(f"[{g.id}] score={score:.3f} ({g.category.value.upper()}, {g.source.value}) {g.title}\nImpact: {g.risk_impact}\n{g.content}")

        kg_facts: list[str] = []
        kg_block = ""

        need_kg = self.use_knowledge_graph and cfg.enable_kg_fallback and (not vector_chunks or "vector_miss" in fallbacks or "keyword" in fallbacks)
        if self.use_knowledge_graph:
            kg = get_knowledge_graph()
            kg_facts = kg.retrieve_context(enriched_query, depth=depth, max_facts=cfg.kg_max_facts)
            kg_block = kg.format_context_block(enriched_query, depth=depth)
            if need_kg and kg_facts:
                fallbacks.append("knowledge_graph")
            elif kg_facts and "knowledge_graph_augment" not in fallbacks:
                fallbacks.append("knowledge_graph_augment")

        combined: list[str] = []
        if vector_chunks:
            combined.extend(vector_chunks)
        if kg_facts:
            combined.append("KG: " + " | ".join(kg_facts[:8]))

        no_context = False
        if not combined:
            no_context = True
            fallbacks.append("no_context")
            combined.append("NO_RETRIEVED_CONTEXT: No matching underwriting guidelines or knowledge-graph facts found. Do not invent guideline citations; escalate with documentation request.")

        mode = "hybrid_rag_kg" if self.use_knowledge_graph else "vector_rag_only"
        if no_context:
            mode = "fallback_no_context"
        elif "keyword" in fallbacks and not any(s.startswith("vector") for s in [scored["source"]]):
            mode = "keyword_kg_fallback"
        if line and "line_specific_inject" in fallbacks:
            mode = "line_aware_rag"

        return {
            "mode": mode,
            "retrieval_source": scored["source"],
            "line_of_business": line or None,
            "guideline_ids": [g.id for g in guidelines],
            "top_k": scored["top_k"],
            "fetch_k": scored["fetch_k"],
            "rerank_enabled": scored["rerank_enabled"],
            "best_raw_vector_score": scored["best_raw_vector_score"],
            "fallbacks_used": fallbacks,
            "no_context": no_context,
            "vector_guideline_chunks": vector_chunks,
            "knowledge_graph_facts": kg_facts,
            "retrieved_contexts": combined,
            "formatted": self.format_context(enriched_query, top_k=top_k),
            "kg_block": kg_block,
            "kg_stats": get_knowledge_graph().stats() if self.use_knowledge_graph else {},
            "config": {
                "top_k": cfg.top_k,
                "fetch_k": cfg.fetch_k,
                "pipeline_top_k": cfg.pipeline_top_k,
                "min_vector_score": cfg.min_vector_score,
                "mmr_lambda": cfg.mmr_lambda,
            },
        }

    def format_context(self, query: str, top_k: int = 5) -> str:
        parts: list[str] = []
        scored = self.search_scored(query, top_k=top_k)
        guidelines = scored["guidelines"]
        if guidelines:
            lines: list[str] = [
                "=== RELEVANT UNDERWRITING GUIDELINES ===",
                f"(source={scored['source']}, top_k={scored['top_k']}, fetch_k={scored['fetch_k']}, rerank={scored['rerank_enabled']})",
            ]
            for g, score in zip(guidelines, scored["scores"]):
                lines.append(f"[{g.id}] score={score:.3f} ({g.category.value.upper()}, {g.source.value}) {g.title}")
                lines.append(f"    Impact: {g.risk_impact}")
                lines.append(f"    {g.content}")
                lines.append("")
            parts.append("\n".join(lines))
        elif scored["fallbacks_used"]:
            parts.append(f"=== NO VECTOR / KEYWORD GUIDELINE HITS ===\nfallbacks_tried={scored['fallbacks_used']}")
        if self.use_knowledge_graph:
            kg_block = get_knowledge_graph().format_context_block(query)
            if kg_block:
                parts.append(kg_block)
        if not parts:
            return "=== NO_RETRIEVED_CONTEXT ===\nNo guidelines or graph facts matched. Do not fabricate citations."
        return "\n".join(parts)

    def augment_synthesis_prompt(self, query: str, original_prompt: str, top_k: int = 5) -> str:
        context = self.format_context(query, top_k=top_k)
        if not context:
            return original_prompt
        return f"{context}\n\n---\n\n{original_prompt}"


def retrieval_policy_payload() -> dict[str, Any]:
    """Interview / dashboard summary of Top-K, re-rank, and fallbacks."""
    cfg = RetrievalConfig.from_env()
    return {
        "top_k": cfg.top_k,
        "fetch_k": cfg.fetch_k,
        "pipeline_top_k": cfg.pipeline_top_k,
        "min_vector_score": cfg.min_vector_score,
        "reranking": {
            "enabled": cfg.enable_rerank,
            "method": "score_fusion(vector + keyword) → MMR diversify",
            "optional_cross_encoder": "set RAG_CROSS_ENCODER_MODEL (sentence-transformers)",
            "vector_weight": cfg.rerank_vector_weight,
            "keyword_weight": cfg.rerank_keyword_weight,
            "mmr_lambda": cfg.mmr_lambda,
        },
        "fallback_ladder": [
            "1. Vector search (pgvector or in-memory char-n-gram) with fetch_k over-retrieve — PRIMARY (no secondary SQL retrieval)",
            "2. If best similarity < min_vector_score → keyword overlap fallback on guideline corpus (non-SQL)",
            "3. Knowledge-graph neighborhood (always augment in hybrid; rescue on vector miss)",
            "4. NO_RETRIEVED_CONTEXT sentinel → agents must not invent guideline citations",
        ],
        "stores": ["pgvector (prod)", "InMemoryVectorStore char-n-gram (local/dev)"],
        "env": [
            "RAG_TOP_K",
            "RAG_FETCH_K",
            "RAG_PIPELINE_TOP_K",
            "RAG_MIN_VECTOR_SCORE",
            "RAG_ENABLE_RERANK",
            "RAG_CROSS_ENCODER_MODEL",
        ],
    }
