"""Pydantic models for banking cash-flow features."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BankTransaction(BaseModel):
    txn_id: str = ""
    amount: float = 0.0  # signed: negative = debit / outflow
    posted_on: str = ""  # YYYY-MM-DD
    description: str = ""
    merchant: str = ""
    mcc: str = ""


class CategorizedTransaction(BaseModel):
    txn_id: str
    amount: float
    posted_on: str
    description: str = ""
    category: str
    confidence: float = Field(ge=0, le=1)
    ach: bool = False


class AchSchedule(BaseModel):
    name: str = "premium"
    cadence: str = "monthly"  # weekly | biweekly | semimonthly | monthly
    start_on: str  # YYYY-MM-DD
    amount: float = 0.0
    weekday: int | None = None  # 0=Mon .. 6=Sun for weekly/biweekly
    count: int = 6


class BalanceForecast(BaseModel):
    as_of: str
    starting_balance: float
    predicted: list[dict[str, Any]] = Field(default_factory=list)
    overdraft_risk: bool = False
    min_predicted_balance: float = 0.0
    method: str = "linear_trend"
    confidence: float = Field(ge=0, le=1, default=0.5)
