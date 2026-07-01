from __future__ import annotations

import logging
from typing import Optional

from insureflow.rag.guidelines import Guideline, builtin_guidelines
from insureflow.rag.vector_store import InMemoryVectorStore, VectorStore

logger = logging.getLogger(__name__)


class RAGAgent:
    def __init__(self, vector_store: Optional[VectorStore] = None) -> None:
        self.store = vector_store or InMemoryVectorStore()
        self._initialized = False

    def ensure_indexed(self) -> None:
        if not self._initialized:
            guidelines = builtin_guidelines()
            self.store.index_guidelines(guidelines.guidelines)
            self._initialized = True
            logger.info("Indexed %d underwriting guidelines", len(guidelines.guidelines))

    def query(self, query: str, top_k: int = 5) -> list[Guideline]:
        self.ensure_indexed()
        results = self.store.search(query, top_k=top_k)
        return [g for g, _ in results]

    def format_context(self, query: str, top_k: int = 5) -> str:
        guidelines = self.query(query, top_k=top_k)
        if not guidelines:
            return ""
        lines: list[str] = ["=== RELEVANT UNDERWRITING GUIDELINES ==="]
        for g in guidelines:
            lines.append(f"[{g.id}] ({g.category.value.upper()}, {g.source.value}) {g.title}")
            lines.append(f"    Impact: {g.risk_impact}")
            lines.append(f"    {g.content}")
            lines.append("")
        return "\n".join(lines)

    def augment_synthesis_prompt(self, query: str, original_prompt: str, top_k: int = 5) -> str:
        context = self.format_context(query, top_k=top_k)
        if not context:
            return original_prompt
        return f"{context}\n\n---\n\n{original_prompt}"
