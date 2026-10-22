"""B-190 — OIDC sign-in and the audit log for the pipeline workbench.

Every view, decision and send needs a signed-in underwriter. The workbench
never trusts a posted actor: the handler replaces it with the session user.
Sessions are short-lived signed cookies; the OIDC authorization-code flow uses
PKCE, state and nonce, and verifies the ID token against the provider's JWKS.

Configuration (shell environment, never a file in the repo):
  OIDC_ISSUER          issuer URL; discovery is <issuer>/.well-known/openid-configuration
  OIDC_CLIENT_ID       client id registered with the provider
  OIDC_CLIENT_SECRET   optional; omit for a public client
  OIDC_REDIRECT_URI    default http://127.0.0.1:8765/auth/callback
  OIDC_SCOPES          default "openid profile email"
  OIDC_TOKEN_AUTH      client_secret_post (default) or client_secret_basic
  SESSION_SECRET       at least 32 characters; signs the session/state cookies
  AUTH_AUDIT_LOG       optional path; default deliverables/software-engineer/auth-audit.jsonl

Without OIDC_ISSUER, OIDC_CLIENT_ID and SESSION_SECRET the workbench fails
closed: it shows that sign-in is not configured and renders no submission.

The OIDC subject is mapped to an id in underwriters.json by "oidc_sub" (or
"issuer" + "subject"), or by a verified email in "email". An identity that is
not on that list gets no session. This is a local sign-in for the pipeline
workbench, not a replacement for the React app's platform auth.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import hmac
import html
import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "app"))
import package  # noqa: E402  (after the sys.path insert)

AUDIT_LOG = Path(os.environ.get("AUTH_AUDIT_LOG") or (ROOT / "deliverables" / "software-engineer" / "auth-audit.jsonl"))
SESSION_COOKIE = "insureflow_workbench_session"
STATE_COOKIE = "insureflow_workbench_oidc"
SESSION_TTL = 8 * 60 * 60
STATE_TTL = 10 * 60
CLOCK_SKEW = 120
MAX_FORM_BYTES = 1024 * 1024
_DISCOVERY: dict[str, dict] = {}
_DISCOVERY_LOCK = threading.Lock()


class AuthError(ValueError):
    """A sign-in or session failure with a plain-language reason."""


@dataclass(frozen=True)
class Config:
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: str
    token_auth: str
    session_secret: bytes


@dataclass(frozen=True)
class User:
    id: str
    name: str
    email: str
    senior: bool
    csrf: str

    def cookie_payload(self) -> dict:
        return {"v": 1, "id": self.id, "name": self.name, "email": self.email, "senior": self.senior, "csrf": self.csrf}


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def config() -> Config:
    """Read the sign-in configuration. Missing values make the workbench fail closed, not open."""
    issuer, client_id, secret = _env("OIDC_ISSUER").rstrip("/"), _env("OIDC_CLIENT_ID"), _env("SESSION_SECRET")
    missing = [name for name, value in (("OIDC_ISSUER", issuer), ("OIDC_CLIENT_ID", client_id), ("SESSION_SECRET", secret)) if not value]
    if missing:
        raise AuthError("sign-in is not configured: " + ", ".join(missing))
    if len(secret) < 32:
        raise AuthError("sign-in is not configured: SESSION_SECRET must be at least 32 characters")
    parsed = urllib.parse.urlsplit(issuer)
    if parsed.scheme != "https" and not _insecure_allowed(issuer):
        raise AuthError("sign-in is not configured: OIDC_ISSUER must use https")
    redirect = _env("OIDC_REDIRECT_URI") or "http://127.0.0.1:8765/auth/callback"
    token_auth = _env("OIDC_TOKEN_AUTH") or "client_secret_post"
    if token_auth not in {"client_secret_post", "client_secret_basic"}:
        raise AuthError("OIDC_TOKEN_AUTH must be client_secret_post or client_secret_basic")
    return Config(issuer=issuer, client_id=client_id, client_secret=_env("OIDC_CLIENT_SECRET"), redirect_uri=redirect,
                  scopes=_env("OIDC_SCOPES") or "openid profile email", token_auth=token_auth,
                  session_secret=secret.encode())


def _insecure_allowed(issuer: str) -> bool:
    host = (urllib.parse.urlsplit(issuer).hostname or "").lower()
    return _env("OIDC_ALLOW_INSECURE_HTTP") == "1" or host in {"127.0.0.1", "localhost", "::1"}


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(data: str, secret: bytes) -> str:
    return _b64e(hmac.new(secret, data.encode(), hashlib.sha256).digest())


def _pack(payload: dict, secret: bytes) -> str:
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    return f"{body}.{_sign(body, secret)}"


def _unpack(value: str, secret: bytes) -> dict:
    try:
        body, signature = value.split(".", 1)
    except ValueError as exc:
        raise AuthError("the sign-in cookie is malformed") from exc
    if not hmac.compare_digest(signature, _sign(body, secret)):
        raise AuthError("the sign-in cookie failed its signature check")
    try:
        payload = json.loads(_b64d(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthError("the sign-in cookie is malformed") from exc
    if not isinstance(payload, dict):
        raise AuthError("the sign-in cookie is malformed")
    return payload


def _cookie_values(header: str | None) -> dict[str, str]:
    out = {}
    for part in (header or "").split(";"):
        key, _, value = part.strip().partition("=")
        if key:
            out[key] = value
    return out


def cookie_header(name: str, value: str, max_age: int, secure: bool) -> str:
    bits = [f"{name}={value}", "Path=/", "HttpOnly", "SameSite=Lax", f"Max-Age={max_age}"]
    if secure:
        bits.append("Secure")
    return "; ".join(bits)


def _secure(config_: Config) -> bool:
    return urllib.parse.urlsplit(config_.redirect_uri).scheme == "https"


def _user_from_payload(payload: dict, now: float) -> User:
    if payload.get("v") != 1 or not isinstance(payload.get("exp"), (int, float)) or payload["exp"] < now:
        raise AuthError("the sign-in session has expired; sign in again")
    ident = (payload.get("id") or "").strip()
    csrf = (payload.get("csrf") or "").strip()
    if not ident or not csrf:
        raise AuthError("the sign-in session is incomplete; sign in again")
    return User(id=ident, name=str(payload.get("name") or ident), email=str(payload.get("email") or ""),
                senior=payload.get("senior") is True, csrf=csrf)


def new_session(user_id: str, name: str, email: str, senior: bool, ttl: int = SESSION_TTL) -> tuple[User, str]:
    """Build a signed session for a mapped underwriter. Only tests and the callback call this."""
    if user_id not in package.underwriters():
        raise AuthError("that identity is not on the underwriter list")
    now = int(time.time())
    user = User(id=user_id, name=name or user_id, email=email, senior=bool(senior), csrf=secrets.token_urlsafe(32))
    payload = {**user.cookie_payload(), "iat": now, "exp": now + ttl}
    try:
        cfg = config()
    except AuthError:
        raise
    return user, _pack(payload, cfg.session_secret)


def session_from_cookie(header: str | None, now: float | None = None) -> User | None:
    """The signed-in user, or None. An expired or tampered cookie is not a session."""
    cfg = config()
    raw = _cookie_values(header).get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        payload = _unpack(raw, cfg.session_secret)
        return _user_from_payload(payload, now if now is not None else time.time())
    except AuthError:
        return None


def clear_cookie(name: str = SESSION_COOKIE) -> str:
    return f"{name}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"


def csrf_for(user: User, ttl: int = 30 * 60) -> str:
    """A fresh signed form token for one render. Bound to the session user and short-lived."""
    body = _b64e(json.dumps({"v": 1, "id": user.id, "iat": int(time.time()), "exp": int(time.time()) + ttl,
                             "nonce": secrets.token_urlsafe(16)}, separators=(",", ":"), sort_keys=True).encode())
    key = hmac.new(user.csrf.encode(), b"csrf", hashlib.sha256).digest()
    return f"{body}.{_sign(body, key)}"


def check_csrf(user: User, token: str) -> None:
    """Validate a per-render token. A missing, stale, forged or other-user token is refused."""
    if not token:
        raise AuthError("the form token is missing or stale; reload the page and try again")
    try:
        body, signature = token.split(".", 1)
        key = hmac.new(user.csrf.encode(), b"csrf", hashlib.sha256).digest()
        if not hmac.compare_digest(signature, _sign(body, key)):
            raise AuthError("the form token is missing or stale; reload the page and try again")
        payload = json.loads(_b64d(body))
        if payload.get("v") != 1 or payload.get("id") != user.id or float(payload.get("exp", 0)) < time.time():
            raise AuthError("the form token is missing or stale; reload the page and try again")
    except (ValueError, json.JSONDecodeError, TypeError) as exc:
        raise AuthError("the form token is missing or stale; reload the page and try again") from exc


def check_origin(origin: str | None, host: str | None) -> None:
    """B-383: a state-changing form must come from this page, not another site."""
    if not origin:
        raise AuthError("the request has no Origin header; reload the page and try again")
    parsed = urllib.parse.urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AuthError("the request Origin is not valid")
    if not host or parsed.netloc.lower() != host.strip().lower():
        raise AuthError("the request Origin does not match this workbench")


def safe_next(value: str) -> str:
    value = (value or "").strip()
    return value if value.startswith("/") and not value.startswith("//") else "/"


def _http_json(url: str, *, form: dict | None = None, headers: dict | None = None, timeout: int = 15) -> dict:
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    request = urllib.request.Request(url, data=data, headers=headers or {})
    if form is not None:
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except (urllib.error.URLError, OSError) as exc:
        raise AuthError(f"the sign-in provider could not be reached: {exc}") from exc
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise AuthError("the sign-in provider returned an unreadable reply") from exc
    if not isinstance(payload, dict):
        raise AuthError("the sign-in provider returned an unreadable reply")
    return payload


def discovery(config_: Config | None = None) -> dict:
    cfg = config_ or config()
    with _DISCOVERY_LOCK:
        if cfg.issuer in _DISCOVERY:
            return _DISCOVERY[cfg.issuer]
    url = cfg.issuer + "/.well-known/openid-configuration"
    data = _http_json(url)
    if str(data.get("issuer") or "").rstrip("/") != cfg.issuer:
        raise AuthError("the sign-in provider's discovery document names a different issuer")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        value = str(data.get(key) or "")
        if not value:
            raise AuthError(f"the sign-in provider's discovery document has no {key}")
    with _DISCOVERY_LOCK:
        _DISCOVERY[cfg.issuer] = data
    return data


def reset_discovery_cache() -> None:
    with _DISCOVERY_LOCK:
        _DISCOVERY.clear()


def sign_in_url(next_path: str = "/") -> tuple[str, str]:
    """Return (authorization URL, short-lived state cookie). No provider call unless discovery is uncached."""
    cfg = config()
    doc = discovery(cfg)
    state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    challenge = _b64e(hashlib.sha256(verifier.encode()).digest())
    now = int(time.time())
    query = urllib.parse.urlencode({
        "response_type": "code", "client_id": cfg.client_id, "redirect_uri": cfg.redirect_uri,
        "scope": cfg.scopes, "state": state, "nonce": nonce,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    auth_url = str(doc["authorization_endpoint"]) + ("&" if "?" in str(doc["authorization_endpoint"]) else "?") + query
    state_payload = {"v": 1, "state": state, "nonce": nonce, "verifier": verifier, "next": safe_next(next_path),
                     "iat": now, "exp": now + STATE_TTL}
    return auth_url, cookie_header(STATE_COOKIE, _pack(state_payload, cfg.session_secret), STATE_TTL, _secure(cfg))


def _state_from_cookie(header: str | None) -> dict:
    cfg = config()
    raw = _cookie_values(header).get(STATE_COOKIE)
    if not raw:
        raise AuthError("the sign-in attempt has no state cookie; start again")
    payload = _unpack(raw, cfg.session_secret)
    if payload.get("v") != 1 or payload.get("exp", 0) < time.time():
        raise AuthError("the sign-in attempt has expired; start again")
    return payload


def complete_sign_in(query: dict[str, str], state_cookie: str | None) -> tuple[User, str, str]:
    """Exchange the authorization code, verify the ID token, map the identity. Returns (user, session cookie, next)."""
    cfg = config()
    if query.get("error"):
        raise AuthError(f"the sign-in provider refused the sign-in: {query.get('error_description') or query['error']}")
    code = (query.get("code") or "").strip()
    state = (query.get("state") or "").strip()
    saved = _state_from_cookie(state_cookie)
    if not code or not state or not hmac.compare_digest(state, str(saved.get("state") or "")):
        raise AuthError("the sign-in reply does not match this attempt; start again")
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": cfg.redirect_uri,
            "client_id": cfg.client_id, "code_verifier": str(saved.get("verifier") or "")}
    headers = {"Accept": "application/json"}
    if cfg.client_secret:
        if cfg.token_auth == "client_secret_basic":
            pair = base64.b64encode(f"{urllib.parse.quote(cfg.client_id)}:{urllib.parse.quote(cfg.client_secret)}".encode()).decode()
            headers["Authorization"] = f"Basic {pair}"
        else:
            form["client_secret"] = cfg.client_secret
    token = _http_json(str(discovery(cfg)["token_endpoint"]), form=form, headers=headers)
    id_token = str(token.get("id_token") or "")
    if not id_token:
        raise AuthError("the sign-in provider returned no ID token")
    claims = verify_id_token(id_token, cfg, str(saved.get("nonce") or ""))
    if not (claims.get("email") or claims.get("preferred_username")):
        doc = discovery(cfg)
        if token.get("access_token") and doc.get("userinfo_endpoint"):
            info = _http_json(str(doc["userinfo_endpoint"]), headers={"Authorization": f"Bearer {token['access_token']}", "Accept": "application/json"})
            claims = {**claims, **info}
    user = map_identity(claims, cfg)
    user, session = new_session(user.id, user.name, user.email, user.senior)
    return user, session, safe_next(str(saved.get("next") or "/"))


def map_identity(claims: dict, config_: Config) -> User:
    """Map verified claims to an underwriters.json entry. No entry means no session."""
    issuer = str(claims.get("iss") or "").rstrip("/")
    subject = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    verified = claims.get("email_verified") is True
    if not subject:
        raise AuthError("the sign-in provider returned no subject")
    try:
        rows = json.loads(package.UNDERWRITERS.read_text())["underwriters"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise AuthError("the underwriter list could not be read") from exc
    for row in rows:
        if not isinstance(row, dict):
            continue
        ident = (row.get("id") or "").strip()
        if not ident:
            continue
        by_sub = (row.get("oidc_sub") or "").strip() == subject and (not row.get("issuer") or str(row.get("issuer")).rstrip("/") == issuer)
        by_issuer_sub = (row.get("issuer") or "").rstrip("/") == issuer and (row.get("subject") or "").strip() == subject
        by_email = verified and email and (row.get("email") or "").strip().lower() == email
        if by_sub or by_issuer_sub or by_email:
            if ident not in package.underwriters():
                break
            name = str(claims.get("name") or row.get("name") or ident)
            return User(id=ident, name=name, email=email, senior=row.get("senior") is True, csrf="")
    who = email or subject
    raise AuthError(f"signed in as {who}, but that identity is not on the workbench underwriter list")


def _jwks(config_: Config) -> list[dict]:
    data = _http_json(str(discovery(config_)["jwks_uri"]))
    keys = data.get("keys")
    if not isinstance(keys, list) or not keys:
        raise AuthError("the sign-in provider returned no signing keys")
    return [k for k in keys if isinstance(k, dict)]


def _verify_signature(signing_input: bytes, signature: bytes, header: dict, keys: list[dict]) -> dict:
    alg, kid = header.get("alg"), header.get("kid")
    if alg not in {"RS256", "RS384", "RS512", "ES256"}:
        raise AuthError(f"the ID token uses an unsupported signing algorithm ({alg or 'none'})")
    candidates = [k for k in keys if not kid or k.get("kid") == kid]
    if not candidates:
        raise AuthError("the ID token names a signing key the provider does not publish")
    hash_alg = {"RS256": hashes.SHA256, "RS384": hashes.SHA384, "RS512": hashes.SHA512, "ES256": hashes.SHA256}[str(alg)]
    last_error = None
    for key in candidates:
        try:
            if alg.startswith("RS"):
                if key.get("kty") != "RSA":
                    continue
                numbers = rsa.RSAPublicNumbers(int.from_bytes(_b64d(str(key["e"])), "big"), int.from_bytes(_b64d(str(key["n"])), "big"))
                numbers.public_key().verify(signature, signing_input, padding.PKCS1v15(), hash_alg())
            else:
                if key.get("kty") != "EC" or key.get("crv") != "P-256":
                    continue
                numbers = ec.EllipticCurvePublicNumbers(int.from_bytes(_b64d(str(key["x"])), "big"), int.from_bytes(_b64d(str(key["y"])), "big"), ec.SECP256R1())
                half = len(signature) // 2
                der = encode_dss_signature(int.from_bytes(signature[:half], "big"), int.from_bytes(signature[half:], "big"))
                numbers.public_key().verify(der, signing_input, ec.ECDSA(hash_alg()))
            return key
        except Exception as exc:  # a key that does not verify is not the signer
            last_error = exc
    raise AuthError("the ID token signature did not verify") from last_error


def verify_id_token(token: str, config_: Config, nonce: str) -> dict:
    """Verify signature, issuer, audience, lifetime and nonce. Returns the claims."""
    try:
        head, body, sig = token.split(".")
    except ValueError as exc:
        raise AuthError("the ID token is malformed") from exc
    try:
        header = json.loads(_b64d(head))
        claims = json.loads(_b64d(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthError("the ID token is malformed") from exc
    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise AuthError("the ID token is malformed")
    signing_input = f"{head}.{body}".encode()
    keys = _jwks(config_)
    try:
        _verify_signature(signing_input, _b64d(sig), header, keys)
    except AuthError:
        keys = _jwks(config_)  # a provider may rotate a key; re-read once
        _verify_signature(signing_input, _b64d(sig), header, keys)
    now = time.time()
    if str(claims.get("iss") or "").rstrip("/") != config_.issuer:
        raise AuthError("the ID token was issued by a different provider")
    audience = claims.get("aud")
    audiences = [audience] if isinstance(audience, str) else list(audience or [])
    if config_.client_id not in audiences:
        raise AuthError("the ID token was issued for a different client")
    if isinstance(audience, list) and len(audience) > 1 and claims.get("azp") not in {None, config_.client_id}:
        raise AuthError("the ID token was authorized for a different client")
    if not isinstance(claims.get("exp"), (int, float)) or claims["exp"] < now - CLOCK_SKEW:
        raise AuthError("the ID token has expired; sign in again")
    if isinstance(claims.get("iat"), (int, float)) and claims["iat"] > now + CLOCK_SKEW:
        raise AuthError("the ID token was issued in the future")
    if not nonce or not hmac.compare_digest(str(claims.get("nonce") or ""), nonce):
        raise AuthError("the ID token does not match this sign-in attempt")
    return claims


def audit_path() -> Path:
    return Path(AUDIT_LOG)


def audit(user: User, action: str, submission: str = "", *, outcome: str = "ok", reason: str = "", run_hash: str = "") -> dict:
    """Append one audit row under a cross-process lock. A failed write raises: never silent."""
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        row = {"v": 1, "user": user.id, "name": user.name, "action": action, "submission": submission or "",
               "outcome": outcome, "reason": (reason or "")[:500], "at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "run_hash": run_hash or ""}
        try:
            with path.open("a") as handle:
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        finally:
            try:
                fcntl.flock(lock, fcntl.LOCK_UN)
            except OSError:
                pass
    return row


def sign_in_page(reason: str = "", next_path: str = "/", status: int = 200) -> str:
    """A plain page. No submission content is rendered before sign-in."""
    detail = f'<p class="bad" role="alert">{html.escape(reason)}</p>' if reason else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Sign in — Underwriter workbench</title>
<style>
body{{font:15px/1.4 sans-serif;max-width:44rem;margin:3rem auto;padding:0 1rem}}
.bad{{padding:.5rem .75rem;border-left:4px solid #b42318;background:#fdecea;color:#b42318;font-weight:600}}
a.button{{display:inline-block;padding:.5rem .9rem;background:#1f4e79;color:#fff;text-decoration:none;border-radius:3px}}
</style></head>
<body><h1>Underwriter workbench</h1>
<p>Assist-only workbench. Sign in to see the synthetic queue. Every view, decision and send is recorded with your name.</p>
{detail}
<p><a class="button" href="/login?next={html.escape(urllib.parse.quote(safe_next(next_path)))}">Sign in</a></p>
<p>No submission is shown until you sign in.</p></body></html>"""


def config_error_page(reason: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Sign-in unavailable — Underwriter workbench</title>
<style>
body{{font:15px/1.4 sans-serif;max-width:44rem;margin:3rem auto;padding:0 1rem}}
.bad{{padding:.5rem .75rem;border-left:4px solid #b42318;background:#fdecea;color:#b42318;font-weight:600}}
</style></head>
<body><h1>Underwriter workbench</h1><p class="bad" role="alert">Sign-in unavailable: {html.escape(reason)}. No submission is shown.</p>
<p>Set the OIDC_* and SESSION_SECRET variables in the shell, then start the workbench again.</p></body></html>"""
