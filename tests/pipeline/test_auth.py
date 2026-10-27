"""B-190: OIDC sign-in, session cookies and audit rows. No model calls; a local fake provider only."""

from __future__ import annotations

import base64
import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import auth
import package
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

ISSUER = "https://idp.example.test"


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def jwt(key, claims: dict, kid: str = "test-key") -> str:
    head = b64(json.dumps({"alg": "RS256", "kid": kid, "typ": "JWT"}).encode())
    body = b64(json.dumps(claims).encode())
    signature = key.sign(f"{head}.{body}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{head}.{body}.{b64(signature)}"


class Provider(BaseHTTPRequestHandler):
    key = None
    id_token = ""
    issuer = ISSUER

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/.well-known/openid-configuration":
            payload = {"issuer": self.issuer, "authorization_endpoint": self.issuer + "/authorize",
                       "token_endpoint": self.issuer + "/token", "jwks_uri": self.issuer + "/jwks"}
        elif self.path == "/jwks":
            numbers = self.key.public_key().public_numbers()
            payload = {"keys": [{"kty": "RSA", "kid": "test-key", "use": "sig",
                                 "n": b64(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
                                 "e": b64(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big"))}]}
        else:
            self.send_error(404)
            return
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        if self.path != "/token":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        raw = json.dumps({"id_token": self.id_token, "access_token": "synthetic"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


@pytest.fixture
def provider(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    Provider.key = key
    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    issuer = f"http://127.0.0.1:{server.server_port}"
    Provider.issuer = issuer
    monkeypatch.setenv("OIDC_ISSUER", issuer)
    monkeypatch.setenv("OIDC_CLIENT_ID", "workbench-test")
    monkeypatch.setenv("SESSION_SECRET", "x" * 40)
    monkeypatch.setenv("OIDC_REDIRECT_URI", f"{issuer}/auth/callback")
    auth.reset_discovery_cache()
    yield server, issuer, key
    server.shutdown()
    auth.reset_discovery_cache()


def claims(issuer: str, **over):
    now = int(time.time())
    base = {"iss": issuer, "sub": "subject-1", "aud": "workbench-test", "exp": now + 300, "iat": now,
            "nonce": "nonce-1", "email": "uw@example.test", "email_verified": True, "name": "Synthetic UW"}
    base.update(over)
    return base


def test_missing_config_fails_closed(monkeypatch):
    for name in ("OIDC_ISSUER", "OIDC_CLIENT_ID", "SESSION_SECRET"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(auth.AuthError, match="sign-in is not configured"):
        auth.config()
    page = auth.config_error_page("sign-in is not configured: OIDC_ISSUER")
    assert "No submission is shown" in page


def test_sign_in_url_uses_pkce_state_nonce_and_safe_next(provider):
    _, issuer, _ = provider
    target, cookie = auth.sign_in_url("/#SUB-002")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(target).query)
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["state"][0]) >= 32 and len(query["nonce"][0]) >= 32
    assert query["redirect_uri"] == [f"{issuer}/auth/callback"]
    assert cookie.startswith(auth.STATE_COOKIE + "=")
    _, bad_cookie = auth.sign_in_url("//evil.example/")
    payload = auth._state_from_cookie(bad_cookie)
    assert payload["next"] == "/"


def test_complete_sign_in_maps_a_verified_email_and_creates_a_session(provider, monkeypatch, tmp_path: Path):
    _, issuer, key = provider
    listing = tmp_path / "underwriters.json"
    listing.write_text(json.dumps({"underwriters": [{"id": "UW-001", "name": "Synthetic UW", "email": "uw@example.test", "senior": True}]}))
    monkeypatch.setattr(package, "UNDERWRITERS", listing)
    target, cookie = auth.sign_in_url("/")
    state = urllib.parse.parse_qs(urllib.parse.urlsplit(target).query)["state"][0]
    nonce = urllib.parse.parse_qs(urllib.parse.urlsplit(target).query)["nonce"][0]
    Provider.id_token = jwt(key, claims(issuer, nonce=nonce))
    user, session, next_path = auth.complete_sign_in({"code": "synthetic", "state": state}, cookie)
    assert (user.id, user.senior, next_path) == ("UW-001", True, "/")
    assert auth.session_from_cookie(f"{auth.SESSION_COOKIE}={session}").id == "UW-001"


def test_an_unlisted_identity_gets_no_session(provider, monkeypatch, tmp_path: Path):
    _, issuer, key = provider
    listing = tmp_path / "underwriters.json"
    listing.write_text(json.dumps({"underwriters": [{"id": "UW-001", "email": "someone-else@example.test"}]}))
    monkeypatch.setattr(package, "UNDERWRITERS", listing)
    target, cookie = auth.sign_in_url("/")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(target).query)
    Provider.id_token = jwt(key, claims(issuer, nonce=query["nonce"][0]))
    with pytest.raises(auth.AuthError, match="not on the workbench underwriter list"):
        auth.complete_sign_in({"code": "synthetic", "state": query["state"][0]}, cookie)


@pytest.mark.parametrize("change", [{"nonce": "wrong"}, {"aud": "another-client"}, {"exp": 1}, {"iss": "https://elsewhere.example"}])
def test_a_bad_id_token_is_rejected(provider, change):
    _, issuer, key = provider
    token = jwt(key, claims(issuer, **change))
    with pytest.raises(auth.AuthError):
        auth.verify_id_token(token, auth.config(), "nonce-1")


def test_a_tampered_signature_is_rejected(provider):
    _, issuer, key = provider
    good = jwt(key, claims(issuer))
    head, body, _ = good.split(".")
    other = jwt(rsa.generate_private_key(public_exponent=65537, key_size=2048), claims(issuer))
    with pytest.raises(auth.AuthError, match="signature"):
        auth.verify_id_token(f"{head}.{body}.{other.split('.')[2]}", auth.config(), "nonce-1")


def test_a_tampered_session_cookie_is_not_a_session(provider):
    user, session = auth.new_session("user", "User", "", False)
    assert auth.session_from_cookie(f"{auth.SESSION_COOKIE}={session}").id == "user"
    assert auth.session_from_cookie(f"{auth.SESSION_COOKIE}={session}x") is None
    assert auth.session_from_cookie("") is None


def test_csrf_and_origin_checks(provider):
    user, _ = auth.new_session("user", "User", "", False)
    first, second = auth.csrf_for(user), auth.csrf_for(user)
    assert first != second
    auth.check_csrf(user, first)
    auth.check_csrf(user, second)
    with pytest.raises(auth.AuthError, match="form token"):
        auth.check_csrf(user, "wrong")
    with pytest.raises(auth.AuthError, match="form token"):
        auth.check_csrf(user, user.csrf)
    auth.check_origin("http://127.0.0.1:8765", "127.0.0.1:8765")
    with pytest.raises(auth.AuthError, match="Origin"):
        auth.check_origin(None, "127.0.0.1:8765")
    with pytest.raises(auth.AuthError, match="does not match"):
        auth.check_origin("https://evil.example", "127.0.0.1:8765")


def test_audit_is_append_only_and_fails_loudly_on_a_bad_path(provider, tmp_path: Path):
    user, _ = auth.new_session("user", "User", "", False)
    saved = auth.AUDIT_LOG
    try:
        auth.AUDIT_LOG = tmp_path / "auth.jsonl"
        row = auth.audit(user, "view", "SUB-002", run_hash="abc")
        assert row["user"] == "user" and row["action"] == "view"
        auth.audit(user, "decision", "SUB-002", outcome="ok", reason="synthetic")
        lines = (tmp_path / "auth.jsonl").read_text().splitlines()
        assert len(lines) == 2 and json.loads(lines[1])["action"] == "decision"
        auth.AUDIT_LOG = tmp_path / "missing" / "auth.jsonl"
        assert auth.audit(user, "send", "SUB-002")["action"] == "send"
    finally:
        auth.AUDIT_LOG = saved
