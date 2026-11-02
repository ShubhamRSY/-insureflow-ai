"""Integration smoke test: OIDC sign-in, per-value confirmation and the send gate together.

This is the combination neither branch tested on its own:
  - sso-b190 (B-190) proved the handler refuses anonymous reads and actions and audits the session user.
  - pilot-conditions (T-027 C1-C6) proved the assist-only pilot refuses send, approve, draft and producer request
    and offers a per-value confirmation instead.
  - Neither branch ran the two together: a signed-in underwriter on a pilot card.

No model calls. Every write goes to a temp sandbox. The sign-in provider is a local fake.
"""

from __future__ import annotations

import base64
import http.client
import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import auth
import llm_extract
import package
import pilot
import prepare
import pytest
import quotes
import workbench


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class Provider(BaseHTTPRequestHandler):
    key = None
    id_token = ""
    issuer = ""

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


def id_token(key, claims: dict) -> str:
    head = b64(json.dumps({"alg": "RS256", "kid": "test-key", "typ": "JWT"}).encode())
    body = b64(json.dumps(claims).encode())
    signature = key.sign(f"{head}.{body}".encode(), __import__("cryptography.hazmat.primitives.asymmetric.padding", fromlist=["padding"]).PKCS1v15(),
                         __import__("cryptography.hazmat.primitives.hashes", fromlist=["hashes"]).SHA256())
    return f"{head}.{body}.{b64(signature)}"


def run_payload(submission: str = "SUB-990", status: str = "complete") -> dict:
    fields = [
        {"field_id": "named_insured", "value": "Example LLC", "confidence": "high", "source": "application.md", "quote": "Named Insured: Example LLC"},
        {"field_id": "premises_address", "value": "100 Main St", "confidence": "high", "source": "application.md", "quote": "100 Main St"},
        {"field_id": "effective_date", "value": "2026-01-01", "confidence": "high", "source": "application.md", "quote": "2026-01-01"},
        {"field_id": "operations", "value": "general office work", "confidence": "high", "source": "application.md", "quote": "Operations: general office work"},
        {"field_id": "construction", "value": "masonry", "confidence": "high", "source": "application.md", "quote": "Construction: masonry"},
        {"field_id": "sales_or_payroll", "value": "500000", "confidence": "high", "source": "application.md", "quote": "Sales: 500000"},
    ]
    payload = {
        "submission": submission, "status": status, "complete": status == "complete",
        "conflicts": [], "needs_human": [], "sprinklers": None, "fields": fields,
        "scope": {"version": "scope-v4", "in_scope": True, "reasons": []},
    }
    payload["hash_algorithm"] = prepare.HASH_ALGORITHM
    payload["saved_hash"] = prepare.hash_payload(payload)
    return payload


@pytest.fixture
def live(monkeypatch, tmp_path: Path):
    """Pilot mode on, one synthetic saved run, a local fake IdP and the workbench server."""
    box = tmp_path / "box"
    box.mkdir()
    saved = {name: getattr(workbench, name) for name in ("PAGE", "LOG", "INBOX", "PENDING", "TO_PRODUCER", "TO_CARRIER", "BANNER")}
    saved_other = (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES,
                   quotes.TO_CARRIER, quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR,
                   llm_extract.CACHE, pilot.CORRECTIONS, pilot.EVENTS)
    saved_audit = auth.AUDIT_LOG
    saved_uw = package.UNDERWRITERS
    workbench.sandbox(box)
    workbench.MESSAGES.clear()
    monkeypatch.setenv("PILOT_MODE", pilot.ASSIST_ONLY)

    listing = tmp_path / "underwriters.json"
    listing.write_text(json.dumps({"underwriters": [{"id": "user", "name": "Synthetic UW", "email": "uw@example.test", "senior": True}]}))
    monkeypatch.setattr(package, "UNDERWRITERS", listing)

    folder = workbench.INBOX / "SUB-990"
    folder.mkdir(parents=True)
    (folder / "application.md").write_text(
        "Named Insured: Example LLC\nPremises: 100 Main St\nEffective Date: 2026-01-01\n"
        "Construction: masonry\nOperations: general office work\nSales: 500000\n"
    )
    prepare.EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    (prepare.EXTRACT_DIR / "SUB-990.json").write_text(json.dumps(run_payload()))

    from cryptography.hazmat.primitives.asymmetric import rsa
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    Provider.key = key
    provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    issuer = f"http://127.0.0.1:{provider.server_port}"
    Provider.issuer = issuer

    monkeypatch.setenv("OIDC_ISSUER", issuer)
    monkeypatch.setenv("OIDC_CLIENT_ID", "workbench-test")
    monkeypatch.setenv("SESSION_SECRET", "z" * 40)
    server = ThreadingHTTPServer(("127.0.0.1", 0), workbench.make_handler("SUB-990"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server.server_port, issuer, key
    finally:
        server.shutdown()
        provider.shutdown()
        for name, value in saved.items():
            setattr(workbench, name, value)
        (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES,
         quotes.TO_CARRIER, quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR,
         llm_extract.CACHE, pilot.CORRECTIONS, pilot.EVENTS) = saved_other
        auth.AUDIT_LOG = saved_audit
        package.UNDERWRITERS = saved_uw
        workbench.MESSAGES.clear()
        auth.reset_discovery_cache()


def request(port: int, method: str, path: str, *, body: str = "", headers: dict | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    payload = response.read().decode()
    result = (response.status, dict(response.getheaders()), payload)
    conn.close()
    return result


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.is_file() else []


def sign_in(port: int, issuer: str, key) -> str:
    """A real sign-in through the workbench: /login, then the provider's code exchange, then /auth/callback."""
    status, headers, _ = request(port, "GET", "/login?next=/")
    assert status == 303
    state_cookie = headers["Set-Cookie"].split(";")[0]
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(headers["Location"]).query)
    now = int(time.time())
    claims = {"iss": issuer, "sub": "subject-1", "aud": "workbench-test", "exp": now + 300, "iat": now,
              "nonce": query["nonce"][0], "email": "uw@example.test", "email_verified": True, "name": "Synthetic UW"}
    Provider.id_token = id_token(key, claims)
    status, headers, body = request(port, "GET", f"/auth/callback?code=synthetic&state={query['state'][0]}",
                                    headers={"Cookie": state_cookie})
    assert status == 303, body
    return headers["Set-Cookie"].split(";")[0]


def test_signed_in_pilot_confirms_every_value_and_the_send_gate_still_refuses(live):
    port, issuer, key = live
    session = sign_in(port, issuer, key)
    cookie = {"Cookie": session}

    status, _, body = request(port, "GET", "/", headers=cookie)
    assert status == 200, body
    assert "Signed in as" in body and "Synthetic UW" in body
    assert "ASSIST-ONLY PILOT" in body
    card = body[body.index('<article id="SUB-990">'):]
    assert "<option>confirm</option>" in card and "<option>approve</option>" not in card
    assert "No send: assist-only pilot — send disabled for SUB-990" in card and 'action="/send"' not in card
    assert 'name="csrf"' in card, "B-190: a signed-in card carries the form token"

    user = auth.session_from_cookie(session)
    form = urllib.parse.urlencode({
        "submission": "SUB-990", "action": "confirm", "reason": "every value checked against the page",
        "csrf": auth.csrf_for(user), "ack": ["named_insured", "premises_address", "effective_date",
                                              "operations", "construction", "sales_or_payroll"],
    }, doseq=True)
    status, headers, body = request(port, "POST", "/decision", body=form,
                                     headers={**cookie, "Content-Type": "application/x-www-form-urlencoded",
                                              "Origin": f"http://127.0.0.1:{port}"})
    assert status == 303, body
    decision = json.loads(workbench.LOG.read_text().splitlines()[-1])
    assert decision["action"] == "confirm" and decision["underwriter_id"] == "user"
    assert decision["bound"] is False and decision["sent_to_carrier"] is False
    assert len(decision["acknowledged"]) == 6
    assert not any(r.get("action") == "approve" for r in rows(workbench.LOG))

    form = urllib.parse.urlencode({"submission": "SUB-990", "user_line": "send to carrier SUB-990",
                                   "csrf": auth.csrf_for(user)})
    status, _, body = request(port, "POST", "/send", body=form,
                               headers={**cookie, "Content-Type": "application/x-www-form-urlencoded",
                                        "Origin": f"http://127.0.0.1:{port}"})
    assert status == 303, body
    status, _, body = request(port, "GET", "/", headers=cookie)
    assert "Send refused: assist-only pilot: send disabled for SUB-990" in body
    assert not (workbench.TO_CARRIER / "SUB-990.md").exists()
    assert not any(p.name.startswith("SUB-990") for p in workbench.TO_CARRIER.iterdir())

    audit_rows = rows(auth.AUDIT_LOG)
    assert any(r["action"] == "view" and r["user"] == "user" for r in audit_rows)
    assert any(r["action"] == "decision" and r["outcome"] == "ok" and r["user"] == "user" for r in audit_rows)
    assert any(r["action"] == "send" and r["outcome"] == "refused" and r["user"] == "user" for r in audit_rows)

    events = rows(pilot.EVENTS)
    assert any(e["action"] == "view" and e["actor"] == "user" for e in events), "C5: the display log carries the signed-in user"
    assert any(e["action"] == "decision" and e["outcome"] == "ok" for e in events)
    assert any(e["action"] == "send" and e["outcome"] == "refused" for e in events)
    assert pilot.summary(workbench.load_queue())["refusals"] >= 1


def test_an_anonymous_reader_sees_no_card_and_no_pilot_log(live):
    port, _, _ = live
    status, _, body = request(port, "GET", "/")
    assert status == 200 and "Sign in" in body
    assert "SUB-990" not in body and "ASSIST-ONLY PILOT" not in body
    assert not any(e["action"] == "view" for e in rows(pilot.EVENTS)), "no view row without a session"


def test_a_confirmation_without_every_value_is_refused_with_a_plain_reason(live):
    port, issuer, key = live
    session = sign_in(port, issuer, key)
    user = auth.session_from_cookie(session)
    form = urllib.parse.urlencode({"submission": "SUB-990", "action": "confirm", "reason": "partial",
                                   "csrf": auth.csrf_for(user), "ack": ["named_insured"]}, doseq=True)
    status, _, body = request(port, "POST", "/decision", body=form,
                               headers={"Cookie": session, "Content-Type": "application/x-www-form-urlencoded",
                                        "Origin": f"http://127.0.0.1:{port}"})
    assert status == 303, body
    status, _, body = request(port, "GET", "/", headers={"Cookie": session})
    assert "Decision refused: confirm every value before recording: premises_address" in body
    assert not workbench.LOG.is_file() or not any(r.get("action") == "confirm" for r in rows(workbench.LOG))
