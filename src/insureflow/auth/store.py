from __future__ import annotations

import json
from pathlib import Path

from insureflow.auth.models import User

# Persisted outside hot-reload paths when possible; survives uvicorn --reload
_DEFAULT_PATH = Path.cwd() / ".insureflow" / "auth_users.json"


class UserStore:
    """File-backed user store — survives server reloads during development."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _DEFAULT_PATH
        self._users: dict[str, User] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self._users = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._users = {k: User.model_validate(v) for k, v in raw.items()}
        except (json.JSONDecodeError, OSError, ValueError):
            self._users = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: v.model_dump(mode="json") for k, v in self._users.items()}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get(self, username: str) -> User | None:
        return self._users.get(username)

    def __contains__(self, username: str) -> bool:
        return username in self._users

    def __bool__(self) -> bool:
        return bool(self._users)

    def __len__(self) -> int:
        return len(self._users)

    def items(self):
        return self._users.items()

    def __setitem__(self, username: str, user: User) -> None:
        self._users[username] = user
        self.save()

    def clear(self) -> int:
        count = len(self._users)
        self._users.clear()
        if self.path.exists():
            self.path.unlink()
        return count


_user_store = UserStore()


def get_user_store() -> UserStore:
    return _user_store


def clear_user_store() -> int:
    return _user_store.clear()
