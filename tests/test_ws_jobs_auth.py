"""GET /ws/jobs/{job_id} must honor the same live-user-store checks as
every REST endpoint — a disabled/deleted user's still-unexpired JWT must
not be able to keep streaming job status, and org scoping must use the
live-resolved org_id, not a potentially stale JWT claim.

Regression test for a real bug: this endpoint called
``decode_access_token`` directly, bypassing both ``get_current_user`` and
``get_current_user_optional`` (and the live-store re-check both of those
apply) entirely.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from insureflow.api import app
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import clear_user_store, get_user_store


def test_websocket_rejects_disabled_user() -> None:
    clear_user_store()
    store = get_user_store()
    store["ws-disabled"] = User(username="ws-disabled", hashed_password="x", role=Role.VIEWER, org_id="acme", disabled=True)
    token = create_access_token({"sub": "ws-disabled", "role": Role.VIEWER.value, "org_id": "acme"})

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/jobs/no-such-job?token={token}"):
            pass
    assert exc_info.value.code == 4001


def test_websocket_rejects_deleted_user() -> None:
    clear_user_store()
    token = create_access_token({"sub": "ws-never-existed", "role": Role.VIEWER.value, "org_id": "acme"})

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/jobs/no-such-job?token={token}"):
            pass
    assert exc_info.value.code == 4001


def test_websocket_uses_live_resolved_org_id_not_stale_jwt_claim() -> None:
    """The org_id embedded in the JWT at issuance must not be trusted over
    the user's current live org_id — same guarantee get_current_user gives
    every REST endpoint."""
    clear_user_store()
    store = get_user_store()
    store["ws-user"] = User(username="ws-user", hashed_password="x", role=Role.VIEWER, org_id="acme")
    ws_user = store.get("ws-user")
    assert ws_user is not None
    resolved_org_id = ws_user.org_id

    # JWT deliberately embeds a DIFFERENT (stale/wrong) org_id than the
    # user's live record — the endpoint must not trust it.
    token = create_access_token({"sub": "ws-user", "role": Role.VIEWER.value, "org_id": "some-other-org-entirely"})

    from insureflow.storage.job_store import get_job_store

    job_store = get_job_store()
    job_store.set("insurance", "job-under-resolved-org", {"status": "processing"}, org_id=resolved_org_id)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/jobs/job-under-resolved-org?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["job_id"] == "job-under-resolved-org"
