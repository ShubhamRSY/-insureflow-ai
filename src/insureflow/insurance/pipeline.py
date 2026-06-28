from __future__ import annotations

import dataclasses
from typing import Any
from uuid import uuid4

from insureflow.agents.appetite_filter import AppetiteFilterAgent
from insureflow.agents.extraction_agent import ExtractionAgent
from insureflow.agents.portfolio_risk_agent import PortfolioRiskAgent
from insureflow.agents.reinsurance_agent import ReinsuranceAgent
from insureflow.agents.triage_agent import TriageAgent, get_triage_agent
from insureflow.oracles.oracle_agent import OracleAgent
from insureflow.agents.supervisor import SupervisorAgent
from insureflow.audit.insurance_audit import InsuranceAuditLogger
from insureflow.audit.store import AuditStore
from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader
from insureflow.ingestion.loader import SubmissionLoader
from insureflow.integration.policy_admin_service import PolicyAdminService
from insureflow.llm.client import LLMClient
from insureflow.models.audit import PipelineEvent
from insureflow.models.submissions import SubmissionStatus
from insureflow.outcomes.feedback import FeedbackEngine
from insureflow.portfolio.store import get_portfolio_store
from insureflow.provenance.hierarchy import ProvenanceEngine
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.reconciliation.engine import ReconciliationEngine
from insureflow.storage.encryption import EnvelopeEncryption
from insureflow.webhooks.dispatcher import webhook_dispatcher
from insureflow.workflow.models import WorkflowState
from insureflow.workflow.service import WorkflowService


class InsurancePipeline:
    """Production insurance pipeline with:
    - Submission triage & scoring (sort 100 apps, surface best first)
    - Fast-fail appetite filter (before expensive processing)
    - External data oracle queries (CLUE, NCCI, CAT)
    - COPE risk analysis (Construction, Occupancy, Protection, Exposure)
    - ISO-style rating with territory relativities & market cycle adjustments
    - Portfolio concentration risk analysis
    - Reinsurance treaty fit with aggregate tracking
    - Authority-based approval routing (Junior/Senior/CUO tiers)
    - Core system integration (BriteCore/Guidewire)
    - Real-time status webhooks for broker visibility
    """

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

        # New pipeline stages
        self.appetite_filter = AppetiteFilterAgent()
        self.oracle_agent = OracleAgent()
        self.portfolio_risk = PortfolioRiskAgent()
        self.reinsurance = ReinsuranceAgent()
        self.triage = get_triage_agent()
        self.policy_admin = PolicyAdminService()
        self.portfolio_store = get_portfolio_store()

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
        skip_appetite_filter: bool = False,
        skip_oracles: bool = False,
        skip_portfolio: bool = False,
        skip_reinsurance: bool = False,
        skip_core_integration: bool = False,
    ) -> dict[str, Any]:
        bid = bundle_id or f"ins-{uuid4().hex[:12]}"
        audit = InsuranceAuditLogger(self.audit_store, self.encryption, org_id=self.org_id)
        audit.start(bid)

        # ── 1. SUBMISSION TRIAGE (score & prioritize before any processing) ──
        triage_result = self.triage.score_submission(
            self._build_preliminary_bundle(
                acord_xml=acord_xml,
                json_payload=json_payload,
                loss_run=loss_run,
                bundle_id=bid,
            )
        )

        # ── 2. FAST-FAIL APPETITE FILTER (before expensive ingestion) ──
        appetite_passed = True
        appetite_result = None
        if not skip_appetite_filter:
            pre_bundle = self._build_preliminary_bundle(
                acord_xml=acord_xml,
                json_payload=json_payload,
                loss_run=loss_run,
                bundle_id=bid,
            )
            appetite_result = self.appetite_filter.check_appetite(pre_bundle)
            if not appetite_result.passed:
                appetite_passed = False
                audit.log(
                    PipelineEvent.STRUCTURED_PARSE_COMPLETE,
                    f"Appetite filter: {appetite_result.reason}",
                    metadata={"appetite_passed": False, "needs_uw_referral": appetite_result.needs_uw_referral},
                )
                if not appetite_result.needs_uw_referral:
                    return self._build_appetite_decline_result(
                        bid, appetite_result.reason, appetite_result.findings, audit,
                    )

        # ── 2. Ingest ──
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

        # ── 3. Extract (LLM on unstructured if enabled) ──
        if self.use_llm and getattr(self.extraction.llm, "api_key", None):
            bundle = self.extraction.process_bundle(bundle)
        bundle.status = SubmissionStatus.EXTRACTED

        # ── 4. EXTERNAL DATA ORACLES (CLUE, NCCI, CAT) ──
        oracle_findings: list[Any] = []
        if not skip_oracles:
            bundle.status = SubmissionStatus.EXTERNAL_ORACLE_CHECK
            oracle_result = self.oracle_agent.run(bundle, org_id=self.org_id)
            oracle_findings = oracle_result.findings
            audit.log(
                PipelineEvent.VERIFICATION_COMPLETE,
                f"Oracle queries: {len(oracle_findings)} findings from CLUE, NCCI, CAT models",
                metadata={"oracle_success": oracle_result.success, "oracle_findings": len(oracle_findings)},
            )

        # ── 5. Provenance + Reconciliation ──
        provenance = self.provenance.build_provenance(bundle)
        reconciliation = self.reconciliation.reconcile(provenance)

        # ── 6. Agent swarm → UW memo ──
        memo = self.supervisor.analyze_submission(bundle, parallel=True, use_celery=False)

        # Merge oracle findings into memo
        if oracle_findings:
            for f in oracle_findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)

        # ── 7. PORTFOLIO CONCENTRATION RISK ──
        portfolio_result = None
        if not skip_portfolio:
            bundle.status = SubmissionStatus.PORTFOLIO_REVIEW
            portfolio_result = self.portfolio_risk.run(bundle, org_id=self.org_id)
            for f in portfolio_result.findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)
                    memo.human_review_required = True
            audit.log(
                PipelineEvent.SYNTHESIS_COMPLETE,
                f"Portfolio risk: {len(portfolio_result.findings)} findings",
                metadata={"portfolio_score": portfolio_result.risk_score},
            )

        # ── 8. REINSURANCE TREATY ANALYSIS ──
        if not skip_reinsurance:
            bundle.status = SubmissionStatus.REINSURANCE_REVIEW
            reinsurance_result = self.reinsurance.run(bundle, org_id=self.org_id)
            for f in reinsurance_result.findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)
                    if "No applicable reinsurance treaty" in f.title:
                        memo.human_review_required = True
            audit.log(
                PipelineEvent.SYNTHESIS_COMPLETE,
                f"Reinsurance: {len(reinsurance_result.findings)} findings",
                metadata={"reinsurance_score": reinsurance_result.risk_score},
            )

        # ── 9. Rating / policy admin quote ──
        quote = self.rating.quote(bundle, memo)

        # ── 9b. Generate quote document HTML ──
        try:
            from insureflow.rating.quote_document import generate_quote_html
            quote_html = generate_quote_html(bundle, memo, quote)
        except Exception:
            quote_html = ""

        # ── 10. CORE SYSTEM INTEGRATION (push to BriteCore/Guidewire) ──
        core_results: list[dict[str, Any]] = []
        if not skip_core_integration:
            core_results = self.policy_admin.submit_to_core_systems(bundle, memo, quote, self.org_id)
            successful = [r for r in core_results if r.get("success")]
            audit.log(
                PipelineEvent.PIPELINE_COMPLETE,
                f"Core system integration: {len(successful)}/{len(core_results)} systems updated",
                metadata={"core_results": core_results},
            )

        # ── 11. Feedback loop: record prediction ──
        prediction = self.feedback.record_prediction(bid, memo, quote, org_id=self.org_id)

        # ── 12. Portfolio: record this new policy ──
        self._record_portfolio_policy(bundle, memo, quote)

        # ── 13. Workflow: submit for licensed UW review ──
        wf = self.workflow.submit_for_review(bid, self.org_id, memo.decision.value)

        # ── 14. Dispatch status webhooks for broker visibility ──
        webhook_dispatcher.dispatch("insurance.completed", self.org_id, {
            "bundle_id": bid,
            "status": "completed",
            "decision": memo.decision.value,
            "insured_name": memo.insured_name,
            "workflow_state": wf.state.value,
        })

        broker_name = ""
        if bundle.structured and bundle.structured.broker:
            broker_name = bundle.structured.broker.broker_name

        summary = {
            "status": "completed",
            "bundle_id": bid,
            "org_id": self.org_id,
            "insured_name": memo.insured_name,
            "broker_name": broker_name,
            "triage_priority": triage_result.priority.value,
            "triage_score": triage_result.score,
            "ai_decision": memo.decision.value,
            "workflow_state": wf.state.value,
            "human_review_required": memo.human_review_required or wf.state == WorkflowState.PENDING_REVIEW,
            "appetite_filter_passed": appetite_passed,
            "appetite_needs_uw_referral": appetite_result.needs_uw_referral if appetite_result else False,
            "oracle_findings_count": len(oracle_findings),
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
            "core_integration": core_results,
            "encryption_at_rest": self.encryption.enabled,
            "prediction_id": prediction.prediction_id,
        }

        # Add portfolio concentration data if available
        if portfolio_result:
            summary["portfolio_concentration_score"] = portfolio_result.risk_score
            portfolio_findings = [f.model_dump() for f in portfolio_result.findings]
            summary["portfolio_findings"] = portfolio_findings

        audit_paths = audit.persist(bundle, memo, provenance, reconciliation, extra=summary)

        return {
            **summary,
            "memo": memo.model_dump(),
            "quote_full": dataclasses.asdict(quote),
            "quote_html": quote_html,
            "reconciliation": reconciliation.model_dump(),
            "audit_paths": audit_paths,
            "audit_trail_entries": len(audit.trail.entries) if audit.trail else 0,
        }

    def _build_preliminary_bundle(
        self,
        acord_xml: str | None = None,
        json_payload: str | None = None,
        loss_run: str | None = None,
        bundle_id: str = "",
    ) -> Any:
        """Build a minimal bundle just for appetite filtering (avoids expensive processing)."""
        bundle = self.legacy_loader.load_bundle(
            acord_xml=acord_xml,
            json_payload=json_payload,
            loss_run=loss_run,
            bundle_id=bundle_id,
        )
        bundle.status = SubmissionStatus.PENDING_APPETITE_CHECK
        return bundle

    def _build_appetite_decline_result(
        self,
        bundle_id: str,
        reason: str,
        appetite_findings: list[Any],
        audit: InsuranceAuditLogger,
    ) -> dict[str, Any]:
        result = {
            "status": "declined",
            "bundle_id": bundle_id,
            "org_id": self.org_id,
            "appetite_filter_passed": False,
            "decline_reason": reason,
            "ai_decision": "decline",
            "workflow_state": "declined",
            "human_review_required": False,
            "ocr_documents": 0,
            "document_count": 0,
            "reconciliation_discrepancies": 0,
            "quote": {},
            "encryption_at_rest": self.encryption.enabled,
        }
        audit.persist(None, None, extra=result)
        webhook_dispatcher.dispatch("insurance.declined", self.org_id, {
            "bundle_id": bundle_id,
            "status": "declined",
            "reason": reason,
        })
        return result

    def _record_portfolio_policy(self, bundle: Any, memo: Any, quote: Any) -> None:
        """Record the bound policy in the portfolio store for future concentration analysis."""
        try:
            from insureflow.portfolio.store import PortfolioPolicy

            state = ""
            naics = ""
            tiv = 0.0
            occupancy = ""
            if bundle.structured:
                if bundle.structured.locations:
                    loc = bundle.structured.locations[0]
                    state = loc.state or ""
                    tiv = (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)
                    occupancy = loc.building_occupancy or ""
                if bundle.structured.risk_profile:
                    naics = bundle.structured.risk_profile.naics_code or ""

            policy = PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}",
                bundle_id=bundle.bundle_id,
                org_id=self.org_id,
                insured_name=memo.insured_name,
                naics_code=naics,
                state=state,
                tiv=tiv,
                premium=quote.adjusted_premium,
                occupancy_type=occupancy,
            )
            self.portfolio_store.add_policy(policy)
        except Exception:
            pass
