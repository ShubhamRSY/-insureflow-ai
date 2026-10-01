from __future__ import annotations

from typing import Awaitable, Callable, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer

from insureflow.auth import ROLE_HIERARCHY, Role
from insureflow.auth.jwt import decode_access_token
from insureflow.auth.models import TokenData
from insureflow.auth.store import clear_user_store, get_user_store

security = HTTPBearer(auto_error=False)
security_required = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

__all__ = [
    "get_user_store",
    "clear_user_store",
    "authenticate_bearer",
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "require_staff_desk",
    "has_role",
    "security",
]


def _refresh_from_live_store(token_data: TokenData) -> TokenData | None:
    """Re-check the live user store so disabled/deleted users lose access
    immediately and role/org reflect the current record, not a stale JWT
    claim. Returns None when the user no longer exists or is disabled —
    callers decide whether that means "raise 401/403" or "treat as
    unauthenticated", but the org_id/role RESOLUTION itself must be
    identical everywhere a token is read, or two endpoints reading the
    same session can disagree on which org_id owns a record (e.g. a job
    written under the org_id resolved here, looked up later under a
    stale JWT-only org_id from a caller that skipped this step).
    """
    store = get_user_store()
    user = store.get(token_data.username) if token_data.username else None
    if user is None:
        return None
    if getattr(user, "disabled", False) or getattr(user, "is_active", True) is False:
        return None
    if getattr(user, "role", None) is not None:
        token_data.role = user.role
    if getattr(user, "org_id", None):
        token_data.org_id = user.org_id
    return token_data


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security_required),
) -> TokenData:
    return authenticate_bearer(credentials.credentials)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[TokenData]:
    if credentials is None:
        return None
    token_data = decode_access_token(credentials.credentials)
    if token_data is None:
        return None
    # Same live-store resolution get_current_user applies — a caller using
    # the optional dependency (e.g. a demo/anonymous-friendly endpoint)
    # must resolve org_id/role identically, or its writes and a later
    # get_current_user-backed read of the same session disagree on org_id.
    return _refresh_from_live_store(token_data)


def extract_bearer_token(header_value: str | None) -> str | None:
    """Parse an ``Authorization: Bearer <token>`` header into the raw token.

    Non-FastAPI transports (the MCP SSE mount, gateway middleware, webhook
    replay) cannot use ``HTTPBearer`` — there is no dependency-injection
    container to resolve it — so they need the header parsed by hand. Kept
    here, next to the scheme definition, so it can never drift from what
    ``HTTPBearer`` accepts: scheme match is case-insensitive per RFC 6750
    and extra whitespace around the scheme is tolerated.
    """
    if not header_value:
        return None
    scheme, _, credentials = header_value.partition(" ")
    if scheme.strip().lower() != "bearer":
        return None
    token = credentials.strip()
    return token or None


def authenticate_bearer(token: str | None) -> TokenData:
    """Resolve a raw bearer token to a live, org-scoped principal.

    The single authority for "who is this caller and which org do they
    belong to". Every transport (FastAPI routes, the MCP mount, background
    workers) must go through this rather than decoding a JWT itself, so a
    disabled user, a deleted user, and a stale ``org_id`` claim all resolve
    the same way no matter which door the request came through. Raises 401
    for an unusable token and 403 for a valid token whose account is no
    longer active.
    """
    token_data = decode_access_token(token) if token else None
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    store = get_user_store()
    user = store.get(token_data.username) if token_data.username else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    if getattr(user, "disabled", False) or getattr(user, "is_active", True) is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account disabled")
    resolved = _refresh_from_live_store(token_data)
    assert resolved is not None  # the two checks above already ruled out None
    return resolved


def has_role(user: TokenData, min_role: Role) -> bool:
    """Role-hierarchy check usable from non-FastAPI call sites.

    ``require_role`` raises on failure; tool transports that return a JSON
    error string instead of an HTTP status need the boolean form.
    """
    if user.role is None:
        return False
    return ROLE_HIERARCHY.get(user.role, 0) >= ROLE_HIERARCHY.get(min_role, 0)


def require_role(min_role: Role) -> Callable[..., Awaitable[TokenData]]:
    async def _check_role(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No role assigned",
            )
        if not has_role(current_user, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' insufficient, requires '{min_role.value}'",
            )
        return current_user

    return _check_role


def require_staff_desk() -> Callable[..., Awaitable[TokenData]]:
    """Staff underwriting desk: staff_uw, licensed_uw (large accounts), admin, or cuo."""

    async def _check(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        from insureflow.underwriting.roles import role_supports_staff_desk

        if not role_supports_staff_desk(current_user.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff underwriting desk requires staff_uw, licensed_uw, admin, or cuo",
            )
        return current_user

    return _check
