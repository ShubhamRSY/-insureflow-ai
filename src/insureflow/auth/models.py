from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from insureflow.auth import Role


class Organization(BaseModel):
    id: str = ""
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class User(BaseModel):
    username: str
    email: str = ""
    hashed_password: str = ""
    role: Role = Role.VIEWER
    disabled: bool = False
    org_id: str = "default"
    company_name: str = ""
    department: str = ""
    team: str = ""
    office_location: str = ""
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
    email: str = ""
    company_name: str = ""
    department: str = ""
    team: str = ""
    office_location: str = ""


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str
    company_name: str
    full_name: str = ""
    plan: str = "free"


class PasswordResetRequest(BaseModel):
    username: str
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
