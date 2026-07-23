"""OIDC / Cognito / Okta SSO — JWKS token exchange for bank identity federation."""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

_jwks_cache: dict[str, Any] = {"keys": {}, "fetched_at": 0}
_JWKS_CACHE_TTL = 3600


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


def _fetch_jwks(issuer: str) -> dict[str, Any]:
    """Fetch JWKS keys from the issuer, with caching."""
    now = time.time()
    if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < _JWKS_CACHE_TTL:
        result: dict[str, Any] = _jwks_cache["keys"]
        return result

    well_known = issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        req = urllib.request.Request(well_known, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            config: dict[str, Any] = json.loads(resp.read().decode())
        jwks_uri = config.get("jwks_uri", issuer.rstrip("/") + "/oauth2/v1/keys")
    except Exception:
        jwks_uri = issuer.rstrip("/") + "/oauth2/v1/keys"

    try:
        req = urllib.request.Request(jwks_uri, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            keys_data: dict[str, Any] = json.loads(resp.read().decode())
        _jwks_cache["keys"] = keys_data
        _jwks_cache["fetched_at"] = now
        return keys_data
    except Exception as exc:
        logger.warning("Failed to fetch JWKS from %s: %s", jwks_uri, exc)
        fallback: dict[str, Any] = _jwks_cache.get("keys", {})
        return fallback


def _base64url_decode(data: str) -> bytes:
    """Decode base64url-encoded data."""
    import base64

    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    decoded: bytes = base64.urlsafe_b64decode(data)
    return decoded


def _verify_jwt_signature(token: str, keys_data: dict[str, Any]) -> dict[str, Any] | None:
    """Verify JWT RS256/ES256 signature using JWKS keys. Returns payload or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, _payload_b64, signature_b64 = parts
        header = json.loads(_base64url_decode(header_b64))

        kid = header.get("kid")
        alg = header.get("alg", "")

        if alg not in ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512"):
            logger.warning("Unsupported JWT algorithm: %s", alg)
            return None

        key_candidates = [k for k in keys_data.get("keys", []) if k.get("kid") == kid]
        if not key_candidates:
            key_candidates = keys_data.get("keys", [])
        if not key_candidates:
            return None

        from jose import jwt as jose_jwt

        for key in key_candidates:
            try:
                verified: dict[str, Any] = jose_jwt.decode(
                    token,
                    key,
                    algorithms=[alg],
                    options={"verify_aud": False},
                )
                return verified
            except Exception:
                continue
        return None
    except Exception as exc:
        logger.debug("JWT signature verification failed: %s", exc)
        return None


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
    """Exchange authorization code for tokens and validate via JWKS.

    1. Exchanges the code at the token endpoint for id_token + access_token.
    2. Verifies the id_token signature against the issuer's JWKS keys.
    3. Returns the validated claims.
    """
    cfg = OIDCConfig.from_env()
    if not cfg.enabled:
        raise RuntimeError("SSO is not enabled")
    if not cfg.client_id or not cfg.issuer:
        raise RuntimeError("OIDC_CLIENT_ID and OIDC_ISSUER are required for SSO token exchange")

    try:
        token_endpoint = cfg.issuer.rstrip("/") + "/oauth2/token"
        post_data = urlencode(
            {
                "grant_type": "authorization_code",
                "client_id": cfg.client_id,
                "client_secret": cfg.client_secret,
                "code": code,
                "redirect_uri": cfg.redirect_uri,
            }
        ).encode()
        req = urllib.request.Request(
            token_endpoint,
            data=post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            token_data = json.loads(resp.read().decode())

        id_token = token_data.get("id_token")
        if not id_token:
            logger.warning("No id_token in token response")
            return {
                "sub": None,
                "email": None,
                "provider": cfg.provider,
                "code_received": True,
                "status": "no_id_token",
            }

        keys_data = _fetch_jwks(cfg.issuer)
        claims = _verify_jwt_signature(id_token, keys_data)
        if claims is None:
            return {
                "sub": None,
                "email": None,
                "provider": cfg.provider,
                "code_received": True,
                "status": "signature_verification_failed",
            }

        return {
            "sub": claims.get("sub"),
            "email": claims.get("email"),
            "name": claims.get("name"),
            "provider": cfg.provider,
            "code_received": True,
            "status": "validated",
            "issuer": claims.get("iss"),
        }
    except Exception as exc:
        logger.warning("SSO code exchange failed: %s", exc)
        return {
            "sub": None,
            "email": None,
            "provider": cfg.provider,
            "code_received": bool(code),
            "status": f"exchange_error: {type(exc).__name__}",
        }
