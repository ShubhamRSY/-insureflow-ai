"""LOB-aware triage checklist for life vs property."""

from __future__ import annotations

from insureflow.agents.triage_agent import REQUIRED_CRITICAL_BY_LOB, DocumentChecklist, TriageAgent
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission


def test_life_checklist_does_not_require_acord_sov() -> None:
    bundle = SubmissionBundle(
        bundle_id="life-1",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                document_type="life_application",
                raw_text="Term life application face amount 750000",
            )
        ],
    )
    cl = DocumentChecklist.from_bundle(bundle, insurance_line="life")
    assert cl.lob == "life"
    assert "Life application" in cl.present
    assert "ACORD application" not in cl.missing
    assert "Schedule of values" not in cl.missing
    assert any("Medical" in m or "APS" in m or "Beneficiary" in m for m in cl.missing)


def test_property_still_requires_acord() -> None:
    bundle = SubmissionBundle(bundle_id="prop-1", unstructured=[])
    cl = DocumentChecklist.from_bundle(bundle, insurance_line="commercial_property")
    assert cl.lob == "property"
    assert any("ACORD application" in m for m in cl.missing)
    assert any("Loss run" in r for r in REQUIRED_CRITICAL_BY_LOB["property"])


def test_triage_score_accepts_insurance_line() -> None:
    agent = TriageAgent()
    bundle = SubmissionBundle(bundle_id="life-2", unstructured=[])
    result = agent.score_submission(bundle, insurance_line="life")
    assert result.document_checklist.lob == "life"
    assert "Life application" in result.missing_documents


def test_life_critical_requirements_are_minimal() -> None:
    assert REQUIRED_CRITICAL_BY_LOB["life"] == ["Life application"]
    assert "ACORD application" not in REQUIRED_CRITICAL_BY_LOB["life"]


def test_checklist_summary_dict_shape() -> None:
    bundle = SubmissionBundle(
        bundle_id="life-3",
        unstructured=[
            UnstructuredSubmission(submission_id="d1", document_type="life_application", raw_text="life"),
        ],
    )
    summary = DocumentChecklist.from_bundle(bundle, insurance_line="life").to_summary_dict()
    assert summary["lob"] == "life"
    assert 0 <= summary["completeness_pct"] <= 1
    assert "Life application" in summary["present_documents"]
