"""Tests for BaseAgent's centralized Finding provenance backfill.

Regression guard for the bug where every Finding's source_document/
extraction_method stayed blank and confidence was always the pydantic
default (0.8), even when real per-field extraction confidence was
available on the bundle.
"""

from __future__ import annotations

from insureflow.agents.base import BaseAgent
from insureflow.agents.tools import UnderwritingTools
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import StructuredSubmission, SubmissionBundle, UnstructuredSubmission


class _DummyAgent(BaseAgent):
    agent_type = AgentType.RISK_ANALYST
    agent_name = "dummy"

    def _analyze(self, bundle: SubmissionBundle, **kwargs) -> None:
        self._add_finding(
            Finding(
                title="Generic finding",
                description="no field_path",
                severity=RiskSeverity.MODERATE,
                category="risk",
            )
        )
        self._add_finding(
            Finding(
                title="Field-specific finding",
                description="names a field with real extraction confidence",
                severity=RiskSeverity.MODERATE,
                category="risk",
                field_path="named_insured.legal_name",
            )
        )
        self._add_finding(
            Finding(
                title="Deliberately low confidence",
                description="agent explicitly set a non-default confidence",
                severity=RiskSeverity.MODERATE,
                category="risk",
                field_path="named_insured.legal_name",
                confidence=0.3,
            )
        )


def test_add_finding_backfills_bundle_level_source_and_method() -> None:
    bundle = SubmissionBundle(
        bundle_id="b1",
        structured=StructuredSubmission(submission_id="s1", source="broker_acord_xml"),
    )
    result = _DummyAgent(tools=UnderwritingTools()).run(bundle)
    generic = next(f for f in result.findings if f.title == "Generic finding")
    assert generic.source_document == "broker_acord_xml"
    assert generic.extraction_method == "structured_parser"


def test_add_finding_uses_field_confidence_when_field_path_matches() -> None:
    bundle = SubmissionBundle(
        bundle_id="b1",
        structured=StructuredSubmission(
            submission_id="s1",
            source="broker_acord_xml",
            field_confidence={"named_insured.legal_name": 0.98},
            field_notes={"named_insured.legal_name": "source element missing — value defaulted"},
        ),
    )
    result = _DummyAgent(tools=UnderwritingTools()).run(bundle)
    field_specific = next(f for f in result.findings if f.title == "Field-specific finding")
    assert field_specific.confidence == 0.98


def test_add_finding_never_overrides_explicit_non_default_confidence() -> None:
    bundle = SubmissionBundle(
        bundle_id="b1",
        structured=StructuredSubmission(
            submission_id="s1",
            field_confidence={"named_insured.legal_name": 0.98},
        ),
    )
    result = _DummyAgent(tools=UnderwritingTools()).run(bundle)
    deliberate = next(f for f in result.findings if f.title == "Deliberately low confidence")
    assert deliberate.confidence == 0.3


def test_add_finding_falls_back_to_unstructured_source_when_no_structured_doc() -> None:
    bundle = SubmissionBundle(
        bundle_id="b1",
        structured=None,
        unstructured=[UnstructuredSubmission(submission_id="d1", source="aps_records.md", document_type="medical")],
    )
    result = _DummyAgent(tools=UnderwritingTools()).run(bundle)
    generic = next(f for f in result.findings if f.title == "Generic finding")
    assert generic.source_document == "aps_records.md"
    assert generic.extraction_method == "llm_extraction"
