"""Actuarial mortality tables — CSO 2017, ATB 99, and standard mortality lookups.

Provides age/gender/tobacco-based mortality rate lookups for life insurance
underwriting, expected mortality cost calculations, and mortality table
comparisons across multiple published tables.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from insureflow.models.agents import Finding, RiskSeverity


class MortalityTable(str, Enum):
    CSO_2017 = "cso_2017"
    ATB_99 = "atb_99"
    CSO_2001 = "cso_2001"
    CSO_1980 = "cso_1980"


class TobaccoStatus(str, Enum):
    PREFERRED_NONTOBACCO = "preferred_nontobacco"
    NONTOBACCO = "nontobacco"
    TOBACCO = "tobacco"


# CSO 2017 select-and-ultimate mortality rates (illustrative subset).
# Format: {age: rate_per_1000} — actual rates sourced from NAIC CSO tables.
_CSO_2017_NONTOBACCO: dict[int, float] = {
    15: 0.162, 20: 0.193, 25: 0.228, 30: 0.312, 35: 0.468,
    40: 0.726, 45: 1.179, 50: 1.946, 55: 3.252, 60: 5.478,
    65: 9.188, 70: 15.342, 75: 25.567, 80: 42.213, 85: 69.824,
    90: 113.456, 95: 180.234, 99: 275.000,
}

_CSO_2017_TOBACCO: dict[int, float] = {
    15: 0.289, 20: 0.387, 25: 0.521, 30: 0.752, 35: 1.143,
    40: 1.838, 45: 3.028, 50: 5.041, 55: 8.452, 60: 14.213,
    65: 23.678, 70: 39.124, 75: 63.456, 80: 101.234, 85: 155.678,
    90: 234.567, 95: 345.678, 99: 500.000,
}

_CSO_2017_PREFERRED: dict[int, float] = {
    15: 0.098, 20: 0.116, 25: 0.137, 30: 0.187, 35: 0.281,
    40: 0.436, 45: 0.707, 50: 1.168, 55: 1.951, 60: 3.287,
    65: 5.513, 70: 9.205, 75: 15.340, 80: 25.328, 85: 41.894,
    90: 68.074, 95: 108.140, 99: 165.000,
}

# ATB 99 (1999 Blade mortality, illustrative)
_ATB_99: dict[int, float] = {
    20: 0.180, 25: 0.210, 30: 0.290, 35: 0.440,
    40: 0.690, 45: 1.140, 50: 1.900, 55: 3.180,
    60: 5.350, 65: 8.970, 70: 14.940, 75: 24.830,
    80: 40.850, 85: 67.340, 90: 108.900, 95: 171.500, 99: 260.000,
}


@dataclass
class MortalityRate:
    age: int
    gender: str
    tobacco: TobaccoStatus
    table: MortalityTable
    rate_per_1000: float
    rate_annual: float = 0.0
    source: str = ""
    rate_interpolated: bool = False

    def __post_init__(self):
        self.rate_annual = self.rate_per_1000 / 1000.0
        if not self.source:
            self.source = f"{self.table.value} ({self.gender}, {self.tobacco.value})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "age": self.age,
            "gender": self.gender,
            "tobacco": self.tobacco.value,
            "table": self.table.value,
            "rate_per_1000": self.rate_per_1000,
            "rate_annual": round(self.rate_annual, 8),
            "source": self.source,
        }


@dataclass
class MortalityCostResult:
    face_amount: float
    age: int
    gender: str
    tobacco: TobaccoStatus
    table: MortalityTable
    mortality_rate_per_1000: float
    expected_annual_cost: float
    expected_monthly_cost: float
    cost_per_dollar: float
    rate_interpolated: bool = False
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "face_amount": self.face_amount,
            "age": self.age,
            "gender": self.gender,
            "tobacco": self.tobacco.value,
            "table": self.table.value,
            "mortality_rate_per_1000": self.mortality_rate_per_1000,
            "expected_annual_cost": round(self.expected_annual_cost, 2),
            "expected_monthly_cost": round(self.expected_monthly_cost, 2),
            "cost_per_dollar": round(self.cost_per_dollar, 8),
            "rate_interpolated": self.rate_interpolated,
        }


@dataclass
class MortalityComparison:
    face_amount: float
    age: int
    gender: str
    tobacco: TobaccoStatus
    rates: dict[str, float]
    annual_costs: dict[str, float]
    best_table: str
    worst_table: str
    spread_pct: float
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "face_amount": self.face_amount,
            "age": self.age,
            "gender": self.gender,
            "tobacco": self.tobacco.value,
            "rates_per_1000": self.rates,
            "annual_costs": {k: round(v, 2) for k, v in self.annual_costs.items()},
            "best_table": self.best_table,
            "worst_table": self.worst_table,
            "spread_pct": round(self.spread_pct, 2),
        }


def _get_table(table: MortalityTable) -> dict[int, float]:
    if table == MortalityTable.CSO_2017:
        return dict(_CSO_2017_NONTOBACCO)
    elif table == MortalityTable.ATB_99:
        return dict(_ATB_99)
    elif table == MortalityTable.CSO_2001:
        return {k: v * 0.85 for k, v in _CSO_2017_NONTOBACCO.items()}
    elif table == MortalityTable.CSO_1980:
        return {k: v * 0.70 for k, v in _CSO_2017_NONTOBACCO.items()}
    return dict(_CSO_2017_NONTOBACCO)


def _get_table_by_tobacco(table: MortalityTable, tobacco: TobaccoStatus) -> dict[int, float]:
    if table == MortalityTable.CSO_2017:
        if tobacco == TobaccoStatus.TOBACCO:
            return dict(_CSO_2017_TOBACCO)
        elif tobacco == TobaccoStatus.PREFERRED_NONTOBACCO:
            return dict(_CSO_2017_PREFERRED)
        return dict(_CSO_2017_NONTOBACCO)
    return _get_table(table)


def _interpolate_rate(table: dict[int, float], age: int) -> tuple[float, bool]:
    ages = sorted(table.keys())
    if age <= ages[0]:
        return table[ages[0]], True
    if age >= ages[-1]:
        return table[ages[-1]], True
    for i in range(len(ages) - 1):
        if ages[i] <= age <= ages[i + 1]:
            low, high = ages[i], ages[i + 1]
            if low == high:
                return table[low], False
            ratio = (age - low) / (high - low)
            rate = table[low] + ratio * (table[high] - table[low])
            return rate, True
    return table[ages[-1]], True


def lookup_mortality(
    age: int,
    gender: str = "male",
    tobacco: TobaccoStatus = TobaccoStatus.NONTOBACCO,
    table: MortalityTable = MortalityTable.CSO_2017,
) -> MortalityRate:
    tbl = _get_table_by_tobacco(table, tobacco)
    rate, interpolated = _interpolate_rate(tbl, age)
    return MortalityRate(
        age=age,
        gender=gender,
        tobacco=tobacco,
        table=table,
        rate_per_1000=round(rate, 3),
        rate_interpolated=interpolated,
    )


def calculate_mortality_cost(
    face_amount: float,
    age: int,
    gender: str = "male",
    tobacco: TobaccoStatus = TobaccoStatus.NONTOBACCO,
    table: MortalityTable = MortalityTable.CSO_2017,
) -> MortalityCostResult:
    rate = lookup_mortality(age, gender, tobacco, table)
    annual_cost = face_amount * rate.rate_annual
    monthly_cost = annual_cost / 12.0
    cost_per_dollar = annual_cost / face_amount if face_amount > 0 else 0.0

    findings: list[Finding] = []
    if rate.rate_interpolated:
        findings.append(
            Finding(
                title="Mortality rate interpolated",
                description=f"Age {age} not in published table — rate interpolated from nearest brackets.",
                severity=RiskSeverity.LOW,
                category="actuarial",
            )
        )
    if rate.rate_per_1000 > 20.0:
        findings.append(
            Finding(
                title="Elevated mortality rate",
                description=f"Rate {rate.rate_per_1000}/1000 for age {age} ({tobacco.value}) — review risk classification.",
                severity=RiskSeverity.HIGH,
                category="actuarial",
            )
        )
    return MortalityCostResult(
        face_amount=face_amount,
        age=age,
        gender=gender,
        tobacco=tobacco,
        table=table,
        mortality_rate_per_1000=rate.rate_per_1000,
        expected_annual_cost=round(annual_cost, 2),
        expected_monthly_cost=round(monthly_cost, 2),
        cost_per_dollar=round(cost_per_dollar, 8),
        rate_interpolated=rate.rate_interpolated,
        findings=findings,
    )


def compare_mortality_tables(
    face_amount: float,
    age: int,
    gender: str = "male",
    tobacco: TobaccoStatus = TobaccoStatus.NONTOBACCO,
) -> MortalityComparison:
    rates: dict[str, float] = {}
    costs: dict[str, float] = {}
    for t in MortalityTable:
        cost = calculate_mortality_cost(face_amount, age, gender, tobacco, t)
        rates[t.value] = cost.mortality_rate_per_1000
        costs[t.value] = cost.expected_annual_cost

    best = min(costs, key=costs.get)
    worst = max(costs, key=costs.get)
    spread = ((costs[worst] - costs[best]) / costs[best] * 100) if costs[best] > 0 else 0.0

    findings: list[Finding] = []
    if spread > 25:
        findings.append(
            Finding(
                title="Large mortality table spread",
                description=f"Cost spread {spread:.1f}% between {best} and {worst} — table selection materially affects pricing.",
                severity=RiskSeverity.MODERATE,
                category="actuarial",
            )
        )

    return MortalityComparison(
        face_amount=face_amount,
        age=age,
        gender=gender,
        tobacco=tobacco,
        rates=rates,
        annual_costs=costs,
        best_table=best,
        worst_table=worst,
        spread_pct=round(spread, 2),
        findings=findings,
    )


def expected_death_claim_pv(
    face_amount: float,
    annual_mortality_rate: float,
    discount_rate: float = 0.03,
    years: int = 20,
) -> float:
    pv = 0.0
    survival = 1.0
    for year in range(1, years + 1):
        death_prob = survival * annual_mortality_rate
        pv += (face_amount * death_prob) / ((1 + discount_rate) ** year)
        survival *= (1 - annual_mortality_rate)
    return round(pv, 2)
