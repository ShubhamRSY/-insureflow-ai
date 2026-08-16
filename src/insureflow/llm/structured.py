"""Schema-forced extraction via Instructor, with JSON-schema fallback.

``instructor`` (https://github.com/instruction-center/instructor) patches the
OpenAI SDK so a Pydantic model is returned directly instead of raw JSON text —
better schema adherence than prompt-only extraction. When the package is not
installed (or the provider is Anthropic), we fall back to the repo's built-in
JSON-schema completion + ``model_validate_json`` path, so behavior never
regresses.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_OPENAI_COMPAT = frozenset({"openai", "vllm", "llama", "ollama"})


def instructor_available() -> bool:
    try:
        import instructor  # noqa: F401

        return True
    except ImportError:
        return False


def extract_structured(
    client: Any,
    system_prompt: str,
    user_prompt: str,
    response_model: type,
) -> Any:
    """Return a validated ``response_model`` instance using the best available path."""
    if instructor_available() and getattr(client, "provider", "") in _OPENAI_COMPAT:
        try:
            return _extract_with_instructor(client, system_prompt, user_prompt, response_model)
        except Exception as exc:
            logger.warning("instructor extraction failed (%s) — falling back to JSON-schema", exc)
    return client.extract_structured(system_prompt, user_prompt, response_model)


def _extract_with_instructor(client: Any, system_prompt: str, user_prompt: str, response_model: type) -> Any:
    import instructor

    raw_client = client._get_client()  # the underlying OpenAI-compatible client
    patched = instructor.from_openai(raw_client, mode=instructor.Mode.JSON_SCHEMA)
    response = patched.chat.completions.create(
        model=client.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_model=response_model,
        max_tokens=client.max_tokens,
        temperature=client.temperature,
    )
    return response
