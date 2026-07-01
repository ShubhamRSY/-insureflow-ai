from __future__ import annotations

from insureflow.graph.builder import build_pipeline_graph
from insureflow.graph.nodes import create_initial_state
from insureflow.models.submissions import SubmissionBundle


def test_graph_construction() -> None:
    pg = build_pipeline_graph()
    assert pg.graph is not None
    assert pg.compiled is not None

    nodes = [n for n in pg.graph.nodes]
    assert "ingest_docs" in nodes
    assert "classify_docs" in nodes
    assert "parse_acord" in nodes
    assert "parse_json" in nodes
    assert "parse_loss_run" in nodes
    assert "parse_sov" in nodes
    assert "parse_inspection" in nodes
    assert "parse_supplemental" in nodes
    assert "merge_structured" in nodes
    assert "extract_agents" in nodes
    assert "build_provenance" in nodes
    assert "reconcile" in nodes
    assert "human_review" in nodes
    assert "synthesize" in nodes
    assert "audit" in nodes

    edges = pg.graph.edges
    ingest_out = {e[1] for e in edges if e[0] == "ingest_docs"}
    assert "classify_docs" in ingest_out

    audit_out = {e[1] for e in edges if e[0] == "audit"}
    assert "__end__" in audit_out


def test_graph_run_acord_only(sample_acord_xml: str) -> None:
    pg = build_pipeline_graph()
    state = create_initial_state(
        acord_xml=sample_acord_xml,
        auto_classify=True,
    )
    result = pg.run(state)

    assert result.get("bundle_id") is not None
    bundle: SubmissionBundle = result.get("bundle")
    assert bundle is not None
    assert bundle.structured is not None
    assert bundle.structured.named_insured is not None
    assert bundle.structured.named_insured.legal_name == "Acme Manufacturing Corp"

    assert result.get("provenance") is not None
    assert result.get("synthesis") is not None

    errors = result.get("errors", [])
    assert len(errors) == 0


def test_graph_run_acord_with_inspection(sample_acord_xml: str, sample_inspection_report: str) -> None:
    pg = build_pipeline_graph()
    state = create_initial_state(
        acord_xml=sample_acord_xml,
        inspection_reports=[sample_inspection_report],
        auto_classify=True,
    )
    result = pg.run(state)

    bundle: SubmissionBundle = result.get("bundle")
    assert bundle is not None
    assert bundle.structured is not None
    assert len(bundle.unstructured) >= 1

    classification_routes = result.get("classification_routes", [])
    assert "parse_acord" in classification_routes
    assert "parse_inspection" in classification_routes


def test_graph_conditional_routing_acord() -> None:
    pg = build_pipeline_graph()
    state = create_initial_state(acord_xml="<ACORD>test</ACORD>", auto_classify=True)
    result = pg.run(state)
    routes = result.get("classification_routes", [])
    assert "parse_acord" in routes


def test_graph_conditional_routing_loss_run() -> None:
    pg = build_pipeline_graph()
    loss_run_text = "LOSS RUN REPORT\nClaim 1: $50,000 incurred\nClaim 2: $25,000 incurred"
    state = create_initial_state(
        acord_xml="<ACORD>test</ACORD>",
        loss_run=loss_run_text,
        auto_classify=True,
    )
    result = pg.run(state)
    routes = result.get("classification_routes", [])
    assert "parse_loss_run" in routes


def test_graph_conditional_routing_sov() -> None:
    pg = build_pipeline_graph()
    sov_text = "SCHEDULE OF VALUES\nBuilding 1: $2,000,000"
    state = create_initial_state(
        acord_xml="<ACORD>test</ACORD>",
        schedule_of_values=sov_text,
        auto_classify=True,
    )
    result = pg.run(state)
    routes = result.get("classification_routes", [])
    assert "parse_sov" in routes


def test_graph_retry_limit() -> None:
    build_pipeline_graph()

    state = create_initial_state(
        acord_xml="<ACORD>test</ACORD>",
        extraction_retries=4,
        max_extraction_retries=3,
    )

    from insureflow.graph.nodes import should_retry_extraction

    decision = should_retry_extraction(state)
    assert decision == "build_provenance"


def test_graph_retry_still_retrying() -> None:
    state = create_initial_state(
        acord_xml="<ACORD>test</ACORD>",
        extraction_retries=2,
        max_extraction_retries=3,
    )

    from insureflow.graph.nodes import should_retry_extraction

    decision = should_retry_extraction(state)
    assert decision == "extract_agents"


def test_graph_human_review_triggered() -> None:
    state = create_initial_state(
        human_review_needed=True,
    )

    from insureflow.graph.nodes import check_human_review

    decision = check_human_review(state)
    assert decision == "human_review"


def test_graph_human_review_skipped() -> None:
    state = create_initial_state(
        human_review_needed=False,
    )

    from insureflow.graph.nodes import check_human_review

    decision = check_human_review(state)
    assert decision == "query_rag"


def test_graph_human_review_node() -> None:
    from insureflow.models.audit import DiscrepancyRecord, EventSeverity, ReconciliationResult

    state = create_initial_state(
        bundle_id="test-human-review",
        reconciliation=ReconciliationResult(
            bundle_id="test-human-review",
            discrepancies=[
                DiscrepancyRecord(
                    field_path="test.field",
                    description="Critical mismatch in test.field",
                    severity=EventSeverity.CRITICAL,
                    source_a="acord",
                    source_b="inspection",
                ),
            ],
        ),
    )

    from insureflow.graph.nodes import human_review

    result = human_review(state)

    reasons = result.get("human_review_reasons", [])
    assert len(reasons) == 1
    assert "test.field" in reasons[0]
    assert "Critical mismatch" in reasons[0]


def test_graph_default_state() -> None:
    state = create_initial_state()
    assert state.get("extraction_retries") == 0
    assert state.get("max_extraction_retries") == 3
    assert state.get("human_review_needed") is False
    assert state.get("human_review_reasons") == []
    assert state.get("errors") == []
    assert state.get("classification_routes") == []


def test_graph_checkpointing(sample_acord_xml: str) -> None:
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    pg = build_pipeline_graph(checkpointer=checkpointer)

    thread_id = "test-checkpoint"
    state = create_initial_state(
        acord_xml=sample_acord_xml,
        bundle_id=thread_id,
        auto_classify=True,
    )
    pg.run(state)

    saved = pg.get_state(thread_id)
    assert saved is not None

    values = saved.values
    assert values.get("bundle_id") == thread_id
    assert values.get("parsed_acord") is True


def test_graph_no_input() -> None:
    pg = build_pipeline_graph()
    state = create_initial_state()
    result = pg.run(state)

    assert result.get("bundle") is not None
    assert result.get("synthesis") is not None


def test_graph_multi_document_routing() -> None:
    pg = build_pipeline_graph()
    state = create_initial_state(
        acord_xml="<ACORD>test</ACORD>",
        loss_run="LOSS RUN: Claim $50k",
        schedule_of_values="SOV: Building $2M",
        inspection_reports=["INSPECTION: Masonry construction"],
        supplemental_docs=["Some additional notes"],
        auto_classify=True,
    )
    result = pg.run(state)

    routes = result.get("classification_routes", [])
    assert "parse_acord" in routes
    assert "parse_loss_run" in routes
    assert "parse_sov" in routes
    assert "parse_inspection" in routes


def test_graph_pipeline_integration(sample_acord_xml: str) -> None:
    from insureflow.pipeline import UnderwritingPipeline

    pipeline = UnderwritingPipeline(use_graph=True)
    results = pipeline.run(acord_xml=sample_acord_xml)

    assert results["status"] in ("completed", "flagged")
    assert "bundle_id" in results
    assert results["steps"]["ingestion"]["status"] == "complete"
    assert results["steps"]["reconciliation"]["match_rate"] >= 0

    errors = results.get("errors", [])
    assert len(errors) == 0


def test_graph_pipeline_backward_compat(sample_acord_xml: str) -> None:
    from insureflow.pipeline import UnderwritingPipeline

    linear = UnderwritingPipeline(use_graph=False)
    graph = UnderwritingPipeline(use_graph=True)

    linear_result = linear.run(acord_xml=sample_acord_xml)
    graph_result = graph.run(acord_xml=sample_acord_xml)

    assert graph_result["status"] in ("completed", "flagged")
    assert linear_result["status"] in ("completed", "flagged")
    assert graph_result.get("bundle_id") is not None


def test_graph_rag_context_produced(sample_acord_xml: str) -> None:
    pg = build_pipeline_graph()
    state = create_initial_state(
        acord_xml=sample_acord_xml,
        auto_classify=True,
    )
    result = pg.run(state)

    rag_context = result.get("rag_context", "")
    assert isinstance(rag_context, str)


def test_graph_rag_in_synthesis(sample_acord_xml: str) -> None:
    from insureflow.pipeline import UnderwritingPipeline

    pipeline = UnderwritingPipeline(use_graph=True)
    results = pipeline.run(acord_xml=sample_acord_xml)

    synthesis = results.get("synthesis", {})
    assert "rag_context_used" in synthesis


def test_rag_agent_query() -> None:
    from insureflow.rag.rag_agent import RAGAgent

    agent = RAGAgent()
    agent.ensure_indexed()
    results = agent.query("masonry construction protection class 4", top_k=3)

    assert len(results) <= 3
    assert len(results) > 0
    titles = [g.title for g in results]
    assert any("Masonry" in t or "Protection" in t for t in titles)


def test_rag_agent_format_context() -> None:
    from insureflow.rag.rag_agent import RAGAgent

    agent = RAGAgent()
    ctx = agent.format_context("sprinkler requirements manufacturing", top_k=2)
    assert "UNDERWRITING GUIDELINES" in ctx
    assert "Sprinkler" in ctx or "sprinkler" in ctx or "Manufacturing" in ctx


def test_rag_guidelines_builtin_count() -> None:
    from insureflow.rag.guidelines import builtin_guidelines

    g = builtin_guidelines()
    assert len(g.guidelines) >= 15
    categories = {g.category for g in g.guidelines}
    assert "construction" in categories
    assert "protection" in categories
    assert "occupancy" in categories


def test_rag_vector_store_search() -> None:
    from insureflow.rag.guidelines import builtin_guidelines
    from insureflow.rag.vector_store import InMemoryVectorStore

    store = InMemoryVectorStore()
    g = builtin_guidelines()
    store.index_guidelines(g.guidelines)
    results = store.search("frame construction maximum", top_k=2)

    assert len(results) == 2
    scores = [s for _, s in results]
    assert all(s > 0 for s in scores)


def test_rag_vector_store_empty() -> None:
    from insureflow.rag.vector_store import InMemoryVectorStore

    store = InMemoryVectorStore()
    results = store.search("anything", top_k=5)
    assert results == []


def test_rag_vector_store_clear() -> None:
    from insureflow.rag.guidelines import builtin_guidelines
    from insureflow.rag.vector_store import InMemoryVectorStore

    store = InMemoryVectorStore()
    store.index_guidelines(builtin_guidelines().guidelines)
    store.clear()
    results = store.search("test", top_k=5)
    assert results == []
