"""Deterministic cash-flow engine: categorize, forecast balances, ACH calendar."""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Any

from insureflow.banking.models import AchSchedule, BalanceForecast, BankTransaction, CategorizedTransaction

_RULES: list[tuple[str, re.Pattern[str], float]] = [
    ("payroll", re.compile(r"\b(payroll|salary|direct dep|adp|paychex|gusto|wage)\b", re.I), 0.95),
    ("rent", re.compile(r"\b(rent|lease pmt|apartment|landlord)\b", re.I), 0.9),
    ("insurance", re.compile(r"\b(insurance|premium|geico|state farm|allstate|progressive|hartford)\b", re.I), 0.9),
    ("utilities", re.compile(r"\b(electric|utility|water bill|gas co|pge|comcast|verizon|att)\b", re.I), 0.85),
    ("groceries", re.compile(r"\b(grocery|whole foods|kroger|safeway|walmart|trader joe)\b", re.I), 0.85),
    ("fuel", re.compile(r"\b(shell|chevron|exxon|bp #|fuel|gas station)\b", re.I), 0.85),
    ("loan_payment", re.compile(r"\b(loan pmt|installment|mortgage|auto loan|navient|sofi)\b", re.I), 0.9),
    ("tax", re.compile(r"\b(irs|treasury|tax pmt|franchise tax)\b", re.I), 0.9),
    ("medical", re.compile(r"\b(hospital|pharmacy|cvs|walgreens|clinic|copay)\b", re.I), 0.8),
    ("subscription", re.compile(r"\b(netflix|spotify|adobe|microsoft 365|aws|github|saas)\b", re.I), 0.85),
    ("atm", re.compile(r"\b(atm |atm withdrawal|cash withdrawal)\b", re.I), 0.95),
    ("fee", re.compile(r"\b(nsf|overdraft|service charge|monthly fee|wire fee)\b", re.I), 0.95),
    ("interest", re.compile(r"\b(interest (paid|earned)|int pmt)\b", re.I), 0.9),
    ("wire", re.compile(r"\b(wire (in|out)|incoming wire|outgoing wire)\b", re.I), 0.95),
    ("ach_pull", re.compile(r"\b(ach (debit|withdraw|pull)|orig co name|electronic (debit|withdrawal))\b", re.I), 0.95),
    ("transfer", re.compile(r"\b(transfer|xfer|venmo|zelle|paypal)\b", re.I), 0.8),
]

_ACH_HINT = re.compile(r"\bach\b|electronic (debit|withdrawal)|orig co", re.I)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def categorize_transactions(transactions: list[BankTransaction]) -> list[CategorizedTransaction]:
    out: list[CategorizedTransaction] = []
    for txn in transactions:
        blob = f"{txn.description} {txn.merchant} {txn.mcc}".strip()
        category = "other"
        confidence = 0.4
        for name, pattern, conf in _RULES:
            if pattern.search(blob):
                category = name
                confidence = conf
                break
        if txn.mcc:
            mcc_map = {"5411": "groceries", "5541": "fuel", "6300": "insurance", "4900": "utilities", "5812": "dining"}
            mapped = mcc_map.get(txn.mcc)
            if mapped:
                category = mapped
                confidence = max(confidence, 0.92)
        ach = bool(_ACH_HINT.search(blob)) or category == "ach_pull"
        out.append(
            CategorizedTransaction(
                txn_id=txn.txn_id or f"{txn.posted_on}:{txn.amount}",
                amount=txn.amount,
                posted_on=txn.posted_on,
                description=txn.description or txn.merchant,
                category=category,
                confidence=confidence,
                ach=ach,
            )
        )
    return out


def next_ach_pull_dates(schedule: AchSchedule) -> list[dict[str, Any]]:
    start = _parse_date(schedule.start_on)
    cadence = (schedule.cadence or "monthly").lower()
    count = max(1, min(schedule.count, 36))
    dates: list[date] = []
    if cadence == "weekly":
        cursor = start
        if schedule.weekday is not None:
            while cursor.weekday() != schedule.weekday:
                cursor += timedelta(days=1)
        for _ in range(count):
            dates.append(cursor)
            cursor += timedelta(days=7)
    elif cadence == "biweekly":
        cursor = start
        if schedule.weekday is not None:
            while cursor.weekday() != schedule.weekday:
                cursor += timedelta(days=1)
        for _ in range(count):
            dates.append(cursor)
            cursor += timedelta(days=14)
    elif cadence == "semimonthly":
        year, month = start.year, start.month
        day = start.day
        first_half = 1 if day <= 15 else 15
        cursor_day = first_half if day <= 15 else 15
        # Align to 1st or 15th on/after start.
        candidate = date(year, month, 1 if cursor_day <= 1 else 15)
        if candidate < start:
            candidate = date(year, month, 15) if candidate.day == 1 else _add_months(date(year, month, 1), 1)
        while len(dates) < count:
            dates.append(candidate)
            if candidate.day == 1:
                candidate = date(candidate.year, candidate.month, 15)
            else:
                candidate = _add_months(date(candidate.year, candidate.month, 1), 1)
    else:  # monthly
        day = start.day
        cursor = start
        for _ in range(count):
            dates.append(cursor)
            cursor = _add_months_keep_day(cursor, 1, day)
    return [{"date": d.isoformat(), "amount": schedule.amount, "name": schedule.name, "cadence": cadence} for d in dates]


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


def _add_months_keep_day(d: date, months: int, day: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def predict_balance(
    transactions: list[BankTransaction],
    *,
    starting_balance: float = 0.0,
    as_of: str | None = None,
    horizon_days: int = 30,
    upcoming_ach: list[AchSchedule] | None = None,
) -> BalanceForecast:
    txns = sorted(transactions, key=lambda t: t.posted_on or "")
    running = starting_balance
    daily: dict[date, float] = {}
    for txn in txns:
        if not txn.posted_on:
            continue
        running += txn.amount
        daily[_parse_date(txn.posted_on)] = running

    if as_of:
        origin = _parse_date(as_of)
    elif daily:
        origin = max(daily)
    else:
        origin = date.today()

    # Linear slope from first to last observed daily balance.
    slope = 0.0
    if len(daily) >= 2:
        ordered = sorted(daily.items())
        span = (ordered[-1][0] - ordered[0][0]).days or 1
        slope = (ordered[-1][1] - ordered[0][1]) / span

    current = daily.get(origin, running if daily else starting_balance)
    ach_debits: dict[date, float] = {}
    for sched in upcoming_ach or []:
        for row in next_ach_pull_dates(sched):
            d = _parse_date(row["date"])
            ach_debits[d] = ach_debits.get(d, 0.0) + float(row["amount"])

    predicted: list[dict[str, Any]] = []
    balance = current
    min_bal = balance
    horizon = max(1, min(horizon_days, 180))
    for i in range(1, horizon + 1):
        day = origin + timedelta(days=i)
        balance = balance + slope
        pull = ach_debits.get(day, 0.0)
        if pull:
            # ACH pulls are outflows unless amount is already negative.
            balance -= abs(pull)
        min_bal = min(min_bal, balance)
        predicted.append({"date": day.isoformat(), "balance": round(balance, 2), "ach_pull": round(pull, 2) if pull else 0.0})

    confidence = 0.75 if len(daily) >= 10 else 0.55 if len(daily) >= 4 else 0.35
    return BalanceForecast(
        as_of=origin.isoformat(),
        starting_balance=round(current, 2),
        predicted=predicted,
        overdraft_risk=min_bal < 0,
        min_predicted_balance=round(min_bal, 2),
        method="linear_trend+ach",
        confidence=confidence,
    )


class BankingEngine:
    """Facade matching BaseMLModel-style predict() for cash-flow features."""

    model_name = "banking_cashflow"
    version = "0.1.0"

    def categorize(self, transactions: list[BankTransaction]) -> list[CategorizedTransaction]:
        return categorize_transactions(transactions)

    def predict(self, transactions: list[BankTransaction], **kwargs: Any) -> BalanceForecast:
        return predict_balance(transactions, **kwargs)

    def ach_dates(self, schedule: AchSchedule) -> list[dict[str, Any]]:
        return next_ach_pull_dates(schedule)
