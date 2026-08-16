"""Self-RAG style retrieve → critique → re-retrieve for UW guidelines.

The model (or a deterministic critic) decides whether retrieved context is
enough. If not, we broaden the query (HyDE / keyword) and try once more.
Never invents a guideline when both passes miss — returns ``no_context``.
"""

from __future__ import annotations

import os
from typing import Any

from insureflow.rag.hyde import hyde_search_query


def self_rag_enabled() -> bool:
    raw = os.getenv("USE_SELF_RAG", "1").strip().lower()
    return raw not in {"0", "false", "off", "no", "none"}


def _context_is_adequate(contexts: dict[str, Any], *, min_chunks: int = 1, min_score: float = 0.15) -> bool:
    if contexts.get("no_context"):
        return False
    chunks = (
        contexts.get("retrieved_contexts")
        or contexts.get("vector_guideline_chunks")
        or contexts.get("contexts")
        or contexts.get("vector_chunks")
        or []
    )
    if len(chunks) < min_chunks:
        return False
    scores = contexts.get("scores") or []
    if scores and max(float(s) for s in scores) < min_score:
        return False
    best = contexts.get("best_raw_vector_score")
    if best is not None and float(best) < min_score and not contexts.get("knowledge_graph_facts"):
        return False
    return True


def _critique_with_llm(query: str, contexts: dict[str, Any], llm: Any) -> bool:
    """Return True if the LLM says the context is enough to answer without invention."""
    if llm is None or not getattr(llm, "api_key", None):
        return _context_is_adequate(contexts)
    joined = "\n".join(
        str(c)
        for c in (
            contexts.get("retrieved_contexts")
            or contexts.get("vector_guideline_chunks")
            or contexts.get("contexts")
            or []
        )[:6]
    )
    prompt = (
        "You are auditing retrieval for an underwriting assistant. "
        "Answer YES if the context is sufficient to answer without inventing rules, else NO.\n\n"
        f"QUESTION: {query}\n\nCONTEXT:\n{joined[:4000]}\n\nAnswer YES or NO only."
    )
    try:
        raw = str(llm.complete(prompt) or "").strip().upper()
        return raw.startswith("YES")
    except Exception:
        return _context_is_adequate(contexts)


def retrieve_with_self_rag(
    rag_agent: Any,
    query: str,
    *,
    top_k: int = 5,
    line_of_business: str | None = None,
    llm: Any = None,
    use_hyde: bool = True,
) -> dict[str, Any]:
    """One adaptive retrieval pass with optional HyDE retry."""
    first = rag_agent.retrieve_contexts(query, top_k=top_k, line_of_business=line_of_business)
    meta: dict[str, Any] = {
        "self_rag": self_rag_enabled(),
        "passes": 1,
        "hyde_used": False,
        "adequate_after_pass_1": _context_is_adequate(first),
    }
    if not self_rag_enabled():
        return {**first, "self_rag_meta": meta}

    adequate = _critique_with_llm(query, first, llm) if llm else _context_is_adequate(first)
    meta["adequate_after_pass_1"] = adequate
    if adequate:
        return {**first, "self_rag_meta": meta}

    if not use_hyde:
        return {**first, "self_rag_meta": meta}

    hypo = hyde_search_query(query, llm=llm, line_of_business=line_of_business, use_llm=bool(llm and getattr(llm, "api_key", None)))
    second = rag_agent.retrieve_contexts(hypo, top_k=top_k, line_of_business=line_of_business)
    meta["passes"] = 2
    meta["hyde_used"] = True
    meta["hyde_query"] = hypo[:240]
    meta["adequate_after_pass_2"] = _context_is_adequate(second)
    # Prefer second if it found anything; else keep honest no_context from first.
    if second.get("no_context") and not first.get("no_context"):
        return {**first, "self_rag_meta": meta}
    return {**second, "self_rag_meta": meta}
