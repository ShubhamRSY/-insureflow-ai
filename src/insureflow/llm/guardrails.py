"""In-process model safety — PII on the way out. Not Guardrails.ai / NeMo."""

from __future__ import annotations

import re

_INJECTION = re.compile(
    r"(ignore\s+(all\s+)?previous\s+instructions|you\s+are\s+now\s+dan|"
    r"developer\s+mode\s+enabled|jailbreak\s+prompt)",
    re.IGNORECASE,
)


def neutralize_injection(text: str) -> str:
    """Strip classic jailbreak phrases from model-bound user text."""
    if not text:
        return text
    return _INJECTION.sub("[INSTRUCTION_BLOCKED]", text)


def guard_model_output(text: str) -> str:
    """Redact PII the model echoed before it reaches the desk UI or audit."""
    if not text:
        return text
    from insureflow.redaction.redactor import PIIRedactor

    return str(PIIRedactor().redact(text, mask=False))
