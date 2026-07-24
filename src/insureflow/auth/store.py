from __future__ import annotations

import json
import logging
import os
from collections.abc import ItemsView
from typing import Any
from pathlib import Path

from insureflow.auth.models import User

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path.cwd() / ".insureflow" / "auth_users.json"

_REDIS_KEY = "rytera:auth:users"


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
        self._redis = _get_redis_client()
        self._path = path or _DEFAULT_PATH
        self.load()

    def load(self) -> None:
        if self._redis:
            try:
                raw = self._redis.get(_REDIS_KEY)
                if raw:
                    data = json.loads(raw)
                    self._users = {k: User.model_validate(v) for k, v in data.items()}
                    logger.info("Loaded %d users from Redis", len(self._users))
                    return
            except Exception as exc:
                logger.warning("Redis load failed, trying file: %s", exc)

        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                self._users = {k: User.model_validate(v) for k, v in raw.items()}
            except (json.JSONDecodeError, OSError, ValueError):
                self._users = {}
        else:
            self._users = {}

    def save(self) -> None:
        payload = {k: v.model_dump(mode="json") for k, v in self._users.items()}
        data = json.dumps(payload, indent=2)

        if self._redis:
            try:
                self._redis.set(_REDIS_KEY, data)
            except Exception as exc:
                logger.warning("Redis save failed: %s", exc)

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(data, encoding="utf-8")
        except OSError:
            pass

    def get(self, username: str) -> User | None:
        return self._users.get(username)

    def __contains__(self, username: str) -> bool:
        return username in self._users

    def __bool__(self) -> bool:
        return bool(self._users)

    def __len__(self) -> int:
        return len(self._users)

    def items(self) -> ItemsView[str, User]:
        return self._users.items()

    def __setitem__(self, username: str, user: User) -> None:
        self._users[username] = user
        self.save()

    def clear(self) -> int:
        count = len(self._users)
        self._users.clear()
        if self._redis:
            try:
                self._redis.delete(_REDIS_KEY)
            except Exception:
                pass
        if self._path.exists():
            try:
                self._path.unlink()
            except OSError:
                pass
        return count


_user_store = UserStore()


def get_user_store() -> UserStore:
    return _user_store


def clear_user_store() -> int:
    return _user_store.clear()
