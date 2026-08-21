"""Mortality tables and lookup functions.

Provides q_x (probability of death within one year) for persons aged x,
by gender and smoking status. Uses a simplified US Male/Female table
derived from the 2017 CSO Valuation Basic Table (illustrative purposes).
"""

from __future__ import annotations

# Simplified US CSO 2017 VBT — q_x values by age (ages 0–99).
# Male non-smoker, male smoker, female non-smoker, female smoker.
# These are illustrative; production would load from regulatory JSON.
_MALE_NS: list[float] = [
    0.000680,
    0.000440,
    0.000360,
    0.000310,
    0.000280,
    0.000250,
    0.000230,
    0.000210,
    0.000190,
    0.000170,
    0.000155,
    0.000145,
    0.000140,
    0.000140,
    0.000145,
    0.000155,
    0.000170,
    0.000185,
    0.000200,
    0.000215,
    0.000230,
    0.000250,
    0.000270,
    0.000290,
    0.000310,
    0.000335,
    0.000360,
    0.000390,
    0.000425,
    0.000465,
    0.000510,
    0.000560,
    0.000620,
    0.000690,
    0.000770,
    0.000860,
    0.000965,
    0.001080,
    0.001210,
    0.001360,
    0.001530,
    0.001720,
    0.001940,
    0.002190,
    0.002480,
    0.002810,
    0.003190,
    0.003620,
    0.004110,
    0.004670,
    0.005300,
    0.006020,
    0.006830,
    0.007750,
    0.008790,
    0.009970,
    0.011310,
    0.012840,
    0.014580,
    0.016560,
    0.018820,
    0.021400,
    0.024330,
    0.027650,
    0.031410,
    0.035660,
    0.040450,
    0.045840,
    0.051900,
    0.058700,
    0.066310,
    0.074810,
    0.084280,
    0.094790,
    0.106410,
    0.119210,
    0.133250,
    0.148600,
    0.165330,
    0.183500,
    0.203180,
    0.224430,
    0.247300,
    0.271830,
    0.298060,
    0.326020,
    0.355730,
    0.387190,
    0.420380,
    0.455280,
    0.491840,
    0.530000,
    0.569680,
    0.610800,
    0.653290,
    0.697070,
    0.742040,
    0.788090,
    0.835100,
    0.882910,
    0.931340,
    0.980210,
    1.000000,
]

_FEMALE_NS: list[float] = [
    0.000560,
    0.000370,
    0.000300,
    0.000260,
    0.000230,
    0.000200,
    0.000180,
    0.000165,
    0.000150,
    0.000135,
    0.000125,
    0.000118,
    0.000115,
    0.000115,
    0.000118,
    0.000125,
    0.000135,
    0.000145,
    0.000155,
    0.000168,
    0.000180,
    0.000195,
    0.000210,
    0.000225,
    0.000240,
    0.000260,
    0.000280,
    0.000300,
    0.000325,
    0.000355,
    0.000390,
    0.000430,
    0.000475,
    0.000525,
    0.000585,
    0.000650,
    0.000725,
    0.000810,
    0.000910,
    0.001020,
    0.001150,
    0.001300,
    0.001480,
    0.001680,
    0.001920,
    0.002190,
    0.002510,
    0.002880,
    0.003310,
    0.003810,
    0.004380,
    0.005030,
    0.005770,
    0.006610,
    0.007570,
    0.008660,
    0.009900,
    0.011300,
    0.012890,
    0.014700,
    0.016750,
    0.019060,
    0.021660,
    0.024580,
    0.027850,
    0.031500,
    0.035580,
    0.040130,
    0.045200,
    0.050840,
    0.057100,
    0.064040,
    0.071720,
    0.080200,
    0.089540,
    0.099800,
    0.111040,
    0.123320,
    0.136700,
    0.151240,
    0.166980,
    0.183970,
    0.202250,
    0.221840,
    0.242770,
    0.265060,
    0.288720,
    0.313750,
    0.340140,
    0.367860,
    0.396860,
    0.427100,
    0.458530,
    0.491090,
    0.524710,
    0.559330,
    0.594880,
    0.631290,
    0.668480,
    0.706360,
    0.744840,
    0.783820,
    0.823200,
    0.862880,
    0.902760,
    0.942740,
    0.982720,
    1.000000,
]

# Smoking load factor — smoker q_x = non-smoker q_x × smoking_factor
_SMOKING_FACTOR_MALE = 2.40
_SMOKING_FACTOR_FEMALE = 2.25

# Maximum age in the table
LIMITING_AGE = 99

_TABLES: dict[str, list[float]] = {
    "male_ns": _MALE_NS,
    "female_ns": _FEMALE_NS,
}


def _key(sex: str, smoker: bool) -> str:
    s = "male" if sex.lower().startswith("m") else "female"
    return f"{s}_ns"  # base table is non-smoker


def q_x(age: int, sex: str = "male", smoker: bool = False) -> float:
    """Probability of death within one year for a person aged x."""
    base = _key(sex, smoker)
    table = _TABLES[base]
    age_idx = max(0, min(age, LIMITING_AGE))
    val = table[age_idx] if age_idx < len(table) else table[-1]
    if smoker:
        factor = _SMOKING_FACTOR_MALE if sex.lower().startswith("m") else _SMOKING_FACTOR_FEMALE
        val = min(val * factor, 1.0)
    return round(val, 8)


def p_x(age: int, sex: str = "male", smoker: bool = False) -> float:
    """Probability of surviving one year."""
    return round(1.0 - q_x(age, sex, smoker), 8)


def k_p_x(age: int, k: int, sex: str = "male", smoker: bool = False) -> float:
    """Probability of surviving k years from age x.
    _k p_x = ∏_{j=0}^{k-1} (1 - q_{x+j})
    """
    prob = 1.0
    for j in range(k):
        prob *= p_x(age + j, sex, smoker)
    return round(prob, 8)


def k_q_x(age: int, k: int, sex: str = "male", smoker: bool = False) -> float:
    """Probability of dying in year k+1 given survival to age x+k.
    _k|q_x = _k p_x × q_{x+k}
    """
    return round(k_p_x(age, k, sex, smoker) * q_x(age + k, sex, smoker), 8)


def discount_factor(interest_rate: float) -> float:
    """v = 1 / (1 + i)"""
    return round(1.0 / (1.0 + interest_rate), 10)


def v_k(interest_rate: float, k: int) -> float:
    """v^k = discount factor raised to the k-th power."""
    return round(discount_factor(interest_rate) ** k, 10)
