from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from insureflow.auth import Role


class User(BaseModel):
    username: str
    hashed_password: str
    role: Role = Role.VIEWER
    disabled: bool = False
    org_id: str = "default"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    full_name: str = ""


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[Role] = None
    org_id: str = "default"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: Role = Role.VIEWER
    full_name: str = ""
    org_id: str = "default"
