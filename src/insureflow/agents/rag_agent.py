from __future__ import annotations

import logging
from typing import Any

from insureflow.rag.retrieval_config import RetrievalConfig

logger = logging.getLogger(__name__)


class RAGAgent:
    """Pipeline RAG wrapper: pgvector when DATABASE_URL is set, else hybrid in-memory + KG."""

    def __init__(self) -> None:
        self.config = RetrievalConfig.from_env()
        self._hybrid: Any = None

    def _get_hybrid(self) -> Any:
        if self._hybrid is None:
            from insureflow.rag.rag_agent import RAGAgent as HybridRAG
            from insureflow.rag.vector_store import get_vector_store

            self._hybrid = HybridRAG(
                vector_store=get_vector_store(),
                use_knowledge_graph=True,
                config=self.config,
            )
        return self._hybrid

    def retrieve_guidelines(self, query: str, top_k: int | None = None) -> list[str]:
        """Retrieve guideline/KG context strings for synthesis / Ragas."""
        k = top_k if top_k is not None else self.config.pipeline_top_k
        ctx = self._get_hybrid().retrieve_contexts(query, top_k=k)
        if ctx.get("no_context"):
            return list(ctx["retrieved_contexts"])
        return ctx["retrieved_contexts"] or ([ctx["formatted"]] if ctx["formatted"] else [])
