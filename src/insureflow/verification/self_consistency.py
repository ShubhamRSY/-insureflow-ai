"""Multi-sample self-consistency sampler for critical underwriting numerics.

Runs N independent reads (callable sampler or dual field lists). High variance
is treated as hallucination risk and blocks STP via the verification engine.
"""

from __future__ import annotations

import os
from typing import Callable, Mapping, Sequence

from insureflow.models.submissions import ExtractedField, VerificationIssue
from insureflow.verification.common import SEVERITY_ERROR, SEVERITY_WARNING, to_number
from insureflow.verification.uncertainty import estimate_uncertainty, uncertainty_issues, variance_from_extracted_fields

_CRITICAL = ("limit", "premium", "deductible", "incurred", "total", "payroll", "tiv", "building_value")


def self_consistency_enabled() -> bool:
    raw = os.getenv("USE_SELF_CONSISTENCY", "1").strip().lower()
    return raw not in {"0", "false", "off", "no", "none"}


def critical_numeric_sample_from_fields(fields: Mapping[str, Sequence[ExtractedField]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, entries in fields.items():
        if not entries:
            continue
        if not any(tok in key.lower() for tok in _CRITICAL):
            continue
        num = to_number(entries[0].value)
        if num is not None:
            out[key] = num
    return out


def sample_with_jitter(
    base: Mapping[str, float],
    *,
    pass_index: int,
) -> dict[str, float]:
    """Deterministic micro-jitter for regression tests / dual-parser stubs.

    Pass 0 is identity. Later passes flip nothing by default — callers should
    supply a real multi-engine ``sample`` callable in production.
    """
    if pass_index == 0:
        return dict(base)
    # No invented disagreement — return the same values. Real dual OCR/LLM
    # samplers replace this callable.
    return dict(base)


def critical_self_consistency_issues(
    fields: Mapping[str, Sequence[ExtractedField]],
    *,
    sample: Callable[[], Mapping[str, float]] | None = None,
    n_passes: int | None = None,
    cv_threshold: float | None = None,
) -> list[VerificationIssue]:
    if not self_consistency_enabled():
        return []
    n_passes = n_passes if n_passes is not None else int(os.getenv("SELF_CONSISTENCY_PASSES", "3"))
    cv_threshold = cv_threshold if cv_threshold is not None else float(os.getenv("SELF_CONSISTENCY_CV", "0.05"))

    # Prefer multi-read disagreement already present on the field lists.
    issues = uncertainty_issues(variance_from_extracted_fields(fields), cv_threshold=cv_threshold)
    # Promote critical-field variance to error (blocks STP).
    promoted: list[VerificationIssue] = []
    for issue in issues:
        if any(tok in (issue.field_name or "").lower() for tok in _CRITICAL):
            promoted.append(
                VerificationIssue(
                    code="critical_self_consistency",
                    severity=SEVERITY_ERROR,
                    message=issue.message.replace("route to human review", "blocks STP — unstable critical numeric"),
                    field_name=issue.field_name,
                    page_number=issue.page_number,
                    bbox=issue.bbox,
                )
            )
        else:
            promoted.append(issue)

    if sample is not None:
        cv = estimate_uncertainty(sample, n_passes=n_passes)
        for issue in uncertainty_issues(cv, cv_threshold=cv_threshold):
            sev = SEVERITY_ERROR if any(tok in (issue.field_name or "").lower() for tok in _CRITICAL) else SEVERITY_WARNING
            promoted.append(
                VerificationIssue(
                    code="multi_pass_variance",
                    severity=sev,
                    message=issue.message,
                    field_name=issue.field_name,
                )
            )
    return promoted
