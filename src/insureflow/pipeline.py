from __future__ import annotations

import logging
import pathlib
from typing import Any, Optional

from insureflow.agents.orchestrator import PipelineOrchestrator
from insureflow.audit.store import AuditStore
from insureflow.exceptions import DataIngestionError
from insureflow.graph.builder import build_pipeline_graph
from insureflow.graph.nodes import create_initial_state
from insureflow.llm.client import LLMClient
from insureflow.registry.service import RegistryService

logger = logging.getLogger(__name__)


class UnderwritingPipeline:
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        audit_store: Optional[AuditStore] = None,
        use_graph: bool = True,
    ) -> None:
        self.llm = llm_client or LLMClient()
        self.audit_store = audit_store or AuditStore()
        self.use_graph = use_graph
        if use_graph:
            self.graph = build_pipeline_graph()
        self._linear_orchestrator: Optional[PipelineOrchestrator] = None

    @property
    def orchestrator(self) -> PipelineOrchestrator:
        if self._linear_orchestrator is None:
            self._linear_orchestrator = PipelineOrchestrator(
                llm_client=self.llm,
                audit_store=self.audit_store,
            )
        return self._linear_orchestrator

    def run(
        self,
        acord_xml: Optional[str] = None,
        inspection_reports: Optional[list[str]] = None,
        supplemental_docs: Optional[list[str]] = None,
        json_payload: Optional[str] = None,
        loss_run: Optional[str] = None,
        schedule_of_values: Optional[str] = None,
        raw_docs: Optional[list[str]] = None,
        auto_classify: bool = False,
        bundle_id: Optional[str] = None,
    ) -> dict[str, Any]:
        logger.info(f"Initiating pipeline run for bundle: {bundle_id or 'auto-generated'}")

        if self.use_graph:
            return self._run_graph(
                acord_xml=acord_xml,
                inspection_reports=inspection_reports,
                supplemental_docs=supplemental_docs,
                json_payload=json_payload,
                loss_run=loss_run,
                schedule_of_values=schedule_of_values,
                raw_docs=raw_docs,
                auto_classify=auto_classify,
                bundle_id=bundle_id,
            )

        return self.orchestrator.run(
            acord_xml=acord_xml,
            inspection_reports=inspection_reports,
            supplemental_docs=supplemental_docs,
            json_payload=json_payload,
            loss_run=loss_run,
            schedule_of_values=schedule_of_values,
            raw_docs=raw_docs,
            auto_classify=auto_classify,
            bundle_id=bundle_id,
        )

    def _run_graph(
        self,
        acord_xml: Optional[str] = None,
        inspection_reports: Optional[list[str]] = None,
        supplemental_docs: Optional[list[str]] = None,
        json_payload: Optional[str] = None,
        loss_run: Optional[str] = None,
        schedule_of_values: Optional[str] = None,
        raw_docs: Optional[list[str]] = None,
        auto_classify: bool = False,
        bundle_id: Optional[str] = None,
    ) -> dict[str, Any]:
        state = create_initial_state(
            acord_xml=acord_xml,
            inspection_reports=inspection_reports,
            supplemental_docs=supplemental_docs,
            json_payload=json_payload,
            loss_run=loss_run,
            schedule_of_values=schedule_of_values,
            raw_docs=raw_docs,
            auto_classify=auto_classify,
            bundle_id=bundle_id,
        )

        result = self.graph.run(state)

        bundle = result.get("bundle")
        synthesis = result.get("synthesis")
        reconciliation = result.get("reconciliation")
        provenance = result.get("provenance")
        audit_trail = result.get("audit_trail")
        errors = result.get("errors", [])

        audit_entries = len(audit_trail.entries) if audit_trail else 0

        registry = RegistryService()
        version_context = registry.version_context()

        return {
            "bundle_id": result.get("bundle_id"),
            "status": "completed" if not result.get("human_review_needed") else "flagged",
            "version_context": version_context,
            "steps": {
                "ingestion": {
                    "bundle_id": bundle.bundle_id if bundle else None,
                    "status": "complete" if bundle else "failed",
                },
                "extraction": {
                    "status": "complete" if bundle else "failed",
                    "retries": result.get("extraction_retries", 0),
                },
                "provenance": {
                    "record_id": provenance.record_id if provenance else None,
                    "nodes": provenance.record_count() if provenance else 0,
                },
                "reconciliation": {
                    "match_rate": reconciliation.match_rate if reconciliation else 0.0,
                    "discrepancies": len(reconciliation.discrepancies) if reconciliation else 0,
                    "overall_status": reconciliation.overall_status if reconciliation else "failed",
                },
                "synthesis": {
                    "human_review_required": synthesis.human_review_required if synthesis else False,
                    "discrepancies_found": synthesis.discrepancies_found if synthesis else 0,
                },
            },
            "synthesis": synthesis.model_dump() if synthesis else {},
            "reconciliation": reconciliation.model_dump() if reconciliation else {},
            "rag_context": result.get("rag_context", ""),
            "human_review_needed": result.get("human_review_needed", False),
            "human_review_reasons": result.get("human_review_reasons", []),
            "errors": errors,
            "classification_routes": result.get("classification_routes", []),
            "audit_summary": {
                "total_audit_entries": audit_entries,
            },
            "graph_state": result,
        }

    def run_from_files(
        self,
        acord_xml_path: Optional[str] = None,
        inspection_report_paths: Optional[list[str]] = None,
        supplemental_paths: Optional[list[str]] = None,
        bundle_id: Optional[str] = None,
    ) -> dict[str, Any]:
        acord_xml: Optional[str] = None
        if acord_xml_path:
            xml_path = pathlib.Path(acord_xml_path)
            if not xml_path.is_file():
                raise DataIngestionError(f"ACORD XML file not found: {acord_xml_path}")
            acord_xml = xml_path.read_text(encoding="utf-8")

        inspection_reports: Optional[list[str]] = None
        if inspection_report_paths:
            inspection_reports = []
            for p in inspection_report_paths:
                path = pathlib.Path(p)
                if not path.is_file():
                    raise DataIngestionError(f"Inspection report file not found: {p}")
                inspection_reports.append(path.read_text(encoding="utf-8"))

        supplemental_docs: Optional[list[str]] = None
        if supplemental_paths:
            supplemental_docs = []
            for p in supplemental_paths:
                path = pathlib.Path(p)
                if not path.is_file():
                    raise DataIngestionError(f"Supplemental document not found: {p}")
                supplemental_docs.append(path.read_text(encoding="utf-8"))

        return self.run(
            acord_xml=acord_xml,
            inspection_reports=inspection_reports,
            supplemental_docs=supplemental_docs,
            bundle_id=bundle_id,
        )
