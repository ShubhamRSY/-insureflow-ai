"""Connected-car / IoT telematics and cyber-scan oracles.

Simulated on Pilot: never invent a clean driving or security score.
Desk+ live mode compares the questionnaire to the feed. Missing keys fail
closed for that check — they do not paint a green history.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.oracles._live import build_oracle_http, resolve_integration_mode

logger = logging.getLogger(__name__)

_VIN_RE = re.compile(r"\b([A-HJ-NPR-Z0-9]{17})\b", re.I)


@dataclass
class TelematicsResult:
    vin: str = ""
    annual_mileage: float | None = None
    hard_brake_per_1k: float | None = None
    night_fraction: float | None = None
    query_completed: bool = True
    error: str = ""
    synthetic: bool = False
    mode: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "vin": self.vin,
            "annual_mileage": self.annual_mileage,
            "hard_brake_per_1k": self.hard_brake_per_1k,
            "night_fraction": self.night_fraction,
            "synthetic": self.synthetic,
            "mode": self.mode,
            "error": self.error,
        }


@dataclass
class CyberScanResult:
    domain: str = ""
    critical_findings: int | None = None
    mfa_observed: bool | None = None
    query_completed: bool = True
    error: str = ""
    synthetic: bool = False
    mode: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "critical_findings": self.critical_findings,
            "mfa_observed": self.mfa_observed,
            "synthetic": self.synthetic,
            "mode": self.mode,
            "error": self.error,
        }


class TelematicsClient:
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://integrations.rytera.ai/oracles/telematics/v1",
        mode: str = "simulated",
        query_path: str = "/vehicles",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self.query_path = query_path
        self.http = build_oracle_http(api_key, base_url)

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

    def query_vehicle(self, vin: str, *, stated_mileage: float | None = None) -> TelematicsResult:
        resolved = self._resolved_mode()
        vin = (vin or "").strip().upper()
        if resolved == "live":
            return self._call_live(vin, stated_mileage)
        if resolved == "misconfigured":
            return TelematicsResult(vin=vin, query_completed=False, error="Telematics API not configured", mode=resolved)
        return TelematicsResult(vin=vin, query_completed=True, synthetic=True, mode=resolved)

    def _call_live(self, vin: str, stated_mileage: float | None) -> TelematicsResult:
        try:
            payload: dict[str, Any] = {"vin": vin}
            if stated_mileage is not None:
                payload["stated_mileage"] = stated_mileage
            resp = self.http.post(self.query_path, payload)
            if not resp.ok:
                return TelematicsResult(vin=vin, query_completed=False, error=f"HTTP {resp.status_code}", mode="live")
            data = resp.json_dict()
            miles = data.get("annual_mileage")
            brakes = data.get("hard_brake_per_1k")
            night = data.get("night_fraction")
            return TelematicsResult(
                vin=str(data.get("vin") or vin),
                annual_mileage=float(miles) if miles is not None else None,
                hard_brake_per_1k=float(brakes) if brakes is not None else None,
                night_fraction=float(night) if night is not None else None,
                synthetic=False,
                mode="live",
            )
        except IntegrationHTTPError as exc:
            logger.warning("telematics live query failed: %s", exc)
            return TelematicsResult(vin=vin, query_completed=False, error=str(exc), mode="live")


class CyberScanClient:
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://integrations.rytera.ai/oracles/cyber-scan/v1",
        mode: str = "simulated",
        query_path: str = "/scans",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self.query_path = query_path
        self.http = build_oracle_http(api_key, base_url)

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

    def query_domain(self, domain: str) -> CyberScanResult:
        resolved = self._resolved_mode()
        domain = (domain or "").strip().lower()
        if resolved == "live":
            return self._call_live(domain)
        if resolved == "misconfigured":
            return CyberScanResult(domain=domain, query_completed=False, error="Cyber scan API not configured", mode=resolved)
        return CyberScanResult(domain=domain, query_completed=True, synthetic=True, mode=resolved)

    def _call_live(self, domain: str) -> CyberScanResult:
        try:
            resp = self.http.post(self.query_path, {"domain": domain})
            if not resp.ok:
                return CyberScanResult(domain=domain, query_completed=False, error=f"HTTP {resp.status_code}", mode="live")
            data = resp.json_dict()
            crit = data.get("critical_findings")
            mfa = data.get("mfa_observed")
            return CyberScanResult(
                domain=str(data.get("domain") or domain),
                critical_findings=int(crit) if crit is not None else None,
                mfa_observed=bool(mfa) if mfa is not None else None,
                synthetic=False,
                mode="live",
            )
        except IntegrationHTTPError as exc:
            logger.warning("cyber scan live query failed: %s", exc)
            return CyberScanResult(domain=domain, query_completed=False, error=str(exc), mode="live")


def extract_vin(text: str) -> str:
    match = _VIN_RE.search(text or "")
    return match.group(1).upper() if match else ""


def extract_domain(text: str) -> str:
    match = re.search(r"\b([a-z0-9][a-z0-9.-]+\.[a-z]{2,})\b", (text or "").lower())
    if not match:
        return ""
    host = match.group(1)
    if host.endswith((".png", ".jpg", ".pdf", ".html")):
        return ""
    return host
