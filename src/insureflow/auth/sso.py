"""OIDC / Cognito / Okta SSO — PKCE + JWKS for bank identity federation."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

_jwks_cache: dict[str, Any] = {"keys": {}, "fetched_at": 0, "openid": {}}
_JWKS_CACHE_TTL = 3600
_pkce_store: dict[str, tuple[str, float]] = {}
_PKCE_TTL = 600.0


def sso_required() -> bool:
    """Banks should set SSO_REQUIRED=true so password login is off at the edge."""
    return os.getenv("SSO_REQUIRED", "").strip().lower() in {"1", "true", "yes", "on"}


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


def _pkce_put(state: str, verifier: str) -> None:
    _pkce_store[state] = (verifier, time.time() + _PKCE_TTL)
    expired = [k for k, (_, exp) in _pkce_store.items() if exp < time.time()]
    for k in expired:
        _pkce_store.pop(k, None)


def _pkce_pop(state: str) -> str | None:
    item = _pkce_store.pop(state, None)
    if not item:
        return None
    verifier, exp = item
    if exp < time.time():
        return None
    return verifier


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _openid_config(issuer: str) -> dict[str, Any]:
    cached = _jwks_cache.get("openid") or {}
    if cached.get("issuer") == issuer and cached.get("fetched_at", 0) > time.time() - _JWKS_CACHE_TTL:
        return cached.get("doc") or {}
    well_known = issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        req = urllib.request.Request(well_known, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            doc: dict[str, Any] = json.loads(resp.read().decode())
        _jwks_cache["openid"] = {"issuer": issuer, "fetched_at": time.time(), "doc": doc}
        return doc
    except Exception as exc:
        logger.debug("OIDC discovery failed for %s: %s", issuer, exc)
        return {}


def _token_endpoint(cfg: OIDCConfig) -> str:
    discovered = _openid_config(cfg.issuer).get("token_endpoint")
    if discovered:
        return str(discovered)
    if cfg.provider == "okta" or os.getenv("OKTA_DOMAIN"):
        issuer = cfg.issuer.rstrip("/")
        if issuer.endswith("/oauth2") or "/oauth2/" in issuer:
            return issuer + "/v1/token"
        return issuer + "/oauth2/v1/token"
    if cfg.provider == "cognito" or os.getenv("COGNITO_DOMAIN"):
        domain = os.getenv("COGNITO_DOMAIN", "").rstrip("/")
        if domain:
            if not domain.startswith("http"):
                domain = f"https://{domain}"
            return f"{domain}/oauth2/token"
    return cfg.issuer.rstrip("/") + "/oauth2/token"


def _fetch_jwks(issuer: str) -> dict[str, Any]:
    """Fetch JWKS keys from the issuer, with caching."""
    now = time.time()
    if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < _JWKS_CACHE_TTL:
        result: dict[str, Any] = _jwks_cache["keys"]
        return result

    discovered = _openid_config(issuer).get("jwks_uri")
    jwks_uri = discovered or (issuer.rstrip("/") + "/oauth2/v1/keys")

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
                options = {
                    "verify_aud": bool(os.getenv("OIDC_CLIENT_ID") or os.getenv("COGNITO_CLIENT_ID")),
                    "verify_iss": bool(os.getenv("OIDC_ISSUER")),
                    "verify_exp": True,
                }
                decode_kwargs: dict[str, Any] = {
                    "algorithms": [alg],
                    "options": options,
                }
                audience = os.getenv("OIDC_CLIENT_ID") or os.getenv("COGNITO_CLIENT_ID") or ""
                issuer = os.getenv("OIDC_ISSUER", "")
                if audience and options["verify_aud"]:
                    decode_kwargs["audience"] = audience
                if issuer and options["verify_iss"]:
                    decode_kwargs["issuer"] = issuer
                verified: dict[str, Any] = jose_jwt.decode(token, key, **decode_kwargs)
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
        "required": sso_required(),
        "pkce": True,
        "note": "Configure OIDC_ISSUER + OIDC_CLIENT_ID (Cognito/Okta). Set SSO_REQUIRED=true to disable password login.",
    }


def start_authorization() -> dict[str, str]:
    """PKCE authorization start — verifier stays on the server, keyed by state."""
    cfg = OIDCConfig.from_env()
    if not cfg.enabled:
        raise RuntimeError("SSO is not enabled")
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    _pkce_put(state, verifier)
    return {"authorize_url": build_authorize_url(state, code_challenge=_code_challenge(verifier)), "state": state}


def build_authorize_url(state: str, *, code_challenge: str | None = None) -> str:
    cfg = OIDCConfig.from_env()
    if not cfg.enabled:
        raise RuntimeError("SSO is not enabled")

    discovered = _openid_config(cfg.issuer).get("authorization_endpoint")
    if discovered:
        base = str(discovered)
    elif cfg.provider == "cognito" or os.getenv("COGNITO_DOMAIN"):
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
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    return f"{base}?{urlencode(params)}"


def exchange_code_for_claims(code: str, *, code_verifier: str | None = None, state: str | None = None) -> dict[str, Any]:
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

    verifier = code_verifier or (_pkce_pop(state) if state else None)

    try:
        token_endpoint = _token_endpoint(cfg)
        body: dict[str, str] = {
            "grant_type": "authorization_code",
            "client_id": cfg.client_id,
            "code": code,
            "redirect_uri": cfg.redirect_uri,
        }
        if cfg.client_secret:
            body["client_secret"] = cfg.client_secret
        if verifier:
            body["code_verifier"] = verifier
        post_data = urlencode(body).encode()
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
