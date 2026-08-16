"""Layered extraction verification for underwriting documents.

Layers (each in its own module):
- ``arithmetic`` — deterministic math constraints (balance-sheet identity,
  sum-to-total, cross-page reconciliation).
- ``guardrails`` — range, regex/checksum and schema/typing enforcement.
- ``spatial_graph`` — layout masking / column-alignment checks over bboxes.
- ``semantic_triangulation`` — table figure ↔ footnote binding (RAE-style).
- ``uncertainty`` — multi-pass epistemic variance (Bayesian-style calibration).
- ``critic`` — critic loops + dual-model consensus with an exception queue.
- ``external_lookup`` — guarded third-party registry cross-referencing.
- ``engine`` — aggregates the layers into a ``VerificationReport``.

Every layer is opt-in/degradation-safe and deterministic unless it explicitly
needs an LLM (critic/uncertainty), which is off unless the env enables it.
"""

from __future__ import annotations

from typing import Any

_LAZY: dict[str, str] = {
    "auto_sum_to_total": "insureflow.verification.arithmetic",
    "balance_sheet_identity": "insureflow.verification.arithmetic",
    "cross_page_reconciliation": "insureflow.verification.arithmetic",
    "sum_to_total_verification": "insureflow.verification.arithmetic",
    "pattern_checks": "insureflow.verification.guardrails",
    "range_checks": "insureflow.verification.guardrails",
    "schema_validation": "insureflow.verification.guardrails",
    "verification_enabled": "insureflow.verification.common",
    "VerificationEngine": "insureflow.verification.engine",
}


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module), name)


def __dir__() -> list[str]:
    return sorted(list(globals()) + list(_LAZY))


__all__ = list(_LAZY)
