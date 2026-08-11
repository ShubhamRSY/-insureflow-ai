"""Optional Arize Phoenix / OpenInference tracing for the underwriting pipeline.

Guarded: tracing only activates when `PHOENIX_COLLECTOR_ENDPOINT` is set, and
every call is wrapped so production is never affected by a Phoenix failure.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

_traced: bool | None = None


def tracing_enabled() -> bool:
    return bool(os.getenv("PHOENIX_COLLECTOR_ENDPOINT"))


def start_tracing() -> bool:
    """Register OpenInference exporters + instrument OpenTelemetry. Idempotent.

    Returns True when tracing is active. Never raises — logs and returns False.
    """
    global _traced
    if _traced is not None:
        return _traced
    if not tracing_enabled():
        _traced = False
        return False
    try:
        endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
        from opentelemetry import trace as otel_trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "insureflow-ai")})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        otel_trace.set_tracer_provider(provider)

        try:
            from openinference.instrumentation.langchain import LangChainInstrumentor

            LangChainInstrumentor().instrument()
        except Exception as exc:  # noqa: BLE001
            logger.debug("LangChain instrumentation unavailable: %s", exc)
        try:
            from openinference.instrumentation.openai import OpenAIInstrumentor

            OpenAIInstrumentor().instrument()
        except Exception as exc:  # noqa: BLE001
            logger.debug("OpenAI instrumentation unavailable: %s", exc)

        _traced = True
        logger.info("Arize Phoenix OpenInference tracing active on %s", endpoint)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Phoenix tracing disabled: %s", exc)
        _traced = False
    return bool(_traced)


def shutdown_tracing() -> None:
    global _traced
    try:
        from opentelemetry import trace as otel_trace

        provider = otel_trace.get_tracer_provider()
        if provider is not None:
            shutdown = getattr(provider, "shutdown", None)
            if callable(shutdown):
                shutdown()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Tracing shutdown failed: %s", exc)
    _traced = None


def traced_pipeline_run(fn: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Run the pipeline inside a Phoenix span when tracing is enabled."""
    if not start_tracing():
        return fn(*args, **kwargs)
    try:
        from opentelemetry import trace as otel_trace

        tracer = otel_trace.get_tracer("insureflow.pipeline")
        bundle_id = kwargs.get("bundle_id") or ""
        with tracer.start_as_current_span("underwriting_pipeline", attributes={"bundle_id": bundle_id or "unknown"}):
            return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Tracing span failed, running untraced: %s", exc)
        return fn(*args, **kwargs)
