from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from insureflow.auth.models import TokenData

SECRET_KEY = "CHANGE_ME_TO_A_LONG_SECRET_KEY_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(__import__("os").getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))


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
    data: dict,
    expires_delta: Optional[timedelta] = None,
    secret_key: str = SECRET_KEY,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def decode_access_token(
    token: str,
    secret_key: str = SECRET_KEY,
) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        org_id: str = payload.get("org_id", "default")
        if username is None:
            return None
        from insureflow.auth import Role
        return TokenData(username=username, role=Role(role) if role else None, org_id=org_id)
    except JWTError:
        return None
