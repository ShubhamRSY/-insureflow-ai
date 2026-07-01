from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from insureflow.agents.extraction_agent import ExtractionAgent
from insureflow.agents.synthesis_agent import SynthesisAgent
from insureflow.agents.verification_agent import VerificationAgent
from insureflow.audit.logger import AuditLogger
from insureflow.audit.store import AuditStore
from insureflow.audit.trail import ProvenanceTrailBuilder
from insureflow.ingestion.loader import SubmissionLoader
from insureflow.llm.client import LLMClient
from insureflow.models.audit import (
    EventSeverity,
    PipelineEvent,
    ReconciliationResult,
    SynthesisOutput,
)
from insureflow.models.provenance import ProvenanceRecord
from insureflow.models.submissions import SubmissionBundle, SubmissionStatus
from insureflow.provenance.hierarchy import ProvenanceEngine
from insureflow.reconciliation.engine import ReconciliationEngine


class PipelineOrchestrator:
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        audit_store: Optional[AuditStore] = None,
    ) -> None:
        self.llm = llm_client or LLMClient()
        self.loader = SubmissionLoader()
        self.extraction_agent = ExtractionAgent(self.llm)
        self.provenance_engine = ProvenanceEngine()
        self.reconciliation_engine = ReconciliationEngine()
        self.verification_agent = VerificationAgent(self.llm)
        self.synthesis_agent = SynthesisAgent(self.llm)
        self.audit_logger = AuditLogger()
        self.audit_store = audit_store or AuditStore()
        self.trail_builder = ProvenanceTrailBuilder()

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
    ) -> dict:
        bundle_id = bundle_id or f"run-{uuid4().hex[:12]}"
        audit_trail = self.audit_logger.create_trail(bundle_id)

        results: dict = {
            "bundle_id": bundle_id,
            "status": "running",
            "steps": {},
        }

        bundle = self._step_ingest(
            acord_xml,
            inspection_reports,
            supplemental_docs,
            json_payload,
            loss_run,
            schedule_of_values,
            raw_docs,
            auto_classify,
            bundle_id,
        )
        results["steps"]["ingestion"] = {"bundle_id": bundle.bundle_id, "status": "complete"}

        bundle = self._step_extract(bundle)
        results["steps"]["extraction"] = {"status": "complete"}

        provenance = self._step_provenance(bundle)
        results["steps"]["provenance"] = {
            "record_id": provenance.record_id,
            "nodes": provenance.record_count(),
        }

        reconciliation = self._step_reconcile(provenance)
        results["steps"]["reconciliation"] = {
            "match_rate": reconciliation.match_rate,
            "discrepancies": len(reconciliation.discrepancies),
            "overall_status": reconciliation.overall_status,
        }

        synthesis = self._step_synthesize(provenance, reconciliation)
        results["steps"]["synthesis"] = {
            "human_review_required": synthesis.human_review_required,
            "discrepancies_found": synthesis.discrepancies_found,
        }

        self._step_audit(bundle, provenance, reconciliation, synthesis, audit_trail)
        results["status"] = "completed" if not synthesis.human_review_required else "flagged"
        results["synthesis"] = synthesis.model_dump()
        results["reconciliation"] = reconciliation.model_dump()
        results["audit_summary"] = self.trail_builder.build_audit_summary(audit_trail, provenance)

        self.audit_logger.complete_trail(bundle_id)
        self.audit_logger.log(
            bundle_id,
            PipelineEvent.PIPELINE_COMPLETE,
            agent_name="orchestrator",
            message=f"Pipeline completed with status: {results['status']}",
            severity=EventSeverity.INFO,
        )

        return results

    def _step_ingest(
        self,
        acord_xml: Optional[str],
        inspection_reports: Optional[list[str]],
        supplemental_docs: Optional[list[str]],
        json_payload: Optional[str],
        loss_run: Optional[str],
        schedule_of_values: Optional[str],
        raw_docs: Optional[list[str]],
        auto_classify: bool,
        bundle_id: str,
    ) -> SubmissionBundle:
        self.audit_logger.log(
            bundle_id,
            PipelineEvent.SUBMISSION_RECEIVED,
            "orchestrator",
            "Loading submission bundle",
        )
        bundle = self.loader.load_bundle(
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
        bundle.status = SubmissionStatus.PARSED
        self.audit_store.persist_bundle(bundle)
        return bundle

    def _step_extract(self, bundle: SubmissionBundle) -> SubmissionBundle:
        self.audit_logger.log(
            bundle.bundle_id,
            PipelineEvent.EXTRACTION_START,
            "extraction_agent",
            "Starting extraction on bundle",
        )
        bundle = self.extraction_agent.process_bundle(bundle)
        bundle.status = SubmissionStatus.EXTRACTED
        self.audit_logger.log(
            bundle.bundle_id,
            PipelineEvent.EXTRACTION_COMPLETE,
            "extraction_agent",
            "Extraction complete",
        )
        return bundle

    def _step_provenance(self, bundle: SubmissionBundle) -> ProvenanceRecord:
        self.audit_logger.log(
            bundle.bundle_id,
            PipelineEvent.PROVENANCE_CHECK,
            "provenance_engine",
            "Building provenance records",
        )
        record = self.provenance_engine.build_provenance(bundle)
        self.audit_store.persist_provenance(record)
        return record

    def _step_reconcile(self, provenance: ProvenanceRecord) -> ReconciliationResult:
        self.audit_logger.log(
            provenance.bundle_id,
            PipelineEvent.RECONCILIATION_START,
            "verification_agent",
            "Running reconciliation",
        )
        result, scores = self.verification_agent.verify(provenance)

        for d in result.discrepancies:
            self.audit_logger.log(
                provenance.bundle_id,
                PipelineEvent.DISCREPANCY_DETECTED,
                "verification_agent",
                d.description,
                severity=d.severity,
                metadata={
                    "field_path": d.field_path,
                    "source_a": d.source_a,
                    "source_b": d.source_b,
                },
            )

        self.audit_store.persist_reconciliation(result)
        self.audit_logger.log(
            provenance.bundle_id,
            PipelineEvent.RECONCILIATION_COMPLETE,
            "verification_agent",
            f"Match rate: {result.match_rate:.1%}, discrepancies: {len(result.discrepancies)}",
        )
        return result

    def _step_synthesize(
        self,
        provenance: ProvenanceRecord,
        reconciliation: ReconciliationResult,
    ) -> SynthesisOutput:
        self.audit_logger.log(
            provenance.bundle_id,
            PipelineEvent.SYNTHESIS_START,
            "synthesis_agent",
            "Building synthesis output",
        )
        synthesis = self.synthesis_agent.synthesize(provenance, reconciliation)
        self.audit_store.persist_synthesis(synthesis)
        self.audit_logger.log(
            provenance.bundle_id,
            PipelineEvent.SYNTHESIS_COMPLETE,
            "synthesis_agent",
            f"Synthesis complete, human_review={synthesis.human_review_required}",
        )
        return synthesis

    def _step_audit(
        self,
        bundle: SubmissionBundle,
        provenance: ProvenanceRecord,
        reconciliation: ReconciliationResult,
        synthesis: SynthesisOutput,
        audit_trail: Any,
    ) -> None:
        self.audit_store.persist_audit_trail(audit_trail)
