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
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "require_staff_desk",
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
    token_data = decode_access_token(credentials.credentials)
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


def require_role(min_role: Role) -> Callable[..., Awaitable[TokenData]]:
    async def _check_role(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        user_role = current_user.role
        if user_role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No role assigned",
            )
        required = ROLE_HIERARCHY.get(min_role, 0)
        actual = ROLE_HIERARCHY.get(user_role, 0)
        if actual < required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role.value}' insufficient, requires '{min_role.value}'",
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
