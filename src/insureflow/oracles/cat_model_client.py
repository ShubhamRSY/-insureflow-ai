from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.integrations.parsers import parse_cat_response
from insureflow.oracles._live import build_oracle_http, resolve_integration_mode

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
    mode: str = ""

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
    """Catastrophe risk modeling client.

    Makes real HTTP calls to the CAT model API (Moody's RMS, Verisk AIR, etc.).
    Set ORACLE_MODE=auto (default) and provide a real API key for live queries.
    Without a valid API key, queries return an error — never fake data.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.verisk.com/cat/v1",
        mode: str = "auto",
        query_path: str = "/model",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self.query_path = query_path
        self.http = build_oracle_http(api_key, base_url)
        self._enabled = True

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

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
            )

        resolved = self._resolved_mode()
        if resolved == "misconfigured":
            return CATExposureResult(
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
            )

        return (
            self._call_live_model(
                [
                    {
                        "address": address,
                        "city": city,
                        "state": state,
                        "zip_code": zip_code,
                        "building_value": tiv,
                        "contents_value": 0,
                        "bi_value": 0,
                    }
                ],
                tiv,
            ).exposures[0]
            if self._call_live_model(
                [
                    {
                        "address": address,
                        "city": city,
                        "state": state,
                        "zip_code": zip_code,
                        "building_value": tiv,
                        "contents_value": 0,
                        "bi_value": 0,
                    }
                ],
                tiv,
            ).exposures
            else CATExposureResult(
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
            )
        )

    def model_submission(
        self,
        locations: list[dict[str, Any]],
        total_tiv: float = 1_000_000.0,
    ) -> CATModelResult:
        resolved = self._resolved_mode()
        if resolved == "misconfigured":
            return CATModelResult(query_completed=False, error="CAT model requires CAT_API_KEY and CAT_API_URL to be configured")

        return self._call_live_model(locations, total_tiv)

    def _call_live_model(self, locations: list[dict[str, Any]], total_tiv: float) -> CATModelResult:
        try:
            resp = self.http.post(self.query_path, {"locations": locations, "total_tiv": total_tiv})
            if not resp.ok:
                return CATModelResult(query_completed=False, error=f"CAT API HTTP {resp.status_code}")
            parsed = parse_cat_response(resp.json_dict())
            exposures: list[CATExposureResult] = []
            for raw in parsed.get("exposures", []):
                exposures.append(
                    CATExposureResult(
                        address=str(raw.get("address", "")),
                        city=str(raw.get("city", "")),
                        state=str(raw.get("state", "")),
                        zip_code=str(raw.get("zip_code", "")),
                        hurricane_risk_score=float(raw.get("hurricane_risk_score", 0)),
                        earthquake_risk_score=float(raw.get("earthquake_risk_score", 0)),
                        wildfire_risk_score=float(raw.get("wildfire_risk_score", 0)),
                        flood_risk_score=float(raw.get("flood_risk_score", 0)),
                        combined_cat_score=float(raw.get("combined_cat_score", 0)),
                        in_coastal_zone=bool(raw.get("in_coastal_zone")),
                        in_wildfire_zone=bool(raw.get("in_wildfire_zone")),
                        in_flood_plain=bool(raw.get("in_flood_plain")),
                        estimated_aal=float(raw.get("estimated_aal", 0)),
                        estimated_pml_100yr=float(raw.get("estimated_pml_100yr", 0)),
                        estimated_pml_250yr=float(raw.get("estimated_pml_250yr", 0)),
                    )
                )
            return CATModelResult(
                exposures=exposures,
                portfolio_aggregate_aal=float(parsed.get("portfolio_aggregate_aal", sum(e.estimated_aal for e in exposures))),
                portfolio_aggregate_pml_100yr=float(parsed.get("portfolio_aggregate_pml_100yr", sum(e.estimated_pml_100yr for e in exposures))),
                portfolio_aggregate_pml_250yr=float(parsed.get("portfolio_aggregate_pml_250yr", sum(e.estimated_pml_250yr for e in exposures))),
            )
        except IntegrationHTTPError as exc:
            logger.exception("CAT live model failed")
            return CATModelResult(query_completed=False, error=str(exc))
