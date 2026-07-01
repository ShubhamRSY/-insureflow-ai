from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from insureflow.agents.mortgage.supervisor import (
    MortgageAssetAgent,
    MortgageCollateralAgent,
    MortgageCreditAgent,
    MortgageDecisionAgent,
    MortgageFraudDetectionAgent,
    MortgageIncomeAgent,
)
from insureflow.audit.store import AuditStore
from insureflow.ingestion.mortgage.loader import MortgageSubmissionLoader
from insureflow.models.mortgage import (
    MortgageAgentResult,
    MortgageBundle,
    MortgageBundleStatus,
    MortgageMemo,
    ProductLine,
)
from insureflow.mortgage.audit import MortgageAuditLogger
from insureflow.mortgage.compliance import MortgageComplianceEngine
from insureflow.mortgage.reconciliation import MortgageReconciliationEngine

logger = logging.getLogger(__name__)


class MortgagePipelineState(TypedDict, total=False):
    bundle_id: str
    product_line: str
    raw_documents: list[dict[str, str]]
    classified_documents: list[dict[str, Any]]
    bundle: dict[str, Any]
    income_analysis: dict[str, Any]
    credit_analysis: dict[str, Any]
    asset_analysis: dict[str, Any]
    collateral_analysis: dict[str, Any]
    fraud_analysis: dict[str, Any]
    compliance_violations: list[dict[str, Any]]
    reconciliation_issues: list[dict[str, Any]]
    memo: dict[str, Any]
    decision: str
    human_review_needed: bool
    human_review_reasons: list[str]
    human_review_approved: bool
    audit_trail: list[dict[str, Any]]
    errors: list[str]


def default_mortgage_state(**overrides: Any) -> dict[str, Any]:
    return {
        "bundle_id": "",
        "product_line": ProductLine.RESIDENTIAL_MORTGAGE.value,
        "raw_documents": [],
        "classified_documents": [],
        "bundle": None,
        "income_analysis": None,
        "credit_analysis": None,
        "asset_analysis": None,
        "collateral_analysis": None,
        "fraud_analysis": None,
        "compliance_violations": [],
        "reconciliation_issues": [],
        "memo": None,
        "decision": "",
        "human_review_needed": False,
        "human_review_reasons": [],
        "human_review_approved": False,
        "audit_trail": [],
        "errors": [],
        **overrides,
    }


def ingest_and_classify(state: dict[str, Any]) -> dict[str, Any]:
    bundle_id = state.get("bundle_id") or f"mortgage-{uuid4().hex[:12]}"
    raw_docs: list[dict[str, str]] = state.get("raw_documents", [])
    product_line_str = state.get("product_line", ProductLine.RESIDENTIAL_MORTGAGE.value)
    product_line = ProductLine(product_line_str)

    loader = MortgageSubmissionLoader(use_llm=True)
    documents = loader.load_from_texts(
        raw_docs,
        bundle_id=bundle_id,
        product_line=product_line,
    )

    bundle = MortgageBundle(
        bundle_id=bundle_id,
        product_line=product_line,
        documents=documents,
        status=MortgageBundleStatus.CLASSIFIED,
    )

    return {
        "bundle_id": bundle_id,
        "product_line": product_line.value,
        "classified_documents": [d.model_dump() for d in documents],
        "bundle": bundle.model_dump(),
    }


def extract_fields(state: dict[str, Any]) -> dict[str, Any]:
    bundle_dict = state.get("bundle")
    if not bundle_dict:
        return {"errors": ["No bundle to extract fields from"]}

    bundle = MortgageBundle(**bundle_dict)

    for doc in bundle.documents:
        from insureflow.ingestion.mortgage.extractors import extract_fields as _run_extract
        extracted = _run_extract(doc.document_type, doc.raw_text)
        doc.extracted_fields.update(extracted)

    return {"bundle": bundle.model_dump()}


def build_summaries_and_reconcile(state: dict[str, Any]) -> dict[str, Any]:
    bundle_dict = state.get("bundle")
    if not bundle_dict:
        return {"errors": ["No bundle to reconcile"]}

    bundle = MortgageBundle(**bundle_dict)
    engine = MortgageReconciliationEngine()
    engine.build_summaries(bundle)
    engine.reconcile(bundle)

    return {
        "bundle": bundle.model_dump(),
        "reconciliation_issues": [i.model_dump() for i in bundle.reconciliation_issues],
    }


def run_compliance(state: dict[str, Any]) -> dict[str, Any]:
    bundle_dict = state.get("bundle")
    if not bundle_dict:
        return {"errors": ["No bundle for compliance check"]}

    bundle = MortgageBundle(**bundle_dict)
    engine = MortgageComplianceEngine()
    violations = engine.evaluate(bundle)

    return {
        "bundle": bundle.model_dump(),
        "compliance_violations": [v.model_dump() for v in violations],
    }


def run_income_agent(state: dict[str, Any]) -> dict[str, Any]:
    bundle = MortgageBundle(**state["bundle"])
    agent = MortgageIncomeAgent()
    result = agent.analyze(bundle)
    return {"income_analysis": result.model_dump()}


def run_credit_agent(state: dict[str, Any]) -> dict[str, Any]:
    bundle = MortgageBundle(**state["bundle"])
    agent = MortgageCreditAgent()
    result = agent.analyze(bundle)
    return {"credit_analysis": result.model_dump()}


def run_asset_agent(state: dict[str, Any]) -> dict[str, Any]:
    bundle = MortgageBundle(**state["bundle"])
    agent = MortgageAssetAgent()
    result = agent.analyze(bundle)
    return {"asset_analysis": result.model_dump()}


def run_collateral_agent(state: dict[str, Any]) -> dict[str, Any]:
    bundle = MortgageBundle(**state["bundle"])
    agent = MortgageCollateralAgent()
    result = agent.analyze(bundle)
    return {"collateral_analysis": result.model_dump()}


def run_fraud_detection(state: dict[str, Any]) -> dict[str, Any]:
    bundle = MortgageBundle(**state["bundle"])
    agent = MortgageFraudDetectionAgent()
    result = agent.analyze(bundle)
    return {"fraud_analysis": result.model_dump()}


def decide(state: dict[str, Any]) -> dict[str, Any]:
    bundle = MortgageBundle(**state["bundle"])
    agent = MortgageDecisionAgent()

    result_keys = (
        "income_analysis",
        "credit_analysis",
        "asset_analysis",
        "collateral_analysis",
        "fraud_analysis",
    )
    agent_results = [
        MortgageAgentResult(**state[k]) for k in result_keys if state.get(k)
    ]
    memo = agent.decide(bundle, agent_results)

    human_review_reasons: list[str] = []
    if memo.human_review_required:
        for f in memo.key_findings:
            if f.severity in ("high", "critical"):
                human_review_reasons.append(
                    f"[{f.severity.upper()}] {f.title}: {f.description}"
                )
        for v in memo.compliance_violations:
            if v.severity in ("high", "critical"):
                human_review_reasons.append(
                    f"[COMPLIANCE] ({v.rule_id}) {v.message}"
                )

    return {
        "memo": memo.model_dump(),
        "decision": memo.decision.value,
        "human_review_needed": memo.human_review_required,
        "human_review_reasons": human_review_reasons,
    }


def check_human_review(state: dict[str, Any]) -> str:
    if state.get("human_review_needed", False):
        return "human_review"
    return "audit"


def human_review(state: dict[str, Any]) -> dict[str, Any]:
    return {"human_review_approved": True}


def audit(state: dict[str, Any]) -> dict[str, Any]:
    bundle_id = state.get("bundle_id", "")
    bundle_dict = state.get("bundle")
    memo_dict = state.get("memo")

    audit_store = AuditStore()
    audit_logger = MortgageAuditLogger(audit_store)
    audit_logger.start(bundle_id)

    if bundle_dict and memo_dict:
        bundle = MortgageBundle(**bundle_dict)
        memo = MortgageMemo(**memo_dict)
        audit_logger.persist(bundle, memo)

    trail = audit_logger.trail
    return {
        "audit_trail": [e.model_dump() for e in trail.entries] if trail and trail.entries else [],
    }


class MortgagePipelineGraph:
    def __init__(self, checkpointer: Optional[Any] = None) -> None:
        self.checkpointer = checkpointer or MemorySaver()
        self.graph = self._build()
        self.compiled = self.graph.compile(checkpointer=self.checkpointer)

    def _build(self) -> StateGraph:
        graph = StateGraph(MortgagePipelineState)

        graph.add_node("ingest_and_classify", ingest_and_classify)
        graph.add_node("extract_fields", extract_fields)
        graph.add_node("build_summaries_and_reconcile", build_summaries_and_reconcile)
        graph.add_node("run_compliance", run_compliance)
        graph.add_node("run_income_agent", run_income_agent)
        graph.add_node("run_credit_agent", run_credit_agent)
        graph.add_node("run_asset_agent", run_asset_agent)
        graph.add_node("run_collateral_agent", run_collateral_agent)
        graph.add_node("run_fraud_detection", run_fraud_detection)
        graph.add_node("decide", decide)
        graph.add_node("human_review", human_review)
        graph.add_node("audit", audit)

        graph.set_entry_point("ingest_and_classify")

        graph.add_edge("ingest_and_classify", "extract_fields")
        graph.add_edge("extract_fields", "build_summaries_and_reconcile")
        graph.add_edge("build_summaries_and_reconcile", "run_compliance")

        graph.add_edge("run_compliance", "run_income_agent")
        graph.add_edge("run_compliance", "run_credit_agent")
        graph.add_edge("run_compliance", "run_asset_agent")
        graph.add_edge("run_compliance", "run_collateral_agent")
        graph.add_edge("run_compliance", "run_fraud_detection")

        graph.add_edge("run_income_agent", "decide")
        graph.add_edge("run_credit_agent", "decide")
        graph.add_edge("run_asset_agent", "decide")
        graph.add_edge("run_collateral_agent", "decide")
        graph.add_edge("run_fraud_detection", "decide")

        graph.add_conditional_edges(
            "decide",
            check_human_review,
            {
                "human_review": "human_review",
                "audit": "audit",
            },
        )

        graph.add_edge("human_review", "audit")
        graph.add_edge("audit", END)

        return graph

    def run(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        config = {"configurable": {"thread_id": initial_state.get("bundle_id", "default")}}
        result = self.compiled.invoke(initial_state, config=config)
        return result

    def get_state(self, thread_id: str) -> Any:
        config = {"configurable": {"thread_id": thread_id}}
        return self.compiled.get_state(config)

    def update_state(self, thread_id: str, values: dict[str, Any]) -> None:
        config = {"configurable": {"thread_id": thread_id}}
        self.compiled.update_state(config, values)


def build_mortgage_pipeline_graph(checkpointer: Optional[Any] = None) -> MortgagePipelineGraph:
    return MortgagePipelineGraph(checkpointer=checkpointer)
