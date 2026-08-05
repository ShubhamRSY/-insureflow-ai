"""Delegation of Authority — Underwriter Tier System.

Small carriers have short approval chains but clear limits on who
can bind what. This matches the real-world junior/senior/CUO tiers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

AUTHORITY_NS = "authority"


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


def _binding_to_dict(ba: BindingAuthority) -> dict[str, Any]:
    return {
        "max_premium": ba.max_premium,
        "max_tiv": ba.max_tiv,
        "max_line_tiv": ba.max_line_tiv,
        "requires_co_sign": ba.requires_co_sign,
        "co_sign_threshold_premium": ba.co_sign_threshold_premium,
        "allowed_states": ba.allowed_states,
        "excluded_occupancies": ba.excluded_occupancies,
        "max_aggregate_exposure": ba.max_aggregate_exposure,
    }


def _binding_from_dict(data: dict[str, Any]) -> BindingAuthority:
    return BindingAuthority(
        max_premium=data.get("max_premium", 0.0),
        max_tiv=data.get("max_tiv", 0.0),
        max_line_tiv=data.get("max_line_tiv", {}),
        requires_co_sign=data.get("requires_co_sign", False),
        co_sign_threshold_premium=data.get("co_sign_threshold_premium", 0.0),
        allowed_states=data.get("allowed_states", []),
        excluded_occupancies=data.get("excluded_occupancies", []),
        max_aggregate_exposure=data.get("max_aggregate_exposure", 0.0),
    )


def _authority_to_dict(a: UnderwriterAuthority) -> dict[str, Any]:
    return {
        "username": a.username,
        "display_name": a.display_name,
        "tier": a.tier.value,
        "license_number": a.license_number,
        "license_states": a.license_states,
        "appointed_carriers": a.appointed_carriers,
        "binding_authority": _binding_to_dict(a.binding_authority),
    }


def _authority_from_dict(data: dict[str, Any]) -> UnderwriterAuthority:
    return UnderwriterAuthority(
        username=data["username"],
        display_name=data["display_name"],
        tier=AuthorityTier(data["tier"]),
        license_number=data.get("license_number", ""),
        license_states=data.get("license_states", []),
        appointed_carriers=data.get("appointed_carriers", []),
        binding_authority=_binding_from_dict(data.get("binding_authority") or {}),
    )


class AuthorityVerdict(str, Enum):
    APPROVED = "approved"
    NEEDS_CO_SIGN = "needs_co_sign"
    DENIED = "denied"


class AuthorityMatrix:
    """Manages underwriter authority levels and binding limits.

    Records are persisted per-org via the durable job store so admin edits
    (add / update / delete) survive restarts. ``_authorities`` is a per-org
    cache refreshed from the store on every read.
    """

    def __init__(self) -> None:
        self._authorities: dict[str, UnderwriterAuthority] = {}
        self._cached_org: str | None = None

    def _store(self) -> Any:
        from insureflow.storage.job_store import get_job_store

        return get_job_store()

    def _seed_into(self, target: dict[str, UnderwriterAuthority]) -> None:
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
            target[a.username] = a

    def _ensure_loaded(self, org_id: str) -> None:
        """Refresh the in-memory cache from the durable store for this org."""
        if self._cached_org == org_id:
            return
        cached: dict[str, UnderwriterAuthority] = {}
        self._seed_into(cached)
        raw = self._store().get(AUTHORITY_NS, "matrix", org_id=org_id)
        if raw:
            for rec in raw.get("authorities", []):
                try:
                    a = _authority_from_dict(rec)
                except (KeyError, ValueError):
                    continue
                cached[a.username] = a
        self._authorities = cached
        self._cached_org = org_id

    def _persist(self, org_id: str) -> None:
        data = {"authorities": [_authority_to_dict(a) for a in self._authorities.values()]}
        self._store().set(AUTHORITY_NS, "matrix", data, org_id=org_id)

    def get_authority(self, username: str, org_id: str = "default") -> Optional[UnderwriterAuthority]:
        self._ensure_loaded(org_id)
        return self._authorities.get(username)

    def set_authority(self, authority: UnderwriterAuthority, org_id: str = "default") -> None:
        self._ensure_loaded(org_id)
        self._authorities[authority.username] = authority

    def upsert(self, authority: UnderwriterAuthority, org_id: str = "default") -> UnderwriterAuthority:
        """Add or update an authority record (admin RBAC) and persist it."""
        self._ensure_loaded(org_id)
        self._authorities[authority.username] = authority
        self._persist(org_id)
        return authority

    def remove(self, username: str, org_id: str = "default") -> bool:
        """Delete an authority record (admin RBAC) and persist it."""
        self._ensure_loaded(org_id)
        if username not in self._authorities:
            return False
        del self._authorities[username]
        self._persist(org_id)
        return True

    def list_by_tier(self, tier: AuthorityTier, org_id: str = "default") -> list[UnderwriterAuthority]:
        self._ensure_loaded(org_id)
        return [a for a in self._authorities.values() if a.tier == tier]

    def list_all(self, org_id: str = "default") -> list[UnderwriterAuthority]:
        self._ensure_loaded(org_id)
        return list(self._authorities.values())

    def evaluate_binding_authority(
        self,
        username: str,
        premium: float,
        tiv: float,
        state: str = "",
        occupancy: str = "",
        org_id: str = "default",
    ) -> tuple[AuthorityVerdict, str]:
        """Evaluate bind authority including co-sign threshold.

        Returns (verdict, reason) where verdict is approved | needs_co_sign | denied.
        """
        self._ensure_loaded(org_id)
        auth = self._authorities.get(username)
        if not auth:
            return AuthorityVerdict.DENIED, f"No authority record for '{username}'"

        ba = auth.binding_authority

        if premium < 0:
            return AuthorityVerdict.DENIED, f"Premium must be non-negative, got ${premium:,.0f}"
        if tiv < 0:
            return AuthorityVerdict.DENIED, f"TIV must be non-negative, got ${tiv:,.0f}"

        if premium > ba.max_premium:
            return AuthorityVerdict.DENIED, (f"Premium ${premium:,.0f} exceeds ${ba.max_premium:,.0f} {auth.tier.value} binding limit for {auth.display_name} — escalate to a higher tier")

        if tiv > ba.max_tiv:
            return AuthorityVerdict.DENIED, (f"TIV ${tiv:,.0f} exceeds ${ba.max_tiv:,.0f} {auth.tier.value} binding limit")

        if ba.allowed_states and state and state not in ba.allowed_states:
            return AuthorityVerdict.DENIED, f"State '{state}' not in {auth.display_name}'s licensed states"

        if occupancy and occupancy in ba.excluded_occupancies:
            return AuthorityVerdict.DENIED, f"Occupancy '{occupancy}' excluded from authority"

        needs_cosign = ba.requires_co_sign or (ba.co_sign_threshold_premium > 0 and premium >= ba.co_sign_threshold_premium)
        if needs_cosign:
            return AuthorityVerdict.NEEDS_CO_SIGN, (f"Premium ${premium:,.0f} requires co-sign (threshold ${ba.co_sign_threshold_premium:,.0f}) for {auth.tier.value} {auth.display_name}")

        return AuthorityVerdict.APPROVED, f"Within {auth.tier.value} authority — approved"

    def check_binding_authority(
        self,
        username: str,
        premium: float,
        tiv: float,
        state: str = "",
        occupancy: str = "",
        org_id: str = "default",
    ) -> tuple[bool, str]:
        """Backward-compatible check — True only when solo-bind is approved (no co-sign needed)."""
        verdict, reason = self.evaluate_binding_authority(
            username=username,
            premium=premium,
            tiv=tiv,
            state=state,
            occupancy=occupancy,
            org_id=org_id,
        )
        return verdict == AuthorityVerdict.APPROVED, reason


_authority_matrix: AuthorityMatrix | None = None


def get_authority_matrix() -> AuthorityMatrix:
    global _authority_matrix
    if _authority_matrix is None:
        _authority_matrix = AuthorityMatrix()
    return _authority_matrix
