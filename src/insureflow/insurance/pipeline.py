from __future__ import annotations

import dataclasses
import logging
from typing import Any, Callable
from uuid import uuid4

from insureflow.agents.appetite_filter import AppetiteFilterAgent
from insureflow.agents.extraction_agent import ExtractionAgent
from insureflow.agents.portfolio_risk_agent import PortfolioRiskAgent
from insureflow.agents.reinsurance_agent import ReinsuranceAgent
from insureflow.agents.supervisor import SupervisorAgent
from insureflow.agents.triage_agent import get_triage_agent
from insureflow.analytics.documents import DocumentAnalyticsEngine
from insureflow.audit.insurance_audit import InsuranceAuditLogger
from insureflow.audit.store import AuditStore
from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader
from insureflow.ingestion.loader import SubmissionLoader
from insureflow.insurance.progress import PipelineProgressTracker
from insureflow.integrations.factory import build_policy_admin_service
from insureflow.llm.client import LLMClient
from insureflow.models.audit import PipelineEvent
from insureflow.models.submissions import SubmissionStatus
from insureflow.oracles.factory import build_oracle_agent
from insureflow.outcomes.feedback import FeedbackEngine
from insureflow.portfolio.store import get_portfolio_store
from insureflow.provenance.hierarchy import ProvenanceEngine
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.reconciliation.engine import ReconciliationEngine
from insureflow.registry.service import RegistryService
from insureflow.storage.encryption import EnvelopeEncryption
from insureflow.webhooks.dispatcher import webhook_dispatcher
from insureflow.workflow.models import WorkflowState
from insureflow.workflow.service import WorkflowService

logger = logging.getLogger(__name__)


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
        self.oracle_agent = build_oracle_agent()
        self.portfolio_risk = PortfolioRiskAgent()
        self.reinsurance = ReinsuranceAgent()
        self.triage = get_triage_agent()
        self.policy_admin = build_policy_admin_service()
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
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        bid = bundle_id or f"ins-{uuid4().hex[:12]}"
        audit = InsuranceAuditLogger(self.audit_store, self.encryption, org_id=self.org_id)
        audit.start(bid)
        progress = PipelineProgressTracker(on_update=progress_callback)

        # ── 1. SUBMISSION TRIAGE (score & prioritize before any processing) ──
        progress.start("intake", "Intake", "Receiving submission package")
        progress.complete("intake", detail="Submission received")
        progress.start("triage", "Triage", "Scoring submission priority")
        triage_result = self.triage.score_submission(
            self._build_preliminary_bundle(
                acord_xml=acord_xml,
                json_payload=json_payload,
                loss_run=loss_run,
                bundle_id=bid,
            )
        )
        progress.complete(
            "triage",
            detail=f"Score {triage_result.score:.0f} · {triage_result.priority.value}",
        )

        # ── 2. FAST-FAIL APPETITE FILTER (before expensive ingestion) ──
        progress.start("appetite", "Appetite", "Checking carrier appetite")
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
                    metadata={
                        "appetite_passed": False,
                        "needs_uw_referral": appetite_result.needs_uw_referral,
                    },
                )
                if not appetite_result.needs_uw_referral:
                    progress.fail("appetite", appetite_result.reason)
                    for sid, label in [
                        ("parse", "Parsed"),
                        ("verify", "Verified"),
                        ("reconcile", "Reconciled"),
                        ("analyze", "Scored"),
                        ("price", "Priced"),
                    ]:
                        progress.skip(sid, label, "Appetite decline")
                    progress.start("decision", "Decision", "Declined")
                    progress.complete("decision", detail="DECLINE", status="failed", findings=1)
                    decline = self._build_appetite_decline_result(
                        bid,
                        appetite_result.reason,
                        appetite_result.findings,
                        audit,
                        triage_result=triage_result,
                    )
                    decline["pipeline_stages"] = progress.finish()
                    return decline

        progress.complete(
            "appetite",
            detail="Within appetite" if appetite_passed else "Referral required",
            status="warning" if appetite_result and appetite_result.needs_uw_referral else "complete",
        )

        # ── 2. Ingest ──
        progress.start("parse", "Parsed", "Ingesting and parsing documents")
        if documents:
            bundle = self.doc_loader.load_from_documents(documents, bundle_id=bid)
            ocr_count = sum(1 for d in bundle.unstructured if d.extracted_fields.get("ocr_engine"))
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
        progress.complete(
            "parse",
            detail=f"{len(bundle.unstructured)} docs · OCR {ocr_count}",
            findings=ocr_count,
        )

        # ── 2b. RE-SCORE DOCUMENT CHECKLIST on fully-ingested bundle ──
        triage_result = self.triage.score_submission(bundle)

        # ── 2c. REQUIRED DATA VALIDATION (hard gate against silent missing-data failures) ──
        validation_findings: list[Any] = []
        missing_docs = triage_result.document_checklist.missing
        required_docs = {
            "Loss run (5 year claims history)": "loss_run",
            "ACORD application form": "acord",
            "Schedule of values": "sov",
        }
        for label in required_docs:
            if label in missing_docs:
                from insureflow.models.agents import Finding, RiskSeverity

                validation_findings.append(
                    Finding(
                        title=f"Missing required document: {label}",
                        description=f"{label} was not provided or could not be parsed. Pricing without this data risks underestimating exposure.",
                        severity=RiskSeverity.CRITICAL,
                        category="data_quality",
                        field_path=required_docs[label],
                    )
                )

        loss_run_raw = loss_run or ""
        loss_run_expected = "Loss run (5 year claims history)" not in missing_docs
        if bundle.structured:
            fin = bundle.structured.financial
            has_claims = fin and fin.loss_run and len(fin.loss_run.claims) > 0
            if not has_claims and (loss_run_raw.strip() or loss_run_expected):
                from insureflow.models.agents import Finding, RiskSeverity

                validation_findings.append(
                    Finding(
                        title="Loss run provided but empty — no claims extracted",
                        description="Loss run attached but zero claims parsed (password-protected, corrupted, or unrecognized format). This is NOT a clean history — data is missing.",
                        severity=RiskSeverity.CRITICAL,
                        category="data_quality",
                        field_path="financial.loss_run.claims",
                    )
                )

        if bundle.structured is None:
            from insureflow.models.agents import Finding, RiskSeverity

            validation_findings.append(
                Finding(
                    title="No structured submission data",
                    description="No ACORD XML, JSON payload, or broker API data was received. Coverage limits, named insured, and policy terms are unknown.",
                    severity=RiskSeverity.CRITICAL,
                    category="data_quality",
                    field_path="structured",
                )
            )
        else:
            has_coverage_limits = bool(bundle.structured.coverages and any(c.limit_amount and c.limit_amount > 0 for c in bundle.structured.coverages))
            if not has_coverage_limits:
                from insureflow.models.agents import Finding, RiskSeverity

                validation_findings.append(
                    Finding(
                        title="No coverage limits available",
                        description="No coverage limits were extracted from any source. Premium cannot be accurately rated without limit data.",
                        severity=RiskSeverity.CRITICAL,
                        category="data_quality",
                        field_path="coverages[].limit",
                    )
                )

        if validation_findings:
            logger.warning("Required-data validation: %d missing-critical finding(s)", len(validation_findings))
            audit.log(
                PipelineEvent.STRUCTURED_PARSE_COMPLETE,
                f"Required-data validation: {len(validation_findings)} critical missing-data finding(s)",
                metadata={
                    "validation_findings": [f.title for f in validation_findings],
                    "human_review_required": True,
                },
            )

        # ── 2.5. PROPERTY PHOTO ANALYSIS (vision LLM + satellite + damage detection) ──
        visual_profile = None
        photos = [d for d in documents if d.get("filename", "").lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp"))] if documents else []
        if photos:
            progress.start("vision", "Vision", "Analyzing property photos")
            try:
                from insureflow.ml.vision.pipeline import PropertyPhotoAnalyzer

                vision_analyzer = PropertyPhotoAnalyzer()
                lat = None
                lng = None
                addr = ""
                if bundle.structured and bundle.structured.locations:
                    loc = bundle.structured.locations[0]
                    addr = f"{loc.address}, {loc.city}, {loc.state} {loc.zip_code}"
                visual_profile = vision_analyzer.analyze_photos(
                    photos,
                    latitude=lat,
                    longitude=lng,
                    address=addr,
                    bundle_id=bid,
                )
                audit.log(
                    PipelineEvent.STRUCTURED_PARSE_COMPLETE,
                    f"Vision analysis: {visual_profile.analyzed_photos} photos, risk={visual_profile.overall_visual_risk.value}",
                    metadata={
                        "vision_photos": visual_profile.analyzed_photos,
                        "vision_risk": visual_profile.overall_visual_risk.value,
                        "vision_damage_count": visual_profile.damage_count,
                    },
                )
                progress.complete(
                    "vision",
                    detail=f"{visual_profile.analyzed_photos} photos · {visual_profile.overall_visual_risk.value} risk",
                    findings=visual_profile.damage_count,
                    status="warning" if visual_profile.damage_count > 0 else "complete",
                )
            except Exception as exc:
                logger.warning("Vision analysis failed: %s", exc)
                progress.complete("vision", detail="Vision analysis skipped", status="warning")

        # ── 3. Extract (LLM on unstructured if enabled) ──
        if self.use_llm and getattr(self.extraction.llm, "api_key", None):
            bundle = self.extraction.process_bundle(bundle)
        bundle.status = SubmissionStatus.EXTRACTED

        # ── 4. EXTERNAL DATA ORACLES (CLUE, NCCI, CAT) ──
        progress.start("verify", "Verified", "Running external oracle checks")
        oracle_findings: list[Any] = []
        if not skip_oracles:
            bundle.status = SubmissionStatus.EXTERNAL_ORACLE_CHECK
            oracle_result = self.oracle_agent.run(bundle, org_id=self.org_id)
            oracle_findings = oracle_result.findings
            audit.log(
                PipelineEvent.VERIFICATION_COMPLETE,
                f"Oracle queries: {len(oracle_findings)} findings from CLUE, NCCI, CAT models",
                metadata={
                    "oracle_success": oracle_result.success,
                    "oracle_findings": len(oracle_findings),
                },
            )

        progress.complete(
            "verify",
            detail=f"{len(oracle_findings)} oracle finding(s)",
            findings=len(oracle_findings),
            status="warning" if oracle_findings else "complete",
        )

        # ── 5. Provenance + Reconciliation ──
        progress.start("reconcile", "Reconciled", "Reconciling cross-document fields")
        try:
            provenance = self.provenance.build_provenance(bundle)
        except Exception as exc:
            logger.error("Provenance build failed: %s", exc)
            audit.log(
                PipelineEvent.VERIFICATION_COMPLETE,
                f"Provenance build failed: {exc}",
                metadata={"provenance_error": str(exc)},
            )
            from insureflow.models.provenance import ProvenanceRecord

            provenance = ProvenanceRecord(record_id=f"prov-{bid}", bundle_id=bid)

        try:
            reconciliation = self.reconciliation.reconcile(provenance)
        except Exception as exc:
            logger.error("Reconciliation failed: %s", exc)
            audit.log(
                PipelineEvent.RECONCILIATION_COMPLETE,
                f"Reconciliation failed: {exc}",
                metadata={"reconciliation_error": str(exc)},
            )
            from insureflow.models.audit import ReconciliationResult

            reconciliation = ReconciliationResult(bundle_id=bid)

        progress.complete(
            "reconcile",
            detail=f"{len(reconciliation.discrepancies)} conflict(s) · {reconciliation.match_rate:.0%} match",
            findings=len(reconciliation.discrepancies),
            status="warning" if reconciliation.discrepancies else "complete",
        )

        # ── 6. Agent swarm → UW memo ──
        progress.start("analyze", "Scored", "Running specialist agent analysis")
        memo = self.supervisor.analyze_submission(bundle, parallel=True, use_celery=False)

        # ── 6a. Low-confidence critical field hold ──
        confidence_floor = 0.6
        low_conf_fields = []
        for field_path, fr in (reconciliation.field_reconciliation or {}).items():
            if field_path.startswith("coverage.") and field_path.endswith((".limit", ".deductible", ".premium")):
                conf = fr.get("confidence", 0) or 0
                if conf < confidence_floor:
                    low_conf_fields.append((field_path, conf))
        if low_conf_fields:
            detail = "; ".join(f"{p} @ {c:.0%}" for p, c in low_conf_fields)
            from insureflow.models.agents import Finding, RiskSeverity

            memo.key_findings.append(
                Finding(
                    title="Low-confidence extraction on critical field",
                    description=f"Coverage financial fields have resolved confidence below {confidence_floor:.0%}, indicating possible OCR error: {detail}",
                    severity=RiskSeverity.HIGH,
                    category="data_quality",
                    confidence=0.95,
                )
            )
            memo.human_review_required = True
            memo.human_review_reasons.append(f"Low-confidence critical fields require review: {detail}")

        # Merge oracle findings into memo
        if oracle_findings:
            for f in oracle_findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)

        # Merge required-data validation findings into memo
        if validation_findings:
            for f in validation_findings:
                memo.key_findings.append(f)
                memo.human_review_reasons.append(f.title)
            memo.human_review_required = True

        agent_findings = len(memo.key_findings) - len(oracle_findings) - len(validation_findings)
        progress.complete(
            "analyze",
            detail=f"Risk {memo.overall_risk_score:.0%}" if memo.overall_risk_score else f"{agent_findings} agent finding(s)",
            findings=max(agent_findings, 0),
            status="warning" if memo.human_review_required else "complete",
        )

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
        progress.start("price", "Priced", "Calculating indicated premium")
        quote = self.rating.quote(bundle, memo)
        progress.complete(
            "price",
            detail=f"Indicated ${quote.adjusted_premium:,.0f}",
        )

        # ── 9b. Generate quote document HTML ──
        try:
            from insureflow.rating.quote_document import generate_quote_html

            quote_html = generate_quote_html(bundle, memo, quote)
        except Exception as exc:
            logger.error("Quote HTML generation failed: %s", exc)
            audit.log(
                PipelineEvent.PIPELINE_COMPLETE,
                f"Quote document generation failed: {exc}",
                metadata={"quote_html_error": str(exc)},
            )
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
        progress.start("decision", "Decision", "Final underwriting recommendation")
        wf = self.workflow.submit_for_review(bid, self.org_id, memo.decision.value)
        progress.complete(
            "decision",
            detail=memo.decision.value.upper(),
            findings=len(memo.human_review_reasons),
            status="warning" if memo.human_review_required else "complete",
        )
        progress.finish()

        # ── 14. Dispatch status webhooks for broker visibility ──
        webhook_dispatcher.dispatch(
            "insurance.completed",
            self.org_id,
            {
                "bundle_id": bid,
                "status": "completed",
                "decision": memo.decision.value,
                "insured_name": memo.insured_name,
                "workflow_state": wf.state.value,
            },
        )

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
            "document_checklist": {
                "completeness_pct": triage_result.document_checklist.completeness_pct,
                "missing_documents": triage_result.document_checklist.missing,
                "present_documents": [
                    k
                    for k, v in {
                        "acord_form": triage_result.document_checklist.acord_form,
                        "loss_run": triage_result.document_checklist.loss_run,
                        "financials": triage_result.document_checklist.financials,
                        "property_photos": triage_result.document_checklist.photos,
                        "inspection_report": triage_result.document_checklist.inspection_report,
                        "schedule_of_values": triage_result.document_checklist.schedule_of_values,
                        "supplemental_forms": triage_result.document_checklist.supplemental,
                        "signed_application": triage_result.document_checklist.signed_application,
                    }.items()
                    if v
                ],
            },
            "reconciliation_discrepancies": len(reconciliation.discrepancies),
            "pipeline_stages": progress.stages,
            "provenance_summary": {
                "total_fields": provenance.record_count(),
                "verified_fields": provenance.verified_count(),
                "contradicted_fields": provenance.discrepancy_count(),
            },
            "human_checkpoints": self._build_checkpoints(memo, reconciliation, oracle_findings),
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

        # Add visual analysis data if available
        if visual_profile:
            summary["visual_analysis"] = visual_profile.to_dict()

        registry = RegistryService()
        version_context = registry.version_context()
        summary["version_context"] = version_context

        doc_analytics = DocumentAnalyticsEngine()
        doc_analytics.record(
            bundle_id=bid,
            document_count=summary.get("document_count", 0),  # type: ignore[arg-type]
            vertical="insurance",
            structured_count=1 if bundle.structured else 0,
            unstructured_count=len(bundle.unstructured),
            human_review_required=summary.get("human_review_required", False),  # type: ignore[arg-type]
            decision=summary.get("ai_decision", ""),  # type: ignore[arg-type]
            org_id=self.org_id,
        )

        audit_paths = audit.persist(bundle, memo, provenance, reconciliation, extra=summary)

        return {
            **summary,
            "memo": memo.model_dump(),
            "quote_full": dataclasses.asdict(quote),
            "quote_html": quote_html,
            "reconciliation": reconciliation.model_dump(),
            "provenance": provenance.model_dump(),
            "audit_paths": audit_paths,
            "audit_trail_entries": len(audit.trail.entries) if audit.trail else 0,
        }

    def _build_checkpoints(self, memo: Any, reconciliation: Any, oracle_findings: list[Any]) -> list[dict[str, Any]]:
        checkpoints: list[dict[str, Any]] = []
        if oracle_findings:
            checkpoints.append(
                {
                    "id": "oracle_review",
                    "label": "Verify oracle results",
                    "status": "pending",
                    "reason": f"{len(oracle_findings)} external data finding(s) require review before bind",
                }
            )
        critical = [d for d in reconciliation.discrepancies if getattr(d.severity, "value", str(d.severity)) == "critical"]
        if critical:
            checkpoints.append(
                {
                    "id": "reconciliation_review",
                    "label": "Resolve critical conflicts",
                    "status": "pending",
                    "reason": f"{len(critical)} critical field conflict(s)",
                }
            )
        if memo.human_review_required:
            checkpoints.append(
                {
                    "id": "uw_signoff",
                    "label": "Licensed UW sign-off",
                    "status": "pending",
                    "reason": "; ".join(memo.human_review_reasons[:3]) or "Human review required",
                }
            )
        return checkpoints

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
        triage_result: Any = None,
    ) -> dict[str, Any]:
        wf = self.workflow.submit_for_review(bundle_id, self.org_id, "decline")
        checklist: dict[str, Any] = {}
        if triage_result and hasattr(triage_result, "document_checklist"):
            cl = triage_result.document_checklist
            checklist = {
                "completeness_pct": cl.completeness_pct,
                "missing_documents": cl.missing,
                "present_documents": [
                    k
                    for k, v in {
                        "acord_form": cl.acord_form,
                        "loss_run": cl.loss_run,
                        "financials": cl.financials,
                        "property_photos": cl.photos,
                        "inspection_report": cl.inspection_report,
                        "schedule_of_values": cl.schedule_of_values,
                        "supplemental_forms": cl.supplemental,
                        "signed_application": cl.signed_application,
                    }.items()
                    if v
                ],
            }
        result = {
            "status": "completed",
            "bundle_id": bundle_id,
            "org_id": self.org_id,
            "appetite_filter_passed": False,
            "decline_reason": reason,
            "ai_decision": "decline",
            "workflow_state": wf.state.value,
            "human_review_required": False,
            "ocr_documents": 0,
            "document_count": 0,
            "document_checklist": checklist or None,
            "reconciliation_discrepancies": 0,
            "quote": {},
            "encryption_at_rest": self.encryption.enabled,
        }
        audit.persist(None, None, extra=result)
        result["audit_trail_entries"] = len(audit.trail.entries) if audit.trail else 0
        webhook_dispatcher.dispatch(
            "insurance.declined",
            self.org_id,
            {
                "bundle_id": bundle_id,
                "status": "declined",
                "reason": reason,
            },
        )
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
        except Exception as exc:
            logger.error("Portfolio recording failed: %s", exc)
