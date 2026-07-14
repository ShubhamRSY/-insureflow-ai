"""Tests for RAG re-ranking, top-k over-fetch, and fallback ladder."""

from __future__ import annotations

from insureflow.rag.rag_agent import RAGAgent, retrieval_policy_payload
from insureflow.rag.rerank import keyword_overlap_score, rerank
from insureflow.rag.retrieval_config import RetrievalConfig
from insureflow.rag.guidelines import builtin_guidelines


def test_retrieval_policy_defaults():
    p = retrieval_policy_payload()
    assert p["top_k"] == 5
    assert p["fetch_k"] >= 15
    assert p["pipeline_top_k"] == 3
    assert "MMR" in p["reranking"]["method"] or "mmr" in p["reranking"]["method"].lower()
    assert len(p["fallback_ladder"]) >= 4


def test_rerank_prefers_keyword_aligned():
    cfg = RetrievalConfig(top_k=2, fetch_k=10, enable_rerank=True)
    guidelines = builtin_guidelines().guidelines
    # Fake equal vector scores — keyword should break ties toward sprinkler/protection
    cands = [(g, 0.5) for g in guidelines[:12]]
    out = rerank("sprinkler protection class manufacturing", cands, top_k=2, cfg=cfg)
    assert len(out) == 2
    blob = " ".join(g.title.lower() + g.content.lower() for g, _ in out)
    assert "sprinkler" in blob or "protection" in blob or "class" in blob


def test_hybrid_retrieve_includes_rerank_metadata():
    agent = RAGAgent(use_knowledge_graph=True, config=RetrievalConfig(top_k=3, fetch_k=12))
    ctx = agent.retrieve_contexts("chemical manufacturing masonry protection class 6", top_k=3)
    assert ctx["top_k"] == 3
    assert ctx["fetch_k"] >= 12
    assert ctx["rerank_enabled"] is True
    assert "retrieval_source" in ctx
    assert ctx["no_context"] is False
    assert len(ctx["retrieved_contexts"]) >= 1


def test_fallback_no_context_on_nonsense_query():
    # Raise min_vector_score very high and disable keyword to force miss → KG or no_context
    cfg = RetrievalConfig(
        top_k=3,
        fetch_k=5,
        min_vector_score=0.99,
        enable_keyword_fallback=False,
        enable_kg_fallback=True,
        enable_rerank=True,
    )
    agent = RAGAgent(use_knowledge_graph=True, config=cfg)
    ctx = agent.retrieve_contexts("xyzzyplughqqq nonexistentnaics99999", top_k=3)
    # Either KG rescue or explicit no_context
    assert "vector_miss" in ctx["fallbacks_used"] or ctx["no_context"] or ctx["knowledge_graph_facts"]


def test_keyword_overlap_nonzero():
    g = builtin_guidelines().guidelines[0]
    assert keyword_overlap_score(g.title, g) > 0
