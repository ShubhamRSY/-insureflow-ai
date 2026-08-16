"""Premium accounting — earned/unearned (pro-rata & short-rate) and collected.

Written premium is the total committed via issued policies; collected premium is
the cash actually received; earned premium is the pro-rata share of written
premium attributable to already-elapsed coverage days, with the remainder held
as unearned premium (UPR) for unexpired days.
"""

from __future__ import annotations

from datetime import date, datetime

from insureflow.models.policy import EarningMethod, PremiumAccounting
from insureflow.models.submissions import SubmissionBundle


def _date_or_datetime(value: date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def compute_earned_unearned(
    written_premium: float,
    *,
    effective_date: date | None,
    expiration_date: date | None,
    as_of_date: date | None = None,
    method: EarningMethod | str = EarningMethod.PRO_RATA,
) -> PremiumAccounting:
    """Split written premium into earned and unearned as of ``as_of_date``.

    ``method`` controls the earning pattern: pro-rata earns in lockstep with
    elapsed calendar days; short-rate imposes a cancellation penalty so the
    carrier keeps more than the pro-rata share of early-cancelled policies.
    """
    written = max(float(written_premium or 0.0), 0.0)
    method = EarningMethod(method) if isinstance(method, str) else method
    as_of = as_of_date or date.today()

    if effective_date is None or expiration_date is None or expiration_date <= effective_date:
        # No usable policy period: treat everything as unearned at inception.
        return PremiumAccounting(
            written_premium=written,
            earned_premium=0.0,
            unearned_premium=written,
            earning_method=method,
            policy_period_days=0,
            elapsed_days=0,
            as_of_date=as_of,
            basis_note="No valid policy period — unearned until a period is established",
        )

    policy_days = max((expiration_date - effective_date).days, 1)
    elapsed = (as_of - effective_date).days
    elapsed_clamped = max(min(elapsed, policy_days), 0)
    elapsed_frac = elapsed_clamped / policy_days

    if method is EarningMethod.SHORT_RATE:
        # Short-rate: carrier keeps earned + a penalty share of the unearned
        # portion (surrender charge on early cancellation), e.g. 10% of the
        # unearned premium is retained.
        earned = written * elapsed_frac
        unearned = written - earned
        penalty = unearned * 0.10
        earned += penalty
        unearned -= penalty
        note = "Short-rate earning with 10% cancellation penalty"
    else:
        earned = written * elapsed_frac
        unearned = written - earned
        note = "Pro-rata earning over policy days"

    return PremiumAccounting(
        written_premium=round(written, 2),
        earned_premium=round(earned, 2),
        unearned_premium=round(unearned, 2),
        earning_method=method,
        policy_period_days=policy_days,
        elapsed_days=elapsed_clamped,
        as_of_date=as_of,
        basis_note=note,
    )


def apply_collection(
    accounting: PremiumAccounting,
    *,
    collected_premium: float | None = None,
    collection_rate: float | None = None,
) -> PremiumAccounting:
    """Populate the collected/premium-receivable side of the accounting."""
    written = accounting.written_premium
    collected = 0.0
    rate = collection_rate
    if collected_premium is not None:
        collected = max(float(collected_premium), 0.0)
    elif rate is not None:
        rate = max(min(float(rate), 1.0), 0.0)
        collected = written * rate
    else:
        collected = written  # default: assumed collected in full at binding
    if rate is None and written > 0:
        rate = round(collected / written, 4)
    accounting.collected_premium = round(collected, 2)
    accounting.collection_rate = rate
    if collected < written:
        accounting.basis_note += f" — {written - collected:,.2f} premium receivable (billed but not yet collected)"
    return accounting


def premium_accounting_for_bundle(
    bundle: SubmissionBundle | None,
    *,
    as_of_date: date | None = None,
    method: EarningMethod | str = EarningMethod.PRO_RATA,
) -> PremiumAccounting:
    """Derive premium accounting from a submission's policy period and premiums."""
    if bundle is None or bundle.structured is None:
        return PremiumAccounting(basis_note="No structured submission — no premium accounting")

    structured = bundle.structured
    effective = expiration = None
    if structured.policy_period:
        effective = _date_or_datetime(structured.policy_period.effective_date)
        expiration = _date_or_datetime(structured.policy_period.expiration_date)

    written = 0.0
    collected = 0.0
    earned_in = 0.0
    if structured.financial:
        lr = structured.financial.loss_run
        if lr is not None:
            written = float(lr.written_premium or 0.0)
            collected = float(getattr(lr, "collected_premium", 0.0) or 0.0)
            earned_in = float(getattr(lr, "earned_premium", 0.0) or 0.0)
    if written <= 0 and structured.coverages:
        written = float(sum(float(c.premium or 0) for c in structured.coverages))

    accounting = compute_earned_unearned(
        written,
        effective_date=effective,
        expiration_date=expiration,
        as_of_date=as_of_date,
        method=method,
    )
    if earned_in > 0 and accounting.unearned_premium == written:
        # Loss run carries an explicit earned premium — honor it as the source
        # of truth over the pro-rata estimate when no policy period exists.
        accounting.earned_premium = round(earned_in, 2)
        accounting.unearned_premium = round(written - earned_in, 2)
        accounting.basis_note = "Earned premium taken from the loss run"
    apply_collection(accounting, collected_premium=collected)
    return accounting
