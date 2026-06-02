from __future__ import annotations

import logging
import os
from typing import Any

import psycopg2

from insureflow.llm.client import LLMClient

logger = logging.getLogger(__name__)


class RAGAgent:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://insureflow:insureflow@localhost:5432/insureflow",
        )

    def retrieve_guidelines(self, query: str, top_k: int = 3) -> list[str]:
        """Embeds the query and performs a vector similarity search in PostgreSQL."""
        try:
            embedding = self.llm.embed(query)
            
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT rule_text FROM underwriting_guidelines 
                        ORDER BY embedding <-> %s::vector LIMIT %s
                        """,
                        (embedding, top_k),
                    )
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error("RAG pgvector retrieval failed: %s", e)
            return []