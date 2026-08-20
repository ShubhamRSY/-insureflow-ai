from __future__ import annotations

import logging
from dataclasses import dataclass, field

from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.integrations.parsers import parse_ncci_response
from insureflow.oracles._live import build_oracle_http, resolve_integration_mode

logger = logging.getLogger(__name__)


@dataclass
class NCCIExperienceMod:
    """Workers' compensation experience modification factor from NCCI."""

    mod_factor: float
    class_code: str
    class_code_description: str = ""
    expected_losses: float = 0.0
    actual_losses: float = 0.0
    primary_losses: float = 0.0
    excess_losses: float = 0.0
    payroll: float = 0.0
    rating_period_years: int = 3

    @property
    def is_debit_mod(self) -> bool:
        return self.mod_factor > 1.0

    @property
    def is_credit_mod(self) -> bool:
        return self.mod_factor < 1.0

    @property
    def risk_band(self) -> str:
        if self.mod_factor >= 1.5:
            return "critical"
        if self.mod_factor >= 1.25:
            return "high"
        if self.mod_factor >= 1.0:
            return "moderate"
        return "low"


@dataclass
class NCCIResult:
    employer_name: str
    fein: str
    experience_mods: list[NCCIExperienceMod] = field(default_factory=list)
    total_expected_losses: float = 0.0
    total_actual_losses: float = 0.0
    query_completed: bool = True
    error: str = ""
    mode: str = ""

    @property
    def worst_mod(self) -> NCCIExperienceMod | None:
        return max(self.experience_mods, key=lambda m: m.mod_factor) if self.experience_mods else None

    @property
    def summary(self) -> str:
        if self.error:
            return f"NCCI query failed: {self.error}"
        if not self.experience_mods:
            return f"NCCI: No experience mod data for {self.employer_name}"
        parts = []
        for mod in self.experience_mods:
            parts.append(f"Class {mod.class_code}: mod {mod.mod_factor:.3f} ({mod.risk_band})")
        return " | ".join(parts)


class NCCIClient:
    """NCCI (National Council on Compensation Insurance) client.

    Makes real HTTP calls to the NCCI Experience Rating API.
    Set ORACLE_MODE=auto (default) and provide a real API key for live queries.
    Without a valid API key, queries return an error — never fake data.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.ncci.com/experience/v2",
        mode: str = "auto",
        query_path: str = "/experience",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self.query_path = query_path
        self.http = build_oracle_http(api_key, base_url)
        self._enabled = True

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

    def query_by_fein(self, fein: str, legal_name: str = "") -> NCCIResult:
        if not self._enabled:
            return NCCIResult(
                employer_name=legal_name,
                fein=fein,
                query_completed=False,
                error="NCCI API not configured",
            )

        resolved = self._resolved_mode()
        if resolved == "misconfigured":
            return NCCIResult(
                employer_name=legal_name,
                fein=fein,
                query_completed=False,
                error="NCCI requires NCCI_API_KEY or VERISK_API_KEY and NCCI_API_URL to be configured",
            )

        return self._call_live_api(fein, legal_name)

    def _call_live_api(self, fein: str, legal_name: str) -> NCCIResult:
        try:
            resp = self.http.post(self.query_path, {"fein": fein, "legal_name": legal_name})
            if not resp.ok:
                return NCCIResult(
                    employer_name=legal_name or fein,
                    fein=fein,
                    query_completed=False,
                    error=f"NCCI API HTTP {resp.status_code}",
                )
            parsed = parse_ncci_response(resp.json_dict())
            mods = [
                NCCIExperienceMod(
                    mod_factor=float(m.get("mod_factor", 1.0)),
                    class_code=str(m.get("class_code", "")),
                    class_code_description=str(m.get("class_code_description", "")),
                    expected_losses=float(m.get("expected_losses", 0)),
                    actual_losses=float(m.get("actual_losses", 0)),
                    primary_losses=float(m.get("primary_losses", 0)),
                    excess_losses=float(m.get("excess_losses", 0)),
                    payroll=float(m.get("payroll", 0)),
                )
                for m in parsed.get("experience_mods", [])
            ]
            return NCCIResult(
                employer_name=legal_name or fein,
                fein=fein,
                experience_mods=mods,
                total_expected_losses=float(parsed.get("total_expected_losses", 0)),
                total_actual_losses=float(parsed.get("total_actual_losses", 0)),
            )
        except IntegrationHTTPError as exc:
            logger.exception("NCCI live query failed")
            return NCCIResult(
                employer_name=legal_name or fein,
                fein=fein,
                query_completed=False,
                error=str(exc),
            )
