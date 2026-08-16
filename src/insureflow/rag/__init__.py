from typing import Any

from insureflow.rag.guidelines import Guideline, GuidelineCategory, GuidelineSource, UnderwritingGuidelines, builtin_guidelines
from insureflow.rag.knowledge_graph import UnderwritingKnowledgeGraph, get_knowledge_graph
from insureflow.rag.rag_agent import RAGAgent, retrieval_policy_payload
from insureflow.rag.retrieval_config import RetrievalConfig
from insureflow.rag.vector_store import InMemoryVectorStore, PgVectorStore, VectorStore, get_vector_store

__all__ = [
    "Guideline",
    "GuidelineCategory",
    "GuidelineSource",
    "UnderwritingGuidelines",
    "builtin_guidelines",
    "RAGAgent",
    "RetrievalConfig",
    "retrieval_policy_payload",
    "VectorStore",
    "InMemoryVectorStore",
    "PgVectorStore",
    "UnderwritingKnowledgeGraph",
    "get_knowledge_graph",
    "get_vector_store",
    "hyde_search_query",
    "retrieve_with_self_rag",
    "build_submission_entity_graph",
    "graph_context_block",
]


def __getattr__(name: str) -> Any:
    if name == "hyde_search_query":
        from insureflow.rag.hyde import hyde_search_query

        return hyde_search_query
    if name == "retrieve_with_self_rag":
        from insureflow.rag.self_rag import retrieve_with_self_rag

        return retrieve_with_self_rag
    if name == "build_submission_entity_graph":
        from insureflow.rag.entity_graph import build_submission_entity_graph

        return build_submission_entity_graph
    if name == "graph_context_block":
        from insureflow.rag.entity_graph import graph_context_block

        return graph_context_block
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
