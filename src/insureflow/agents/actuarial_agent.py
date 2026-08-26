"""Actuarial agent — mortality table lookups and expected cost calculations.

Runs after extraction to provide actuarial data (mortality rates, expected
death claim costs) that feeds into premium calculation and risk assessment.
"""

from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.actuarial_tables import (
    MortalityComparison,
    MortalityCostResult,
    MortalityTable,
    TobaccoStatus,
    calculate_mortality_cost,
    compare_mortality_tables,
    expected_death_claim_pv,
)
from insureflow.underwriting.personal_lines import extract_life_factors


class ActuarialAgent(BaseAgent):
    agent_type = AgentType.ACTUARIAL
    agent_name = "actuarial_agent"

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        factors = extract_life_factors(bundle)
        age = factors.age or 40
        face = float(factors.face_amount or 500_000)
        tobacco = TobaccoStatus.TOBACCO if factors.smoker else TobaccoStatus.NONTOBACCO
        gender = "male"

        cost = calculate_mortality_cost(face, age, gender, tobacco, MortalityTable.CSO_2017)
        comparison = compare_mortality_tables(face, age, gender, tobacco)
        pv = expected_death_claim_pv(face, cost.mortality_rate_per_1000 / 1000)

        for f in cost.findings:
            self._add_finding(f)
        for f in comparison.findings:
            self._add_finding(f)

        if cost.expected_annual_cost > 0:
            self._add_finding(
                Finding(
                    title=f"Expected mortality cost ${cost.expected_annual_cost:,.2f}/yr",
                    description=(
                        f"CSO 2017 rate {cost.mortality_rate_per_1000}/1000 for age {age} "
                        f"({tobacco.value}). PV of death claim: ${pv:,.2f}."
                    ),
                    severity=RiskSeverity.LOW,
                    category="actuarial",
                )
            )

        if comparison.spread_pct > 20:
            self._add_finding(
                Finding(
                    title=f"Table spread {comparison.spread_pct:.1f}%",
                    description=f"Cost ranges from ${comparison.annual_costs[comparison.best_table]:,.2f} ({comparison.best_table}) to ${comparison.annual_costs[comparison.worst_table]:,.2f} ({comparison.worst_table}).",
                    severity=RiskSeverity.MODERATE,
                    category="actuarial",
                )
            )

        if age >= 70:
            self._add_finding(
                Finding(
                    title=f"Advanced age {age} — elevated mortality",
                    description="Consider guaranteed issue or graded benefit alternatives if standard issue is declined.",
                    severity=RiskSeverity.HIGH,
                    category="actuarial",
                )
            )

        self._actuarial_cost = cost
        self._actuarial_comparison = comparison
        self._pv = pv

    def _build_summary(self) -> str:
        if hasattr(self, "_actuarial_cost"):
            c = self._actuarial_cost
            return (
                f"Actuarial: age {c.age}, rate {c.mortality_rate_per_1000}/1000, "
                f"expected cost ${c.expected_annual_cost:,.2f}/yr, PV ${self._pv:,.2f}"
            )
        return super()._build_summary()
