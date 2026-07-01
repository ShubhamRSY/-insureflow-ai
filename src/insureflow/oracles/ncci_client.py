from __future__ import annotations

import logging
from dataclasses import dataclass, field

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
    """Simulated NCCI (National Council on Compensation Insurance) client.

    In production, this would call the NCCI Experience Rating API.
    Set ORACLE_MODE=live and provide a real API key for production use.
    """

    def __init__(self, api_key: str = "", base_url: str = "https://api.ncci.com/experience/v2", mode: str = "simulated"):
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self._enabled = bool(api_key) or True

    def query_by_fein(self, fein: str, legal_name: str = "") -> NCCIResult:
        if not self._enabled:
            return NCCIResult(employer_name=legal_name, fein=fein, query_completed=False, error="NCCI API not configured")

        if self.mode == "live":
            return self._call_live_api(fein, legal_name)

        name_lower = (legal_name or "").lower()
        mods: list[NCCIExperienceMod] = []

        if "pacific" in name_lower or "marine" in name_lower:
            mods.append(NCCIExperienceMod(
                mod_factor=1.12,
                class_code="8380",
                class_code_description="Marine Cargo Handling",
                expected_losses=120_000.0,
                actual_losses=134_400.0,
                primary_losses=45_000.0,
                excess_losses=89_400.0,
                payroll=3_200_000.0,
            ))
        elif "construction" in name_lower or "veririsk" in name_lower:
            mods.append(NCCIExperienceMod(
                mod_factor=1.35,
                class_code="5221",
                class_code_description="Concrete or Cement Work",
                expected_losses=180_000.0,
                actual_losses=243_000.0,
                primary_losses=68_000.0,
                excess_losses=175_000.0,
                payroll=4_500_000.0,
            ))
        elif "northwind" in name_lower:
            mods.append(NCCIExperienceMod(
                mod_factor=0.88,
                class_code="8810",
                class_code_description="Clerical Office",
                expected_losses=45_000.0,
                actual_losses=39_600.0,
                primary_losses=12_000.0,
                excess_losses=27_600.0,
                payroll=1_800_000.0,
            ))
        else:
            mods.append(NCCIExperienceMod(
                mod_factor=1.00,
                class_code="5555",
                class_code_description="General Classification",
                expected_losses=50_000.0,
                actual_losses=50_000.0,
                primary_losses=15_000.0,
                excess_losses=35_000.0,
                payroll=1_000_000.0,
            ))

        return NCCIResult(
            employer_name=legal_name or fein,
            fein=fein,
            experience_mods=mods,
            total_expected_losses=sum(m.expected_losses for m in mods),
            total_actual_losses=sum(m.actual_losses for m in mods),
        )

    def _call_live_api(self, fein: str, legal_name: str) -> NCCIResult:
        return NCCIResult(
            employer_name=legal_name or fein,
            fein=fein,
            query_completed=True,
            error="Live NCCI adapter not yet implemented — set ORACLE_MODE=simulated",
        )
