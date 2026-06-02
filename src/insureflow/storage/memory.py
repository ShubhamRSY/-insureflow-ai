from __future__ import annotations

from typing import Any, Optional

from insureflow.storage.base import StorageBackend


class InMemoryStore(StorageBackend):
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def save(self, key: str, value: Any) -> None:
        self._data[key] = value

    def load(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def list_keys(self, prefix: str = "") -> list[str]:
        return [k for k in self._data if k.startswith(prefix)]
