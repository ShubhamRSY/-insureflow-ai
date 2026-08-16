"""Layered extraction verification for underwriting documents.

Layers (each in its own module):
- ``arithmetic`` — deterministic math constraints (balance-sheet identity,
  sum-to-total, cross-page reconciliation).
- ``cross_field`` — chronology, payroll vs headcount, size vs rebuild cost.
- ``guardrails`` — range, regex/checksum and schema/typing enforcement.
- ``spatial_graph`` — layout masking / column-alignment checks over bboxes.
- ``semantic_triangulation`` — table figure ↔ footnote binding (RAE-style).
- ``uncertainty`` — multi-pass epistemic variance (Bayesian-style calibration).
- ``citation_gate`` — uncited critical claims fail closed (page/bbox/source_ref).
- ``conformal_stp`` — holdout-calibrated STP confidence thresholds.
- ``audit_loop`` — bounded Extractor↔Auditor recursive correction.
- ``self_consistency`` — multi-read / multi-pass variance on critical numerics.
- ``zero_hallucination`` — target hallucination_count ≤ 0 on bind-ready memos.
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
    "cross_field_checks": "insureflow.verification.cross_field",
    "sum_to_total_verification": "insureflow.verification.arithmetic",
    "pattern_checks": "insureflow.verification.guardrails",
    "range_checks": "insureflow.verification.guardrails",
    "schema_validation": "insureflow.verification.guardrails",
    "verification_enabled": "insureflow.verification.common",
    "VerificationEngine": "insureflow.verification.engine",
    "citation_issues": "insureflow.verification.citation_gate",
    "gate_memo_claims": "insureflow.verification.citation_gate",
    "calibrate_stp_threshold": "insureflow.verification.conformal_stp",
    "run_audit_loop": "insureflow.verification.audit_loop",
    "enforce_zero_hallucination_on_memo": "insureflow.verification.zero_hallucination",
    "evaluate_zero_hallucination": "insureflow.verification.zero_hallucination",
    "critical_self_consistency_issues": "insureflow.verification.self_consistency",
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
