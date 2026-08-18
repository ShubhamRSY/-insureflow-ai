from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCollector(ABC):
    """Abstract base for regulatory data collectors."""

    def __init__(self, source_name: str, config: dict[str, Any]) -> None:
        self.source_name = source_name
        self.config = config

    @abstractmethod
    def collect(self) -> list[dict[str, Any]]:
        """Poll the source and return raw data items.

        Returns list of dicts, each with at minimum:
        - source: str (source name)
        - title: str (headline/summary)
        - url: str (link to original)
        - published: str (ISO date)
        - raw: dict (full parsed data)
        """
        ...

    def is_enabled(self) -> bool:
        """Return whether this collector is enabled in config."""
        return bool(self.config.get("enabled", False))
