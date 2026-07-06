from __future__ import annotations

from fastapi import Header, HTTPException, status

from insureflow.config import settings


def verify_gateway_key(authorization: str | None = Header(default=None)) -> None:
    expected = (settings.integration_gateway_api_key or "").strip()
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid gateway API key")
