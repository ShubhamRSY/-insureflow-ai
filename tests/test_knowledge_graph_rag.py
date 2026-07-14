"""Tests for UW knowledge graph + hybrid RAG retrieval."""

from __future__ import annotations

from insureflow.rag.knowledge_graph import build_underwriting_knowledge_graph, get_knowledge_graph
from insureflow.rag.rag_agent import RAGAgent


def test_kg_has_nodes_and_edges():
    kg = build_underwriting_knowledge_graph()
    stats = kg.stats()
    assert stats["nodes"] >= 20
    assert stats["edges"] >= 15
    assert "construction" in stats["node_types"]
    assert "guideline" in stats["node_types"]


def test_kg_retrieve_manufacturing_context():
    kg = get_knowledge_graph()
    facts = kg.retrieve_context("manufacturing frame construction protection class 5 sprinkler")
    assert facts
    blob = " ".join(facts).lower()
    assert "manufactur" in blob or "sprinkler" in blob or "frame" in blob


def test_hybrid_rag_returns_vector_and_kg():
    agent = RAGAgent(use_knowledge_graph=True)
    ctx = agent.retrieve_contexts("chemical manufacturing masonry protection class 6", top_k=3)
    assert ctx["mode"] == "hybrid_rag_kg"
    assert isinstance(ctx["vector_guideline_chunks"], list)
    assert isinstance(ctx["knowledge_graph_facts"], list)
    assert len(ctx["retrieved_contexts"]) >= 1
    formatted = agent.format_context("chemical manufacturing sprinklers")
    assert "GUIDELINES" in formatted or "KNOWLEDGE GRAPH" in formatted
