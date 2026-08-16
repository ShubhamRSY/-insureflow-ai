"""Morbidity tables — incidence rates for illness / disability, by age and sex.

Morbidity tables track the frequency and duration of illness, injury, and
disability (as mortality tables track death). These power critical-illness and
disability incidence underwriting for health products.
"""

from __future__ import annotations

# Annual incidence per 1,000 exposed lives for a representative disability plan.
# key: sex -> {age: incidence_per_1000}
_DISABILITY_INCIDENCE: dict[str, dict[int, float]] = {
    "male": {
        20: 4.1,
        25: 4.5,
        30: 5.0,
        35: 5.9,
        40: 7.2,
        45: 9.4,
        50: 13.1,
        55: 18.6,
        60: 25.4,
        65: 32.8,
        70: 40.1,
        75: 46.0,
    },
    "female": {
        20: 4.6,
        25: 5.1,
        30: 5.7,
        35: 6.5,
        40: 7.9,
        45: 10.2,
        50: 14.0,
        55: 19.6,
        60: 26.3,
        65: 33.4,
        70: 40.8,
        75: 46.5,
    },
}

# Annual critical-illness incidence per 1,000 exposed lives (CI event-based).
_CI_INCIDENCE: dict[str, dict[int, float]] = {
    "male": {
        20: 0.5,
        25: 0.7,
        30: 1.0,
        35: 1.6,
        40: 2.7,
        45: 4.6,
        50: 7.8,
        55: 12.4,
        60: 18.9,
        65: 27.0,
        70: 36.2,
        75: 44.0,
    },
    "female": {
        20: 0.4,
        25: 0.6,
        30: 0.9,
        35: 1.4,
        40: 2.4,
        45: 4.0,
        50: 6.6,
        55: 10.2,
        60: 15.1,
        65: 21.4,
        70: 28.7,
        75: 35.1,
    },
}

_TABLES = {"disability": _DISABILITY_INCIDENCE, "critical_illness": _CI_INCIDENCE}

# Baseline incidence (per 1,000) the rating factors are normalized against.
_BASELINE = {"disability": 9.4, "critical_illness": 4.6}


def _nearest_age(table: dict[int, float], age: int) -> int:
    age = max(20, min(age, 75))
    if age in table:
        return age
    keys = sorted(table)
    return min(keys, key=lambda k: abs(k - age))


def morbidity_rate(
    *,
    age: int,
    sex: str = "male",
    benefit_type: str = "disability",
) -> float:
    """Annual incidence per 1,000 exposed lives at the given age/sex."""
    tables = _TABLES.get(benefit_type, _DISABILITY_INCIDENCE)
    sex_key = "female" if sex == "female" else "male"
    table = tables.get(sex_key, tables["male"])
    return float(table[_nearest_age(table, int(age))])


def morbidity_rating_factor(
    *,
    age: int,
    sex: str = "male",
    benefit_type: str = "disability",
) -> float:
    """Relative morbidity cost vs the baseline age, for rating load."""
    baseline = _BASELINE.get(benefit_type, _BASELINE["disability"])
    rate = morbidity_rate(age=age, sex=sex, benefit_type=benefit_type)
    if baseline <= 0:
        return 1.0
    return round(rate / baseline, 4)


def available_tables() -> list[str]:
    return list(_TABLES)
