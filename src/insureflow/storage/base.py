from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class StorageBackend(ABC):
    @abstractmethod
    def save(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def load(self, key: str) -> Optional[Any]: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]: ...
