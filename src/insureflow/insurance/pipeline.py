from __future__ import annotations

import dataclasses
import logging
from typing import Any, Callable
from uuid import uuid4

from insureflow.agents.adverse_selection_agent import AdverseSelectionAgent
from insureflow.agents.appetite_filter import AppetiteFilterAgent
from insureflow.agents.extraction_agent import ExtractionAgent
from insureflow.agents.portfolio_risk_agent import PortfolioRiskAgent
from insureflow.agents.producer_experience_agent import ProducerExperienceAgent
from insureflow.agents.reinsurance_agent import ReinsuranceAgent
from insureflow.agents.selection_standards_agent import SelectionStandardsAgent
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
from insureflow.models.agents import Recommendation
from insureflow.models.audit import PipelineEvent
from insureflow.models.submissions import SubmissionBundle, SubmissionStatus
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
from insureflow.zta.config import ZtaConfig
from insureflow.zta.models import RouteContext, RouteDecision, ZtaTask
from insureflow.zta.report import ZtaReporter
from insureflow.zta.router import ZeroTokenRouter

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

        # Zero Token Architecture — deterministic-first routing layer
        self.zta_config = ZtaConfig()
        self.zta_router = ZeroTokenRouter(
            config=self.zta_config,
            llm_available=bool(use_llm and getattr(self.extraction.llm, "api_key", None)),
        )
        self.zta_reporter = ZtaReporter(self.zta_router)

        # New pipeline stages
        self.appetite_filter = AppetiteFilterAgent()
        self.oracle_agent = build_oracle_agent()
        self.portfolio_risk = PortfolioRiskAgent()
        self.reinsurance = ReinsuranceAgent()
        self.selection_standards = SelectionStandardsAgent()
        self.producer_experience = ProducerExperienceAgent()
        self.adverse_selection = AdverseSelectionAgent()
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
        insurance_line: str | None = None,
        skip_appetite_filter: bool = False,
        skip_oracles: bool = False,
        skip_portfolio: bool = False,
        skip_reinsurance: bool = False,
        skip_core_integration: bool = False,
        funnel: bool = False,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        bid = bundle_id or f"ins-{uuid4().hex[:12]}"
        audit = InsuranceAuditLogger(self.audit_store, self.encryption, org_id=self.org_id)
        audit.start(bid)
        progress = PipelineProgressTracker(on_update=progress_callback)

        # Deferred stages in funnel mode are re-run on demand via deep_dive().
        deferred_stages: list[str] = []
        if funnel:
            deferred_stages = ["oracles", "portfolio", "selection_standards", "producer_experience", "adverse_selection", "reinsurance", "fraud_ml"]

        # ── 1. SUBMISSION TRIAGE (score & prioritize before any processing) ──
        progress.start("intake", "Intake", "Receiving submission package")
        progress.complete("intake", detail="Submission received")
        progress.start("triage", "Triage", "Scoring submission priority")
        from insureflow.underwriting.personal_lines import detect_insurance_line, parse_insurance_line

        resolved_line = parse_insurance_line(insurance_line)
        if resolved_line is None:
            pre_blob = " ".join(
                [
                    acord_xml or "",
                    json_payload or "",
                    loss_run or "",
                    " ".join(inspection_reports or []),
                    " ".join(d.get("filename", "") + " " + d.get("content", "")[:2000] for d in (documents or [])),
                ]
            )
            resolved_line = detect_insurance_line(pre_blob, insurance_line or "")

        triage_result = self.triage.score_submission(
            self._build_preliminary_bundle(
                acord_xml=acord_xml,
                json_payload=json_payload,
                loss_run=loss_run,
                bundle_id=bid,
            ),
            insurance_line=resolved_line.value if resolved_line else insurance_line,
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
            appetite_result = self.appetite_filter.check_appetite(
                pre_bundle,
                insurance_line=resolved_line.value if resolved_line else None,
            )
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
        line_hint = resolved_line.value if resolved_line else insurance_line
        triage_result = self.triage.score_submission(bundle, insurance_line=line_hint)
        checklist_lob = triage_result.document_checklist.lob

        # ── 2c. REQUIRED DATA VALIDATION (LOB-aware hard gates) ──
        validation_findings: list[Any] = []
        from insureflow.agents.triage_agent import REQUIRED_CRITICAL_BY_LOB
        from insureflow.models.agents import Finding, RiskSeverity

        missing_docs = set(triage_result.document_checklist.missing)
        required_labels = REQUIRED_CRITICAL_BY_LOB.get(checklist_lob, REQUIRED_CRITICAL_BY_LOB["property"])
        for label in required_labels:
            if label in missing_docs:
                validation_findings.append(
                    Finding(
                        title=f"Missing required document: {label}",
                        description=(f"{label} was not provided or could not be parsed. Cannot complete {checklist_lob} underwriting without it."),
                        severity=RiskSeverity.CRITICAL,
                        category="data_quality",
                        field_path=label.lower().replace(" ", "_").replace("/", "_"),
                    )
                )

        if checklist_lob == "property":
            loss_run_raw = loss_run or ""
            loss_run_expected = any("loss" in m.lower() for m in triage_result.document_checklist.present)
            if bundle.structured:
                fin = bundle.structured.financial
                has_claims = fin and fin.loss_run and len(fin.loss_run.claims) > 0
                if not has_claims and (loss_run_raw.strip() or loss_run_expected):
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
                    validation_findings.append(
                        Finding(
                            title="No coverage limits available",
                            description="No coverage limits were extracted from any source. Premium cannot be accurately rated without limit data.",
                            severity=RiskSeverity.CRITICAL,
                            category="data_quality",
                            field_path="coverages[].limit",
                        )
                    )

            # ── 2d. NON-CRITICAL (GUIDELINE) DATA GAPS — property only ──
            if bundle.structured and bundle.structured.locations:
                for li, loc in enumerate(bundle.structured.locations):
                    if loc.year_built is None or loc.year_built == 0:
                        validation_findings.append(
                            Finding(
                                title="Roof age or year built not provided",
                                description=f"Location {li}: year built is unknown. Age of roof is required per underwriting guidelines for hail-prone regions.",
                                severity=RiskSeverity.MODERATE,
                                category="data_quality",
                                field_path=f"locations[{li}].year_built",
                                confidence=0.95,
                            )
                        )
                    if loc.protection_class is None or loc.protection_class == 0:
                        validation_findings.append(
                            Finding(
                                title="Protection class not provided",
                                description=f"Location {li}: ISO protection class is unknown. May affect fire rating.",
                                severity=RiskSeverity.MODERATE,
                                category="data_quality",
                                field_path=f"locations[{li}].protection_class",
                                confidence=0.95,
                            )
                        )
        elif checklist_lob == "life" and not triage_result.document_checklist.present:
            validation_findings.append(
                Finding(
                    title="Incomplete life underwriting package",
                    description="Life application / medical evidence was not identified. Paramedical exam and APS may be required before bind.",
                    severity=RiskSeverity.HIGH,
                    category="data_quality",
                    field_path="life_package",
                )
            )

        # ── 2e. NON-STANDARD / MANUSCRIPT DOCUMENT DETECTION (commercial property) ──
        manuscript_keywords = (
            "endorsement",
            "manuscript",
            "rider",
            "amendment",
            "exclusion",
            "waiver",
            "limitation of liability",
            "additional insured",
            "policy change",
            "modification",
        )
        scrutinized: list[str] = []
        if checklist_lob != "property":
            pass  # life/auto/home use LOB catalogs — skip P&C manuscript heuristics
        for doc in bundle.unstructured if checklist_lob == "property" else []:
            if doc.document_type in ("loss_run", "schedule_of_values", "inspection_report"):
                continue
            text = (doc.raw_text or "").lower()
            matches = [kw for kw in manuscript_keywords if kw in text]
            if not matches:
                continue
            from insureflow.models.agents import Finding, RiskSeverity

            validation_findings.append(
                Finding(
                    title=f"Non-standard document with legal terms: {doc.document_type}",
                    description=f"Document '{doc.document_type}' has {len(matches)} manuscript keyword(s): {', '.join(matches)}. May impose liability or restrict coverage outside structured data.",
                    severity=RiskSeverity.CRITICAL,
                    category="compliance",
                    field_path="unstructured",
                    evidence=[doc.submission_id, doc.raw_text[:500]],
                )
            )
            scrutinized.append(doc.document_type)
        for doc in bundle.supplemental if checklist_lob == "property" else []:
            text = (doc.raw_text or "").lower()
            matches = [kw for kw in manuscript_keywords if kw in text]
            if not matches:
                continue
            from insureflow.models.agents import Finding, RiskSeverity

            validation_findings.append(
                Finding(
                    title=f"Supplemental document with legal terms: {doc.document_type}",
                    description=f"Supplemental doc has {len(matches)} manuscript keyword(s): {', '.join(matches)}. May modify policy terms outside standard endorsements.",
                    severity=RiskSeverity.CRITICAL,
                    category="compliance",
                    field_path="supplemental",
                    evidence=[doc.submission_id, doc.raw_text[:500]],
                )
            )
            scrutinized.append("supplemental")
        if scrutinized:
            logger.warning("Manuscript detection: %d non-standard doc(s) flagged with legal keywords", len(scrutinized))

        if validation_findings:
            logger.warning("Required-data validation: %d finding(s)", len(validation_findings))
            audit.log(
                PipelineEvent.STRUCTURED_PARSE_COMPLETE,
                f"Validation: {len(validation_findings)} finding(s)",
                metadata={
                    "validation_findings": [f.title for f in validation_findings],
                    "human_review_required": True,
                },
            )

        # ── 2.5. PROPERTY PHOTO ANALYSIS (vision LLM + satellite + damage detection) ──
        visual_profile = None
        photos = [d for d in documents if d.get("filename", "").lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp"))] if documents else []
        if photos:
            vision_route = self.zta_reporter.route(
                ZtaTask.VISION,
                RouteContext(photo_count=len(photos)),
            )
            progress.start("vision", "Vision", "Analyzing property photos")
            if vision_route.decision == RouteDecision.SKIP:
                progress.complete("vision", detail="Skipped (no deterministic substitute, zero-token mode)", status="warning")
            else:
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

        # ── 3. Extract (ZTA: deterministic regex first, LLM only when a doc genuinely needs it) ──
        for doc in bundle.unstructured:
            extract_route = self.zta_reporter.route(
                ZtaTask.EXTRACT_UNSTRUCTURED,
                RouteContext(
                    text=getattr(doc, "raw_text", None),
                    regex_field_count=len(getattr(doc, "extracted_fields", {}) or {}),
                    doc_type="inspection_report",
                ),
            )
            if extract_route.decision == RouteDecision.LLM and self.zta_config.enabled:
                self.extraction.enhance_unstructured(doc)
        if self.use_llm and getattr(self.extraction.llm, "api_key", None):
            bundle = self.extraction.process_bundle(bundle)
        bundle.status = SubmissionStatus.EXTRACTED

        # ── 4. EXTERNAL DATA ORACLES (CLUE, NCCI, CAT) — skip property oracles on life ──
        oracle_findings: list[Any] = []
        is_life_line = (resolved_line is not None and resolved_line.value == "life") or checklist_lob == "life"
        if funnel:
            progress.skip("verify", "Verified", "Deferred — available via Deep Dive")
        elif is_life_line:
            progress.start("verify", "Verified", "Life medical UW (P&C oracles skipped)")
            progress.complete("verify", detail="Life — medical underwriting path", findings=0)
        else:
            progress.start("verify", "Verified", "Running external oracle checks")
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
            provenance_failed = False
        except Exception as exc:
            logger.error("Provenance build failed: %s", exc)
            audit.log(
                PipelineEvent.VERIFICATION_COMPLETE,
                f"Provenance build failed: {exc}",
                metadata={"provenance_error": str(exc)},
            )
            from insureflow.models.provenance import ProvenanceRecord

            provenance = ProvenanceRecord(record_id=f"prov-{bid}", bundle_id=bid)
            provenance_failed = True

        try:
            reconciliation = self.reconciliation.reconcile(provenance)
            reconciliation_failed = False
        except Exception as exc:
            logger.error("Reconciliation failed: %s", exc)
            audit.log(
                PipelineEvent.RECONCILIATION_COMPLETE,
                f"Reconciliation failed: {exc}",
                metadata={"reconciliation_error": str(exc)},
            )
            from insureflow.models.audit import ReconciliationResult

            reconciliation = ReconciliationResult(bundle_id=bid)
            reconciliation_failed = True

        progress.complete(
            "reconcile",
            detail=f"{len(reconciliation.discrepancies)} conflict(s) · {reconciliation.match_rate:.0%} match",
            findings=len(reconciliation.discrepancies),
            status="warning" if reconciliation.discrepancies or provenance_failed or reconciliation_failed else "complete",
        )

        # ── 6. Agent swarm → UW memo (ZTA: LLM only when conflicts need reasoning) ──
        progress.start("analyze", "Scored", "Running specialist agent analysis")
        reconcile_route = self.zta_reporter.route(
            ZtaTask.RECONCILE,
            RouteContext(
                conflict_count=len(reconciliation.discrepancies),
                critical_conflict_count=sum(1 for d in reconciliation.discrepancies if getattr(d.severity, "value", str(d.severity)) == "critical"),
            ),
        )
        memo_route = self.zta_reporter.route(
            ZtaTask.MEMO,
            RouteContext(conflict_count=len(reconciliation.discrepancies)),
        )
        resolve_with_llm = reconcile_route.decision == RouteDecision.LLM or memo_route.decision == RouteDecision.LLM
        memo = self.supervisor.analyze_submission(
            bundle,
            parallel=True,
            use_celery=False,
            resolve_with_llm=resolve_with_llm,
            skip_ml_fraud=funnel,
        )

        if provenance_failed or reconciliation_failed:
            from insureflow.models.agents import Finding, RiskSeverity, UWDecision

            memo.key_findings.append(
                Finding(
                    title="Provenance/reconciliation pipeline failure",
                    description=("Provenance or reconciliation failed during processing. Decision forced to REFER — do not treat empty reconciliation as clean."),
                    severity=RiskSeverity.HIGH,
                    category="data_quality",
                )
            )
            memo.human_review_required = True
            memo.human_review_reasons.append("Provenance/reconciliation failure")
            if memo.decision != UWDecision.DECLINE:
                memo.decision = UWDecision.REFER

        # OCR failure signals from ingestion
        ocr_failures = [d for d in bundle.unstructured if d.extracted_fields.get("ocr_failed") or (isinstance(d.raw_text, str) and d.raw_text.startswith("[OCR: No text"))]
        if ocr_failures:
            from insureflow.models.agents import Finding, RiskSeverity, UWDecision

            memo.key_findings.append(
                Finding(
                    title="OCR extraction failed on required document(s)",
                    description=f"{len(ocr_failures)} document(s) produced no usable OCR text",
                    severity=RiskSeverity.HIGH,
                    category="data_quality",
                    evidence=[getattr(d, "submission_id", "") for d in ocr_failures[:5]],
                )
            )
            memo.human_review_required = True
            memo.human_review_reasons.append("OCR failure on required documents")
            if memo.decision not in (UWDecision.DECLINE, UWDecision.REFER):
                memo.decision = UWDecision.REFER

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

        # Merge required-data validation findings into memo — CRITICAL forces REFER
        if validation_findings:
            from insureflow.models.agents import UWDecision

            for f in validation_findings:
                memo.key_findings.append(f)
                memo.human_review_reasons.append(f.title)
            memo.human_review_required = True
            critical_validation = [f for f in validation_findings if getattr(f.severity, "value", "") == "critical"]
            if critical_validation and memo.decision not in (UWDecision.DECLINE, UWDecision.REFER):
                memo.decision = UWDecision.REFER
                memo.conditions = list(memo.conditions or []) + [f"SUBJECT TO resolution of: {f.title}" for f in critical_validation[:5]]

        # Carry appetite referral findings into the memo (they otherwise only live in audit)
        if appetite_result and appetite_result.findings:
            from insureflow.models.agents import UWDecision

            for f in appetite_result.findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)
            if appetite_result.needs_uw_referral:
                memo.human_review_required = True
                if memo.decision not in (UWDecision.DECLINE, UWDecision.REFER):
                    memo.decision = UWDecision.REFER
                memo.conditions = list(memo.conditions or []) + [f"SUBJECT TO appetite clearance: {appetite_result.reason}"]

        agent_findings = len(memo.key_findings) - len(oracle_findings) - len(validation_findings)
        progress.complete(
            "analyze",
            detail=f"Risk {memo.overall_risk_score:.0%}" if memo.overall_risk_score else f"{agent_findings} agent finding(s)",
            findings=max(agent_findings, 0),
            status="warning" if memo.human_review_required else "complete",
        )

        # Drop P&C-only findings on life so the memo/report stay coherent
        if is_life_line:
            from insureflow.underwriting.memo_sync import dedupe_findings, resync_memo_narrative

            def _property_only(f: Any) -> bool:
                blob = f"{getattr(f, 'title', '')} {getattr(f, 'description', '')}".lower()
                markers = (
                    "schedule of values",
                    "acord application",
                    "protection class",
                    "roof age",
                    "year built",
                    "reinsurance treaty",
                    "tiv $",
                    "ncci",
                    "experience mod",
                    "catastrophe",
                    "wildfire",
                    "flood zone",
                    "locations, coverages",
                    "risk profile, locations",
                    "named insured, risk profile, locations",
                    "clue report",
                    "property photos",
                    "iso protection",
                    "hail-prone",
                    "building occupancy",
                )
                return any(m in blob for m in markers)

            memo.key_findings = dedupe_findings([f for f in memo.key_findings if not _property_only(f)])
            memo.compliance_findings = [f for f in (memo.compliance_findings or []) if not _property_only(f)]
            memo.risk_analyst_findings = [f for f in (memo.risk_analyst_findings or []) if not _property_only(f)]
            resync_memo_narrative(memo)

        # ── 7. PORTFOLIO CONCENTRATION RISK ──
        portfolio_result = None
        selection_result = None
        producer_result = None
        adverse_result = None
        if funnel:
            progress.skip("portfolio", "Portfolio", "Deferred — available via Deep Dive")
        elif is_life_line:
            progress.skip("portfolio", "Portfolio", "Not applicable for life")
        elif not skip_portfolio:
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

            selection_result = self.selection_standards.run(
                bundle,
                org_id=self.org_id,
                candidate_risk_score=memo.overall_risk_score,
            )
            for f in selection_result.findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)
                    memo.human_review_required = True
            audit.log(
                PipelineEvent.SYNTHESIS_COMPLETE,
                f"Selection standards: {len(selection_result.findings)} findings",
                metadata={"selection_score": selection_result.risk_score},
            )

            producer_result = self.producer_experience.run(bundle, org_id=self.org_id)
            for f in producer_result.findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)
                    memo.human_review_required = True
            audit.log(
                PipelineEvent.SYNTHESIS_COMPLETE,
                f"Producer experience: {len(producer_result.findings)} findings",
                metadata={"producer_score": producer_result.risk_score},
            )

            adverse_result = self.adverse_selection.run(bundle, org_id=self.org_id)
            for f in adverse_result.findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)
                    memo.human_review_required = True
            audit.log(
                PipelineEvent.SYNTHESIS_COMPLETE,
                f"Adverse selection: {len(adverse_result.findings)} findings",
                metadata={"adverse_selection_score": adverse_result.risk_score},
            )

            # Substandard candidates admitted by the selection gate carry a rate
            # loading into pricing (the "higher premium rate" for substandard risks).
            sel_rec = selection_result.recommendation
            if sel_rec and sel_rec.suggested_premium_modification:
                if memo.recommendation is None:
                    memo.recommendation = Recommendation(
                        action=sel_rec.action,
                        rationale=sel_rec.rationale,
                        conditions=sel_rec.conditions,
                        suggested_premium_modification=sel_rec.suggested_premium_modification,
                    )
                else:
                    memo.recommendation.suggested_premium_modification = (memo.recommendation.suggested_premium_modification or 0.0) + sel_rec.suggested_premium_modification
                memo.conditions = list(memo.conditions or []) + [f"SUBJECT TO substandard loading: {sel_rec.suggested_premium_modification:.0f}%"]

        # ── 8. REINSURANCE TREATY ANALYSIS ──
        reinsurance_result = None
        if funnel:
            progress.skip("reinsurance", "Reinsurance", "Deferred — available via Deep Dive")
        elif is_life_line:
            progress.skip("reinsurance", "Reinsurance", "Not applicable for life")
        elif not skip_reinsurance:
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
        from insureflow.rating.models import InsuranceLine
        from insureflow.underwriting.personal_lines import detect_insurance_line, parse_insurance_line

        line_for_quote = parse_insurance_line(insurance_line) or resolved_line
        if line_for_quote is None:
            doc_blob = " ".join((getattr(d, "filename", "") or "") + " " + (getattr(d, "raw_text", "") or "")[:3000] for d in (bundle.unstructured or []))
            line_for_quote = detect_insurance_line(doc_blob, insurance_line or "")
        if not isinstance(line_for_quote, InsuranceLine):
            line_for_quote = InsuranceLine.COMMERCIAL_PROPERTY
        quote = self.rating.quote(bundle, memo, line=line_for_quote)
        # Apply life medical / personal filing decision hints onto the memo
        if line_for_quote == InsuranceLine.LIFE:
            from insureflow.underwriting.life_medical import underwrite_life
            from insureflow.underwriting.memo_sync import resync_memo_narrative, worst_decision

            medical = underwrite_life(bundle)
            for f in medical.findings:
                memo.key_findings.append(f)
            # Never let medical ACCEPT override agent critical/decline — take worst of both.
            agent_decision = memo.decision
            memo.decision = worst_decision(agent_decision, medical.decision)
            if medical.decision != memo.decision and medical.reasons:
                memo.human_review_reasons.extend([f"Life medical suggested {medical.decision.value}: {r}" for r in medical.reasons])
            memo.human_review_reasons.extend(medical.reasons)
            memo.conditions.extend((quote.metadata or {}).get("conditions") or [])
            resync_memo_narrative(
                memo,
                extra_summary=f"Life class={medical.underwriting_class}; tobacco={medical.tobacco}.",
            )
        elif line_for_quote in (InsuranceLine.PERSONAL_HOMEOWNERS, InsuranceLine.PERSONAL_AUTO):
            from insureflow.underwriting.memo_sync import resync_memo_narrative

            for flag in (quote.metadata or {}).get("referral_flags") or []:
                memo.human_review_reasons.append(str(flag))
                memo.human_review_required = True
            if quote.eligible is False:
                from insureflow.models.agents import UWDecision

                memo.decision = UWDecision.DECLINE
                memo.human_review_required = True
                memo.human_review_reasons.extend(quote.ineligibility_reasons or [])
                resync_memo_narrative(memo)
        else:
            from insureflow.underwriting.memo_sync import dedupe_findings

            memo.key_findings = dedupe_findings(list(memo.key_findings or []))

        progress.complete(
            "price",
            detail=f"{line_for_quote.value} · Indicated ${quote.adjusted_premium:,.0f}",
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
        # Skip provisional core push for referrals/declines — avoid fake "submitted" status.
        core_results: list[dict[str, Any]] = []
        from insureflow.decisions import DecisionOutcome, normalize_decision, skips_core_push

        skip_core_for_decision = skips_core_push(memo.decision)
        appetite_referral = bool(appetite_result and appetite_result.needs_uw_referral and not appetite_passed)
        if not skip_core_integration and not skip_core_for_decision and not appetite_referral:
            core_results = self.policy_admin.submit_to_core_systems(bundle, memo, quote, self.org_id)
            successful = [r for r in core_results if r.get("success")]
            audit.log(
                PipelineEvent.PIPELINE_COMPLETE,
                f"Core system integration: {len(successful)}/{len(core_results)} systems updated",
                metadata={"core_results": core_results},
            )
        elif skip_core_for_decision or appetite_referral:
            audit.log(
                PipelineEvent.PIPELINE_COMPLETE,
                "Core system integration skipped (referral/decline — provisional only)",
                metadata={"ai_decision": memo.decision.value, "appetite_referral": appetite_referral},
            )

        # ── 11. Feedback loop: record prediction ──
        prediction = self.feedback.record_prediction(bid, memo, quote, org_id=self.org_id)

        # Portfolio is recorded only after successful bind (see bind_policy API), not at quote time.

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
        primary_state = ""
        estimated_tiv = 0.0
        if bundle.structured and bundle.structured.broker:
            broker_name = bundle.structured.broker.broker_name
        if bundle.structured and bundle.structured.locations:
            loc0 = bundle.structured.locations[0]
            primary_state = loc0.state or ""
            estimated_tiv = (loc0.building_value or 0) + (loc0.contents_value or 0) + (loc0.bi_value or 0)
        if estimated_tiv <= 0:
            estimated_tiv = float(getattr(quote, "tiv", 0) or 0) or float((getattr(quote, "metadata", {}) or {}).get("tiv") or 0)

        human_checkpoints = self._build_checkpoints(memo, reconciliation, oracle_findings)
        open_conditions = list(memo.conditions or [])

        # ZTA routing records for the deterministic scoring/pricing/decision stages
        self.zta_reporter.route(
            ZtaTask.SCORE,
            RouteContext(
                required_features_present=not missing_docs,
                missing_required=list(missing_docs)[:5],
            ),
        )
        self.zta_reporter.route(ZtaTask.PRICE, RouteContext(required_features_present=True))
        self.zta_reporter.route(
            ZtaTask.DECIDE,
            RouteContext(
                required_features_present=not memo.human_review_required,
                missing_required=memo.human_review_reasons[:5],
            ),
        )
        zta_report = self.zta_reporter.report()
        if normalize_decision(memo.decision) == DecisionOutcome.CONDITIONAL_ACCEPT and open_conditions:
            human_checkpoints.append(
                {
                    "id": "subjectivities",
                    "label": "Clear subjectivities",
                    "status": "pending",
                    "reason": "; ".join(open_conditions[:3]),
                }
            )

        summary = {
            "status": "completed",
            "bundle_id": bid,
            "org_id": self.org_id,
            "insured_name": memo.insured_name,
            "broker_name": broker_name,
            "primary_state": primary_state,
            "tiv": estimated_tiv,
            "triage_priority": triage_result.priority.value,
            "triage_score": triage_result.score,
            "ai_decision": memo.decision.value,
            "outcome": normalize_decision(memo.decision).value,
            "workflow_state": wf.state.value,
            "insurance_line": line_for_quote.value,
            "product_line": line_for_quote.value,
            "human_review_required": memo.human_review_required or wf.state == WorkflowState.PENDING_REVIEW,
            "funnel": funnel,
            "deep_dive_available": (
                [s for s in deferred_stages if s not in ("oracles", "portfolio", "selection_standards", "producer_experience", "adverse_selection", "reinsurance")]
                if is_life_line
                else list(deferred_stages)
            ),
            "appetite_filter_passed": appetite_passed,
            "appetite_needs_uw_referral": appetite_result.needs_uw_referral if appetite_result else False,
            "appetite_reason": appetite_result.reason if appetite_result else "",
            "oracle_findings_count": len(oracle_findings),
            "ocr_documents": ocr_count,
            "document_count": len(bundle.unstructured) + (1 if bundle.structured else 0),
            "document_checklist": triage_result.document_checklist.to_summary_dict(),
            "reconciliation_discrepancies": len(reconciliation.discrepancies),
            "pipeline_stages": progress.stages,
            "provenance_summary": {
                "total_fields": provenance.record_count(),
                "verified_fields": provenance.verified_count(),
                "contradicted_fields": provenance.discrepancy_count(),
            },
            "human_checkpoints": human_checkpoints,
            "open_conditions": open_conditions,
            "quote": {
                "adjusted_premium": quote.adjusted_premium,
                "base_premium": quote.base_premium,
                "eligible": quote.eligible,
                "policy_admin_reference": quote.policy_admin_reference,
                "quote_valid_until": quote.quote_valid_until,
                "tiv": estimated_tiv,
                "ineligibility_reasons": list(getattr(quote, "ineligibility_reasons", []) or []),
                "filing_id": (quote.metadata or {}).get("filing_id"),
                "rating_engine": (quote.metadata or {}).get("rating_engine"),
                "serff_tracking": (quote.metadata or {}).get("serff_tracking"),
                "insurance_line": line_for_quote.value,
                "medical": (quote.metadata or {}).get("medical"),
                "components": [
                    {
                        "name": c.name,
                        "amount": c.amount,
                        "basis": c.basis,
                        "modifier_pct": c.modifier_pct,
                    }
                    for c in (quote.schedule_modifications or [])
                ],
            },
            "core_integration": core_results,
            "encryption_at_rest": self.encryption.enabled,
            "prediction_id": prediction.prediction_id,
            "zta_mode": self.zta_config.mode,
            "zta_report": zta_report,
        }

        # Add portfolio concentration data if available
        if portfolio_result:
            summary["portfolio_concentration_score"] = portfolio_result.risk_score
            portfolio_findings = [f.model_dump() for f in portfolio_result.findings]
            summary["portfolio_findings"] = portfolio_findings

        # Add selection standards / book-balance data if available
        if selection_result:
            summary["selection_standards"] = selection_result.model_dump()
            sel_rec = selection_result.recommendation
            if sel_rec and sel_rec.suggested_premium_modification:
                summary["selection_loading_pct"] = sel_rec.suggested_premium_modification
            exp = self.selection_standards.last_experience
            if exp is not None:
                summary["selection_experience"] = exp.model_dump()

        # Add producer experience / distribution quality data if available
        if producer_result:
            summary["producer_experience"] = producer_result.model_dump()

        # Add adverse-selection screen data if available
        if adverse_result:
            summary["adverse_selection"] = adverse_result.model_dump()

        # Add visual analysis data if available
        if visual_profile:
            summary["visual_analysis"] = visual_profile.to_dict()

        registry = RegistryService()
        version_context = registry.version_context()
        summary["version_context"] = version_context

        doc_analytics = DocumentAnalyticsEngine()
        doc_analytics.record(
            bundle_id=bid,
            document_count=len(bundle.unstructured) + (1 if bundle.structured else 0),
            vertical="insurance",
            structured_count=1 if bundle.structured else 0,
            unstructured_count=len(bundle.unstructured),
            human_review_required=bool(memo.human_review_required or wf.state == WorkflowState.PENDING_REVIEW),
            decision=str(memo.decision.value if hasattr(memo.decision, "value") else memo.decision),
            org_id=self.org_id,
        )

        audit_paths = audit.persist(bundle, memo, provenance, reconciliation, extra=summary)
        try:
            audit.store.save_json(bid, "checkpoints.json", human_checkpoints, org_id=self.org_id)
        except Exception as exc:
            logger.warning("Failed to persist checkpoints.json: %s", exc)

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

    def deep_dive(
        self,
        bundle_id: str,
        *,
        org_id: str | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """Re-run the analyses deferred by funnel mode on a persisted submission.

        Nothing is lost by the funnel — oracles, portfolio concentration,
        selection standards, producer experience, adverse selection,
        reinsurance treaty fit, and the ML fraud/premium/churn models are all
        available here on demand.
        """
        allowed = ["oracles", "portfolio", "selection_standards", "producer_experience", "adverse_selection", "reinsurance", "fraud_ml", "premium_ml", "churn_ml"]
        include = [i for i in (include or allowed) if i in allowed]
        scope = org_id or self.org_id

        bundle_data = self.audit_store.load_json(bundle_id, "submission_bundle.json", org_id=scope)
        if not bundle_data:
            raise KeyError(f"No persisted submission found for bundle {bundle_id!r} (org={scope})")

        bundle = SubmissionBundle(**bundle_data)
        results: dict[str, Any] = {"bundle_id": bundle_id, "completed": [], "findings": {}}

        if "oracles" in include:
            oracle_result = self.oracle_agent.run(bundle, org_id=scope)
            results["completed"].append("oracles")
            results["findings"]["oracles"] = [f.model_dump() for f in oracle_result.findings]

        if "portfolio" in include:
            portfolio_result = self.portfolio_risk.run(bundle, org_id=scope)
            results["completed"].append("portfolio")
            results["findings"]["portfolio"] = {
                "risk_score": portfolio_result.risk_score,
                "findings": [f.model_dump() for f in portfolio_result.findings],
            }

        if "selection_standards" in include:
            selection_result = self.selection_standards.run(bundle, org_id=scope)
            results["completed"].append("selection_standards")
            results["findings"]["selection_standards"] = selection_result.model_dump()

        if "producer_experience" in include:
            producer_result = self.producer_experience.run(bundle, org_id=scope)
            results["completed"].append("producer_experience")
            results["findings"]["producer_experience"] = producer_result.model_dump()

        if "adverse_selection" in include:
            adverse_result = self.adverse_selection.run(bundle, org_id=scope)
            results["completed"].append("adverse_selection")
            results["findings"]["adverse_selection"] = adverse_result.model_dump()

        if "reinsurance" in include:
            reinsurance_result = self.reinsurance.run(bundle, org_id=scope)
            results["completed"].append("reinsurance")
            results["findings"]["reinsurance"] = {
                "risk_score": reinsurance_result.risk_score,
                "findings": [f.model_dump() for f in reinsurance_result.findings],
            }

        ml_inputs = self._deep_dive_ml_inputs(bundle)
        for ml_name in ("fraud_ml", "premium_ml", "churn_ml"):
            if ml_name not in include:
                continue
            results["completed"].append(ml_name)
            results["findings"][ml_name] = self._run_ml_deep_dive(ml_name, ml_inputs)

        return results

    def _deep_dive_ml_inputs(self, bundle: SubmissionBundle) -> dict[str, float]:
        """Derive ML model inputs from a persisted submission bundle."""
        tiv = 0.0
        prior_claims = 0
        revenue = 0.0
        loss_ratio = 0.5
        credit_score = 0.0
        requested_premium = 0.0
        year_built = 0
        square_footage = 0.0
        if bundle.structured:
            for loc in bundle.structured.locations or []:
                tiv += (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)
                if not year_built and loc.year_built:
                    year_built = int(loc.year_built)
                if not square_footage and loc.square_footage:
                    square_footage = float(loc.square_footage)
            requested_premium = sum(c.premium or 0 for c in (bundle.structured.coverages or []))
            if bundle.structured.risk_profile:
                prior_claims = len(bundle.structured.risk_profile.prior_claims)
                credit_score = float(getattr(bundle.structured.risk_profile, "credit_score", 0) or 0)
            fin = bundle.structured.financial
            if fin is not None:
                revenue = float(fin.annual_revenue or 0.0)
                if fin.loss_run and fin.loss_run.claims:
                    incurred = sum(c.incurred_amount or 0 for c in fin.loss_run.claims)
                    if tiv > 0:
                        loss_ratio = min(incurred / tiv, 3.0)
                credit_score = float(getattr(fin, "credit_score", 0) or credit_score or 0)
            if credit_score <= 0 and bundle.structured.risk_profile is not None:
                credit_score = float(getattr(bundle.structured.risk_profile, "credit_score", 0) or 0)
        return {
            "tiv": float(tiv),
            "loss_ratio": float(loss_ratio),
            "credit_score": float(credit_score) if credit_score > 0 else 0.0,
            "prior_claims_count": float(prior_claims),
            "revenue": float(revenue),
            "requested_premium": float(requested_premium),
            "year_built": float(year_built),
            "square_footage": float(square_footage),
        }

    def _run_ml_deep_dive(self, ml_name: str, inputs: dict[str, float]) -> dict[str, Any]:
        """Run a single ML model on bundle-derived inputs (never raises)."""
        from insureflow.agents.tools import MLTools

        try:
            if ml_name == "fraud_ml":
                return MLTools.predict_fraud(
                    tiv=inputs["tiv"],
                    loss_ratio=inputs["loss_ratio"],
                    credit_score=inputs["credit_score"],
                    prior_claims_count=int(inputs["prior_claims_count"]),
                    requested_premium=inputs.get("requested_premium", 0.0),
                    year_built=int(inputs.get("year_built", 0)),
                    square_footage=inputs.get("square_footage", 0.0),
                )
            if ml_name == "premium_ml":
                return MLTools.predict_premium(
                    tiv=inputs["tiv"],
                    loss_ratio=inputs["loss_ratio"],
                    credit_score=inputs["credit_score"],
                    prior_claims_count=int(inputs["prior_claims_count"]),
                )
            if ml_name == "churn_ml":
                return MLTools.predict_churn(
                    loss_ratio=inputs["loss_ratio"],
                    credit_score=inputs["credit_score"],
                    years_in_business=5.0,
                )
        except Exception as exc:
            logger.warning("Deep-dive ML %s failed: %s", ml_name, exc)
            return {"error": str(exc)}
        return {"error": f"Unknown ML deep-dive: {ml_name}"}

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
            checklist = (
                cl.to_summary_dict()
                if hasattr(cl, "to_summary_dict")
                else {
                    "completeness_pct": cl.completeness_pct,
                    "missing_documents": cl.missing,
                    "present_documents": [],
                }
            )
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
            "insurance_line": (checklist or {}).get("lob") if checklist else None,
            "product_line": (checklist or {}).get("lob") if checklist else None,
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
            producer = ""
            if bundle.structured:
                if bundle.structured.locations:
                    loc = bundle.structured.locations[0]
                    state = loc.state or ""
                    tiv = (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)
                    occupancy = loc.building_occupancy or ""
                if bundle.structured.risk_profile:
                    naics = bundle.structured.risk_profile.naics_code or ""
                if bundle.structured.broker:
                    producer = bundle.structured.broker.broker_name or ""

            policy = PortfolioPolicy(
                policy_id=f"pol-{uuid4().hex[:8]}",
                bundle_id=bundle.bundle_id,
                org_id=self.org_id,
                insured_name=memo.insured_name,
                producer_name=producer,
                naics_code=naics,
                state=state,
                tiv=tiv,
                premium=quote.adjusted_premium,
                risk_score=memo.overall_risk_score,
                occupancy_type=occupancy,
            )
            self.portfolio_store.add_policy(policy)
        except Exception as exc:
            logger.error("Portfolio recording failed: %s", exc)
