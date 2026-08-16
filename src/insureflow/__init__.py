"""Rytera underwriting pipeline.

Heavy graph/LLM imports stay lazy so unit tests can load oracles, vision, and
fraud checks without installing LangGraph.
"""

from __future__ import annotations

from typing import Any

__all__ = ["UnderwritingPipeline"]


def __getattr__(name: str) -> Any:
    if name == "UnderwritingPipeline":
        from insureflow.pipeline import UnderwritingPipeline

        return UnderwritingPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
