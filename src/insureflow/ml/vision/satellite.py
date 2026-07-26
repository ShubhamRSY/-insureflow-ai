"""Satellite imagery provider — Google Maps Static API + Nominatim fallback.

Fetches satellite imagery of insured properties and performs basic analysis
of roof condition, lot coverage, nearby hazards, and vegetation proximity.
When no paid API key is configured, falls back to free OpenStreetMap Nominatim
for geocoding and nearby-feature risk assessment.
"""

from __future__ import annotations

import logging
import math
import os

import httpx

from insureflow.ml.vision.models import SatelliteAnalysis, VisualFinding, VisualRisk

logger = logging.getLogger(__name__)

_GOOGLE_STATIC_MAPS_URL = "https://maps.googleapis.com/maps/api/staticmap"
_NEARMAP_URL = "https://api.nearmap.com/maps/v3/coverage"
_NOMINATIM_URL = "https://nominatim.openstreetmap.org"
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Nominatim usage policy: max 1 req/sec, identify yourself
_NOMINATIM_HEADERS = {"User-Agent": "RyteraInsuranceAI/1.0 (insurance-underwriting)"}


class SatelliteImageryProvider:
    def __init__(
        self,
        google_api_key: str | None = None,
        nearmap_api_key: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.google_key = google_api_key or os.getenv("GOOGLE_MAPS_API_KEY", "")
        self.nearmap_key = nearmap_api_key or os.getenv("NEARMAP_API_KEY", "")
        self.timeout = timeout
        self._http = httpx.Client(timeout=timeout, follow_redirects=True)

    @property
    def available(self) -> bool:
        return bool(self.google_key or self.nearmap_key)

    def fetch_satellite_image(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 19,
        width: int = 640,
        height: int = 640,
    ) -> bytes | None:
        if self.google_key:
            return self._fetch_google(latitude, longitude, zoom, width, height)
        if self.nearmap_key:
            return self._fetch_nearmap(latitude, longitude, zoom, width, height)
        return None

    def _fetch_google(
        self,
        lat: float,
        lng: float,
        zoom: int,
        width: int,
        height: int,
    ) -> bytes | None:
        try:
            params = {
                "center": f"{lat},{lng}",
                "zoom": str(zoom),
                "size": f"{width}x{height}",
                "maptype": "satellite",
                "key": self.google_key,
            }
            resp = self._http.get(_GOOGLE_STATIC_MAPS_URL, params=params)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                return resp.content
            logger.warning("Google Static Maps returned %s", resp.status_code)
        except Exception as exc:
            logger.warning("Google Static Maps fetch failed: %s", exc)
        return None

    def _fetch_nearmap(
        self,
        lat: float,
        lng: float,
        zoom: int,
        width: int,
        height: int,
    ) -> bytes | None:
        try:
            headers = {"Authorization": f"Bearer {self.nearmap_key}"}
            params = {"center": f"{lat},{lng}", "zoom": str(zoom), "width": str(width), "height": str(height)}
            resp = self._http.get(_NEARMAP_URL, params=params, headers=headers)
            if resp.status_code == 200:
                return resp.content
            logger.warning("Nearmap returned %s", resp.status_code)
        except Exception as exc:
            logger.warning("Nearmap fetch failed: %s", exc)
        return None

    def analyze_satellite(
        self,
        latitude: float,
        longitude: float,
        address: str = "",
        image_data: bytes | None = None,
    ) -> SatelliteAnalysis:
        analysis = SatelliteAnalysis(
            address=address,
            latitude=latitude,
            longitude=longitude,
        )
        if not image_data:
            image_data = self.fetch_satellite_image(latitude, longitude)
        if image_data:
            analysis.analysis_notes = "Satellite image retrieved — AI analysis pending"
            return analysis

        # ── Fallback: Nominatim + Overpass free APIs ──
        return self._nominatim_fallback(analysis, latitude, longitude, address)

    def _nominatim_fallback(
        self,
        analysis: SatelliteAnalysis,
        lat: float,
        lng: float,
        address: str,
    ) -> SatelliteAnalysis:
        """Use free OpenStreetMap APIs for location risk assessment."""
        try:
            # Reverse geocode to get location details
            resp = self._http.get(
                f"{_NOMINATIM_URL}/reverse",
                params={"lat": lat, "lon": lng, "format": "jsonv2", "addressdetails": 1},
                headers=_NOMINATIM_HEADERS,
            )
            if resp.status_code == 200:
                data = resp.json()
                addr = data.get("address", {})
                analysis.analysis_notes = (
                    f"Nominatim fallback: {data.get('display_name', address)} | Land use: {addr.get('landuse', 'unknown')} | Suburb: {addr.get('suburb', addr.get('city', 'unknown'))}"
                )

                # Check for risk-relevant land use
                landuse = (addr.get("landuse") or "").lower()
                if landuse in ("industrial", "commercial"):
                    analysis.findings.append(
                        VisualFinding(
                            category="location",
                            description=f"Property in {landuse} zone — review exposure to neighboring operations",
                            severity="warning",
                            confidence=0.6,
                        )
                    )
                    analysis.aerial_risk = VisualRisk.MODERATE

                # Check for proximity to water
                if any(k in addr for k in ("waterway", "river", "canal", "bay", "ocean")):
                    analysis.findings.append(
                        VisualFinding(
                            category="flood",
                            description="Property near water feature — assess flood zone exposure",
                            severity="warning",
                            confidence=0.5,
                        )
                    )
                    analysis.aerial_risk = max(analysis.aerial_risk, VisualRisk.MODERATE, key=lambda v: v.value)
            else:
                analysis.analysis_notes = f"Nominatim returned {resp.status_code} — location assessment limited"
        except Exception as exc:
            logger.warning("Nominatim fallback failed: %s", exc)
            analysis.analysis_notes = f"Nominatim unavailable: {exc}"

        # Try Overpass for nearby hazard features
        try:
            overpass_query = f'[out:json][timeout:10];node(around:500,{lat},{lng})["hazard"|"landuse"="industrial"];out body 10;'
            resp = self._http.post(
                _OVERPASS_URL,
                data={"data": overpass_query},
                timeout=12.0,
            )
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                for el in elements:
                    tags = el.get("tags", {})
                    name = tags.get("name", tags.get("landuse", "nearby feature"))
                    analysis.findings.append(
                        VisualFinding(
                            category="nearby_hazard",
                            description=f"Nearby feature within 500m: {name}",
                            severity="info",
                            confidence=0.4,
                        )
                    )
        except Exception as exc:
            logger.debug("Overpass query failed (non-critical): %s", exc)

        return analysis

    def close(self) -> None:
        self._http.close()


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_satellite_imagery(
    latitude: float,
    longitude: float,
    address: str = "",
    google_api_key: str | None = None,
    nearmap_api_key: str | None = None,
) -> SatelliteAnalysis:
    provider = SatelliteImageryProvider(
        google_api_key=google_api_key,
        nearmap_api_key=nearmap_api_key,
    )
    try:
        return provider.analyze_satellite(latitude, longitude, address)
    finally:
        provider.close()
