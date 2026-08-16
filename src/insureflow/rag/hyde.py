"""Hypothetical Document Embeddings (HyDE) for underwriting retrieval.

When the query is short or uses desk slang, vector search can miss. HyDE first
builds a *hypothetical* guideline-like passage, then searches with that text.
Without an LLM we use a deterministic template expansion — never invents a
binding rule, only improves recall of indexed guidelines.
"""

from __future__ import annotations

from typing import Any

_LOB_HINTS = {
    "property": "COPE construction occupancy protection exposure building value sprinkler",
    "gl": "general liability premises operations products completed operations aggregate",
    "workers_comp": "workers compensation experience mod class code payroll NCCI",
    "auto": "commercial auto fleet MVR VIN radius of use",
    "cyber": "cyber MFA ransomware contingency business interruption",
    "marine": "ocean marine hull cargo warehouse-to-warehouse",
}


def expand_query_deterministic(query: str, *, line_of_business: str | None = None) -> str:
    """Template HyDE: expand a short UW question into a guideline-shaped blob."""
    q = (query or "").strip()
    lob = (line_of_business or "").strip().lower().replace(" ", "_")
    hints = _LOB_HINTS.get(lob, "")
    for key, words in _LOB_HINTS.items():
        if key in q.lower():
            hints = f"{hints} {words}".strip()
    hypo = (
        f"Underwriting guideline regarding: {q}. "
        f"Risk factors, appetite limits, required documentation, and referral triggers. "
        f"{hints}".strip()
    )
    return hypo


def expand_query_llm(query: str, llm: Any, *, line_of_business: str | None = None) -> str:
    """Optional LLM HyDE. Falls back to deterministic on any failure."""
    if llm is None or not getattr(llm, "api_key", None):
        return expand_query_deterministic(query, line_of_business=line_of_business)
    lob = (line_of_business or "commercial").strip()
    prompt = (
        "Write one short hypothetical underwriting guideline paragraph that would "
        f"answer this desk question for {lob}. Do not invent carrier names or rates. "
        "No bullet list. Plain prose only.\n\n"
        f"Question: {query}"
    )
    try:
        text = str(llm.complete(prompt) or "").strip()
        if len(text) < 40:
            return expand_query_deterministic(query, line_of_business=line_of_business)
        return text[:1200]
    except Exception:
        return expand_query_deterministic(query, line_of_business=line_of_business)


def hyde_search_query(
    query: str,
    *,
    llm: Any = None,
    line_of_business: str | None = None,
    use_llm: bool = False,
) -> str:
    if use_llm:
        return expand_query_llm(query, llm, line_of_business=line_of_business)
    return expand_query_deterministic(query, line_of_business=line_of_business)
