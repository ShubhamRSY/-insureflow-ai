"""Regression tests for round-5 fixes:

1. The entity resolver must never mark two identical values from different
   sources as CONTRADICTED — that's cross-confirmation, not a conflict.
2. Every finding-summarizing section (Decision Logic gates, Agent Findings
   agent status) must read gate/category membership from the same
   canonical classification (finding_gates.py), not re-derive it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from insureflow.agents.uw_decision_agent import UWDecisionAgent
from insureflow.entities.resolver import EntityResolver
from insureflow.models.agents import AgentResult, AgentType
from insureflow.models.provenance import DataSource, ProvenanceNode, ProvenanceRecord, SourceType, VerificationStatus
from insureflow.models.submissions import ExtractedField, SubmissionBundle, UnstructuredSubmission
from insureflow.underwriting.finding_gates import COMPLIANCE_GATE_CATEGORIES, RISK_GATE_CATEGORIES, compute_gate_summary


def _node(node_id: str, value: str, source_name: str) -> ProvenanceNode:
    src = DataSource(source_id=node_id, source_type=SourceType.UNSTRUCTURED, source_name=source_name, received_at=datetime.now(tz=timezone.utc))
    return ProvenanceNode(node_id=node_id, field_path="named_insured.legal_name", value=value, source=src)


def _uw_result() -> AgentResult:
    return AgentResult(agent_type=AgentType.UW_DECISION, agent_name="UWDecisionAgent")


# ── Item 1: entity resolver ──────────────────────────────────────────────


def test_identical_values_are_never_marked_contradicted() -> None:
    record = ProvenanceRecord(
        record_id="prov-1",
        bundle_id="b1",
        nodes={"named_insured.legal_name": [_node("n1", "Priya Nair", "broker_life_application"), _node("n2", "Priya Nair", "broker_medical_exam")]},
    )
    resolved = EntityResolver().resolve_record(record)
    statuses = {n.verification_status for n in resolved.nodes["named_insured.legal_name"]}

    assert statuses == {VerificationStatus.VERIFIED}
    assert resolved.discrepancy_count() == 0


def test_case_and_whitespace_differences_still_count_as_agreement() -> None:
    record = ProvenanceRecord(
        record_id="prov-1",
        bundle_id="b1",
        nodes={"named_insured.legal_name": [_node("n1", "Priya Nair", "doc_a"), _node("n2", "  priya   nair ", "doc_b")]},
    )
    resolved = EntityResolver().resolve_record(record)
    statuses = {n.verification_status for n in resolved.nodes["named_insured.legal_name"]}

    assert statuses == {VerificationStatus.VERIFIED}


def test_genuinely_different_values_are_still_contradicted() -> None:
    """The fix must not neuter real contradiction detection — only remove
    the false positive for identical values. "ABC Corp" vs "ABC Corporation"
    cluster together (the resolver's abbreviation-expansion similarity
    treats them as the same entity) but are not identical strings, so this
    must still land as a genuine, reportable contradiction."""
    record = ProvenanceRecord(
        record_id="prov-1",
        bundle_id="b1",
        nodes={"named_insured.legal_name": [_node("n1", "ABC Corp", "doc_a"), _node("n2", "ABC Corporation", "doc_b")]},
    )
    resolved = EntityResolver().resolve_record(record)
    statuses = [n.verification_status for n in resolved.nodes["named_insured.legal_name"]]

    assert VerificationStatus.CONTRADICTED in statuses
    assert resolved.discrepancy_count() == 1


def test_confirmed_dupe_note_explains_cross_confirmation() -> None:
    record = ProvenanceRecord(
        record_id="prov-1",
        bundle_id="b1",
        nodes={"named_insured.legal_name": [_node("n1", "Priya Nair", "broker_life_application"), _node("n2", "Priya Nair", "broker_medical_exam")]},
    )
    resolved = EntityResolver().resolve_record(record)
    non_winner = next(n for n in resolved.nodes["named_insured.legal_name"] if n.node_id == "n2")

    assert "confirm" in (non_winner.notes or "").lower()


def test_cross_confirmed_name_finding_uses_accurate_wording() -> None:
    """Round-5 item 1: when a name is found in 2+ documents (agreeing), the
    finding text must not claim it's "not present in or confirmed against
    the application" — that's self-contradictory once cross-confirmed."""
    bundle = SubmissionBundle(
        bundle_id="b1",
        structured=None,
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                source="broker_life_application",
                extracted_fields={"insured_name": [ExtractedField(field_name="insured_name", value="Priya Nair", confidence=0.85)]},
            ),
            UnstructuredSubmission(
                submission_id="d2",
                source="broker_medical_exam",
                extracted_fields={"insured_name": [ExtractedField(field_name="insured_name", value="Priya Nair", confidence=0.4)]},
            ),
        ],
    )
    memo = UWDecisionAgent().produce_underwriting_memo(bundle, [], _uw_result())

    assert memo.insured_name == "Priya Nair"
    finding = next(f for f in memo.key_findings if "Priya Nair" in f.description)
    assert "not present in or confirmed against the application itself" not in finding.description
    assert "not independently verified" in finding.title.lower() or "not independently" in finding.description.lower()
    assert "2 submitted documents" in finding.description


def test_single_source_name_finding_still_flags_uncorroborated() -> None:
    bundle = SubmissionBundle(
        bundle_id="b1",
        structured=None,
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                source="broker_medical_exam",
                extracted_fields={"insured_name": [ExtractedField(field_name="insured_name", value="Priya Nair", confidence=0.4)]},
            ),
        ],
    )
    memo = UWDecisionAgent().produce_underwriting_memo(bundle, [], _uw_result())

    assert memo.insured_name == "Priya Nair"
    finding = next(f for f in memo.key_findings if "Priya Nair" in f.description)
    assert "single source" in finding.title.lower()
    assert "not corroborated by any other document" in finding.description


# ── Item 2: gate/category classification single source of truth ─────────


def test_compute_gate_summary_buckets_pipeline_level_compliance_findings() -> None:
    """Regression guard for the exact bug: MIB/sanctions findings are added
    directly to key_findings by pipeline.py, never through ComplianceAgent —
    the gate classification must catch them by category regardless of which
    code path created them."""
    key_findings = [
        {"title": "MIB check not performed", "description": "x", "severity": "high", "category": "mib"},
        {"title": "Sanctions screening incomplete", "description": "x", "severity": "high", "category": "sanctions"},
        {"title": "Elevated aggregate risk score", "description": "x", "severity": "high", "category": "uw_decision"},
    ]
    summary = compute_gate_summary(key_findings)

    assert summary["compliance"]["count"] == 2
    assert {f["title"] for f in summary["compliance"]["findings"]} == {"MIB check not performed", "Sanctions screening incomplete"}
    assert summary["risk"]["count"] == 1


def test_compute_gate_summary_empty_when_no_matching_categories() -> None:
    summary = compute_gate_summary([{"title": "x", "description": "y", "severity": "low", "category": "external_oracle"}])
    assert summary["compliance"]["count"] == 0
    assert summary["risk"]["count"] == 0


def test_gate_categories_are_disjoint() -> None:
    """Sanity guard: a category should not double-count toward both gates."""
    assert RISK_GATE_CATEGORIES.isdisjoint(COMPLIANCE_GATE_CATEGORIES)
