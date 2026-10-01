"""The MCP SSE mount must be authenticated and org-scoped.

A mount is a separate ASGI app, so none of the parent router's
``Depends(require_role(...))`` guards run for ``/mcp``. These tests drive
``MCPAuthMiddleware`` directly against a stub downstream app to pin the two
properties the old mount lacked: an anonymous caller gets nothing, and a
caller's tenancy comes from their verified token rather than anything they
pass as an argument.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from insureflow.auth import Role
from insureflow.auth.dependencies import extract_bearer_token
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import get_user_store
from insureflow.mcp.auth import (
    AUTH_DISABLED_ENV,
    MCPAuthError,
    MCPAuthMiddleware,
    _response_start,
    audit_auth_disabled,
    auth_enabled,
    bound_principal,
    current_principal,
    require_org_id,
    require_role,
)


async def _whoami(request: Any) -> JSONResponse:
    """Stand-in for an MCP tool: report the identity it can see.

    ``reached`` distinguishes "the middleware let the request through and
    the tool then refused" from "the middleware rejected the request" —
    both are 401, and conflating them would let a broken middleware pass.
    """
    try:
        org = require_org_id()
        return JSONResponse({"reached": True, "org_id": org})
    except MCPAuthError as exc:
        return JSONResponse({"reached": True, "error": exc.detail, "status": exc.status_code}, status_code=exc.status_code)


def _client() -> TestClient:
    app = Starlette(routes=[Route("/mcp/messages", _whoami, methods=["GET", "POST"])])
    return TestClient(MCPAuthMiddleware(app))


def _headers(*, org_id: str = "acme", role: Role = Role.VIEWER, username: str = "uw") -> tuple[dict[str, str], str]:
    """Register a user, mint a token, and report the org the store assigned.

    The store rewrites ``user.org_id`` in place when it maps a friendly org
    name onto its real org row (a Postgres org id, often a generated
    uuid), so tests compare against what the store settled on rather than
    the name they passed in.
    """
    user = User(
        username=username,
        hashed_password="unused",
        role=role,
        org_id=org_id,
    )
    get_user_store()[username] = user
    token = create_access_token({"sub": username, "role": role.value, "org_id": org_id})
    return {"Authorization": f"Bearer {token}"}, user.org_id


class TestMountAuthentication:
    def test_anonymous_caller_is_rejected(self) -> None:
        resp = _client().get("/mcp/messages")
        assert resp.status_code == 401
        assert "missing bearer token" in resp.json()["detail"]
        assert "reached" not in resp.json(), "request must not reach the tools"

    def test_invalid_token_is_rejected(self) -> None:
        resp = _client().get("/mcp/messages", headers={"Authorization": "Bearer not-a-jwt"})
        assert resp.status_code == 401
        assert "reached" not in resp.json()

    def test_wrong_scheme_is_rejected(self) -> None:
        resp = _client().get("/mcp/messages", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert resp.status_code == 401
        assert "reached" not in resp.json()

    def test_bearer_token_authenticates(self) -> None:
        headers, resolved_org = _headers()
        resp = _client().get("/mcp/messages", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"reached": True, "org_id": resolved_org}

    def test_disabled_account_is_forbidden(self) -> None:
        get_user_store()["disabled-user"] = User(
            username="disabled-user",
            hashed_password="unused",
            role=Role.VIEWER,
            org_id="acme",
            disabled=True,
        )
        token = create_access_token({"sub": "disabled-user", "role": "viewer", "org_id": "acme"})
        resp = _client().get("/mcp/messages", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert "reached" not in resp.json()

    def test_deleted_account_is_rejected(self) -> None:
        token = create_access_token({"sub": "ghost", "role": "admin", "org_id": "acme"})
        resp = _client().get("/mcp/messages", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "reached" not in resp.json()

    def test_principal_does_not_leak_between_requests(self) -> None:
        """A second caller's request must not inherit the first one's org."""
        client = _client()
        headers_a, org_a = _headers(org_id="tenant-a", username="a")
        headers_b, org_b = _headers(org_id="tenant-b", username="b")
        assert org_a != org_b, "the two test orgs must actually differ"
        assert client.get("/mcp/messages", headers=headers_a).json()["org_id"] == org_a
        assert client.get("/mcp/messages", headers=headers_b).json()["org_id"] == org_b
        assert current_principal() is None, "principal must not outlive the request"

    def test_rejection_content_length_matches_body(self) -> None:
        """Content-Length must be measured from the bytes actually sent.

        No reachable detail currently needs JSON escaping, so this pins the
        contract directly: a detail containing a quote or backslash encodes
        longer than the detail itself, and a Content-Length derived from
        the unescaped detail would desync the response.
        """
        detail = 'a"b\\c'
        payload = json.dumps({"detail": detail}).encode("utf-8")
        assert len(payload) != len(detail.encode("utf-8")), "detail must need JSON escaping for this to test anything"

        headers = dict(_response_start(401, payload)["headers"])
        assert int(headers[b"content-length"]) == len(payload)


class TestEventSourceFallback:
    def test_query_param_token_accepted(self) -> None:
        """EventSource cannot set headers, so the SSE connect may carry the token."""
        headers, resolved_org = _headers()
        token = headers["Authorization"].split(" ", 1)[1]
        resp = _client().get(f"/mcp/messages?access_token={token}")
        assert resp.status_code == 200
        assert resp.json() == {"reached": True, "org_id": resolved_org}


class TestPrincipalScoping:
    def test_org_comes_from_token_not_argument(self) -> None:
        with bound_principal(_principal(org_id="real-org")):
            assert require_org_id() == "real-org"

    def test_no_principal_fails_closed(self) -> None:
        with pytest.raises(MCPAuthError) as exc:
            require_org_id()
        assert exc.value.status_code == 401

    def test_blank_org_id_is_refused(self) -> None:
        with bound_principal(_principal(org_id="   ")), pytest.raises(MCPAuthError) as exc:
            require_org_id()
        assert exc.value.status_code == 403

    def test_write_tool_rejects_viewer(self) -> None:
        with bound_principal(_principal(role=Role.VIEWER)), pytest.raises(MCPAuthError) as exc:
            require_role(Role.UNDERWRITER)
        assert exc.value.status_code == 403

    def test_write_tool_allows_underwriter(self) -> None:
        with bound_principal(_principal(role=Role.UNDERWRITER)):
            assert require_role(Role.UNDERWRITER).org_id == "acme"


class TestAuthToggle:
    def test_enabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(AUTH_DISABLED_ENV, raising=False)
        assert auth_enabled() is True

    def test_can_be_disabled_for_local_demo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(AUTH_DISABLED_ENV, "false")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("BANK_MODE", raising=False)
        assert auth_enabled() is False
        assert audit_auth_disabled() == []
        # The middleware must not reject; the tool still refuses to guess a
        # tenant, so the 401 comes from the tool and carries `reached`.
        resp = _client().get("/mcp/messages")
        assert resp.json()["reached"] is True
        assert resp.status_code == 401

    def test_disabling_is_blocked_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(AUTH_DISABLED_ENV, "false")
        monkeypatch.setenv("ENVIRONMENT", "production")
        assert any("MCP_AUTH_ENABLED" in msg for msg in audit_auth_disabled())

    def test_disabling_is_blocked_in_bank_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(AUTH_DISABLED_ENV, "false")
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("BANK_MODE", "true")
        assert audit_auth_disabled() != []


class TestBearerParsing:
    @pytest.mark.parametrize(
        "header,expected",
        [
            ("Bearer abc", "abc"),
            ("bearer abc", "abc"),
            ("BEARER  abc  ", "abc"),
            ("Basic abc", None),
            ("abc", None),
            ("Bearer ", None),
            ("", None),
            (None, None),
        ],
    )
    def test_matches_httpbearer(self, header: str | None, expected: str | None) -> None:
        assert extract_bearer_token(header) == expected


def _principal(*, org_id: str = "acme", role: Role = Role.ADMIN) -> Any:
    from insureflow.auth.models import TokenData

    return TokenData(username="uw", role=role, org_id=org_id)
