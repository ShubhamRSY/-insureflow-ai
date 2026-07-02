from __future__ import annotations

import logging
from typing import Any, Optional, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from insureflow.graph.nodes import (
    audit,
    build_provenance,
    check_human_review,
    classify_docs,
    extract_agents,
    human_review,
    ingest_docs,
    merge_structured,
    parse_acord,
    parse_inspection,
    parse_json,
    parse_loss_run,
    parse_sov,
    parse_supplemental,
    query_rag,
    reconcile,
    route_by_classification,
    should_retry_extraction,
    synthesize,
)
from insureflow.graph.state import PipelineState

logger = logging.getLogger(__name__)


class PipelineGraph:
    def __init__(self, checkpointer: Optional[Any] = None) -> None:
        self.checkpointer = checkpointer or MemorySaver()
        self.graph = self._build()
        self.compiled = self.graph.compile(checkpointer=self.checkpointer)

    def _build(self) -> StateGraph[PipelineState]:
        graph = StateGraph(PipelineState)

        graph.add_node("ingest_docs", ingest_docs)
        graph.add_node("classify_docs", classify_docs)
        graph.add_node("parse_acord", parse_acord)
        graph.add_node("parse_json", parse_json)
        graph.add_node("parse_loss_run", parse_loss_run)
        graph.add_node("parse_sov", parse_sov)
        graph.add_node("parse_inspection", parse_inspection)
        graph.add_node("parse_supplemental", parse_supplemental)
        graph.add_node("merge_structured", merge_structured)
        graph.add_node("extract_agents", extract_agents)
        graph.add_node("build_provenance", build_provenance)
        graph.add_node("reconcile", reconcile)
        graph.add_node("human_review", human_review)
        graph.add_node("query_rag", query_rag)
        graph.add_node("synthesize", synthesize)
        graph.add_node("audit", audit)

        graph.set_entry_point("ingest_docs")

        graph.add_edge("ingest_docs", "classify_docs")

        graph.add_conditional_edges(
            "classify_docs",
            route_by_classification,
            {
                "parse_acord": "parse_acord",
                "parse_json": "parse_json",
                "parse_loss_run": "parse_loss_run",
                "parse_sov": "parse_sov",
                "parse_inspection": "parse_inspection",
                "parse_supplemental": "parse_supplemental",
                "merge_structured": "merge_structured",
            },
        )

        parse_nodes = [
            "parse_acord",
            "parse_json",
            "parse_loss_run",
            "parse_sov",
            "parse_inspection",
        ]
        for node in parse_nodes:
            graph.add_conditional_edges(
                node,
                _parse_next_router,
                {
                    "parse_acord": "parse_acord",
                    "parse_json": "parse_json",
                    "parse_loss_run": "parse_loss_run",
                    "parse_sov": "parse_sov",
                    "parse_inspection": "parse_inspection",
                    "parse_supplemental": "parse_supplemental",
                    "merge_structured": "merge_structured",
                },
            )

        graph.add_edge("parse_supplemental", "merge_structured")

        graph.add_edge("merge_structured", "extract_agents")

        graph.add_conditional_edges(
            "extract_agents",
            should_retry_extraction,
            {
                "extract_agents": "extract_agents",
                "build_provenance": "build_provenance",
            },
        )

        graph.add_edge("build_provenance", "reconcile")

        graph.add_conditional_edges(
            "reconcile",
            check_human_review,
            {
                "human_review": "human_review",
                "query_rag": "query_rag",
            },
        )

        graph.add_edge("human_review", "query_rag")

        graph.add_edge("query_rag", "synthesize")

        graph.add_edge("synthesize", "audit")

        graph.add_edge("audit", END)

        return graph

    def run(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        config: RunnableConfig = {"configurable": {"thread_id": initial_state.get("bundle_id", "default")}}
        result: Any = self.compiled.invoke(initial_state, config=config)  # type: ignore
        return cast(dict[str, Any], result)

    def get_state(self, thread_id: str) -> Any:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        return self.compiled.get_state(config)

    def update_state(self, thread_id: str, values: dict[str, Any]) -> None:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        self.compiled.update_state(config, values)


def build_pipeline_graph(checkpointer: Optional[Any] = None) -> PipelineGraph:
    return PipelineGraph(checkpointer=checkpointer)


def _parse_next_router(state: dict[str, Any]) -> str:
    routes: list[str] = state.get("classification_routes", [])
    parsed_flags = {
        "parse_acord": state.get("parsed_acord", False),
        "parse_json": state.get("parsed_json", False),
        "parse_loss_run": state.get("parsed_loss_run", False),
        "parse_sov": state.get("parsed_sov", False),
        "parse_inspection": state.get("parsed_inspection", False),
    }

    for route in routes:
        if not parsed_flags.get(route, False):
            return route

    return "merge_structured"
