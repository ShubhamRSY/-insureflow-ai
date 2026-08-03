"""Tests for the AA-vocabulary model/endpoint/system registry."""

from __future__ import annotations

from insureflow.llm.model_registry import (
    MODEL_REGISTRY,
    PRICED_MODELS,
    Endpoint,
    System,
    get_model_metadata,
    list_model_metadata,
    registry_inventory,
)


def test_registry_contains_priced_models() -> None:
    for model in PRICED_MODELS:
        assert model in MODEL_REGISTRY


def test_gpt4o_metadata() -> None:
    meta = get_model_metadata("gpt-4o")
    assert meta.creator.name == "OpenAI"
    assert meta.open_weights is False
    assert meta.license == "OpenAI API Terms"
    assert len(meta.endpoints) >= 1
    ep = meta.endpoints[0]
    assert ep.provider == "OpenAI"
    assert ep.serverless is True


def test_claude_metadata() -> None:
    meta = get_model_metadata("claude-sonnet-4-20250514")
    assert meta.creator.name == "Anthropic"
    assert meta.open_weights is False


def test_open_weights_examples() -> None:
    llama = get_model_metadata("llama-3.1-8b-instruct")
    assert llama.open_weights is True
    assert llama.parameters_b == 8.0
    assert llama.creator.name == "Meta"


def test_unknown_model_minimal_entry() -> None:
    meta = get_model_metadata("not-a-real-model")
    assert meta.model == "not-a-real-model"
    assert meta.creator.name == "Unknown"
    assert meta.endpoints == ()


def test_metadata_to_dict() -> None:
    d = get_model_metadata("gpt-4o").to_dict()
    assert d["model"] == "gpt-4o"
    assert d["creator"]["name"] == "OpenAI"
    assert d["open_weights"] is False
    assert isinstance(d["endpoints"], list)
    assert d["endpoints"][0]["provider"] == "OpenAI"


def test_system_roundtrip() -> None:
    sys_obj = System(name="bench-sys-1", compute="8x NVIDIA H100", max_seq_len=131072)
    d = sys_obj.to_dict()
    assert d["name"] == "bench-sys-1"
    assert d["compute"] == "8x NVIDIA H100"
    assert d["max_seq_len"] == 131072


def test_endpoint_roundtrip() -> None:
    ep = Endpoint(provider="AWS Bedrock", base_url="", serverless=True, region="us-east-1")
    d = ep.to_dict()
    assert d["provider"] == "AWS Bedrock"
    assert d["serverless"] is True


def test_multi_provider_endpoint() -> None:
    mistral = get_model_metadata("mistral-large-2411")
    providers = {e.provider for e in mistral.endpoints}
    assert "Mistral AI" in providers
    assert "AWS Bedrock" in providers


def test_list_model_metadata() -> None:
    items = list_model_metadata()
    assert len(items) == len(MODEL_REGISTRY)
    assert all("creator" in i and "endpoints" in i for i in items)


def test_registry_inventory() -> None:
    inv = registry_inventory()
    assert inv["model_count"] == len(MODEL_REGISTRY)
    assert "OpenAI" in inv["creators"]
    assert "Anthropic" in inv["creators"]
    assert "OpenAI" in inv["providers"]
    assert "llama-3.1-8b-instruct" in inv["open_weights_models"]
    assert set(inv["vocabulary"]) == {
        "model",
        "model_creator",
        "endpoint",
        "system",
        "provider",
        "serverless",
        "open_weights",
    }
    # every priced serverless model appears
    for m in PRICED_MODELS:
        assert m in inv["models"]


def test_benchmark_output_includes_registry() -> None:
    from evaluations.benchmark import run_benchmark
    from tests.test_benchmark import FakeLLMClient

    result = run_benchmark(
        model="gpt-4o",
        client=FakeLLMClient(delay=0.0),
        categories=["coding"],
        output_path=None,
    )
    meta = result["model_metadata"]
    assert meta["model"] == "gpt-4o"
    assert meta["creator"]["name"] == "OpenAI"
    assert result["registry_inventory"]["model_count"] >= 10
