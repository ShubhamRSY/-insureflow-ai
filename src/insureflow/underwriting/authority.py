"""Delegation of Authority — Underwriter Tier System.

Small carriers have short approval chains but clear limits on who
can bind what. This matches the real-world junior/senior/CUO tiers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AuthorityTier(str, Enum):
    JUNIOR = "junior"  # Simple, small accounts (< $25K premium)
    SENIOR = "senior"  # Complex/high-value (up to $500K)
    CUO = "cuo"  # Chief Underwriting Officer (unlimited)
    MGA = "mga"  # Managing General Agent (delegated)


@dataclass
class BindingAuthority:
    max_premium: float = 0.0  # Maximum annual premium
    max_tiv: float = 0.0  # Maximum total insured value
    max_line_tiv: dict[str, float] = field(default_factory=dict)  # Per-line limits
    requires_co_sign: bool = False  # Needs second signature
    co_sign_threshold_premium: float = 0.0
    allowed_states: list[str] = field(default_factory=list)
    excluded_occupancies: list[str] = field(default_factory=list)
    max_aggregate_exposure: float = 0.0  # Total portfolio exposure this UW can bind


@dataclass
class UnderwriterAuthority:
    username: str
    display_name: str
    tier: AuthorityTier
    binding_authority: BindingAuthority = field(default_factory=BindingAuthority)
    license_number: str = ""
    license_states: list[str] = field(default_factory=list)
    appointed_carriers: list[str] = field(default_factory=list)


# Default binding limits per tier (realistic for small carrier)
_JUNIOR_BASIC = BindingAuthority(
    max_premium=25_000,
    max_tiv=1_000_000,
    requires_co_sign=False,
    max_aggregate_exposure=5_000_000,
)

_SENIOR_STANDARD = BindingAuthority(
    max_premium=250_000,
    max_tiv=10_000_000,
    requires_co_sign=False,
    co_sign_threshold_premium=150_000,
    max_aggregate_exposure=25_000_000,
)

_CUO_UNLIMITED = BindingAuthority(
    max_premium=10_000_000,
    max_tiv=500_000_000,
    requires_co_sign=False,
    max_aggregate_exposure=500_000_000,
)

_MGA_DELEGATED = BindingAuthority(
    max_premium=100_000,
    max_tiv=5_000_000,
    requires_co_sign=False,
    max_aggregate_exposure=20_000_000,
)


class AuthorityMatrix:
    """Manages underwriter authority levels and binding limits."""

    def __init__(self) -> None:
        self._authorities: dict[str, UnderwriterAuthority] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        defaults = [
            UnderwriterAuthority(
                username="junderwood",
                display_name="Jamie Underwood",
                tier=AuthorityTier.JUNIOR,
                binding_authority=_JUNIOR_BASIC,
                license_number="P&C-48291-TX",
                license_states=["TX", "OK"],
            ),
            UnderwriterAuthority(
                username="sfields",
                display_name="Sarah Fields",
                tier=AuthorityTier.SENIOR,
                binding_authority=_SENIOR_STANDARD,
                license_number="P&C-77124-TX",
                license_states=["TX", "OK", "LA", "AR"],
            ),
            UnderwriterAuthority(
                username="mchen",
                display_name="Michael Chen",
                tier=AuthorityTier.CUO,
                binding_authority=_CUO_UNLIMITED,
                license_number="P&C-33901-TX",
                license_states=["TX", "OK", "LA", "AR", "FL", "CA", "NY"],
            ),
            UnderwriterAuthority(
                username="tbroker",
                display_name="Tom Broker",
                tier=AuthorityTier.MGA,
                binding_authority=_MGA_DELEGATED,
                license_number="MGA-55129-TX",
                license_states=["TX"],
            ),
        ]
        for a in defaults:
            self._authorities[a.username] = a

    def get_authority(self, username: str) -> Optional[UnderwriterAuthority]:
        return self._authorities.get(username)

    def set_authority(self, authority: UnderwriterAuthority) -> None:
        self._authorities[authority.username] = authority

    def list_by_tier(self, tier: AuthorityTier) -> list[UnderwriterAuthority]:
        return [a for a in self._authorities.values() if a.tier == tier]

    def list_all(self) -> list[UnderwriterAuthority]:
        return list(self._authorities.values())

    def check_binding_authority(
        self,
        username: str,
        premium: float,
        tiv: float,
        state: str = "",
        occupancy: str = "",
    ) -> tuple[bool, str]:
        """Check if underwriter has authority to bind this risk.

        Returns (approved, reason).
        """
        auth = self._authorities.get(username)
        if not auth:
            return False, f"No authority record for '{username}'"

        ba = auth.binding_authority

        if premium > ba.max_premium:
            if ba.requires_co_sign or premium > ba.co_sign_threshold_premium:
                return False, (f"Premium ${premium:,.0f} exceeds ${ba.max_premium:,.0f} {auth.tier.value} limit for {auth.display_name} — requires co-sign from senior UW/CUO")
            return False, (f"Premium ${premium:,.0f} exceeds ${ba.max_premium:,.0f} {auth.tier.value} binding limit")

        if tiv > ba.max_tiv:
            return False, (f"TIV ${tiv:,.0f} exceeds ${ba.max_tiv:,.0f} {auth.tier.value} binding limit")

        if ba.allowed_states and state and state not in ba.allowed_states:
            return False, f"State '{state}' not in {auth.display_name}'s licensed states"

        if occupancy in ba.excluded_occupancies:
            return False, f"Occupancy '{occupancy}' excluded from authority"

        return True, f"Within {auth.tier.value} authority — approved"


_authority_matrix: AuthorityMatrix | None = None


def get_authority_matrix() -> AuthorityMatrix:
    global _authority_matrix
    if _authority_matrix is None:
        _authority_matrix = AuthorityMatrix()
    return _authority_matrix
