from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseParser(ABC):
    @abstractmethod
    def parse(self, raw_data: str, submission_id: str) -> Any: ...
