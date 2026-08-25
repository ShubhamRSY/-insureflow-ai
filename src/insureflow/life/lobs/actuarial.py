"""Rule-free actuarial primitives for the dedicated life LOB logic paths.

Pure math on the ``insureflow.life.mortality`` table — no underwriting rules,
no state tables, no product decisions. Each product module calls these with
its OWN explicit constants so every pricing decision stays auditable in the
module that owns it.
"""

from __future__ import annotations

from insureflow.life.mortality import LIMITING_AGE, discount_factor, k_p_x, q_x


def temporary_annuity_due(
    age: int,
    n: int,
    sex: str = "male",
    smoker: bool = False,
    interest_rate: float = 0.04,
) -> float:
    """ä_{x:n̄} — present value of $1/yr payable at the start of each of n years."""
    v = discount_factor(interest_rate)
    return sum((v**k) * k_p_x(age, k, sex, smoker) for k in range(max(n, 0)))


def whole_life_annuity_due_factor(
    age: int,
    sex: str = "male",
    smoker: bool = False,
    interest_rate: float = 0.04,
) -> float:
    """ä_x — lifetime annuity due to the limiting age of the table."""
    n = max(LIMITING_AGE - age, 0)
    return temporary_annuity_due(age, n + 1, sex, smoker, interest_rate)


def term_insurance_nsp(
    age: int,
    n: int,
    sex: str = "male",
    smoker: bool = False,
    interest_rate: float = 0.04,
) -> float:
    """A^1_{x:n̄} per $1 of cover — PV of $1 paid at end of year of death within n."""
    v = discount_factor(interest_rate)
    total = 0.0
    for k in range(max(n, 0)):
        total += (v ** (k + 1)) * k_p_x(age, k, sex, smoker) * q_x(age + k, sex, smoker)
    return total


def pure_endowment_nsp(
    age: int,
    n: int,
    sex: str = "male",
    smoker: bool = False,
    interest_rate: float = 0.04,
) -> float:
    """A_{x:n̄}^{1} (pure endowment) per $1 — v^n × probability of surviving n."""
    v = discount_factor(interest_rate)
    return (v**n) * k_p_x(age, n, sex, smoker)


def endowment_insurance_nsp(
    age: int,
    n: int,
    sex: str = "male",
    smoker: bool = False,
    interest_rate: float = 0.04,
) -> float:
    """A_{x:n̄} per $1 — pays at death within n OR at maturity, whichever first."""
    return term_insurance_nsp(age, n, sex, smoker, interest_rate) + pure_endowment_nsp(age, n, sex, smoker, interest_rate)


def joint_survival_curve(
    age_a: int,
    age_b: int,
    sex_a: str = "male",
    sex_b: str = "female",
    smoker_a: bool = False,
    smoker_b: bool = False,
) -> list[float]:
    """Probability BOTH lives survive k more years (index 0 = 1.0)."""
    curve = [1.0]
    pa = pb = 1.0
    for k in range(max(LIMITING_AGE - max(age_a, age_b), 0)):
        pa *= 1.0 - q_x(age_a + k, sex_a, smoker_a)
        pb *= 1.0 - q_x(age_b + k, sex_b, smoker_b)
        curve.append(pa * pb)
    return curve


def joint_and_survivor_annuity_factor(
    age_primary: int,
    age_spouse: int,
    survivor_pct: float,
    *,
    sex_primary: str = "male",
    sex_spouse: str = "female",
    smoker: bool = False,
    interest_rate: float = 0.04,
) -> float:
    """PV of $1/yr while the PRIMARY lives, then `survivor_pct` while the spouse outlives.

    survivor_pct=1.0 → 100% J&S; 0.5 → 50% continuation.
    Payment in year k = 1 if primary alive, else survivor_pct × P(spouse alive).
    """
    d = discount_factor(interest_rate)
    total = 1.0  # first payment certain
    vp = 1.0
    pp = ps = 1.0
    for k in range(max(LIMITING_AGE - max(age_primary, age_spouse), 0)):
        q_p = q_x(age_primary + k, sex_primary, smoker)
        q_s = q_x(age_spouse + k, sex_spouse, smoker)
        vp *= d
        pp *= 1.0 - q_p
        ps *= 1.0 - q_s
        only_spouse = max(ps - pp * ps, 0.0)  # primary dead, spouse alive
        total += vp * (pp + only_spouse * survivor_pct)
    return total


def certain_and_life_annuity_due(
    age: int,
    certain_years: int,
    sex: str = "male",
    smoker: bool = False,
    interest_rate: float = 0.04,
) -> float:
    """Annuity paying $1/yr for n years CERTAIN, then for life thereafter."""
    v = discount_factor(interest_rate)
    certain = sum(v**k for k in range(max(certain_years, 0)))
    deferred = sum((v**k) * k_p_x(age, k, sex, smoker) for k in range(max(certain_years, 0), max(LIMITING_AGE - age, 0) + 1))
    return certain + deferred
