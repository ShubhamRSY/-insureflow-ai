"""Authentication and tenant scoping for the MCP surface.

The MCP server is mounted as a sub-application (``app.mount("/mcp", ...)``),
so it never passes through FastAPI's dependency injection. That means the
``Depends(require_role(...))`` guards on the REST routes are simply not in
the request path for MCP — the mount runs the SSE transport's own ASGI app
directly. Two consequences this module exists to close:

1. **No authentication at all.** Anyone who could reach ``/mcp`` could list
   and read every pipeline job, every underwriting memo, and add or delete
   writing-panel companies.
2. **Caller-supplied tenancy.** Every tenant-scoped tool took ``org_id`` as
   an argument defaulting to ``"default"``. Even with a valid token, *any*
   authenticated user could name *any* org and read its data.

The fix is deliberately boring: a plain ASGI middleware in front of the
mount authenticates the ``Authorization: Bearer`` header through the same
``authenticate_bearer`` the REST routes use, and stashes the resolved
principal in a :class:`~contextvars.ContextVar` for the duration of the
request. Tools read the org from that principal; no tool accepts an
``org_id`` argument at all. Failing to find a principal is an error, never
a silent fall back to ``"default"``.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator
from urllib.parse import parse_qs

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from insureflow.auth import Role
from insureflow.auth.dependencies import authenticate_bearer, extract_bearer_token, has_role
from insureflow.auth.models import TokenData
from insureflow.security.posture import resolve_security_posture

logger = logging.getLogger("insureflow.mcp")

#: Env var holding a bearer token that authenticates the whole stdio
#: process. stdio has no request to hang a header off, so this is how a
#: local MCP client (Claude Desktop, a CLI) proves who it is.
STDIO_TOKEN_ENV = "MCP_ACCESS_TOKEN"

#: Set to "false" to leave the SSE mount unauthenticated. Only ever
#: meaningful for a laptop demo on localhost; ``config.bootstrap_security``
#: turns it into a blocking startup error in hardened deployments.
AUTH_DISABLED_ENV = "MCP_AUTH_ENABLED"

_principal_var: ContextVar[TokenData | None] = ContextVar("insureflow_mcp_principal", default=None)


class MCPAuthError(Exception):
    """Raised inside a tool when there is no usable caller identity.

    Tools return errors as JSON strings (that is the MCP tool-result shape
    this server already uses), so this carries the status code the
    transport *would* have returned for the middleware to reproduce.
    """

    def __init__(self, detail: str, status_code: int = 401) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


# ── Principal plumbing ────────────────────────────────────────────


@contextmanager
def bound_principal(principal: TokenData | None) -> Iterator[None]:
    """Scope a principal to a block — used by the middleware and by tests."""
    token = _principal_var.set(principal)
    try:
        yield
    finally:
        _principal_var.reset(token)


def current_principal() -> TokenData | None:
    """The authenticated caller, or None when there is no bound identity."""
    return _principal_var.get()


def require_principal() -> TokenData:
    """The authenticated caller.

    Raises :class:`MCPAuthError` rather than degrading to a default org.
    An unauthenticated tenant-scoped read has no safe interpretation, so
    the honest answer is to refuse it.
    """
    principal = _principal_var.get()
    if principal is None:
        raise MCPAuthError("Authentication required: no verified caller identity for this request", 401)
    return principal


def require_org_id() -> str:
    """The org the caller belongs to — the only tenancy any tool may use."""
    org_id = (require_principal().org_id or "").strip()
    if not org_id:
        raise MCPAuthError("Token carries no org_id; cannot scope this read", 403)
    return org_id


def require_role(min_role: Role) -> TokenData:
    """Role gate mirroring ``auth.dependencies.require_role`` for tool code."""
    principal = require_principal()
    if not has_role(principal, min_role):
        role_value = principal.role.value if principal.role else "none"
        raise MCPAuthError(f"Role '{role_value}' insufficient, requires '{min_role.value}'", 403)
    return principal


def auth_enabled() -> bool:
    """Whether the SSE mount should authenticate.

    Defaults to on everywhere. The escape hatch exists so a fresh clone
    still has a working ``/mcp`` on localhost without minting a token, and
    is rejected at startup under BANK_MODE/production.
    """
    flag = os.getenv(AUTH_DISABLED_ENV, "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    return True


def bind_process_principal(token: str | None = None) -> TokenData | None:
    """Authenticate a whole stdio process and bind the principal to it.

    stdio has no HTTP request, so the identity comes from
    ``MCP_ACCESS_TOKEN`` instead of a header. Returns the resolved
    principal, or None when no token is configured — in which case
    org-scoped tools fail closed with an actionable message while
    tenant-agnostic tools (health, life taxonomy, source listing, the
    mortgage calculator) keep working.
    """
    raw = (token if token is not None else os.getenv(STDIO_TOKEN_ENV, "")).strip()
    if not raw:
        return None
    principal = authenticate_bearer(raw)
    _principal_var.set(principal)
    return principal


# ── ASGI middleware ───────────────────────────────────────────────


def _response_start(status_code: int, payload: bytes) -> Message:
    return {
        "type": "http.response.start",
        "status": status_code,
        "headers": [
            (b"content-type", b"application/json"),
            # Measured from the exact bytes that get sent — the JSON
            # encoding of a detail containing a quote or backslash is
            # longer than the detail itself.
            (b"content-length", str(len(payload)).encode("latin-1")),
            (b"www-authenticate", b"Bearer"),
        ],
    }


class MCPAuthMiddleware:
    """Authenticates the MCP SSE mount and binds the caller's identity.

    Wraps the mounted ASGI app rather than relying on a FastAPI dependency,
    because a mount is a separate ASGI app and inherits none of the parent
    router's dependency graph. The middleware only *reads* the response —
    it does not buffer it — so long-lived SSE streams are unaffected.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or not auth_enabled():
            await self.app(scope, receive, send)
            return

        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope.get("headers") or []}
        # Browsers cannot set headers on an EventSource, so the token may
        # also arrive as a query parameter on the SSE connect request.
        # Accepted deliberately: it is still a secret that must not be
        # logged, and the alternative is no browser client at all.
        raw_token = extract_bearer_token(headers.get("authorization")) or _query_token(scope)
        if not raw_token:
            await self._reject(send, 401, "Authentication required: missing bearer token")
            return

        try:
            principal = authenticate_bearer(raw_token)
        except Exception as exc:
            status_code = getattr(exc, "status_code", 401)
            detail = getattr(exc, "detail", "Invalid or expired token")
            await self._reject(send, int(status_code), str(detail))
            return

        # Record it in scope state too, so anything downstream that has the
        # raw scope (logging, audit) can see who called without re-decoding.
        state = scope.setdefault("state", {})
        if isinstance(state, dict):
            state["mcp_principal"] = principal

        with bound_principal(principal):
            await self.app(scope, receive, send)

    async def _reject(self, send: Send, status_code: int, detail: str) -> None:
        payload = json.dumps({"detail": detail}).encode("utf-8")
        await send(_response_start(status_code, payload))
        await send({"type": "http.response.body", "body": payload})


def _query_token(scope: Scope) -> str | None:
    query = scope.get("query_string") or b""
    if not query:
        return None
    values = parse_qs(query.decode("latin-1")).get("access_token") or []
    return values[0].strip() if values and values[0] else None


def audit_auth_disabled() -> list[str]:
    """Blocking startup errors when the MCP mount is left unauthenticated."""
    if auth_enabled():
        return []
    if resolve_security_posture().is_hardened:
        return [f"{AUTH_DISABLED_ENV}=false is forbidden in BANK_MODE/production. The /mcp mount must be authenticated; remove the override."]
    return []
