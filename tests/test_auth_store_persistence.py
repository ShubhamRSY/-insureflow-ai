"""File-backed UserStore must actually survive a process restart.

Regression test for a real bug: ``_load_locked`` iterated
``json.loads(raw)`` directly instead of ``.items()``, which iterates a
dict's KEYS only. Unpacking each key string into ``k, v`` either raised
(caught by the broad ``except ... ValueError`` — pydantic's
ValidationError is a ValueError subclass) or, for exactly-2-character
usernames, silently produced garbage. Either way every fresh UserStore
load from a file with real data silently reset to empty — invisible
within a single process (the already-loaded in-memory dict looked fine),
but a real user-data-loss bug on every actual restart.
"""

from __future__ import annotations

from pathlib import Path

from insureflow.auth import Role
from insureflow.auth.models import User
from insureflow.auth.store import UserStore


def test_userstore_reloads_multiple_users_after_reconstruction(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("CELERY_BROKER_URL", "")
    path = tmp_path / "auth_users.json"

    store = UserStore(path=path)
    store["uw"] = User(username="uw", hashed_password="x", role=Role.VIEWER, org_id="acme")
    store["admin"] = User(username="admin", hashed_password="y", role=Role.ADMIN, org_id="acme")
    assert len(store) == 2

    # Simulate a process restart: a brand new instance reading the same file.
    reloaded = UserStore(path=path)
    assert len(reloaded) == 2
    reloaded_uw = reloaded.get("uw")
    assert reloaded_uw is not None
    assert reloaded_uw.org_id == "acme"
    reloaded_admin = reloaded.get("admin")
    assert reloaded_admin is not None
    assert reloaded_admin.role == Role.ADMIN


def test_userstore_single_user_also_survives_reload(tmp_path: Path, monkeypatch) -> None:
    """A single 2-character username is the case that silently 'succeeded'
    at wrongly unpacking (k, v) from the raw string instead of raising —
    the most dangerous form of this bug, since it produced no exception at
    all and just corrupted data instead. Covered explicitly here."""
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("CELERY_BROKER_URL", "")
    path = tmp_path / "auth_users.json"

    store = UserStore(path=path)
    store["uw"] = User(username="uw", hashed_password="x", role=Role.VIEWER, org_id="acme")

    reloaded = UserStore(path=path)
    assert len(reloaded) == 1
    user = reloaded.get("uw")
    assert user is not None
    assert user.username == "uw"
    assert user.org_id == "acme"
