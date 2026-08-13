"""Statutory / CAS loss ratio: incurred losses ÷ earned premium.

Never use TIV (or a made-up % of TIV) as the denominator. Written premium is
only a fallback when earned premium is missing. Unknown LR must not be treated
as loss-free for experience rating.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from insureflow.models.submissions import SubmissionBundle


@dataclass(frozen=True)
class LossRatioResult:
    ratio: float  # decimal (0.65 = 65%)
    known: bool
    basis: str  # stored | earned_premium | written_premium | unknown
    incurred: float = 0.0
    premium: float = 0.0


def normalize_stored_ratio(value: float) -> float:
    """Accept decimal (0.65) or percent (65) loss ratios."""
    v = float(value)
    if v < 0:
        return 0.0
    if v > 3.0:
        v = v / 100.0
    return min(v, 5.0)


def compute_loss_ratio(
    *,
    incurred: float = 0.0,
    earned_premium: float = 0.0,
    written_premium: float = 0.0,
    stored_ratio: float | None = None,
    stored_ratios: dict[str, Any] | None = None,
) -> LossRatioResult:
    """Incurred losses ÷ earned premium, with explicit stored ratios first."""
    if stored_ratio is not None:
        try:
            ratio = normalize_stored_ratio(float(stored_ratio))
            if ratio > 0:
                return LossRatioResult(ratio=round(ratio, 4), known=True, basis="stored")
        except (TypeError, ValueError):
            pass
    if stored_ratios:
        best = 0.0
        found = False
        for value in stored_ratios.values():
            try:
                ratio = normalize_stored_ratio(float(value))
            except (TypeError, ValueError):
                continue
            if ratio > 0:
                best = max(best, ratio)
                found = True
        if found:
            return LossRatioResult(ratio=round(best, 4), known=True, basis="stored")

    inc = max(float(incurred or 0.0), 0.0)
    earned = max(float(earned_premium or 0.0), 0.0)
    written = max(float(written_premium or 0.0), 0.0)
    if earned > 0:
        return LossRatioResult(
            ratio=round(inc / earned, 4),
            known=True,
            basis="earned_premium",
            incurred=inc,
            premium=earned,
        )
    if written > 0:
        return LossRatioResult(
            ratio=round(inc / written, 4),
            known=True,
            basis="written_premium",
            incurred=inc,
            premium=written,
        )
    return LossRatioResult(ratio=0.0, known=False, basis="unknown", incurred=inc, premium=0.0)


def loss_ratio_from_bundle(bundle: SubmissionBundle | None) -> LossRatioResult:
    """Derive LR from a submission: stored ratios, then incurred ÷ premium."""
    if bundle is None or bundle.structured is None:
        return LossRatioResult(ratio=0.0, known=False, basis="unknown")

    structured = bundle.structured
    fin = structured.financial
    stored_ratio: float | None = None
    stored_ratios: dict[str, Any] | None = None
    incurred = 0.0
    earned = 0.0
    written = 0.0

    if fin is not None:
        raw = getattr(fin, "loss_ratio", None)
        if raw is not None:
            try:
                stored_ratio = float(raw)
            except (TypeError, ValueError):
                stored_ratio = None
        loss_run = fin.loss_run
        if loss_run is not None:
            if loss_run.loss_ratios:
                stored_ratios = dict(loss_run.loss_ratios)
            incurred = float(loss_run.total_incurred or 0.0)
            if incurred <= 0 and loss_run.claims:
                incurred = float(sum(float(c.incurred_amount or 0) for c in loss_run.claims))
            earned = float(getattr(loss_run, "earned_premium", 0.0) or 0.0)
            written = float(getattr(loss_run, "written_premium", 0.0) or 0.0)

    if incurred <= 0 and structured.risk_profile and structured.risk_profile.prior_claims:
        incurred = float(sum(float(c.incurred_amount or 0) for c in structured.risk_profile.prior_claims))

    if written <= 0 and structured.coverages:
        written = float(sum(float(c.premium or 0) for c in structured.coverages))

    return compute_loss_ratio(
        incurred=incurred,
        earned_premium=earned,
        written_premium=written,
        stored_ratio=stored_ratio,
        stored_ratios=stored_ratios,
    )
