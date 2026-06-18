from __future__ import annotations

from typing import Any
from uuid import uuid4

from insureflow.agents.extraction_agent import ExtractionAgent
from insureflow.agents.supervisor import SupervisorAgent
from insureflow.audit.insurance_audit import InsuranceAuditLogger
from insureflow.audit.store import AuditStore
from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader
from insureflow.ingestion.loader import SubmissionLoader
from insureflow.llm.client import LLMClient
from insureflow.models.audit import PipelineEvent
from insureflow.models.submissions import SubmissionStatus
from insureflow.outcomes.feedback import FeedbackEngine
from insureflow.provenance.hierarchy import ProvenanceEngine
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.reconciliation.engine import ReconciliationEngine
from insureflow.storage.encryption import EnvelopeEncryption
from insureflow.workflow.models import WorkflowState
from insureflow.workflow.service import WorkflowService


class InsurancePipeline:
    """Production insurance pipeline: OCR ingest → agents → rating → audit → UW workflow."""

    def __init__(
        self,
        org_id: str = "default",
        use_llm: bool = True,
        audit_store: AuditStore | None = None,
    ) -> None:
        self.org_id = org_id
        self.use_llm = use_llm
        self.doc_loader = InsuranceDocumentLoader()
        self.legacy_loader = SubmissionLoader()
        self.extraction = ExtractionAgent(LLMClient(model_tier="cheap") if use_llm else None)
        self.provenance = ProvenanceEngine()
        self.reconciliation = ReconciliationEngine()
        self.supervisor = SupervisorAgent()
        self.rating = InsuranceRatingEngine()
        self.workflow = WorkflowService()
        self.feedback = FeedbackEngine()
        self.audit_store = audit_store or AuditStore()
        self.encryption = EnvelopeEncryption()

    def run(
        self,
        *,
        acord_xml: str | None = None,
        inspection_reports: list[str] | None = None,
        supplemental_docs: list[str] | None = None,
        json_payload: str | None = None,
        loss_run: str | None = None,
        schedule_of_values: str | None = None,
        documents: list[dict[str, str]] | None = None,
        pdf_paths: list[str] | None = None,
        bundle_id: str | None = None,
    ) -> dict[str, Any]:
        bid = bundle_id or f"ins-{uuid4().hex[:12]}"
        audit = InsuranceAuditLogger(self.audit_store, self.encryption, org_id=self.org_id)
        audit.start(bid)

        # ── Ingest ──
        if documents:
            bundle = self.doc_loader.load_from_documents(documents, bundle_id=bid)
            ocr_count = sum(
                1 for d in bundle.unstructured
                if d.extracted_fields.get("ocr_engine")
            )
        else:
            bundle = self.legacy_loader.load_bundle(
                acord_xml=acord_xml,
                inspection_reports=inspection_reports,
                supplemental_docs=supplemental_docs,
                json_payload=json_payload,
                loss_run=loss_run,
                schedule_of_values=schedule_of_values,
                pdf_paths=pdf_paths,
                bundle_id=bid,
            )
            ocr_count = len(pdf_paths or [])

        audit.log(
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            f"Ingested {len(bundle.unstructured)} unstructured docs, structured={'yes' if bundle.structured else 'no'}",
            metadata={"ocr_documents": ocr_count},
        )

        # ── Extract (LLM on unstructured if enabled) ──
        if self.use_llm and getattr(self.extraction.llm, "api_key", None):
            bundle = self.extraction.process_bundle(bundle)
        bundle.status = SubmissionStatus.EXTRACTED

        # ── Provenance + Reconciliation ──
        provenance = self.provenance.build_provenance(bundle)
        reconciliation = self.reconciliation.reconcile(provenance)

        # ── Agent swarm → UW memo ──
        memo = self.supervisor.analyze_submission(bundle, parallel=True, use_celery=False)

        # ── Rating / policy admin quote ──
        quote = self.rating.quote(bundle, memo)

        # ── Feedback loop: record prediction ──
        prediction = self.feedback.record_prediction(bid, memo, quote, org_id=self.org_id)

        # ── Workflow: submit for licensed UW review ──
        wf = self.workflow.submit_for_review(bid, self.org_id, memo.decision.value)

        summary = {
            "status": "completed",
            "bundle_id": bid,
            "org_id": self.org_id,
            "insured_name": memo.insured_name,
            "ai_decision": memo.decision.value,
            "workflow_state": wf.state.value,
            "human_review_required": memo.human_review_required or wf.state == WorkflowState.PENDING_REVIEW,
            "ocr_documents": ocr_count,
            "document_count": len(bundle.unstructured) + (1 if bundle.structured else 0),
            "reconciliation_discrepancies": len(reconciliation.discrepancies),
            "quote": {
                "adjusted_premium": quote.adjusted_premium,
                "base_premium": quote.base_premium,
                "eligible": quote.eligible,
                "policy_admin_reference": quote.policy_admin_reference,
                "quote_valid_until": quote.quote_valid_until,
            },
            "encryption_at_rest": self.encryption.enabled,
            "prediction_id": prediction.prediction_id,
        }

        audit_paths = audit.persist(bundle, memo, provenance, reconciliation, extra=summary)

        return {
            **summary,
            "memo": memo.model_dump(),
            "reconciliation": reconciliation.model_dump(),
            "audit_paths": audit_paths,
            "audit_trail_entries": len(audit.trail.entries) if audit.trail else 0,
        }
