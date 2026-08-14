"""Redact PII from log records so CloudWatch/stdout is not a leak path."""

from __future__ import annotations

import logging
from typing import Any


class PiiLogFilter(logging.Filter):
    """Applies the same redactor used for LLM egress to every log message."""

    def __init__(self, name: str = "") -> None:
        super().__init__(name)
        self._redactor: Any = None

    def _get_redactor(self) -> Any:
        if self._redactor is None:
            from insureflow.redaction.redactor import PIIRedactor

            self._redactor = PIIRedactor()
        return self._redactor

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            redactor = self._get_redactor()
            if isinstance(record.msg, str):
                record.msg = redactor.redact(record.msg, mask=False)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        k: redactor.redact(v, mask=False) if isinstance(v, str) else v for k, v in record.args.items()
                    }
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        redactor.redact(a, mask=False) if isinstance(a, str) else a for a in record.args
                    )
        except Exception:
            pass
        return True


def install_pii_log_filter() -> None:
    root = logging.getLogger()
    if any(isinstance(f, PiiLogFilter) for f in root.filters):
        return
    root.addFilter(PiiLogFilter())
