from __future__ import annotations

from typing import Any, Optional

from insureflow.config import settings


class LLMClient:
    def __init__(
        self,
        model_tier: str = "default",
    ) -> None:
        self.model_tier = model_tier
        self._client: Any = None

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

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[type] = None,
    ) -> str:
        client = self._get_client()
        provider = self.provider

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
            return response.content[0].text if response.content else ""

        else:
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
            return response_model.model_validate_json(clean_raw)
        except Exception:
            return response_model(raw=raw)

    def embed(self, text: str) -> list[float]:
        """Generates a vector embedding for the given text."""
        client = self._get_client()
        provider = self.provider

        if provider in ("openai", "vllm"):
            # Using OpenAI's standard embedding model
            response = client.embeddings.create(input=text, model="text-embedding-3-small")
            return response.data[0].embedding

        # Fallback for non-supported providers during local testing
        return [0.0] * 1536
