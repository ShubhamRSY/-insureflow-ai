from __future__ import annotations

from typing import Any, TypedDict

from insureflow.models.audit import ReconciliationResult, SynthesisOutput
from insureflow.models.provenance import ProvenanceRecord
from insureflow.models.submissions import SubmissionBundle


class PipelineState(TypedDict, total=False):
    bundle_id: str
    auto_classify: bool

    acord_xml: str
    inspection_reports: list[str]
    supplemental_docs: list[str]
    json_payload: str
    loss_run: str
    schedule_of_values: str
    raw_docs: list[str]

    bundle: SubmissionBundle
    provenance: ProvenanceRecord
    reconciliation: ReconciliationResult
    synthesis: SynthesisOutput
    audit_trail: Any

    extraction_retries: int
    max_extraction_retries: int
    human_review_needed: bool
    human_review_reasons: list[str]
    errors: list[str]
    classification_routes: list[str]
    parsed_acord: bool
    parsed_json: bool
    parsed_loss_run: bool
    parsed_sov: bool
    parsed_inspection: bool
    audit_entries: list[dict[str, Any]]
    rag_context: str


def default_state(**overrides: Any) -> dict[str, Any]:
    return {
        "bundle_id": "",
        "auto_classify": False,
        "acord_xml": "",
        "inspection_reports": None,
        "supplemental_docs": None,
        "json_payload": "",
        "loss_run": "",
        "schedule_of_values": "",
        "raw_docs": None,
        "bundle": None,
        "provenance": None,
        "reconciliation": None,
        "synthesis": None,
        "audit_trail": None,
        "extraction_retries": 0,
        "max_extraction_retries": 3,
        "human_review_needed": False,
        "human_review_reasons": [],
        "errors": [],
        "classification_routes": [],
        "parsed_acord": False,
        "parsed_json": False,
        "parsed_loss_run": False,
        "parsed_sov": False,
        "parsed_inspection": False,
        "audit_entries": [],
        "rag_context": "",
        **overrides,
    }
