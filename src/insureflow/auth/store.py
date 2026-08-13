from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from collections.abc import ItemsView
from pathlib import Path
from typing import Any

from insureflow.auth.models import User
from insureflow.storage.lock import FileLock, atomic_write

logger = logging.getLogger(__name__)


def _test_namespace() -> bool:
    """Tests run against an isolated store so they can never wipe real credentials."""
    return os.environ.get("INSUREFLOW_AUTH_TESTING") == "1"


def _default_path() -> Path:
    if os.environ.get("INSUREFLOW_AUTH_STORE_PATH"):
        return Path(os.environ["INSUREFLOW_AUTH_STORE_PATH"])
    if _test_namespace():
        return Path(tempfile.gettempdir()) / "insureflow_test" / "auth_users.json"
    return Path.cwd() / ".insureflow" / "auth_users.json"


_DEFAULT_PATH = _default_path()

_REDIS_KEY = "rytera:auth:users"
_TEST_REDIS_KEY = "rytera:auth:users:test"


def _get_redis_client() -> Any:
    redis_url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "")
    if not redis_url or not redis_url.startswith("redis"):
        return None
    try:
        import redis as _redis

        client = _redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
        client.ping()
        return client
    except Exception as exc:
        logger.warning("Redis unavailable for user store: %s", exc)
        return None


class UserStore:
    """Redis-backed user store with file fallback — survives container redeploys."""

    def __init__(self, path: Path | None = None) -> None:
        self._users: dict[str, User] = {}
        self._lock = threading.RLock()
        self._redis = _get_redis_client()
        self._redis_key = _TEST_REDIS_KEY if _test_namespace() else _REDIS_KEY
        self._path = path or _DEFAULT_PATH
        self.load()

    def load(self) -> None:
        with self._lock:
            self._load_locked()

    def _load_locked(self) -> None:
        if self._redis:
            try:
                raw = self._redis.get(self._redis_key)
                if raw:
                    data = json.loads(raw)
                    self._users = {k: User.model_validate(v) for k, v in data.items()}
                    logger.info("Loaded %d users from Redis", len(self._users))
                    return
            except Exception as exc:
                logger.warning("Redis load failed, trying file: %s", exc)

        if self._path.exists():
            try:
                with FileLock(str(self._path) + ".lock"):
                    raw = self._path.read_text(encoding="utf-8")
                self._users = {k: User.model_validate(v) for k, v in json.loads(raw).items()}
            except (json.JSONDecodeError, OSError, ValueError):
                self._users = {}
        else:
            self._users = {}

    def save(self) -> None:
        with self._lock:
            self._save_locked()

    def _save_locked(self) -> None:
        payload = {k: v.model_dump(mode="json") for k, v in self._users.items()}
        data = json.dumps(payload, indent=2)

        if self._redis:
            try:
                self._redis.set(self._redis_key, data)
            except Exception as exc:
                logger.warning("Redis save failed: %s", exc)

        try:
            with FileLock(str(self._path) + ".lock"):
                atomic_write(self._path, data)
        except OSError:
            pass

    def get(self, username: str) -> User | None:
        return self._users.get(username)

    def resolve_user(self, identifier: str) -> User | None:
        """Match by username key, then case-insensitive username/email lookup."""
        key = identifier.strip()
        if not key:
            return None
        user = self._users.get(key)
        if user:
            return user
        lower = key.lower()
        for candidate in self._users.values():
            if candidate.username.lower() == lower:
                return candidate
            if candidate.email and candidate.email.lower() == lower:
                return candidate
        return None

    def __contains__(self, username: str) -> bool:
        return username in self._users

    def __bool__(self) -> bool:
        return bool(self._users)

    def __len__(self) -> int:
        return len(self._users)

    def items(self) -> ItemsView[str, User]:
        return self._users.items()

    def __setitem__(self, username: str, user: User) -> None:
        with self._lock:
            self._users[username] = user
            self._save_locked()

    def clear(self) -> int:
        with self._lock:
            count = len(self._users)
            self._users.clear()
            if self._redis:
                try:
                    self._redis.delete(self._redis_key)
                except Exception:
                    pass
            if self._path.exists():
                try:
                    backup = self._path.with_suffix(".json.bak")
                    self._path.rename(backup)
                except OSError:
                    pass
            return count


_user_store = UserStore()


def get_user_store() -> UserStore:
    return _user_store


def clear_user_store() -> int:
    return _user_store.clear()
