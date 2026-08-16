"""Holdout-calibrated STP confidence thresholds (conformal-style).

Fixed 0.95 is a guess. Given a set of (confidence, was_correct) labels from
golden / UW override history, we pick the lowest threshold that keeps the
empirical error rate at or below ``target_error`` on the holdout set.

This is a non-parametric coverage gate — not a full conformal prediction set
over continuous premiums. We do not invent statistical guarantees we have not
measured on your book.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ConformalSTPResult:
    threshold: float
    target_error: float
    empirical_error: float
    n_holdout: int
    n_accepted: int
    method: str = "holdout_quantile"

    def to_dict(self) -> dict:
        return {
            "threshold": round(self.threshold, 4),
            "target_error": self.target_error,
            "empirical_error": round(self.empirical_error, 4),
            "n_holdout": self.n_holdout,
            "n_accepted": self.n_accepted,
            "method": self.method,
        }


def calibrate_stp_threshold(
    labels: Sequence[tuple[float, bool]],
    *,
    target_error: float = 0.05,
    default_threshold: float = 0.95,
    grid_step: float = 0.01,
) -> ConformalSTPResult:
    """Return the lowest confidence threshold with empirical error ≤ target.

    ``labels`` is ``(confidence, was_correct)``. Fields accepted at threshold
    ``t`` are those with ``confidence >= t``. Error rate among accepted must
    stay ≤ ``target_error``. If nothing works, fall back to ``default_threshold``.
    """
    if not labels:
        return ConformalSTPResult(
            threshold=default_threshold,
            target_error=target_error,
            empirical_error=1.0,
            n_holdout=0,
            n_accepted=0,
            method="default_no_holdout",
        )

    confidences = [max(0.0, min(1.0, float(c))) for c, _ in labels]
    correct = [bool(ok) for _, ok in labels]
    n = len(labels)

    best_t = default_threshold
    best_err = 1.0
    best_accepted = 0
    found = False

    # Search from high → low so we prefer the most permissive threshold that still covers.
    steps = int(round(1.0 / grid_step))
    for i in range(steps + 1):
        t = 1.0 - i * grid_step
        accepted_idx = [j for j, c in enumerate(confidences) if c >= t]
        if not accepted_idx:
            continue
        errors = sum(1 for j in accepted_idx if not correct[j])
        err_rate = errors / len(accepted_idx)
        if err_rate <= target_error + 1e-12:
            best_t = t
            best_err = err_rate
            best_accepted = len(accepted_idx)
            found = True
            # keep searching lower to maximize acceptance under the error budget

    if not found:
        # Finite-sample fallback: (ceil((n+1)*(1-α)) / n) quantile of incorrect confidences.
        wrong_conf = sorted(c for c, ok in zip(confidences, correct) if not ok)
        if wrong_conf:
            # Require threshold above the worst incorrect confidence we observed.
            best_t = min(1.0, max(default_threshold, wrong_conf[-1] + grid_step))
            best_err = sum(1 for c, ok in zip(confidences, correct) if c >= best_t and not ok) / max(
                sum(1 for c in confidences if c >= best_t), 1
            )
            best_accepted = sum(1 for c in confidences if c >= best_t)
            method = "fallback_above_wrong"
        else:
            best_t = default_threshold
            best_err = 0.0
            best_accepted = n
            method = "default_all_correct"
        return ConformalSTPResult(
            threshold=round(best_t, 4),
            target_error=target_error,
            empirical_error=best_err,
            n_holdout=n,
            n_accepted=best_accepted,
            method=method,
        )

    return ConformalSTPResult(
        threshold=round(best_t, 4),
        target_error=target_error,
        empirical_error=best_err,
        n_holdout=n,
        n_accepted=best_accepted,
        method="holdout_quantile",
    )


def prediction_set_for_metric(
    candidates: Iterable[tuple[float, float]],
    *,
    residual_quantile: float,
) -> tuple[float, float] | None:
    """Conformal-style interval around a point estimate.

    ``candidates`` is ``(prediction, residual)`` from a calibration set.
    Returns ``(lo, hi)`` for the *last* prediction using the absolute residual
    quantile, or None if empty.
    """
    rows = list(candidates)
    if not rows:
        return None
    residuals = sorted(abs(float(r)) for _, r in rows)
    q = max(0.0, min(1.0, residual_quantile))
    idx = min(len(residuals) - 1, max(0, math.ceil(q * len(residuals)) - 1))
    width = residuals[idx]
    point = float(rows[-1][0])
    return point - width, point + width
