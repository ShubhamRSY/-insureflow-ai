from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class PortfolioPolicy(BaseModel):
    """A single policy in the carrier's portfolio for concentration analysis."""
    policy_id: str
    bundle_id: str
    org_id: str = "default"
    insured_name: str = ""
    naics_code: str = ""
    state: str = ""
    zip_code: str = ""
    tiv: float = 0.0
    premium: float = 0.0
    occupancy_type: str = ""
    construction_type: str = ""
    written_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    is_active: bool = True

    @property
    def geographic_region(self) -> str:
        return self.state if self.state else "unknown"

    @property
    def industry_code(self) -> str:
        return self.naics_code[:2] if self.naics_code else "unknown"


class PortfolioConcentrationSummary(BaseModel):
    """Concentration analysis result for a new submission."""
    bundle_id: str
    org_id: str

    existing_policy_count: int = 0
    existing_tiv_total: float = 0.0

    same_state_policy_count: int = 0
    same_state_tiv_total: float = 0.0
    same_state_pct_of_portfolio: float = 0.0

    same_naics2_policy_count: int = 0
    same_naics2_tiv_total: float = 0.0
    same_naics2_pct_of_portfolio: float = 0.0

    concentration_warnings: list[str] = Field(default_factory=list)
    concentration_score: float = 0.0  # 0.0 = no concern, 1.0 = critical

    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class PortfolioStore:
    """In-memory store tracking portfolio policies for concentration analysis.

    In production, this queries the carrier's policy administration database.
    """

    def __init__(self) -> None:
        self._policies: dict[str, PortfolioPolicy] = {}
        self._load_demo_seed()

    def _load_demo_seed(self) -> None:
        seeds = [
            PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}", bundle_id="seed-001",
                insured_name="Bayfront Retail LLC", naics_code="452210",
                state="FL", zip_code="33101", tiv=4_500_000, premium=22_500,
                occupancy_type="retail",
            ),
            PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}", bundle_id="seed-002",
                insured_name="Suncoast Office Park", naics_code="531120",
                state="FL", zip_code="33139", tiv=8_200_000, premium=41_000,
                occupancy_type="office",
            ),
            PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}", bundle_id="seed-003",
                insured_name="Texas Warehousing Inc", naics_code="493110",
                state="TX", zip_code="77001", tiv=12_000_000, premium=60_000,
                occupancy_type="warehouse",
            ),
            PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}", bundle_id="seed-004",
                insured_name="Pacific Marine Services", naics_code="488320",
                state="CA", zip_code="90001", tiv=3_200_000, premium=16_000,
                occupancy_type="marine",
            ),
            PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}", bundle_id="seed-005",
                insured_name="Midwest Manufacturing Co", naics_code="332710",
                state="IL", zip_code="60601", tiv=6_800_000, premium=34_000,
                occupancy_type="manufacturing",
            ),
            PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}", bundle_id="seed-006",
                insured_name="NYC Commercial Properties", naics_code="531120",
                state="NY", zip_code="10001", tiv=15_000_000, premium=75_000,
                occupancy_type="office",
            ),
            PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}", bundle_id="seed-007",
                insured_name="Georgia Logistics Corp", naics_code="484110",
                state="GA", zip_code="30301", tiv=5_500_000, premium=27_500,
                occupancy_type="transportation",
            ),
            PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}", bundle_id="seed-008",
                insured_name="SoCal Restaurant Group", naics_code="722511",
                state="CA", zip_code="90210", tiv=1_200_000, premium=6_000,
                occupancy_type="restaurant",
            ),
            PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}", bundle_id="seed-009",
                insured_name="Texas Healthcare Partners", naics_code="622110",
                state="TX", zip_code="75201", tiv=20_000_000, premium=100_000,
                occupancy_type="healthcare",
            ),
            PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}", bundle_id="seed-010",
                insured_name="Florida Hotel Group", naics_code="721110",
                state="FL", zip_code="33101", tiv=25_000_000, premium=125_000,
                occupancy_type="lodging",
            ),
        ]
        for p in seeds:
            self._policies[p.policy_id] = p

    def add_policy(self, policy: PortfolioPolicy) -> None:
        self._policies[policy.policy_id] = policy

    def list_policies(self, org_id: str = "default") -> list[PortfolioPolicy]:
        return [p for p in self._policies.values() if p.org_id == org_id and p.is_active]

    def get_by_state(self, state: str, org_id: str = "default") -> list[PortfolioPolicy]:
        return [p for p in self._policies.values() if p.state == state and p.org_id == org_id and p.is_active]

    def get_by_naics2(self, naics2: str, org_id: str = "default") -> list[PortfolioPolicy]:
        return [p for p in self._policies.values() if p.naics_code.startswith(naics2) and p.org_id == org_id and p.is_active]

    def analyze_concentration(
        self,
        state: str,
        naics_code: str,
        new_tiv: float,
        org_id: str = "default",
    ) -> PortfolioConcentrationSummary:
        all_policies = self.list_policies(org_id)
        total_tiv = sum(p.tiv for p in all_policies)
        total_count = len(all_policies)

        same_state = self.get_by_state(state, org_id)
        same_state_tiv = sum(p.tiv for p in same_state)
        same_state_count = len(same_state)

        naics2 = naics_code[:2] if naics_code else ""
        same_naics = self.get_by_naics2(naics2, org_id) if naics2 else []
        same_naics_tiv = sum(p.tiv for p in same_naics)
        same_naics_count = len(same_naics)

        warnings: list[str] = []
        score = 0.0

        new_combined_tiv = total_tiv + new_tiv
        new_state_tiv = same_state_tiv + new_tiv
        new_naics_tiv = same_naics_tiv + new_tiv

        state_pct = (new_state_tiv / new_combined_tiv * 100) if new_combined_tiv > 0 else 0
        naics_pct = (new_naics_tiv / new_combined_tiv * 100) if new_combined_tiv > 0 else 0

        if state_pct > 40:
            warnings.append(
                f"Geographic concentration: {state} would represent {state_pct:.0f}% "
                f"of portfolio TIV (threshold: 40%) — increased CAT tail risk"
            )
            score += 0.4
        elif state_pct > 30:
            warnings.append(
                f"Geographic concentration: {state} would represent {state_pct:.0f}% "
                f"of portfolio TIV — monitor concentration"
            )
            score += 0.2

        if naics_pct > 35:
            warnings.append(
                f"Industry concentration: NAICS {naics2} would represent {naics_pct:.0f}% "
                f"of portfolio TIV (threshold: 35%) — sector downturn risk"
            )
            score += 0.3
        elif naics_pct > 25:
            warnings.append(
                f"Industry concentration: NAICS {naics2} would represent {naics_pct:.0f}% "
                f"of portfolio TIV — monitor industry exposure"
            )
            score += 0.15

        if new_tiv > 25_000_000:
            warnings.append(
                f"Single-risk TIV ${new_tiv:,.0f} exceeds $25M — facultative reinsurance recommended"
            )
            score += 0.2

        combined_state_and_naics = len([p for p in same_state if p.naics_code.startswith(naics2) and naics2])
        if combined_state_and_naics >= 2 and state_pct > 20 and naics_pct > 20:
            warnings.append(
                f"Double concentration: {combined_state_and_naics + 1} policies in {state} "
                f"with NAICS {naics2} — geographic AND industry overlap"
            )
            score += 0.3

        if total_count == 0 and new_tiv > 10_000_000:
            warnings.append("First policy in portfolio with TIV > $10M — no diversification baseline")
            score += 0.1

        score = min(1.0, score)

        return PortfolioConcentrationSummary(
            bundle_id="",
            org_id=org_id,
            existing_policy_count=total_count,
            existing_tiv_total=total_tiv,
            same_state_policy_count=same_state_count,
            same_state_tiv_total=same_state_tiv,
            same_state_pct_of_portfolio=round(state_pct, 2),
            same_naics2_policy_count=same_naics_count,
            same_naics2_tiv_total=same_naics_tiv,
            same_naics2_pct_of_portfolio=round(naics_pct, 2),
            concentration_warnings=warnings,
            concentration_score=round(score, 2),
        )


# Module-level singleton
_portfolio_store: PortfolioStore | None = None


def get_portfolio_store() -> PortfolioStore:
    global _portfolio_store
    if _portfolio_store is None:
        _portfolio_store = PortfolioStore()
    return _portfolio_store
