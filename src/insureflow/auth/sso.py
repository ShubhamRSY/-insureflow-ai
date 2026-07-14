"""OIDC / Cognito / Okta SSO stubs for bank identity federation."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


@dataclass
class OIDCConfig:
    enabled: bool
    provider: str  # cognito | okta | generic
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: str = "openid profile email"

    @classmethod
    def from_env(cls) -> OIDCConfig:
        provider = os.getenv("SSO_PROVIDER", "").strip().lower()
        enabled = os.getenv("SSO_ENABLED", "").lower() in {"1", "true", "yes"} or bool(provider)
        return cls(
            enabled=enabled and bool(os.getenv("OIDC_ISSUER") or os.getenv("COGNITO_DOMAIN") or os.getenv("OKTA_DOMAIN")),
            provider=provider or "generic",
            issuer=os.getenv("OIDC_ISSUER", ""),
            client_id=os.getenv("OIDC_CLIENT_ID", os.getenv("COGNITO_CLIENT_ID", "")),
            client_secret=os.getenv("OIDC_CLIENT_SECRET", os.getenv("COGNITO_CLIENT_SECRET", "")),
            redirect_uri=os.getenv("OIDC_REDIRECT_URI", "https://app.rytera.ai/auth/sso/callback"),
            scopes=os.getenv("OIDC_SCOPES", "openid profile email"),
        )


def sso_status() -> dict[str, Any]:
    cfg = OIDCConfig.from_env()
    return {
        "enabled": cfg.enabled,
        "provider": cfg.provider if cfg.enabled else None,
        "issuer": cfg.issuer or None,
        "login_path": "/auth/sso/login" if cfg.enabled else None,
        "note": "Configure OIDC_ISSUER + OIDC_CLIENT_ID (Cognito/Okta) to enable bank SSO.",
    }


def build_authorize_url(state: str) -> str:
    cfg = OIDCConfig.from_env()
    if not cfg.enabled:
        raise RuntimeError("SSO is not enabled")

    if cfg.provider == "cognito" or os.getenv("COGNITO_DOMAIN"):
        domain = os.getenv("COGNITO_DOMAIN", "").rstrip("/")
        base = f"https://{domain}/oauth2/authorize" if not domain.startswith("http") else f"{domain}/oauth2/authorize"
    elif cfg.provider == "okta" or os.getenv("OKTA_DOMAIN"):
        domain = os.getenv("OKTA_DOMAIN", "").rstrip("/")
        base = f"{domain}/oauth2/v1/authorize" if domain.startswith("http") else f"https://{domain}/oauth2/v1/authorize"
    else:
        base = cfg.issuer.rstrip("/") + "/authorize"

    params = {
        "client_id": cfg.client_id,
        "response_type": "code",
        "scope": cfg.scopes,
        "redirect_uri": cfg.redirect_uri,
        "state": state,
    }
    return f"{base}?{urlencode(params)}"


def exchange_code_for_claims(code: str) -> dict[str, Any]:
    """Exchange authorization code for tokens and return identity claims.

    Full OIDC token validation requires provider JWKS; this stub documents the
    bank integration surface and returns structured errors when incomplete.
    """
    cfg = OIDCConfig.from_env()
    if not cfg.enabled:
        raise RuntimeError("SSO is not enabled")
    if not cfg.client_id or not cfg.issuer:
        raise RuntimeError("OIDC_CLIENT_ID and OIDC_ISSUER are required for SSO token exchange")

    # Placeholder for production IdP wiring — callers should use authlib/jose JWKS verify.
    logger.warning("SSO code exchange stub invoked — wire JWKS validation for production IdP")
    return {
        "sub": "sso-user-pending-jwks",
        "email": None,
        "provider": cfg.provider,
        "code_received": bool(code),
        "status": "stub_requires_jwks_validation",
    }
