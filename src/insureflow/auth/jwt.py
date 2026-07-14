from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from insureflow.auth.models import TokenData
from insureflow.config import settings

ALGORITHM = "HS256"


def _secret_key() -> str:
    """Honor live env first so AWS Secrets Manager injection and tests work."""
    return os.getenv("SECRET_KEY") or settings.secret_key


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: str | None = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return str(jwt.encode(to_encode, secret_key or _secret_key(), algorithm=ALGORITHM))


def decode_access_token(
    token: str,
    secret_key: str | None = None,
) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, secret_key or _secret_key(), algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        org_id: str = payload.get("org_id", "default")
        if username is None:
            return None
        from insureflow.auth import Role

        return TokenData(username=username, role=Role(role) if role else None, org_id=org_id)
    except JWTError:
        return None


# Legacy alias — resolves dynamically when read at call sites that import the function,
# but keep a name for older imports that referenced the constant.
SECRET_KEY = settings.secret_key
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
