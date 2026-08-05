"""Co-sign workflow — second signature required above authority thresholds."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from insureflow.underwriting.authority import AuthorityTier, get_authority_matrix


class CoSignStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class CoSignRecord(BaseModel):
    cosign_id: str
    bundle_id: str
    org_id: str = "default"
    requested_by: str
    requester_tier: str = ""
    required_tier: str = "senior"
    premium: float = 0.0
    tiv: float = 0.0
    status: CoSignStatus = CoSignStatus.PENDING
    signed_by: str = ""
    signer_tier: str = ""
    notes: str = ""
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    resolved_at: datetime | None = None


_TIER_RANK = {
    AuthorityTier.JUNIOR: 1,
    AuthorityTier.MGA: 2,
    AuthorityTier.SENIOR: 3,
    AuthorityTier.CUO: 4,
}


def required_cosigner_tier(requester_tier: AuthorityTier) -> AuthorityTier:
    if requester_tier in (AuthorityTier.JUNIOR, AuthorityTier.MGA):
        return AuthorityTier.SENIOR
    if requester_tier == AuthorityTier.SENIOR:
        return AuthorityTier.CUO
    return AuthorityTier.CUO


def can_cosign(*, signer_username: str, requester_username: str, required_tier: str, org_id: str) -> tuple[bool, str]:
    if signer_username == requester_username:
        return False, "Co-signer must be a different underwriter"
    matrix = get_authority_matrix()
    signer = matrix.get_authority(signer_username, org_id=org_id)
    if not signer:
        return False, f"No authority record for co-signer '{signer_username}'"
    try:
        need = AuthorityTier(required_tier)
    except ValueError:
        need = AuthorityTier.SENIOR
    if _TIER_RANK.get(signer.tier, 0) < _TIER_RANK.get(need, 0):
        return False, f"Co-signer tier '{signer.tier.value}' below required '{need.value}'"
    return True, "ok"


def create_cosign_request(
    *,
    bundle_id: str,
    org_id: str,
    requested_by: str,
    premium: float,
    tiv: float,
    reason: str = "",
) -> CoSignRecord:
    matrix = get_authority_matrix()
    requester = matrix.get_authority(requested_by, org_id=org_id)
    tier = requester.tier if requester else AuthorityTier.JUNIOR
    need = required_cosigner_tier(tier)
    return CoSignRecord(
        cosign_id=f"cs-{uuid4().hex[:10]}",
        bundle_id=bundle_id,
        org_id=org_id,
        requested_by=requested_by,
        requester_tier=tier.value,
        required_tier=need.value,
        premium=premium,
        tiv=tiv,
        reason=reason,
    )


def resolve_cosign(
    record: CoSignRecord,
    *,
    signer_username: str,
    approve: bool,
    notes: str = "",
    org_id: str = "default",
) -> CoSignRecord:
    ok, reason = can_cosign(
        signer_username=signer_username,
        requester_username=record.requested_by,
        required_tier=record.required_tier,
        org_id=org_id or record.org_id,
    )
    if not ok:
        raise ValueError(reason)
    matrix = get_authority_matrix()
    signer = matrix.get_authority(signer_username, org_id=org_id or record.org_id)
    record.status = CoSignStatus.APPROVED if approve else CoSignStatus.REJECTED
    record.signed_by = signer_username
    record.signer_tier = signer.tier.value if signer else ""
    record.notes = notes
    record.resolved_at = datetime.now(tz=timezone.utc)
    return record


def active_cosign(metadata: dict[str, Any] | None) -> CoSignRecord | None:
    raw = (metadata or {}).get("co_sign")
    if not raw or not isinstance(raw, dict):
        return None
    try:
        return CoSignRecord.model_validate(raw)
    except Exception:  # noqa: BLE001
        return None


def cosign_allows_bind(metadata: dict[str, Any] | None, binder_username: str) -> tuple[bool, str]:
    """Return whether an approved co-sign clears the binder for bind."""
    record = active_cosign(metadata)
    if record is None:
        return True, "no co-sign required"
    if record.status == CoSignStatus.APPROVED:
        if record.signed_by == binder_username:
            return False, "Binder cannot be the same person who co-signed"
        return True, f"Co-signed by {record.signed_by}"
    if record.status == CoSignStatus.PENDING:
        return False, f"Co-sign pending (requires {record.required_tier})"
    return False, f"Co-sign status is {record.status.value}"
