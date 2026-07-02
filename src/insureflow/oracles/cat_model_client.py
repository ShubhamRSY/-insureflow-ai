from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CATExposureResult:
    """Catastrophe risk assessment for a single location."""

    address: str
    city: str
    state: str
    zip_code: str

    hurricane_risk_score: float = 0.0
    earthquake_risk_score: float = 0.0
    wildfire_risk_score: float = 0.0
    flood_risk_score: float = 0.0
    combined_cat_score: float = 0.0

    in_coastal_zone: bool = False
    in_wildfire_zone: bool = False
    in_flood_plain: bool = False

    estimated_aal: float = 0.0
    estimated_pml_100yr: float = 0.0
    estimated_pml_250yr: float = 0.0

    @property
    def max_threat(self) -> str:
        scores = {
            "hurricane": self.hurricane_risk_score,
            "earthquake": self.earthquake_risk_score,
            "wildfire": self.wildfire_risk_score,
            "flood": self.flood_risk_score,
        }
        return max(scores, key=lambda k: scores[k])

    @property
    def risk_band(self) -> str:
        if self.combined_cat_score >= 0.7:
            return "critical"
        if self.combined_cat_score >= 0.4:
            return "high"
        if self.combined_cat_score >= 0.2:
            return "moderate"
        return "low"


@dataclass
class CATModelResult:
    exposures: list[CATExposureResult] = field(default_factory=list)
    portfolio_aggregate_aal: float = 0.0
    portfolio_aggregate_pml_100yr: float = 0.0
    portfolio_aggregate_pml_250yr: float = 0.0
    query_completed: bool = True
    error: str = ""

    @property
    def worst_exposure(self) -> CATExposureResult | None:
        return max(self.exposures, key=lambda e: e.combined_cat_score) if self.exposures else None

    @property
    def summary(self) -> str:
        if self.error:
            return f"CAT model query failed: {self.error}"
        parts = [
            f"{len(self.exposures)} location(s) modeled",
        ]
        if self.worst_exposure:
            we = self.worst_exposure
            parts.append(f"Worst: {we.city}, {we.state} ({we.max_threat}: {we.combined_cat_score:.0%})")
            parts.append(f"PML 100yr: ${self.portfolio_aggregate_pml_100yr:,.0f}")
        return " | ".join(parts)


class CatastropheModelClient:
    """Simulated catastrophe risk modeling client.

    In production, this would integrate with Moody's RMS, Verisk AIR, or similar.
    Returns deterministic mock CAT risk scores based on location geography.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.verisk.com/cat/v1",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self._enabled = bool(api_key) or True

    def model_location(
        self,
        address: str,
        city: str,
        state: str,
        zip_code: str,
        tiv: float = 1_000_000.0,
    ) -> CATExposureResult:
        if not self._enabled:
            return CATExposureResult(
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                query_completed=False,
            )

        state_upper = (state or "").upper()
        zip_str = (zip_code or "").strip()

        # Deterministic risk scoring based on geography
        hurricane_risk = 0.0
        earthquake_risk = 0.0
        wildfire_risk = 0.0
        flood_risk = 0.0
        in_coastal = False
        in_wildfire = False
        in_flood_plain = False

        if state_upper == "FL":
            hurricane_risk = 0.85
            earthquake_risk = 0.02
            flood_risk = 0.60
            wildfire_risk = 0.05
            in_coastal = True
            in_flood_plain = True
        elif state_upper == "TX":
            hurricane_risk = 0.55
            earthquake_risk = 0.03
            flood_risk = 0.50
            wildfire_risk = 0.15
            in_flood_plain = True
            try:
                zip_int = int(zip_str[:5]) if zip_str else 0
                if 77500 <= zip_int <= 78500:
                    in_coastal = True
            except ValueError:
                pass
        elif state_upper == "CA":
            hurricane_risk = 0.05
            earthquake_risk = 0.80
            flood_risk = 0.20
            wildfire_risk = 0.75
            in_wildfire = True
        elif state_upper == "LA":
            hurricane_risk = 0.75
            earthquake_risk = 0.02
            flood_risk = 0.70
            wildfire_risk = 0.05
            in_coastal = True
            in_flood_plain = True
        elif state_upper in ("NY", "NJ", "CT"):
            hurricane_risk = 0.35
            earthquake_risk = 0.05
            flood_risk = 0.25
            wildfire_risk = 0.03
        elif state_upper in ("OK", "KS", "NE", "IA"):
            hurricane_risk = 0.02
            earthquake_risk = 0.05
            flood_risk = 0.30
            wildfire_risk = 0.10
        else:
            hurricane_risk = 0.05
            earthquake_risk = 0.03
            flood_risk = 0.10
            wildfire_risk = 0.05

        combined = hurricane_risk * 0.30 + earthquake_risk * 0.25 + flood_risk * 0.25 + wildfire_risk * 0.20

        aal = tiv * combined * 0.005
        pml_100yr = tiv * combined * 0.15
        pml_250yr = tiv * combined * 0.35

        return CATExposureResult(
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            hurricane_risk_score=hurricane_risk,
            earthquake_risk_score=earthquake_risk,
            wildfire_risk_score=wildfire_risk,
            flood_risk_score=flood_risk,
            combined_cat_score=round(combined, 4),
            in_coastal_zone=in_coastal,
            in_wildfire_zone=in_wildfire,
            in_flood_plain=in_flood_plain,
            estimated_aal=round(aal, 2),
            estimated_pml_100yr=round(pml_100yr, 2),
            estimated_pml_250yr=round(pml_250yr, 2),
        )

    def model_submission(
        self,
        locations: list[dict[str, Any]],
        total_tiv: float = 1_000_000.0,
    ) -> CATModelResult:
        results: list[CATExposureResult] = []
        for loc in locations:
            tiv = ((loc.get("building_value") or 0) + (loc.get("contents_value") or 0) + (loc.get("bi_value") or 0)) or total_tiv / max(len(locations), 1)
            result = self.model_location(
                address=loc.get("address", ""),
                city=loc.get("city", ""),
                state=loc.get("state", ""),
                zip_code=loc.get("zip_code", ""),
                tiv=tiv,
            )
            results.append(result)

        return CATModelResult(
            exposures=results,
            portfolio_aggregate_aal=round(sum(r.estimated_aal for r in results), 2),
            portfolio_aggregate_pml_100yr=round(sum(r.estimated_pml_100yr for r in results), 2),
            portfolio_aggregate_pml_250yr=round(sum(r.estimated_pml_250yr for r in results), 2),
        )
