from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer

from insureflow.auth import ROLE_HIERARCHY, Role
from insureflow.auth.jwt import decode_access_token
from insureflow.auth.models import TokenData
from insureflow.auth.store import clear_user_store, get_user_store

security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

__all__ = ["get_user_store", "clear_user_store", "get_current_user", "require_role", "security"]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> TokenData:
    token_data = decode_access_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return token_data


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[TokenData]:
    if credentials is None:
        return None
    return decode_access_token(credentials.credentials)


def require_role(min_role: Role):
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
