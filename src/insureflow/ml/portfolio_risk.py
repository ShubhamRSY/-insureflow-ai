"""Portfolio risk modeling — Monte Carlo simulation, VaR, tail risk, concentration analysis."""

from __future__ import annotations

from typing import Any

import numpy as np

from insureflow.ml.models import ModelType, PortfolioRiskResult


class PortfolioRiskModel:
    """Monte Carlo portfolio risk engine — no sklearn training needed."""

    model_type = ModelType.PORTFOLIO_RISK
    model_name = "Portfolio Risk (Monte Carlo)"
    version: str = "1.0.0"

    def __init__(self, n_simulations: int = 10000, seed: int = 42) -> None:
        self.n_simulations = n_simulations
        self.rng = np.random.RandomState(seed)
        self.is_trained = True

    def simulate(
        self,
        exposures: list[float],
        loss_probabilities: list[float],
        severity_means: list[float],
        severity_stds: list[float] | None = None,
        cat_weight: float = 0.15,
        concentration_weights: list[float] | None = None,
    ) -> PortfolioRiskResult:
        """Run Monte Carlo simulation on portfolio."""
        n = len(exposures)
        if n == 0:
            return PortfolioRiskResult(
                total_exposure=0,
                expected_loss=0,
                var_95=0,
                var_99=0,
                tail_var=0,
                cat_contribution=0,
                concentration_index=0,
                diversification_benefit=0,
                scenarios_tested=self.n_simulations,
            )

        exp_arr = np.array(exposures, dtype=np.float64)
        prob_arr = np.array(loss_probabilities, dtype=np.float64).clip(0, 1)
        sev_mean = np.array(severity_means, dtype=np.float64)
        sev_std = np.array(severity_stds if severity_stds else [s * 0.5 for s in severity_means], dtype=np.float64)

        total_exposure = float(exp_arr.sum())
        portfolio_losses = np.zeros(self.n_simulations)
        cat_losses = np.zeros(self.n_simulations)

        for i in range(n):
            freq = self.rng.poisson(max(prob_arr[i] * 10, 0.001), self.n_simulations)
            sev = self.rng.lognormal(
                mean=np.log(max(sev_mean[i], 1)),
                sigma=min(sev_std[i] / max(sev_mean[i], 1), 2.0),
                size=self.n_simulations,
            )
            loss = freq * sev
            if i < n * max(cat_weight, 0.01):
                cat_losses += loss
            portfolio_losses += loss

        expected_loss = float(portfolio_losses.mean())
        var_95 = float(np.percentile(portfolio_losses, 95))
        var_99 = float(np.percentile(portfolio_losses, 99))
        tail_var = float(np.percentile(portfolio_losses, 99.5))

        cat_pct = float(cat_losses.sum() / max(portfolio_losses.sum(), 1))

        hhi = 0.0
        if concentration_weights:
            hhi = sum(w**2 for w in concentration_weights)
        else:
            shares = exp_arr / total_exposure if total_exposure > 0 else np.zeros(n)
            hhi = float(np.sum(shares**2))

        undiversified_loss = float(exp_arr.sum() * prob_arr.mean() * sev_mean.mean())
        diversification_benefit = max(0, 1 - expected_loss / max(undiversified_loss, 1))

        return PortfolioRiskResult(
            total_exposure=round(total_exposure, 2),
            expected_loss=round(expected_loss, 2),
            var_95=round(var_95, 2),
            var_99=round(var_99, 2),
            tail_var=round(tail_var, 2),
            cat_contribution=round(cat_pct, 4),
            concentration_index=round(min(hhi, 1.0), 4),
            diversification_benefit=round(diversification_benefit, 4),
            scenarios_tested=self.n_simulations,
            model_version=self.version,
        )

    def stress_test(
        self,
        exposures: list[float],
        loss_probabilities: list[float],
        severity_means: list[float],
        stress_scenarios: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Run stress test scenarios on the portfolio."""
        if stress_scenarios is None:
            stress_scenarios = [
                {"name": "base", "freq_mult": 1.0, "sev_mult": 1.0},
                {"name": "mild_stress", "freq_mult": 1.5, "sev_mult": 1.3},
                {"name": "severe_stress", "freq_mult": 2.0, "sev_mult": 2.0},
                {"name": "catastrophe", "freq_mult": 3.0, "sev_mult": 3.0},
                {"name": "pandemic", "freq_mult": 4.0, "sev_mult": 1.5},
            ]

        results = []
        for scenario in stress_scenarios:
            stressed_probs = [p * scenario["freq_mult"] for p in loss_probabilities]
            stressed_sev = [s * scenario["sev_mult"] for s in severity_means]
            result = self.simulate(exposures, stressed_probs, stressed_sev)
            results.append(
                {
                    "scenario": scenario["name"],
                    "expected_loss": result.expected_loss,
                    "var_95": result.var_95,
                    "var_99": result.var_99,
                    "tail_var": result.tail_var,
                }
            )
        return results
