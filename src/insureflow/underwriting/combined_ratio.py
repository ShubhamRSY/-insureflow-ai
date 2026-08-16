"""Combined ratio — the sum of the loss ratio and the expense ratio.

A combined ratio under 100% indicates an underwriting profit. The loss-ratio
side reuses the statutory/CAS ``loss_ratio_from_bundle`` computation; the
expense side is underwriting & operational expense divided by written premium.
"""

from __future__ import annotations

from insureflow.models.policy import CombinedRatioResult
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.loss_ratio import loss_ratio_from_bundle


def expense_ratio(*, expenses: float, written_premium: float) -> float | None:
    """Underwriting & operational expenses ÷ written premium (decimal)."""
    expenses = max(float(expenses or 0.0), 0.0)
    written = max(float(written_premium or 0.0), 0.0)
    if written <= 0:
        return None
    return round(expenses / written, 4)


def combined_ratio(
    *,
    loss_ratio: float | None,
    expense_ratio: float | None,
) -> CombinedRatioResult:
    """Loss ratio + expense ratio. Below 100% (1.0) is an underwriting profit."""
    if loss_ratio is None and expense_ratio is None:
        return CombinedRatioResult(detail="Neither a loss ratio nor an expense ratio is known")
    loss = max(float(loss_ratio or 0.0), 0.0)
    exp = max(float(expense_ratio or 0.0), 0.0)
    combined = round(loss + exp, 4)
    detail = f"Combined ratio {combined:.1%} = loss ratio {loss:.1%} + expense ratio {exp:.1%}" + (" — underwriting profit" if combined < 1.0 else " — underwriting loss")
    return CombinedRatioResult(
        loss_ratio=loss,
        expense_ratio=exp,
        combined_ratio=combined,
        underwriting_profit=combined < 1.0,
        detail=detail,
    )


def _estimate_expenses_from_bundle(bundle: SubmissionBundle) -> float | None:
    """Underwriting & operational expense estimate for the submission's written premium.

    Uses the insurer's modelled expense base (commissions, fixed expenses) when
    available; otherwise a representative 25% expense ratio is applied so the
    combined ratio is still computable from a known loss ratio.
    """
    if bundle is None or bundle.structured is None:
        return None
    written = 0.0
    if bundle.structured.financial and bundle.structured.financial.loss_run:
        written = float(bundle.structured.financial.loss_run.written_premium or 0.0)
    if written <= 0 and bundle.structured.coverages:
        written = float(sum(float(c.premium or 0) for c in bundle.structured.coverages))
    if written <= 0:
        return None
    try:
        from insureflow.rating.expenses import project_expenses

        projections = project_expenses({"commissions": written * 0.15, "general_expense": written * 0.10})
        expenses = float(sum(p.projected for p in projections))
        if expenses > 0:
            return expenses
    except Exception:
        pass
    return written * 0.25


def combined_ratio_from_bundle(
    bundle: SubmissionBundle | None,
    *,
    expenses: float | None = None,
) -> CombinedRatioResult:
    """Combined ratio for a submission from its loss run + an expense estimate."""
    lr = loss_ratio_from_bundle(bundle)
    loss = lr.ratio if lr.known else None
    exp = None
    if expenses is not None:
        exp = expense_ratio(expenses=expenses, written_premium=lr.premium or 0.0)
    elif bundle is not None:
        est = _estimate_expenses_from_bundle(bundle)
        if est is not None:
            exp = expense_ratio(expenses=est, written_premium=lr.premium or 0.0)
    if loss is None and exp is None:
        return CombinedRatioResult(detail="No loss-ratio or expense data available")
    return combined_ratio(loss_ratio=loss, expense_ratio=exp)
