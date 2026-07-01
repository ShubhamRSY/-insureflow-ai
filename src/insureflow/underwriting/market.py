"""Market Cycle Awareness — Hard Market / Soft Market Adjustments.

Insurance markets cycle between hard (prices up, capacity down) and soft
(prices down, capacity up) phases. This module adjusts appetite filter
thresholds and pricing based on the current market phase, matching the
real-world behavior described in underwriting reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class MarketPhase(str, Enum):
    HARD = "hard"  # Prices rising, capacity tight
    TRANSITIONING_HARD = "transitioning_hard"  # Peaking but easing
    SOFT = "soft"  # Prices falling, capacity abundant
    TRANSITIONING_SOFT = "transitioning_soft"  # Softening further


@dataclass
class MarketCycle:
    phase: MarketPhase = MarketPhase.SOFT
    # Premium adjustment factors (1.0 = baseline)
    property_rate_mod: float = 1.0
    liability_rate_mod: float = 1.0
    workers_comp_rate_mod: float = 1.0
    auto_rate_mod: float = 1.0

    # Appetite tightness (1.0 = normal, >1.0 = more restrictive)
    appetite_tightness: float = 1.0

    # Reinsurance cost impact passed to insureds
    reinsurance_cost_mod: float = 1.0

    # Underlying market metrics
    industry_loss_ratio: float = 0.65
    capacity_available: bool = True
    nuclear_verdict_trend: str = "stable"

    # Narrative
    description: str = ""
    effective_from: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


# Realistic data from late 2024/2025 market reports
_HARD_CYCLE = MarketCycle(
    phase=MarketPhase.HARD,
    property_rate_mod=1.25,  # +25% property rates
    liability_rate_mod=1.15,  # +15% liability rates
    workers_comp_rate_mod=0.95,  # WC still competitive
    auto_rate_mod=1.30,  # +30% auto (nuclear verdicts)
    appetite_tightness=1.4,  # 40% more restrictive
    reinsurance_cost_mod=1.20,  # +20% reinsurance cost pass-through
    industry_loss_ratio=0.73,
    capacity_available=False,
    nuclear_verdict_trend="rising",
    description="Hard market: Rates rising, capacity tightening. Nuclear verdicts driving auto/liability increases. Reinsurance costs up 20%+.",
)

_SOFT_CYCLE = MarketCycle(
    phase=MarketPhase.SOFT,
    property_rate_mod=0.92,  # -8% property
    liability_rate_mod=0.95,  # -5% liability
    workers_comp_rate_mod=0.90,  # -10% WC
    auto_rate_mod=0.96,  # -4% auto
    appetite_tightness=0.80,  # 20% more willing to write
    reinsurance_cost_mod=0.90,  # -10% reinsurance cost
    industry_loss_ratio=0.55,
    capacity_available=True,
    nuclear_verdict_trend="stable",
    description="Soft market: Rates declining 4-8% across lines. Capacity abundant. Reinsurance costs down 10%.",
)

_TRANSITIONING_HARD = MarketCycle(
    phase=MarketPhase.TRANSITIONING_HARD,
    property_rate_mod=1.10,
    liability_rate_mod=1.05,
    workers_comp_rate_mod=0.92,
    auto_rate_mod=1.15,
    appetite_tightness=1.15,
    reinsurance_cost_mod=1.08,
    industry_loss_ratio=0.65,
    capacity_available=True,
    nuclear_verdict_trend="stable",
    description="Transitioning from hard to soft: Rates still elevated but capacity returning. Competition increasing.",
)


class MarketCycleAwareness:
    """Provides market-adjusted appetite thresholds and pricing modifiers."""

    def __init__(self, cycle: Optional[MarketCycle] = None) -> None:
        self._cycle = cycle or _SOFT_CYCLE  # Default to soft (current market)
        self._history: list[MarketCycle] = []

    @property
    def current(self) -> MarketCycle:
        return self._cycle

    def set_cycle(self, cycle: MarketCycle) -> None:
        self._history.append(self._cycle)
        self._cycle = cycle

    def adjust_appetite_threshold(
        self,
        base_threshold: float,
    ) -> float:
        """Tighten or loosen appetite thresholds based on market."""
        return base_threshold * self._cycle.appetite_tightness

    def adjust_premium(
        self,
        base_premium: float,
    ) -> float:
        """Apply market-cycle rate adjustment to premium."""
        # Use the average of line-specific mods as a general adjustment
        avg_rate_mod = (self._cycle.property_rate_mod + self._cycle.liability_rate_mod + self._cycle.workers_comp_rate_mod + self._cycle.auto_rate_mod) / 4.0
        return base_premium * avg_rate_mod * self._cycle.reinsurance_cost_mod

    def market_adjustment_narrative(self) -> dict:
        """Return human-readable market condition summary."""
        return {
            "phase": self._cycle.phase.value,
            "description": self._cycle.description,
            "property_mod": f"{self._cycle.property_rate_mod:.0%}",
            "liability_mod": f"{self._cycle.liability_rate_mod:.0%}",
            "workers_comp_mod": f"{self._cycle.workers_comp_rate_mod:.0%}",
            "auto_mod": f"{self._cycle.auto_rate_mod:.0%}",
            "appetite_tightness": f"{self._cycle.appetite_tightness:.0%}",
            "reinsurance_cost_mod": f"{self._cycle.reinsurance_cost_mod:.0%}",
            "industry_loss_ratio": f"{self._cycle.industry_loss_ratio:.0%}",
            "nuclear_verdict_trend": self._cycle.nuclear_verdict_trend,
        }

    def adjust_loss_ratio_threshold(self, base_lr: float) -> float:
        """In a hard market, accept higher loss ratios; in soft, be stricter."""
        if self._cycle.phase == MarketPhase.HARD:
            return base_lr * 1.2
        elif self._cycle.phase == MarketPhase.TRANSITIONING_HARD:
            return base_lr * 1.1
        elif self._cycle.phase == MarketPhase.SOFT:
            return base_lr * 0.9
        return base_lr

    def adjust_tiv_limit(self, base_limit: float) -> float:
        """In hard market, lower TIV limits; in soft, raise them."""
        if self._cycle.phase == MarketPhase.HARD:
            return base_limit * 0.75
        elif self._cycle.phase == MarketPhase.SOFT:
            return base_limit * 1.15
        return base_limit


_market_cycle: MarketCycleAwareness | None = None


def get_market_cycle() -> MarketCycleAwareness:
    global _market_cycle
    if _market_cycle is None:
        _market_cycle = MarketCycleAwareness(_SOFT_CYCLE)
    return _market_cycle
