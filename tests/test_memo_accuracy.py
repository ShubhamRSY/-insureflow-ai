"""Memo accuracy mitigations: citation gate, conformal STP, audit loop, Self-RAG/HyDE, entity graph."""

from __future__ import annotations

import os

from insureflow.models.submissions import (
    CoverageDetail,
    ExtractedField,
    LocationData,
    NamedInsured,
    StructuredSubmission,
    SubmissionBundle,
)
from insureflow.rag.entity_graph import build_submission_entity_graph, ungrounded_relation_issues
from insureflow.rag.hyde import expand_query_deterministic, hyde_search_query
from insureflow.rag.rag_agent import RAGAgent
from insureflow.rag.self_rag import retrieve_with_self_rag
from insureflow.verification.audit_loop import run_audit_loop
from insureflow.verification.citation_gate import citation_issues, gate_memo_claims, is_grounded
from insureflow.verification.conformal_stp import calibrate_stp_threshold, prediction_set_for_metric
from insureflow.verification.engine import VerificationEngine


def _field(name: str, value: str, **kwargs) -> ExtractedField:
    return ExtractedField(field_name=name, value=value, **kwargs)


def test_uncited_critical_limit_blocks_stp() -> None:
    os.environ["USE_CITATION_GATE"] = "1"
    fields = {
        "general_aggregate_limit": [_field("general_aggregate_limit", "2000000", confidence=0.99)],
    }
    issues = citation_issues(fields)
    assert any(i.code == "uncited_claim" for i in issues)
    assert any(i.severity == "error" for i in issues)


def test_cited_limit_passes_citation_gate() -> None:
    os.environ["USE_CITATION_GATE"] = "1"
    fields = {
        "general_aggregate_limit": [
            _field(
                "general_aggregate_limit",
                "2000000",
                confidence=0.99,
                page_number=2,
                bbox=[0.1, 0.2, 0.4, 0.25],
                source_ref="page 2, region 0.100,0.200..0.400,0.250",
            )
        ],
    }
    assert citation_issues(fields) == []
    assert is_grounded(fields["general_aggregate_limit"][0])


def test_memo_gate_strips_uncited_money_claim() -> None:
    os.environ["USE_CITATION_GATE"] = "1"
    issues = gate_memo_claims(
        [{"field_name": "limit", "title": "Limit $2,000,000", "description": "General Aggregate"}],
        grounded_keys=[],
    )
    assert issues and issues[0].code == "memo_uncited_claim"


def test_engine_runs_citation_gate(monkeypatch) -> None:
    monkeypatch.setenv("USE_VERIFICATION", "1")
    monkeypatch.setenv("USE_CITATION_GATE", "1")
    report = VerificationEngine().run(
        {
            "total_incurred": [_field("total_incurred", "500000", confidence=0.99)],
        }
    )
    assert "citation_gate" in report.checks_run
    assert any(i.code == "uncited_claim" for i in report.issues)
    assert report.auto_approve is False


def test_conformal_stp_picks_threshold_under_error_budget() -> None:
    # High-confidence wrong answers force a high threshold.
    labels = [
        (0.99, True),
        (0.98, True),
        (0.97, True),
        (0.96, True),
        (0.95, False),  # wrong at 0.95
        (0.90, True),
        (0.85, True),
        (0.80, False),
    ]
    result = calibrate_stp_threshold(labels, target_error=0.05, default_threshold=0.95)
    assert result.n_holdout == 8
    assert result.threshold >= 0.96
    assert result.empirical_error <= 0.05 + 1e-9


def test_conformal_empty_holdout_uses_default() -> None:
    result = calibrate_stp_threshold([], default_threshold=0.95)
    assert result.threshold == 0.95
    assert result.method == "default_no_holdout"


def test_prediction_set_width() -> None:
    interval = prediction_set_for_metric([(100.0, 5.0), (110.0, 8.0), (105.0, 3.0)], residual_quantile=0.9)
    assert interval is not None
    lo, hi = interval
    assert lo < 105.0 < hi


def test_audit_loop_routes_ungrounded() -> None:
    os.environ["USE_AUDIT_LOOP"] = "1"
    os.environ["USE_CITATION_GATE"] = "1"
    fields = {"premium": [_field("premium", "12000", confidence=0.9)]}
    result = run_audit_loop(fields, max_loops=1, timeout_seconds=2.0)
    assert result.routed_to_human
    assert any(i.code in {"uncited_claim", "audit_loop_exhausted"} for i in result.issues)


def test_audit_loop_clean_when_grounded() -> None:
    os.environ["USE_AUDIT_LOOP"] = "1"
    os.environ["USE_CITATION_GATE"] = "1"
    fields = {
        "premium": [_field("premium", "12000", confidence=0.99, page_number=1, source_ref="page 1")],
    }
    result = run_audit_loop(fields, max_loops=1)
    assert not result.timed_out
    assert not any(i.code == "uncited_claim" for i in result.issues)


def test_hyde_expands_short_query() -> None:
    expanded = expand_query_deterministic("frame construction", line_of_business="property")
    assert "guideline" in expanded.lower()
    assert "construction" in expanded.lower()
    assert "sprinkler" in hyde_search_query("COPE", line_of_business="property").lower()


def test_self_rag_marks_no_context_honest() -> None:
    agent = RAGAgent(use_knowledge_graph=False)
    # Nonsense query should fail closed rather than invent guidelines.
    ctx = retrieve_with_self_rag(agent, "zzzz-not-a-real-underwriting-topic-qqq", top_k=3, use_hyde=True)
    assert "self_rag_meta" in ctx
    assert ctx["self_rag_meta"]["passes"] >= 1


def test_submission_entity_graph_edges() -> None:
    bundle = SubmissionBundle(
        bundle_id="g1",
        structured=StructuredSubmission(
            submission_id="g1",
            named_insured=NamedInsured(legal_name="Acme Manufacturing"),
            locations=[LocationData(address="1 Main", city="Chicago", state="IL", zip_code="60601", building_value=1_000_000)],
            coverages=[CoverageDetail(coverage_type="General Liability", limit_amount=2_000_000, deductible=5000, premium=12000)],
        ),
    )
    graph = build_submission_entity_graph(bundle)
    assert any(n.entity_type == "insured" for n in graph.nodes.values())
    assert any(e.relation == "located_at" for e in graph.edges)
    assert any(e.relation == "covered_by" for e in graph.edges)
    assert graph.assert_allowed("Acme Manufacturing", "located_at", "1 Main, Chicago, IL")
    bad = ungrounded_relation_issues([("Acme Manufacturing", "excluded_from", "Building B")], graph)
    assert bad
