"""Bayesian-style uncertainty calibration (multi-pass variance).

A single extraction pass can report high per-field confidence and still be wrong.
This layer runs the extractor ``N > 1`` times (LLM passes at varied temperature,
or any parameterized sampler), then measures *epistemic variance* — how unstable
the answer is across runs. Fields with a high coefficient of variation get
flagged for human review even when their mean confidence looks high.

``estimate_uncertainty`` is generic over any ``sample()`` callable returning
``dict[str, float]`` so callers can pass a temperature-jittered LLM extractor, a
dual-OCR sampler, or a deterministic function (which trivially yields zero
variance and passes clean).
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence

from insureflow.models.submissions import VerificationIssue
from insureflow.verification.common import SEVERITY_WARNING

_DEFAULT_N_PASSES = 3
_DEFAULT_CV_THRESHOLD = 0.05  # 5% coefficient of variation


def estimate_uncertainty(
    sample: Callable[[], Mapping[str, float]],
    n_passes: int = _DEFAULT_N_PASSES,
) -> dict[str, float]:
    """Return ``{field: coefficient_of_variation}`` across ``n_passes`` samples.

    A deterministic sampler yields CV 0.0 for every field. Fields missing from a
    sample are treated as 0.0 for that run (sporadic presence is itself a signal).
    """
    runs: list[dict[str, float]] = []
    for _ in range(max(n_passes, 2)):
        try:
            run = dict(sample())
        except Exception:
            run = {}
        runs.append(run)

    by_field: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        for field, value in run.items():
            try:
                by_field[field].append(float(value))
            except (TypeError, ValueError):
                continue

    cv: dict[str, float] = {}
    for field, values in by_field.items():
        if len(values) < 2:
            cv[field] = 0.0
            continue
        mean = statistics.fmean(values)
        if mean == 0:
            cv[field] = 0.0 if statistics.pstdev(values) == 0 else 1.0
            continue
        cv[field] = statistics.pstdev(values) / abs(mean)
    return cv


def high_variance_fields(
    cv_map: Mapping[str, float],
    cv_threshold: float = _DEFAULT_CV_THRESHOLD,
) -> list[str]:
    """Fields whose coefficient of variation exceeds the threshold."""
    return [field for field, cv in cv_map.items() if cv > cv_threshold]


def variance_from_extracted_fields(
    fields: Mapping[str, Sequence[Any]],
) -> dict[str, float]:
    """Coefficient of variation when the same field was read more than once.

    Two extractors (or two pages) that disagree on a dollar figure are a
    self-consistency failure — we do not pick the pretty number.
    """
    from insureflow.verification.common import to_number

    cv: dict[str, float] = {}
    for key, entries in fields.items():
        values: list[float] = []
        for entry in entries or []:
            raw = getattr(entry, "value", entry)
            num = to_number(str(raw))
            if num is not None:
                values.append(num)
        if len(values) < 2:
            continue
        mean = statistics.fmean(values)
        if mean == 0:
            cv[key] = 0.0 if statistics.pstdev(values) == 0 else 1.0
            continue
        cv[key] = statistics.pstdev(values) / abs(mean)
    return cv


def uncertainty_issues(
    cv_map: Mapping[str, float],
    cv_threshold: float = _DEFAULT_CV_THRESHOLD,
) -> list[VerificationIssue]:
    """Issues for fields with unstable extraction across passes."""
    issues: list[VerificationIssue] = []
    for field in high_variance_fields(cv_map, cv_threshold):
        issues.append(
            VerificationIssue(
                code="epistemic_variance",
                severity=SEVERITY_WARNING,
                message=(f"{field} varied with CV {cv_map[field]:.3f} across extraction passes (> {cv_threshold:.2f}); unstable value — route to human review"),
                field_name=field,
            )
        )
    return issues
