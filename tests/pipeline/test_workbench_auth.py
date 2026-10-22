"""B-190: the workbench handler refuses anonymous reads and actions, and records the session user in the audit log."""

from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import auth
import llm_extract
import package
import prepare
import pytest
import quotes
import workbench


def request(port: int, method: str, path: str, *, body: str = "", headers: dict | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    payload = response.read().decode()
    result = (response.status, dict(response.getheaders()), payload)
    conn.close()
    return result


@pytest.fixture
def live(monkeypatch, tmp_path: Path):
    box = tmp_path / "box"
    box.mkdir()
    saved = {name: getattr(workbench, name) for name in ("PAGE", "LOG", "INBOX", "PENDING", "TO_PRODUCER", "TO_CARRIER", "BANNER")}
    saved_other = (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES, quotes.TO_CARRIER,
                   quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR, llm_extract.CACHE)
    saved_audit = auth.AUDIT_LOG
    workbench.sandbox(box)
    audit_path = box / "auth-audit.jsonl"
    audit_path.unlink(missing_ok=True)
    audit_path.with_suffix(".jsonl.lock").unlink(missing_ok=True)
    auth.AUDIT_LOG = audit_path
    workbench.MESSAGES.clear()
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("OIDC_CLIENT_ID", "workbench-test")
    monkeypatch.setenv("SESSION_SECRET", "y" * 40)
    user, session = auth.new_session("user", "Synthetic User", "", False)
    server = ThreadingHTTPServer(("127.0.0.1", 0), workbench.make_handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, user, session, audit_path
    finally:
        server.shutdown()
        for name, value in saved.items():
            setattr(workbench, name, value)
        (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES, quotes.TO_CARRIER,
         quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR, llm_extract.CACHE) = saved_other
        auth.AUDIT_LOG = saved_audit
        workbench.MESSAGES.clear()


def cookie(session: str) -> str:
    return f"{auth.SESSION_COOKIE}={session}"


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []


def test_anonymous_read_shows_no_submission(live):
    port, _, _, audit_path = live
    status, _, body = request(port, "GET", "/")
    assert status == 200 and "Sign in" in body
    assert "SUB-" not in body
    assert rows(audit_path) == []


def test_anonymous_action_is_refused_with_a_plain_reason_and_not_audited(live):
    port, _, _, audit_path = live
    status, _, body = request(port, "POST", "/decision", body="submission=SUB-002&action=decline&reason=x",
                              headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert status == 401
    assert "Sign-in required: decision refused was not recorded" in body
    assert rows(audit_path) == []


def test_signed_in_read_shows_the_queue_and_records_a_view_per_submission(live):
    port, user, session, audit_path = live
    status, _, body = request(port, "GET", "/", headers={"Cookie": cookie(session)})
    assert status == 200 and "Signed in as" in body and user.name in body
    assert "SUB-" in body and "Underwriter id" not in body
    viewed = [r for r in rows(audit_path) if r["action"] == "view"]
    assert viewed and all(r["user"] == "user" for r in viewed)


def test_a_missing_csrf_token_is_refused(live):
    port, _, session, audit_path = live
    port_body = "submission=SUB-002&action=decline&reason=synthetic"
    status, _, body = request(port, "POST", "/decision", body=port_body,
                              headers={"Cookie": cookie(session), "Content-Type": "application/x-www-form-urlencoded",
                                       "Origin": f"http://127.0.0.1:{port}"})
    assert status == 403 and "form token" in body
    assert not [r for r in rows(audit_path) if r["action"] == "decision"]


def test_a_foreign_origin_is_refused(live):
    port, user, session, _ = live
    body = f"submission=SUB-002&action=decline&reason=synthetic&csrf={auth.csrf_for(user)}"
    status, _, text = request(port, "POST", "/decision", body=body,
                              headers={"Cookie": cookie(session), "Content-Type": "application/x-www-form-urlencoded",
                                       "Origin": "https://evil.example"})
    assert status == 403 and "Origin" in text


def test_a_posted_actor_is_replaced_by_the_session_user(live):
    port, user, session, audit_path = live
    body = f"submission=SUB-002&action=decline&reason=synthetic&csrf={auth.csrf_for(user)}&underwriter_id=UW-001"
    status, headers, _ = request(port, "POST", "/decision", body=body,
                                 headers={"Cookie": cookie(session), "Content-Type": "application/x-www-form-urlencoded",
                                          "Origin": f"http://127.0.0.1:{port}"})
    assert status == 303 and headers["Location"] == "/#SUB-002"
    decision = json.loads(workbench.LOG.read_text().splitlines()[-1])
    assert decision["underwriter_id"] == "user"
    action = [r for r in rows(audit_path) if r["action"] == "decision"][-1]
    assert action["user"] == "user" and action["outcome"] == "ok"


def test_logout_clears_the_cookie_and_is_audited(live):
    port, user, session, audit_path = live
    status, headers, _ = request(port, "POST", "/logout", body=f"csrf={auth.csrf_for(user)}",
                                 headers={"Cookie": cookie(session), "Content-Type": "application/x-www-form-urlencoded",
                                          "Origin": f"http://127.0.0.1:{port}"})
    assert status == 303
    assert any("Max-Age=0" in value for value in headers.values() if "Set-Cookie" in str(value)) or "Max-Age=0" in str(headers)
    assert rows(audit_path)[-1]["action"] == "logout"
