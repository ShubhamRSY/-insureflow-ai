from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from insureflow.config import settings

logger = logging.getLogger(__name__)

_OPENAI_COMPAT = frozenset({"openai", "vllm", "llama", "ollama"})
_ANTHROPIC = frozenset({"anthropic", "claude"})


def _is_transient_error(exc: Exception) -> bool:
    """Distinguish transient (retryable) errors from permanent ones."""
    msg = str(exc).lower()
    exc_type = type(exc).__name__
    # Rate limits — always retryable
    if "429" in msg or "rate" in msg or "too many" in msg:
        return True
    # Network / timeout
    if any(k in msg for k in ("timeout", "timed out", "connection", "network", "eof", "reset")):
        return True
    if "timeout" in exc_type.lower() or "connection" in exc_type.lower():
        return True
    # Server errors (5xx) — retryable
    if any(f"{c}" in msg for c in ("500", "502", "503", "504")):
        return True
    # Authentication errors — NOT retryable
    if "401" in msg or "403" in msg or "auth" in msg or "permission" in msg:
        return False
    # Bad request (400) — NOT retryable
    if "400" in msg or "invalid" in msg:
        return False
    # Default: treat unknown errors as non-transient to avoid infinite retry loops
    return False


@dataclass
class StreamChunk:
    """One streamed token/delta from an LLM response.

    text: answer-token text (non-reasoning).
    reasoning: reasoning/tokenizer-hidden token text, when the provider exposes it.
    usage: provider usage object populated on the final chunk (may be None).
    """

    text: str = ""
    reasoning: str = ""
    usage: Any = None


class LLMClient:
    def __init__(
        self,
        model_tier: str = "default",
        agent: str = "",
        redact_pii: bool = True,
    ) -> None:
        self.model_tier = model_tier
        self.agent = agent
        self.redact_pii = redact_pii
        self._client: Any = None
        self._redactor: Any = None
        self._enable_fallback = True

        if model_tier == "cheap":
            self.provider = os.getenv("LLM_CHEAP_PROVIDER") or settings.llm_cheap_provider or os.getenv("LLM_PROVIDER") or settings.llm_provider
            self.model = os.getenv("LLM_CHEAP_MODEL") or settings.llm_cheap_model
            self.api_key = os.getenv("LLM_CHEAP_API_KEY") or settings.llm_cheap_api_key or os.getenv("LLM_API_KEY") or settings.llm_api_key
            self.base_url = os.getenv("LLM_CHEAP_BASE_URL") or settings.llm_cheap_base_url or os.getenv("LLM_BASE_URL") or settings.llm_base_url
        elif model_tier == "expensive":
            self.provider = os.getenv("LLM_EXPENSIVE_PROVIDER") or settings.llm_expensive_provider or os.getenv("LLM_PROVIDER") or settings.llm_provider
            self.model = os.getenv("LLM_EXPENSIVE_MODEL") or settings.llm_expensive_model
            self.api_key = os.getenv("LLM_EXPENSIVE_API_KEY") or settings.llm_expensive_api_key or os.getenv("LLM_API_KEY") or settings.llm_api_key
            self.base_url = os.getenv("LLM_EXPENSIVE_BASE_URL") or settings.llm_expensive_base_url or os.getenv("LLM_BASE_URL") or settings.llm_base_url
        else:
            self.provider = os.getenv("LLM_PROVIDER") or settings.llm_provider
            self.model = os.getenv("LLM_MODEL") or settings.llm_model
            self.api_key = os.getenv("LLM_API_KEY") or settings.llm_api_key
            self.base_url = os.getenv("LLM_BASE_URL") or settings.llm_base_url

        self.provider = (self.provider or "openai").strip().lower()
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens

        self._tracker: Any = None
        self._budget: Any = None

    def _get_tracker(self) -> Any:
        if self._tracker is None:
            try:
                from insureflow.llm.tracker import get_token_tracker

                self._tracker = get_token_tracker()
            except Exception:
                logger.warning("Failed to initialise token tracker", exc_info=True)
                pass
        return self._tracker

    def _get_budget(self) -> Any:
        if self._budget is None:
            try:
                from insureflow.llm.budget import get_budget_manager

                self._budget = get_budget_manager()
            except Exception:
                logger.warning("Failed to initialise budget manager", exc_info=True)
                pass
        return self._budget

    def _track_usage(self, response: Any) -> None:
        tracker = self._get_tracker()
        if tracker is None:
            return
        input_tokens = 0
        cached_tokens = 0
        output_tokens = 0
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                input_tokens = getattr(usage, "prompt_tokens", 0) or 0
                output_tokens = getattr(usage, "completion_tokens", 0) or 0
                details = getattr(usage, "prompt_tokens_details", None)
                if details is not None:
                    cached_tokens = getattr(details, "cached_tokens", 0) or 0
        except Exception:
            logger.warning("Failed to extract usage from LLM response", exc_info=True)
            pass
        if input_tokens > 0 or cached_tokens > 0 or output_tokens > 0:
            tracker.record(
                model=self.model,
                tier=self.model_tier,
                input_tokens=input_tokens,
                cached_tokens=cached_tokens,
                output_tokens=output_tokens,
                agent=self.agent,
            )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        provider = self.provider

        if provider in _OPENAI_COMPAT:
            from openai import OpenAI

            client_kwargs: dict[str, Any] = {
                "api_key": self.api_key or "sk-local",
            }
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self._client = OpenAI(**client_kwargs)

        elif provider in _ANTHROPIC:
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError("Anthropic package required. Install: pip install anthropic")
            api_key = self.api_key or settings.claude_api_key
            if not api_key:
                raise ValueError("Claude API key required. Set ANTHROPIC_API_KEY, CLAUDE_API_KEY, or LLM_API_KEY")
            kwargs: dict[str, Any] = {"api_key": api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = Anthropic(**kwargs)

        else:
            msg = f"Unsupported LLM provider: {provider}"
            raise ValueError(msg)

        return self._client

    def _redact_for_egress(self, text: str) -> str:
        """Strip named insureds and PII before any model API call.

        Deterministic UW still sees the original file locally. Only the
        payload that leaves the process toward an LLM provider is redacted.
        """
        if not self.redact_pii or not text:
            return text
        if self._redactor is None:
            from insureflow.redaction.redactor import PIIRedactor

            self._redactor = PIIRedactor()
        # Full token replacement — last-4 / email domain must not leave the process.
        return str(self._redactor.redact(text, mask=False))

    def _spawn_fallback(self) -> LLMClient | None:
        if not self._enable_fallback:
            return None
        provider = os.getenv("LLM_FALLBACK_PROVIDER", "").strip().lower()
        if not provider or provider == self.provider:
            return None
        fb = LLMClient(model_tier=self.model_tier, agent=self.agent, redact_pii=self.redact_pii)
        fb._enable_fallback = False
        fb.provider = provider
        fb.model = os.getenv("LLM_FALLBACK_MODEL", "").strip() or fb.model
        fb.api_key = os.getenv("LLM_FALLBACK_API_KEY", "").strip() or fb.api_key
        fb.base_url = os.getenv("LLM_FALLBACK_BASE_URL", "").strip() or fb.base_url
        fb._client = None
        return fb

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[type] = None,
    ) -> str:
        from insureflow.llm.guardrails import guard_model_output, neutralize_injection

        budget = self._get_budget()
        if budget is not None:
            budget.enforce()

        system_prompt = self._redact_for_egress(system_prompt)
        user_prompt = neutralize_injection(self._redact_for_egress(user_prompt))

        last_exc: Exception | None = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                text = self._complete_once(system_prompt, user_prompt, response_format)
                return guard_model_output(text)
            except Exception as exc:
                last_exc = exc
                is_transient = _is_transient_error(exc)
                if attempt < max_retries - 1 and is_transient:
                    backoff = min(2**attempt * 1.0, 10.0)
                    logger.warning(
                        "LLM %s/%s attempt %d/%d failed (%s): %s — retrying in %.1fs",
                        self.provider,
                        self.model,
                        attempt + 1,
                        max_retries,
                        type(exc).__name__,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue
                # Non-transient or final attempt: try fallback
                fb = self._spawn_fallback()
                if fb is None:
                    raise
                logger.warning(
                    "Primary LLM (%s/%s) failed: %s — routing to %s",
                    self.provider,
                    self.model,
                    exc,
                    fb.provider,
                )
                text = fb._complete_once(system_prompt, user_prompt, response_format)
                return guard_model_output(text)
        raise last_exc  # type: ignore[misc]

    def _complete_once(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[type] = None,
    ) -> str:
        client = self._get_client()
        provider = self.provider

        if provider in _OPENAI_COMPAT:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            if response_format is not None:
                try:
                    from pydantic import BaseModel

                    if issubclass(response_format, BaseModel):
                        kwargs["response_format"] = response_format
                except (ImportError, TypeError):
                    pass

            response = client.chat.completions.create(**kwargs)
            self._track_usage(response)
            return response.choices[0].message.content or ""

        if provider in _ANTHROPIC:
            kwargs = {
                "model": self.model,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            response = client.messages.create(**kwargs)
            self._track_usage(response)
            return str(response.content[0].text) if response.content else ""

        msg = f"Unsupported LLM provider: {provider}"
        raise ValueError(msg)

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[StreamChunk]:
        """Stream a completion token-by-token, yielding StreamChunk deltas.

        Supports openai/vllm (chat.completions streaming) and anthropic
        (messages streaming). The final chunk carries provider usage.
        """
        client = self._get_client()
        provider = self.provider
        from insureflow.llm.guardrails import neutralize_injection

        system_prompt = self._redact_for_egress(system_prompt)
        user_prompt = neutralize_injection(self._redact_for_egress(user_prompt))

        if provider in _OPENAI_COMPAT:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            for chunk in client.chat.completions.create(**kwargs):
                if not getattr(chunk, "choices", None):
                    usage = getattr(chunk, "usage", None)
                    if usage is not None:
                        yield StreamChunk(usage=usage)
                    continue
                delta = chunk.choices[0].delta
                text = getattr(delta, "content", None) or ""
                reasoning = getattr(delta, "reasoning_content", None) or ""
                yield StreamChunk(text=text, reasoning=reasoning)
            return

        if provider in _ANTHROPIC:
            kwargs = {
                "model": self.model,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            with client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield StreamChunk(text=text)
            return

        msg = f"Unsupported LLM provider: {provider}"
        raise ValueError(msg)

    def extract_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type,
    ) -> Any:
        raw = self.complete(system_prompt, user_prompt, response_format=response_model)

        clean_raw = raw.strip()
        if clean_raw.startswith("```json"):
            clean_raw = clean_raw[7:]
        if clean_raw.startswith("```"):
            clean_raw = clean_raw[3:]
        if clean_raw.endswith("```"):
            clean_raw = clean_raw[:-3]
        clean_raw = clean_raw.strip()

        try:
            return response_model.model_validate_json(clean_raw)  # type: ignore[attr-defined]
        except Exception:
            return response_model(raw=raw)

    def embed(self, text: str) -> list[float]:
        """Guideline/query embedding — local hashed vectors in bank mode."""
        from insureflow.llm.embeddings import embed_text

        return embed_text(self._redact_for_egress(text))
