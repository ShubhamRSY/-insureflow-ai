"""Sanitize pipeline job payloads for client-facing API — hides internal eval / telemetry."""

from __future__ import annotations

from typing import Any

_STRIP_RESULT_KEYS = frozenset(
    {
        "shadow_eval",
        "_shadow_eval",
        "eval_scores",
        "zta_report",
        "prediction_id",
        "version_context",
        "audit_paths",
    }
)

_STRIP_QUOTE_META = frozenset({"lob_profile", "surcharges_raw"})


def sanitize_job_for_client(job: dict[str, Any] | None) -> dict[str, Any] | None:
    if not job:
        return job
    out = dict(job)
    results = out.get("results")
    if not isinstance(results, dict):
        return out
    clean = {k: v for k, v in results.items() if k not in _STRIP_RESULT_KEYS}
    quote = clean.get("quote")
    if isinstance(quote, dict) and isinstance(quote.get("metadata"), dict):
        q = dict(quote)
        q["metadata"] = {k: v for k, v in q["metadata"].items() if k not in _STRIP_QUOTE_META}
        clean["quote"] = q
    out["results"] = clean
    return out
