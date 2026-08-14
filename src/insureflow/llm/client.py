from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterator, Optional, cast

from insureflow.config import settings

logger = logging.getLogger(__name__)


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

        if model_tier == "cheap":
            self.provider = settings.llm_cheap_provider or settings.llm_provider
            self.model = settings.llm_cheap_model
            self.api_key = settings.llm_cheap_api_key or settings.llm_api_key
            self.base_url = settings.llm_cheap_base_url or settings.llm_base_url
        elif model_tier == "expensive":
            self.provider = settings.llm_expensive_provider or settings.llm_provider
            self.model = settings.llm_expensive_model
            self.api_key = settings.llm_expensive_api_key or settings.llm_api_key
            self.base_url = settings.llm_expensive_base_url or settings.llm_base_url
        else:
            self.provider = settings.llm_provider
            self.model = settings.llm_model
            self.api_key = settings.llm_api_key
            self.base_url = settings.llm_base_url

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

        if provider == "openai" or provider == "vllm":
            from openai import OpenAI

            client_kwargs: dict[str, Any] = {
                "api_key": self.api_key or "sk-local",
            }
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self._client = OpenAI(**client_kwargs)

        elif provider == "anthropic" or provider == "claude":
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
        return self._redactor.redact(text)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[type] = None,
    ) -> str:
        budget = self._get_budget()
        if budget is not None:
            budget.enforce()

        client = self._get_client()
        provider = self.provider
        system_prompt = self._redact_for_egress(system_prompt)
        user_prompt = self._redact_for_egress(user_prompt)

        if provider == "openai" or provider == "vllm":
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

        elif provider == "anthropic" or provider == "claude":
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

        else:
            msg = f"Unsupported LLM provider: {provider}"
            raise ValueError(msg)

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[StreamChunk]:
        """Stream a completion token-by-token, yielding StreamChunk deltas.

        Supports openai/vllm (chat.completions streaming) and anthropic
        (messages streaming). The final chunk carries provider usage.
        """
        client = self._get_client()
        provider = self.provider
        system_prompt = self._redact_for_egress(system_prompt)
        user_prompt = self._redact_for_egress(user_prompt)

        if provider == "openai" or provider == "vllm":
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

        if provider == "anthropic" or provider == "claude":
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
        raw = self.complete(system_prompt, user_prompt)

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
        """Generates a vector embedding for the given text."""
        client = self._get_client()
        provider = self.provider
        text = self._redact_for_egress(text)

        if provider in ("openai", "vllm"):
            # Using OpenAI's standard embedding model
            response = client.embeddings.create(input=text, model="text-embedding-3-small")
            return cast(list[float], response.data[0].embedding)

        # Fallback for non-supported providers during local testing
        return [0.0] * 1536
