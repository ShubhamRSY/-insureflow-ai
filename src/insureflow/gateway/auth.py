from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from insureflow.config import settings


def verify_gateway_key(authorization: str | None = Header(default=None)) -> None:
    expected = (settings.integration_gateway_api_key or "").strip()
    # Fail closed — an empty key must never open the integration surface.
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integration gateway is not configured (INTEGRATION_GATEWAY_API_KEY missing)",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid gateway API key")
