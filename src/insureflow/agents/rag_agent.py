from __future__ import annotations

import logging
import os
from typing import Any

from insureflow.rag.retrieval_config import RetrievalConfig

logger = logging.getLogger(__name__)


class RAGAgent:
    """Pipeline RAG wrapper: prefer pgvector when available, else hybrid vector+KG.

    Uses pipeline_top_k (default 3) for synthesis; hybrid path applies re-rank + fallbacks.
    """

    def __init__(self) -> None:
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://insureflow:insureflow@localhost:5432/insureflow",
        )
        self.config = RetrievalConfig.from_env()
        self._hybrid: Any = None

    def _get_hybrid(self) -> Any:
        if self._hybrid is None:
            from insureflow.rag.rag_agent import RAGAgent as HybridRAG

            self._hybrid = HybridRAG(use_knowledge_graph=True, config=self.config)
        return self._hybrid

    def retrieve_guidelines(self, query: str, top_k: int | None = None) -> list[str]:
        """Retrieve guideline/KG context strings for synthesis / Ragas."""
        k = top_k if top_k is not None else self.config.pipeline_top_k
        # Try live pgvector first when DATABASE_URL is reachable
        try:
            import psycopg2

            from insureflow.llm.client import LLMClient
            from insureflow.rag.knowledge_graph import get_knowledge_graph

            # Over-fetch then take top_k (DB has no in-SQL re-rank; hybrid path re-ranks)
            fetch_k = max(self.config.fetch_k, k)
            embedding = LLMClient().embed(query)
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT rule_text FROM underwriting_guidelines
                        ORDER BY embedding <-> %s::vector LIMIT %s
                        """,
                        (embedding, fetch_k),
                    )
                    rows = [row[0] for row in cur.fetchall()][:k]
                    if rows:
                        kg_only = get_knowledge_graph().format_context_block(query)
                        if kg_only:
                            rows = rows + [kg_only]
                        return rows
                    # empty pgvector → fall through to hybrid fallback ladder
                    logger.info("pgvector returned 0 rows — hybrid keyword/KG fallback")
        except Exception as e:
            logger.debug("pgvector RAG unavailable, using hybrid in-memory RAG+KG: %s", e)

        ctx = self._get_hybrid().retrieve_contexts(query, top_k=k)
        if ctx.get("no_context"):
            return list(ctx["retrieved_contexts"])
        return ctx["retrieved_contexts"] or ([ctx["formatted"]] if ctx["formatted"] else [])
