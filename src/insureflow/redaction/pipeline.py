from __future__ import annotations

from typing import Any

from insureflow.llm.client import LLMClient
from insureflow.redaction.redactor import PIIRedactor


class RedactedLLMClient(LLMClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.redactor = PIIRedactor()

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: type | None = None,
    ) -> str:
        redacted_system = self.redactor.redact(system_prompt)
        redacted_user = self.redactor.redact(user_prompt)
        return super().complete(redacted_system, redacted_user, response_format)

    def extract_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type,
    ) -> Any:
        redacted_system = self.redactor.redact(system_prompt)
        redacted_user = self.redactor.redact(user_prompt)
        return super().extract_structured(redacted_system, redacted_user, response_model)
