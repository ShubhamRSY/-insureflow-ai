"""Model / endpoint / system registry matching Artificial Analysis vocabulary.

Maps the AA concepts (Model, Model Creator, Endpoint, System, Provider,
Serverless, Open Weights) onto concrete metadata used by the performance and
price benchmark (evaluations/benchmark.py) and cost tracking (llm/tracker.py).

  - Model: an LLM, identified by its API model id.
  - Model Creator: the org that developed/trained it.
  - Provider: the company hosting an endpoint (may equal the creator).
  - Endpoint: a hosted, API-accessible instance of a model.
  - System: a dedicated compute environment (VM) targetable for load tests
    (AA-SLT). Serverless endpoints have no fixed system.
  - Serverless: priced per input/output token, no fixed-rate reservation.
  - Open Weights: weights released publicly (license may not be OSI-open).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelCreator:
    """Organization that developed and trained a model."""

    name: str
    homepage: str = ""
    is_provider: bool = True  # companies are often both creators and providers

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "homepage": self.homepage,
            "is_provider": self.is_provider,
        }


@dataclass(frozen=True)
class Endpoint:
    """A hosted instance of a model reachable via an API."""

    provider: str
    base_url: str = ""
    serverless: bool = True
    region: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "serverless": self.serverless,
            "region": self.region,
        }


@dataclass(frozen=True)
class System:
    """A dedicated compute environment for running models under load (AA-SLT)."""

    name: str
    description: str = ""
    compute: str = ""  # e.g. "8x NVIDIA H100"
    max_seq_len: int | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "compute": self.compute,
            "max_seq_len": self.max_seq_len,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ModelMetadata:
    """Full AA-style metadata for one model."""

    model: str
    creator: ModelCreator
    open_weights: bool = False
    license: str = ""  # e.g. "OpenAI API", "Apache-2.0", "Meta Llama 3 License"
    parameters_b: float | None = None  # parameter count in billions
    release_date: str = ""
    endpoints: tuple[Endpoint, ...] = ()
    system: System | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "creator": self.creator.to_dict(),
            "open_weights": self.open_weights,
            "license": self.license,
            "parameters_b": self.parameters_b,
            "release_date": self.release_date,
            "endpoints": [e.to_dict() for e in self.endpoints],
            "system": self.system.to_dict() if self.system else None,
            "description": self.description,
        }


def _openai_creator() -> ModelCreator:
    return ModelCreator(name="OpenAI", homepage="https://openai.com", is_provider=True)


def _anthropic_creator() -> ModelCreator:
    return ModelCreator(name="Anthropic", homepage="https://anthropic.com", is_provider=True)


def _meta_creator() -> ModelCreator:
    return ModelCreator(name="Meta", homepage="https://ai.meta.com", is_provider=False)


def _mistral_creator() -> ModelCreator:
    return ModelCreator(name="Mistral AI", homepage="https://mistral.ai", is_provider=True)


def _openai_endpoint(region: str = "us-east-1") -> Endpoint:
    return Endpoint(
        provider="OpenAI",
        base_url="https://api.openai.com/v1",
        serverless=True,
        region=region,
    )


def _anthropic_endpoint(region: str = "us-east-1") -> Endpoint:
    return Endpoint(
        provider="Anthropic",
        base_url="https://api.anthropic.com/v1",
        serverless=True,
        region=region,
    )


# Canonical registry: model id -> AA-style metadata. Extend as models are added.
MODEL_REGISTRY: dict[str, ModelMetadata] = {
    "gpt-4o": ModelMetadata(
        model="gpt-4o",
        creator=_openai_creator(),
        open_weights=False,
        license="OpenAI API Terms",
        parameters_b=None,
        release_date="2024-05-13",
        endpoints=(_openai_endpoint(),),
        system=None,
        description="OpenAI flagship multimodal model (2024).",
    ),
    "gpt-4o-mini": ModelMetadata(
        model="gpt-4o-mini",
        creator=_openai_creator(),
        open_weights=False,
        license="OpenAI API Terms",
        parameters_b=None,
        release_date="2024-07-18",
        endpoints=(_openai_endpoint(),),
        system=None,
        description="OpenAI small fast model, low-cost.",
    ),
    "gpt-4-turbo": ModelMetadata(
        model="gpt-4-turbo",
        creator=_openai_creator(),
        open_weights=False,
        license="OpenAI API Terms",
        parameters_b=None,
        release_date="2024-04-09",
        endpoints=(_openai_endpoint(),),
        system=None,
        description="OpenAI GPT-4 turbo (legacy).",
    ),
    "gpt-3.5-turbo": ModelMetadata(
        model="gpt-3.5-turbo",
        creator=_openai_creator(),
        open_weights=False,
        license="OpenAI API Terms",
        parameters_b=None,
        release_date="2023-03-01",
        endpoints=(_openai_endpoint(),),
        system=None,
        description="OpenAI GPT-3.5 turbo (legacy).",
    ),
    "claude-sonnet-4-20250514": ModelMetadata(
        model="claude-sonnet-4-20250514",
        creator=_anthropic_creator(),
        open_weights=False,
        license="Anthropic API Terms",
        parameters_b=None,
        release_date="2025-05-14",
        endpoints=(_anthropic_endpoint(),),
        system=None,
        description="Anthropic Claude Sonnet 4.",
    ),
    "claude-3-5-sonnet-20241022": ModelMetadata(
        model="claude-3-5-sonnet-20241022",
        creator=_anthropic_creator(),
        open_weights=False,
        license="Anthropic API Terms",
        parameters_b=None,
        release_date="2024-10-22",
        endpoints=(_anthropic_endpoint(),),
        system=None,
        description="Anthropic Claude 3.5 Sonnet.",
    ),
    "claude-3-haiku-20240307": ModelMetadata(
        model="claude-3-haiku-20240307",
        creator=_anthropic_creator(),
        open_weights=False,
        license="Anthropic API Terms",
        parameters_b=None,
        release_date="2024-03-07",
        endpoints=(_anthropic_endpoint(),),
        system=None,
        description="Anthropic Claude 3 Haiku (small/fast).",
    ),
    # Open-weights examples (for reference / self-hosted System benchmarking)
    "llama-3.1-8b-instruct": ModelMetadata(
        model="llama-3.1-8b-instruct",
        creator=_meta_creator(),
        open_weights=True,
        license="Meta Llama 3.1 License",
        parameters_b=8.0,
        release_date="2024-07-23",
        endpoints=(),
        system=None,
        description="Meta Llama 3.1 8B — open weights, Apache/Meta license.",
    ),
    "llama-3.1-70b-instruct": ModelMetadata(
        model="llama-3.1-70b-instruct",
        creator=_meta_creator(),
        open_weights=True,
        license="Meta Llama 3.1 License",
        parameters_b=70.0,
        release_date="2024-07-23",
        endpoints=(),
        system=None,
        description="Meta Llama 3.1 70B — open weights.",
    ),
    "mistral-large-2411": ModelMetadata(
        model="mistral-large-2411",
        creator=_mistral_creator(),
        open_weights=True,
        license="Mistral AI (open weights)",
        parameters_b=123.0,
        release_date="2024-11-18",
        endpoints=(
            Endpoint(provider="Mistral AI", base_url="https://api.mistral.ai/v1", serverless=True),
            Endpoint(provider="AWS Bedrock", base_url="", serverless=True, region="us-east-1"),
        ),
        system=None,
        description="Mistral Large 2 — open weights, multi-provider.",
    ),
}

# Model ids with pricing defined in llm/tracker.py (serverless, price per token).
_PRICED_MODEL_IDS: tuple[str, ...] = (
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "claude-sonnet-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307",
)

PRICED_MODELS: frozenset[str] = frozenset(_PRICED_MODEL_IDS)


def get_model_metadata(model: str) -> ModelMetadata:
    """Return registry metadata for a model id; unknown models get a minimal entry."""
    known = MODEL_REGISTRY.get(model)
    if known is not None:
        return known
    return ModelMetadata(
        model=model,
        creator=ModelCreator(name="Unknown", is_provider=False),
        open_weights=False,
        license="Unknown",
        endpoints=(),
        system=None,
        description="Model not present in MODEL_REGISTRY.",
    )


def list_model_metadata() -> list[dict[str, Any]]:
    """Serialize the full registry."""
    return [m.to_dict() for m in MODEL_REGISTRY.values()]


def registry_inventory() -> dict[str, Any]:
    """High-level inventory of models, creators, providers, endpoints, systems."""
    creators = sorted({m.creator.name for m in MODEL_REGISTRY.values()})
    providers = sorted(
        {e.provider for m in MODEL_REGISTRY.values() for e in m.endpoints}
    )
    open_models = sorted(m.model for m in MODEL_REGISTRY.values() if m.open_weights)
    serverless_models = sorted(m.model for m in MODEL_REGISTRY.values() if any(e.serverless for e in m.endpoints))
    systems = sorted(
        (m.system.name for m in MODEL_REGISTRY.values() if m.system is not None)
    )
    return {
        "model_count": len(MODEL_REGISTRY),
        "models": sorted(MODEL_REGISTRY),
        "creators": creators,
        "providers": providers,
        "open_weights_models": open_models,
        "serverless_models": serverless_models,
        "systems": systems,
        "vocabulary": {
            "model": "An LLM, identified by its API model id.",
            "model_creator": "Organization that developed/trained the model.",
            "endpoint": "Hosted API instance of a model.",
            "system": "Dedicated compute environment for load testing (AA-SLT).",
            "provider": "Company hosting a model endpoint.",
            "serverless": "Priced per input/output token; no fixed-rate reservation.",
            "open_weights": "Weights released publicly (license may not be OSI-open).",
        },
    }


if __name__ == "__main__":
    import json

    print(json.dumps(registry_inventory(), indent=2))
