"""Motor vehicle record (MVR) oracle — commercial auto / fleet drivers.

Makes real HTTP calls to the MVR API. Without a valid API key, queries return
an error — never fake data.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.oracles._live import build_oracle_http, resolve_integration_mode

logger = logging.getLogger(__name__)


@dataclass
class MVRViolation:
    description: str
    points: int = 0
    date: str = ""
    major: bool = False


@dataclass
class MVRResult:
    driver_name: str
    license_state: str = ""
    violations: list[MVRViolation] = field(default_factory=list)
    accidents: int = 0
    suspensions: int = 0
    query_completed: bool = True
    error: str = ""
    synthetic: bool = False
    mode: str = ""

    @property
    def total_points(self) -> int:
        return sum(v.points for v in self.violations)

    @property
    def has_major(self) -> bool:
        return any(v.major for v in self.violations) or self.suspensions > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "driver_name": self.driver_name,
            "license_state": self.license_state,
            "violations": [{"description": v.description, "points": v.points, "date": v.date, "major": v.major} for v in self.violations],
            "accidents": self.accidents,
            "suspensions": self.suspensions,
            "total_points": self.total_points,
            "synthetic": self.synthetic,
            "mode": self.mode,
            "error": self.error,
        }


class MVRClient:
    """Motor vehicle record (MVR) client.

    Makes real HTTP calls to the MVR API.
    Set ORACLE_MODE=auto (default) and provide a real API key for live queries.
    Without a valid API key, queries return an error — never fake data.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://integrations.rytera.ai/oracles/mvr/v1",
        mode: str = "auto",
        query_path: str = "/records",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self.query_path = query_path
        self.http = build_oracle_http(api_key, base_url)

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

    def query_driver(self, driver_name: str, *, license_state: str = "", license_number: str = "") -> MVRResult:
        resolved = self._resolved_mode()
        if resolved == "misconfigured":
            return MVRResult(
                driver_name=driver_name or "unknown",
                license_state=license_state,
                query_completed=False,
                error="MVR requires MVR_API_KEY and MVR_API_URL to be configured",
                mode=resolved,
            )
        return self._call_live(driver_name, license_state, license_number)

    def _call_live(self, driver_name: str, license_state: str, license_number: str) -> MVRResult:
        try:
            resp = self.http.post(
                self.query_path,
                {"driver_name": driver_name, "license_state": license_state, "license_number": license_number},
            )
            if not resp.ok:
                return MVRResult(driver_name=driver_name, query_completed=False, error=f"HTTP {resp.status_code}", mode="live")
            data = resp.json_dict()
            violations = [
                MVRViolation(
                    description=str(v.get("description") or ""),
                    points=int(v.get("points") or 0),
                    date=str(v.get("date") or ""),
                    major=bool(v.get("major")),
                )
                for v in (data.get("violations") or [])
            ]
            return MVRResult(
                driver_name=str(data.get("driver_name") or driver_name),
                license_state=str(data.get("license_state") or license_state),
                violations=violations,
                accidents=int(data.get("accidents") or 0),
                suspensions=int(data.get("suspensions") or 0),
                synthetic=False,
                mode="live",
            )
        except IntegrationHTTPError as exc:
            logger.warning("MVR live query failed: %s", exc)
            return MVRResult(driver_name=driver_name, query_completed=False, error=str(exc), mode="live")


def extract_drivers(text: str) -> list[str]:
    names: list[str] = []
    for m in re.finditer(r"(?:driver|operator)\s*[:=#]\s*([A-Za-z][A-Za-z .'-]{2,50})", text or "", re.I):
        names.append(m.group(1).strip())
    return names[:12]
