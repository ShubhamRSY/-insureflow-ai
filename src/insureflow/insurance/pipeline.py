from __future__ import annotations

import dataclasses
import logging
from typing import Any, Callable
from uuid import uuid4

from insureflow.agents.adverse_selection_agent import AdverseSelectionAgent
from insureflow.agents.appetite_filter import AppetiteFilterAgent
from insureflow.agents.extraction_agent import ExtractionAgent
from insureflow.agents.moral_hazard_agent import MoralHazardAgent
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
from insureflow.ingestion.insurance.validation import validate_extraction
from insureflow.ingestion.loader import SubmissionLoader
from insureflow.insurance.progress import PipelineProgressTracker
from insureflow.integrations.factory import build_policy_admin_service
from insureflow.models.agents import Recommendation
from insureflow.models.audit import PipelineEvent
from insureflow.models.submissions import SubmissionBundle, SubmissionStatus
from insureflow.oracles.factory import build_oracle_agent
from insureflow.outcomes.feedback import FeedbackEngine
from insureflow.portfolio.store import get_portfolio_store
from insureflow.provenance.hierarchy import ProvenanceEngine
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.reconciliation.engine import ReconciliationEngine
from insureflow.redaction.pipeline import RedactedLLMClient
from insureflow.registry.service import RegistryService
from insureflow.regulatory.state_rules import StateRegulatoryEngine
from insureflow.storage.encryption import EnvelopeEncryption
from insureflow.webhooks.dispatcher import webhook_dispatcher
from insureflow.workflow.models import WorkflowState
from insureflow.workflow.service import WorkflowService
from insureflow.zta.config import ZtaConfig
from insureflow.zta.models import RouteContext, RouteDecision, ZtaTask
from insureflow.zta.report import ZtaReporter
from insureflow.zta.router import ZeroTokenRouter

logger = logging.getLogger(__name__)


def _resolve_picker_scope(
    *,
    insurance_line: str | None = None,
    commercial_product_id: str | None = None,
    life_product_id: str | None = None,
    life_coverage_id: str | None = None,
    health_product_id: str | None = None,
    health_coverage_id: str | None = None,
    general_product_id: str | None = None,
    general_coverage_id: str | None = None,
    commercial_coverage_id: str | None = None,
    commercial_product_name: str | None = None,
    commercial_coverage_name: str | None = None,
    pre_blob: str = "",
) -> dict[str, Any]:
    """Honor the taxonomy picker: only the selected product + coverage runs."""
    from insureflow.insurance.commercial_lobs import get_commercial_line, get_line_coverage
    from insureflow.insurance.general_lobs import detect_general_product, get_general_coverage, resolve_general_checklist_lob
    from insureflow.insurance.health_lobs import detect_health_product, get_health_coverage, resolve_health_checklist_lob
    from insureflow.insurance.life_lobs import detect_life_product, get_life_coverage, resolve_life_checklist_lob
    from insureflow.rating.models import InsuranceLine
    from insureflow.underwriting.personal_lines import detect_insurance_line, parse_insurance_line

    selected_coverage_id = (general_coverage_id or health_coverage_id or life_coverage_id or commercial_coverage_id or "").strip() or None
    life_checklist_lob: str | None = None
    health_checklist_lob: str | None = None
    general_checklist_lob: str | None = None
    commercial_checklist_lob: str | None = None
    product_name = commercial_product_name
    coverage_name = commercial_coverage_name
    resolved_line = None

    general_from_coverage = bool(selected_coverage_id and resolve_general_checklist_lob(selected_coverage_id))
    if general_product_id or general_from_coverage:
        general_line, general_cov = get_general_coverage(general_product_id, selected_coverage_id)
        general_checklist_lob = (
            (str(general_line.get("checklist_lob") or "").strip() or None if general_line else None)
            or resolve_general_checklist_lob(general_product_id)
            or resolve_general_checklist_lob(selected_coverage_id)
        )
        if general_checklist_lob:
            resolved_line = InsuranceLine.GENERAL
            if general_line:
                product_name = product_name or str(general_line.get("name") or "") or None
            if general_cov:
                coverage_name = coverage_name or str(general_cov.get("name") or "") or None
                selected_coverage_id = str(general_cov.get("id") or selected_coverage_id)
    health_from_coverage = bool(selected_coverage_id and resolve_health_checklist_lob(selected_coverage_id))
    if resolved_line is None and (health_product_id or health_from_coverage):
        health_line, health_cov = get_health_coverage(health_product_id, selected_coverage_id)
        health_checklist_lob = (
            (str(health_line.get("checklist_lob") or "").strip() or None if health_line else None)
            or resolve_health_checklist_lob(health_product_id)
            or resolve_health_checklist_lob(selected_coverage_id)
        )
        if health_checklist_lob:
            resolved_line = InsuranceLine.HEALTH
            if health_line:
                product_name = product_name or str(health_line.get("name") or "") or None
            if health_cov:
                coverage_name = coverage_name or str(health_cov.get("name") or "") or None
                selected_coverage_id = str(health_cov.get("id") or selected_coverage_id)
    life_from_coverage = bool(selected_coverage_id and resolve_life_checklist_lob(selected_coverage_id))
    if resolved_line is None and (life_product_id or life_from_coverage):
        life_line, life_cov = get_life_coverage(life_product_id, selected_coverage_id)
        life_checklist_lob = (
            (str(life_line.get("checklist_lob") or "").strip() or None if life_line else None) or resolve_life_checklist_lob(life_product_id) or resolve_life_checklist_lob(selected_coverage_id)
        )
        if life_checklist_lob:
            resolved_line = InsuranceLine.LIFE
            if life_line:
                product_name = product_name or str(life_line.get("name") or "") or None
            if life_cov:
                coverage_name = coverage_name or str(life_cov.get("name") or "") or None
                selected_coverage_id = str(life_cov.get("id") or selected_coverage_id)
    if resolved_line is None and commercial_product_id:
        comm_line = get_commercial_line(commercial_product_id)
        if comm_line:
            commercial_checklist_lob = str(comm_line.get("checklist_lob") or "").strip() or None
            product_name = product_name or str(comm_line.get("name") or "") or None
            cov = get_line_coverage(comm_line, selected_coverage_id)
            if cov:
                coverage_name = coverage_name or str(cov.get("name") or "") or None
                selected_coverage_id = str(cov.get("id") or selected_coverage_id)
            for key in (comm_line.get("rating_line"), comm_line.get("insurance_line"), commercial_checklist_lob):
                parsed = parse_insurance_line(str(key or ""))
                if parsed is not None:
                    resolved_line = parsed
                    break

    if resolved_line is None:
        resolved_line = detect_insurance_line(pre_blob, insurance_line or "")
        if resolved_line is not None and resolved_line.value == "general":
            general_checklist_lob = resolve_general_checklist_lob(general_product_id) or detect_general_product(pre_blob)
        elif resolved_line is not None and resolved_line.value == "health":
            health_checklist_lob = resolve_health_checklist_lob(health_product_id) or detect_health_product(pre_blob)
        elif resolved_line is not None and resolved_line.value == "life":
            life_checklist_lob = resolve_life_checklist_lob(life_product_id) or detect_life_product(pre_blob)

    return {
        "resolved_line": resolved_line,
        "life_checklist_lob": life_checklist_lob,
        "health_checklist_lob": health_checklist_lob,
        "general_checklist_lob": general_checklist_lob,
        "commercial_checklist_lob": commercial_checklist_lob,
        "checklist_hint": general_checklist_lob or health_checklist_lob or life_checklist_lob or commercial_checklist_lob,
        "selected_coverage_id": selected_coverage_id,
        "product_name": product_name,
        "coverage_name": coverage_name,
    }


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
        self.extraction = ExtractionAgent(RedactedLLMClient(model_tier="cheap") if use_llm else None)
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
        self.moral_hazard = MoralHazardAgent()
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
        commercial_product_id: str | None = None,
        life_product_id: str | None = None,
        life_coverage_id: str | None = None,
        health_product_id: str | None = None,
        health_coverage_id: str | None = None,
        general_product_id: str | None = None,
        general_coverage_id: str | None = None,
        commercial_coverage_id: str | None = None,
        commercial_product_name: str | None = None,
        commercial_coverage_name: str | None = None,
        commercial_category_id: str | None = None,
        insurance_company_id: str | None = None,
        insurance_company_name: str | None = None,
        skip_appetite_filter: bool = False,
        skip_oracles: bool = False,
        skip_portfolio: bool = False,
        skip_reinsurance: bool = False,
        skip_core_integration: bool = False,
        funnel: bool = False,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        bid = bundle_id or f"ins-{uuid4().hex[:12]}"
        from insureflow.insurance.companies import resolve_company

        company = resolve_company(
            company_id=insurance_company_id or "",
            company_name=insurance_company_name or "",
            org_id=self.org_id,
        )
        insurance_company_id = company.get("id") or None
        insurance_company_name = company.get("name") or None
        audit = InsuranceAuditLogger(self.audit_store, self.encryption, org_id=self.org_id)
        audit.start(bid)
        progress = PipelineProgressTracker(on_update=progress_callback)
        try:
            from insureflow.analytics.metrics import get_pipeline_metrics

            get_pipeline_metrics().cycle_time.start_pipeline(bid, org_id=self.org_id)
        except Exception:
            pass

        # Deferred stages in funnel mode are re-run on demand via deep_dive().
        deferred_stages: list[str] = []
        pending_oracle_failures: list[Any] = []
        if funnel:
            deferred_stages = ["oracles", "portfolio", "selection_standards", "producer_experience", "adverse_selection", "moral_hazard", "reinsurance", "fraud_ml"]

        # ── 1. SUBMISSION TRIAGE (score & prioritize before any processing) ──
        progress.start("intake", "Intake", "Receiving submission package")
        progress.complete("intake", detail="Submission received")
        progress.start("triage", "Triage", "Scoring submission priority")

        # Explicit taxonomy picker (product + coverage) wins. Without a picker,
        # infer from the full package so a wrong UI hint cannot short-circuit.
        pre_blob = " ".join(
            [
                acord_xml or "",
                json_payload or "",
                loss_run or "",
                schedule_of_values or "",
                " ".join(supplemental_docs or []),
                " ".join(inspection_reports or []),
                " ".join(d.get("filename", "") + " " + d.get("content", "")[:2000] for d in (documents or [])),
            ]
        )
        scope = _resolve_picker_scope(
            insurance_line=insurance_line,
            commercial_product_id=commercial_product_id,
            life_product_id=life_product_id,
            life_coverage_id=life_coverage_id,
            health_product_id=health_product_id,
            health_coverage_id=health_coverage_id,
            general_product_id=general_product_id,
            general_coverage_id=general_coverage_id,
            commercial_coverage_id=commercial_coverage_id,
            commercial_product_name=commercial_product_name,
            commercial_coverage_name=commercial_coverage_name,
            pre_blob=pre_blob,
        )
        resolved_line = scope["resolved_line"]
        life_checklist_lob = scope["life_checklist_lob"]
        health_checklist_lob = scope["health_checklist_lob"]
        general_checklist_lob = scope["general_checklist_lob"]
        checklist_hint = scope["checklist_hint"]
        selected_coverage_id = scope["selected_coverage_id"]
        commercial_product_name = scope["product_name"] or commercial_product_name
        commercial_coverage_name = scope["coverage_name"] or commercial_coverage_name
        commercial_coverage_id = selected_coverage_id or commercial_coverage_id

        triage_result = self.triage.score_submission(
            self._build_preliminary_bundle(
                acord_xml=acord_xml,
                json_payload=json_payload,
                loss_run=loss_run,
                bundle_id=bid,
            ),
            insurance_line=resolved_line.value if resolved_line else insurance_line,
            checklist_lob_hint=checklist_hint,
            coverage_id=selected_coverage_id,
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
                    try:
                        from insureflow.analytics.business_kpis import get_business_kpi_service
                        from insureflow.analytics.metrics import get_pipeline_metrics

                        cycle_rec = get_pipeline_metrics().cycle_time.finish_pipeline(bid, status="completed")
                        get_business_kpi_service().record_pipeline_result(
                            bundle_id=bid,
                            decision="decline",
                            org_id=self.org_id,
                            human_review_required=False,
                            cycle_ms=cycle_rec.total_ms if cycle_rec else None,
                            source="pipeline",
                        )
                    except Exception:
                        pass
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

        # ── 2a. DOCUMENT QUALITY GATE (block STP on poor-quality docs) ──
        doc_quality_result: dict[str, Any] = {}
        try:
            from insureflow.ingestion.quality_gate import DocQualityGate

            quality_gate = DocQualityGate()
            doc_quality_result = quality_gate.evaluate(documents or [])

            if doc_quality_result["decision"] == "block":
                logger.warning(
                    "Document quality gate BLOCKED: %d issue(s), score=%.2f",
                    len(doc_quality_result["issues"]),
                    doc_quality_result["score"],
                )
                audit.log(
                    PipelineEvent.STRUCTURED_PARSE_COMPLETE,
                    f"Doc quality gate: BLOCKED — {len(doc_quality_result['resubmit_required'])} doc(s) need resubmission",
                    metadata={
                        "doc_quality_decision": "block",
                        "doc_quality_score": doc_quality_result["score"],
                        "resubmit_required": doc_quality_result["resubmit_required"],
                    },
                )
            elif doc_quality_result["decision"] == "warn":
                logger.info(
                    "Document quality gate WARN: score=%.2f, %d issue(s)",
                    doc_quality_result["score"],
                    len(doc_quality_result["issues"]),
                )
                audit.log(
                    PipelineEvent.STRUCTURED_PARSE_COMPLETE,
                    f"Doc quality gate: WARN — score {doc_quality_result['score']:.2f}",
                    metadata={
                        "doc_quality_decision": "warn",
                        "doc_quality_score": doc_quality_result["score"],
                    },
                )
            else:
                logger.debug(
                    "Document quality gate PASSED: score=%.2f",
                    doc_quality_result["score"],
                )

        except Exception as exc:
            logger.warning("Document quality gate failed (non-blocking): %s", exc)
            doc_quality_result = {"decision": "error", "error": str(exc)}

        # ── 2b. RE-SCORE DOCUMENT CHECKLIST on fully-ingested bundle ──
        line_hint = resolved_line.value if resolved_line else insurance_line
        triage_result = self.triage.score_submission(
            bundle,
            insurance_line=line_hint,
            checklist_lob_hint=checklist_hint,
            coverage_id=selected_coverage_id,
        )
        checklist_lob = triage_result.document_checklist.lob

        # ── 2c. REQUIRED DATA VALIDATION (LOB-aware hard gates) ──
        validation_findings: list[Any] = []
        from insureflow.agents.triage_agent import REQUIRED_CRITICAL_BY_LOB
        from insureflow.models.agents import Finding, RiskSeverity

        missing_docs = set(triage_result.document_checklist.missing)
        required_labels = REQUIRED_CRITICAL_BY_LOB.get(checklist_lob, REQUIRED_CRITICAL_BY_LOB["property"])
        for label in required_labels:
            # Exact match, or catalog label that starts with / contains the required token
            matched_missing = label in missing_docs or any(m == label or m.startswith(label) or label in m for m in missing_docs)
            if matched_missing:
                validation_findings.append(
                    Finding(
                        title=f"Missing required document: {label}",
                        description=(f"{label} was not provided or could not be parsed. Cannot complete {checklist_lob} underwriting without it."),
                        severity=RiskSeverity.CRITICAL,
                        category="data_quality",
                        field_path=label.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace("–", "-"),
                    )
                )

        if checklist_lob == "property":
            loss_run_raw = loss_run or ""
            loss_run_expected = any("loss" in m.lower() for m in triage_result.document_checklist.present)
            if bundle.structured:
                fin = bundle.structured.financial
                has_claims = bool(fin and fin.loss_run and len(fin.loss_run.claims) > 0)
                has_ratios = bool(fin and fin.loss_run and fin.loss_run.loss_ratios)
                # Ratio tables without claim rows are usable history — only hard-fail when
                # nothing structured was extracted from an expected/attached loss run.
                if not has_claims and not has_ratios and (loss_run_raw.strip() or loss_run_expected):
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

        # ── 2d2. IRRELEVANT FILE FLAGS ──
        from insureflow.insurance.relevance import score_document_relevance

        irrelevant_hits = 0
        for doc in bundle.unstructured or []:
            dtype = str(getattr(doc, "document_type", "") or "").lower()
            if dtype == "irrelevant":
                irrelevant_hits += 1
                validation_findings.append(
                    Finding(
                        title=f"Irrelevant document: {getattr(doc, 'filename', None) or doc.submission_id}",
                        description="File does not look related to this underwriting package and should be removed or replaced.",
                        severity=RiskSeverity.HIGH,
                        category="data_quality",
                        field_path="irrelevant_document",
                    )
                )
                continue
            # Catch supplemental junk that slipped through with a generic type
            scored = score_document_relevance(
                filename=str(getattr(doc, "filename", "") or doc.submission_id or "document"),
                content=str(getattr(doc, "raw_text", "") or "")[:6000],
                encoding="utf-8",
            )
            if not scored.relevant and dtype in {"supplemental", "irrelevant", ""}:
                irrelevant_hits += 1
                validation_findings.append(
                    Finding(
                        title=f"Possibly irrelevant document: {scored.filename}",
                        description=scored.reason,
                        severity=RiskSeverity.MODERATE,
                        category="data_quality",
                        field_path="irrelevant_document",
                    )
                )
        if irrelevant_hits and irrelevant_hits >= max(1, len(bundle.unstructured or [])):
            validation_findings.append(
                Finding(
                    title="Package appears to contain only irrelevant files",
                    description="No underwriting-relevant documents were identified. Add ACORD, loss runs, SOV, or other package docs.",
                    severity=RiskSeverity.CRITICAL,
                    category="data_quality",
                    field_path="package_relevance",
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
                    bundle.visual_analysis = visual_profile.to_dict()
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
                    doc_type=getattr(doc, "document_type", "inspection_report"),
                ),
            )
            if extract_route.decision == RouteDecision.LLM and self.zta_config.enabled:
                self.extraction.enhance_unstructured(doc)
        if self.use_llm and getattr(self.extraction.llm, "api_key", None):
            bundle = self.extraction.process_bundle(bundle)
        extraction_issues = validate_extraction(bundle)
        bundle.status = SubmissionStatus.EXTRACTED

        # ── 3a. LAYERED EXTRACTION VERIFICATION (deterministic + agentic) ──
        verification_meta: dict[str, Any] = {}
        try:
            from insureflow.verification.aggregate import aggregate_verification, flagged_submissions

            verification_meta = aggregate_verification(bundle)
            if verification_meta["checked_docs"]:
                flagged = verification_meta["flagged_doc_count"]
                audit.log(
                    PipelineEvent.VERIFICATION_COMPLETE,
                    f"Extraction verification: {verification_meta['checked_docs']} doc(s) checked, "
                    f"{flagged} flagged · {verification_meta['error_count']} error(s) · "
                    f"{verification_meta['warning_count']} warning(s)",
                    metadata={
                        "flagged_doc_count": flagged,
                        "error_count": verification_meta["error_count"],
                        "warning_count": verification_meta["warning_count"],
                        "exception_count": verification_meta["exception_count"],
                        "issues_by_code": verification_meta["issues_by_code"],
                        "straight_through_processing": verification_meta["straight_through_processing"],
                    },
                )
                try:
                    audit.store.save_json(bid, "verification.json", verification_meta, org_id=self.org_id)
                except Exception as exc:
                    logger.debug("verification.json persist failed: %s", exc)
                if flagged:
                    progress.complete(
                        "extraction",
                        detail=f"{len(flagged_submissions(bundle))} doc(s) flagged for review",
                        status="warning",
                    )
        except Exception as exc:
            logger.warning("extraction verification aggregation failed: %s", exc)

        # ── 4. EXTERNAL DATA ORACLES (CLUE, NCCI, CAT / life MIB+Rx) + OFAC ──
        oracle_findings: list[Any] = []
        ofac_meta: dict[str, Any] = {}
        is_life_line = (resolved_line is not None and resolved_line.value == "life") or checklist_lob == "life" or life_checklist_lob is not None
        is_health_line = (resolved_line is not None and resolved_line.value == "health") or checklist_lob == "health" or health_checklist_lob is not None
        is_general_line = (resolved_line is not None and resolved_line.value == "general") or checklist_lob == "general" or general_checklist_lob is not None
        if funnel:
            progress.skip("verify", "Verified", "Deferred — available via Deep Dive")
        elif is_general_line:
            progress.start("verify", "Verified", "General / non-life — OFAC / sanctions")
            from insureflow.underwriting.sanctions_gate import screen_submission

            ofac_result = screen_submission(bundle)
            ofac_meta = ofac_result.to_metadata()
            progress.complete("verify", detail="OFAC complete")
        elif is_health_line:
            progress.start("verify", "Verified", "Health — OFAC / sanctions")
            from insureflow.underwriting.sanctions_gate import screen_submission

            ofac_result = screen_submission(bundle)
            ofac_meta = ofac_result.to_metadata()
            progress.complete("verify", detail="OFAC complete")
        elif is_life_line:
            progress.start("verify", "Verified", "Life bureaus — MIB / Rx / OFAC")
            from insureflow.underwriting.mib import persist_mib_report, request_mib_report
            from insureflow.underwriting.rx_history import screen_rx
            from insureflow.underwriting.sanctions_gate import screen_submission

            mib_report = request_mib_report(bundle)
            persist_mib_report(mib_report, org_id=self.org_id)
            rx_result = screen_rx(bundle)
            ofac_result = screen_submission(bundle)
            ofac_meta = ofac_result.to_metadata()
            from insureflow.models.agents import Finding, RiskSeverity

            if mib_report.no_hit and mib_report.discrepancies:
                oracle_findings.append(
                    Finding(
                        title="MIB not run",
                        description=mib_report.discrepancies[0].reason or "MIB authorization is not a bureau hit.",
                        severity=RiskSeverity.CRITICAL,
                        category="mib",
                    )
                )
            elif mib_report.discrepancies:
                for d in mib_report.discrepancies:
                    oracle_findings.append(
                        Finding(
                            title=f"MIB discrepancy: {d.description}",
                            description=d.reason,
                            severity=d.severity,
                            category="mib",
                        )
                    )
            elif mib_report.no_hit:
                oracle_findings.append(
                    Finding(
                        title="MIB check not performed — order bureau report",
                        description=(
                            "The MIB authorization is signed, but no MIB report or codes were included "
                            "with the application. A signed authorization alone is not a bureau search — "
                            "order an MIB report before finalizing the underwriting class."
                        ),
                        severity=RiskSeverity.HIGH,
                        category="mib",
                    )
                )
            oracle_findings.extend(rx_result.findings)
            oracle_findings.extend(ofac_result.findings)
            progress.complete(
                "verify",
                detail=f"{len(oracle_findings)} life bureau/OFAC finding(s)",
                findings=len(oracle_findings),
                status="warning" if oracle_findings else "complete",
            )
        else:
            progress.start("verify", "Verified", "Running external oracle checks")
            if not skip_oracles:
                from insureflow.models.agents import Finding, RiskSeverity

                bundle.status = SubmissionStatus.EXTERNAL_ORACLE_CHECK
                oracle_result = self.oracle_agent.run(
                    bundle,
                    org_id=self.org_id,
                    insurance_line=insurance_line or (resolved_line.value if resolved_line else "") or "",
                )
                oracle_findings = list(oracle_result.findings)
                oracle_failures = oracle_result.oracle_failures
                critical_oracle_failures = [f for f in oracle_failures if f.is_critical and f.status in ("error", "unavailable")]
                if critical_oracle_failures:
                    pending_oracle_failures.extend(critical_oracle_failures)
                audit.log(
                    PipelineEvent.VERIFICATION_COMPLETE,
                    f"Oracle queries: {len(oracle_findings)} findings from CLUE, NCCI, CAT models",
                    metadata={
                        "oracle_success": oracle_result.success,
                        "oracle_findings": len(oracle_findings),
                        "oracle_failures": len(oracle_failures),
                        "critical_oracle_failures": len(critical_oracle_failures),
                    },
                )
            from insureflow.underwriting.sanctions_gate import screen_submission

            ofac_result = screen_submission(bundle)
            ofac_meta = ofac_result.to_metadata()
            oracle_findings.extend(ofac_result.findings)

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
            insurance_line=resolved_line.value if resolved_line else insurance_line,
        )

        # ── 6a. Apply deferred critical oracle failures to memo ──
        if pending_oracle_failures:
            from insureflow.models.agents import Finding, RiskSeverity, UWDecision

            memo.human_review_required = True
            memo.human_review_reasons.append(f"Critical oracle(s) unavailable: {', '.join(f.oracle_name for f in pending_oracle_failures)}")
            if memo.decision not in (UWDecision.DECLINE, UWDecision.REFER):
                memo.decision = UWDecision.REFER
            for failure in pending_oracle_failures:
                memo.key_findings.append(
                    Finding(
                        title=f"CRITICAL: {failure.oracle_name} oracle unavailable",
                        description=(
                            f"{failure.oracle_name} returned status '{failure.status}' ({failure.error_code}): {failure.error_message}. "
                            "Decision forced to REFER — do not treat missing external data as clean."
                        ),
                        severity=RiskSeverity.CRITICAL,
                        category="oracle_failure",
                        evidence=[
                            f"oracle={failure.oracle_name}",
                            f"status={failure.status}",
                            f"error_code={failure.error_code}",
                            f"mode={failure.mode}",
                            f"timestamp={failure.timestamp.isoformat()}",
                        ],
                    )
                )

        # ── 6b. Apply document quality gate results to memo ──
        if doc_quality_result and doc_quality_result.get("decision") == "block":
            from insureflow.models.agents import Finding, RiskSeverity, UWDecision

            memo.human_review_required = True
            memo.human_review_reasons.append(f"Document quality gate blocked: {len(doc_quality_result.get('resubmit_required', []))} document(s) failed quality check")
            for resubmit_file in doc_quality_result.get("resubmit_required", []):
                memo.key_findings.append(
                    Finding(
                        title=f"Low-quality document: {resubmit_file}",
                        description="Document failed quality gate — resubmit required before STP processing can proceed.",
                        severity=RiskSeverity.HIGH,
                        category="data_quality",
                    )
                )
            if memo.decision not in (UWDecision.DECLINE, UWDecision.REFER):
                memo.decision = UWDecision.REFER
        elif doc_quality_result and doc_quality_result.get("decision") == "warn":
            memo.human_review_required = True
            memo.human_review_reasons.append(f"Document quality warning: batch score {doc_quality_result['score']:.2f}")

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

        # Extraction-verification hold: flagged docs block straight-through processing.
        if verification_meta and verification_meta.get("flagged_doc_count"):
            from insureflow.models.agents import Finding, UWDecision
            from insureflow.models.audit import EventSeverity
            from insureflow.verification.aggregate import verification_findings

            for finding in verification_findings(bundle):
                memo.key_findings.append(Finding(**finding))
            memo.human_review_required = True
            memo.human_review_reasons.append(f"Extraction verification flagged {verification_meta['flagged_doc_count']} document(s)")
            if memo.decision not in (UWDecision.DECLINE, UWDecision.REFER):
                memo.decision = UWDecision.REFER
            audit.log(
                PipelineEvent.HUMAN_REVIEW_REQUIRED,
                f"Extraction verification hold: {verification_meta['flagged_doc_count']} document(s) flagged · {verification_meta['exception_count']} exception(s) in queue",
                severity=EventSeverity.WARNING,
            )

        # ── 6a0. Zero-hallucination gate (target count ≤ 0) ──
        try:
            from insureflow.underwriting.memo_sync import enforce_decision_consistency, resync_memo_narrative
            from insureflow.verification.zero_hallucination import enforce_zero_hallucination_on_memo

            zh_report = enforce_zero_hallucination_on_memo(memo, bundle)
            if zh_report.checks_run and zh_report.checks_run != ["zero_hallucination_disabled"]:
                audit.store.save_json(bid, "zero_hallucination.json", zh_report.to_dict(), org_id=self.org_id)
            if not zh_report.passed:
                from insureflow.models.audit import EventSeverity

                audit.log(
                    PipelineEvent.HUMAN_REVIEW_REQUIRED,
                    f"Zero-hallucination gate: {zh_report.hallucination_count} uncited claim(s) (max {zh_report.max_allowed})",
                    severity=EventSeverity.CRITICAL,
                    metadata=zh_report.to_dict(),
                )
                enforce_decision_consistency(memo)
                resync_memo_narrative(memo)
        except Exception as exc:
            logger.warning("zero-hallucination gate failed open to REFER: %s", exc)
            from insureflow.models.agents import Finding, RiskSeverity, UWDecision

            memo.key_findings.append(
                Finding(
                    title="Hallucination gate unavailable — human review required",
                    description=f"Zero-hallucination enforcement error: {type(exc).__name__}. Fail closed.",
                    severity=RiskSeverity.CRITICAL,
                    category="hallucination",
                    confidence=1.0,
                )
            )
            memo.human_review_required = True
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

        # Drop P&C-only findings on life/health so the memo/report stay coherent
        if is_life_line or is_health_line or is_general_line:
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
        elif is_life_line or is_health_line or is_general_line:
            progress.skip("portfolio", "Portfolio", "Not applicable for personal life/health/general")
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

            # The producer's realized-vs-expected book is fed into the selection
            # gate so that a producer's past performance can tip the acceptance of
            # a marginally acceptable exposure (the financial function's
            # underwriter/agent balance).
            selection_result = self.selection_standards.run(
                bundle,
                org_id=self.org_id,
                candidate_risk_score=memo.overall_risk_score,
                producer_experiences=self.producer_experience.last_experiences,
            )
            for f in selection_result.findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)
                    memo.human_review_required = True
            # Selection gate must move the headline decision (never leave ACCEPT + decline finding)
            from insureflow.underwriting.memo_sync import enforce_decision_consistency, worst_decision

            sel_action = getattr(selection_result.recommendation, "action", None) if selection_result.recommendation else None
            if sel_action:
                memo.decision = worst_decision(memo.decision, sel_action)
            enforce_decision_consistency(memo)
            audit.log(
                PipelineEvent.SYNTHESIS_COMPLETE,
                f"Selection standards: {len(selection_result.findings)} findings",
                metadata={"selection_score": selection_result.risk_score, "decision_after_selection": memo.decision.value},
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

        # ── 7a. MORAL HAZARD / CHARACTER SCREEN ──
        # The doctrine: the underwriter must be a skillful judge of people. If
        # the applicant's morals are open to question the policy is declined no
        # matter how sound the property or how healthy the life — so this check
        # runs on every line and a critical finding overrides any acceptance.
        moral_result = None
        if funnel:
            progress.skip("moral_hazard", "Character", "Deferred — available via Deep Dive")
        else:
            progress.start("moral_hazard", "Character", "Judging applicant character")
            from insureflow.models.agents import UWDecision

            moral_result = self.moral_hazard.run(bundle, org_id=self.org_id)
            memo.moral_hazard_findings = list(moral_result.findings)
            for f in moral_result.findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)
                    memo.human_review_required = True
            critical_moral = [f for f in moral_result.findings if f.severity.value == "critical"]
            if critical_moral:
                memo.decision = UWDecision.DECLINE
                memo.human_review_required = True
                memo.human_review_reasons.extend(f.title for f in critical_moral)
                memo.conditions = list(memo.conditions or []) + [f"DECLINED — {f.title}" for f in critical_moral]
            audit.log(
                PipelineEvent.SYNTHESIS_COMPLETE,
                f"Moral hazard: {len(moral_result.findings)} findings",
                metadata={
                    "moral_hazard_score": moral_result.risk_score,
                    "status": moral_result.risk_severity.value,
                    "declined": bool(critical_moral),
                },
            )
            progress.complete(
                "moral_hazard",
                detail=f"Score {moral_result.risk_score:.0%}" if moral_result.risk_score else "No character red flags",
                status="warning" if critical_moral else "complete",
            )

        # ── 8. REINSURANCE TREATY ANALYSIS ──
        reinsurance_result = None
        life_reinsurance_meta: dict[str, Any] = {}
        if funnel:
            progress.skip("reinsurance", "Reinsurance", "Deferred — available via Deep Dive")
        elif is_health_line or is_general_line:
            progress.skip("reinsurance", "Reinsurance", "Not applicable for retail health/general catalog")
        elif is_life_line:
            from insureflow.underwriting.life_reinsurance import evaluate_life_reinsurance
            from insureflow.underwriting.memo_sync import worst_decision

            life_re = evaluate_life_reinsurance(bundle)
            life_reinsurance_meta = life_re.to_metadata()
            for f in life_re.findings:
                memo.key_findings.append(f)
                if f.severity.value in ("critical", "high"):
                    memo.human_review_reasons.append(f.title)
                    memo.human_review_required = True
            memo.decision = worst_decision(memo.decision, life_re.decision_hint)
            progress.complete(
                "reinsurance",
                detail=f"Retain ${life_re.retention:,.0f} · cede ${life_re.cession:,.0f}",
                status="warning" if life_re.facultative_required or life_re.jumbo else "complete",
            )
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
        from insureflow.rating.commercial_actuarial import resolve_quote_line
        from insureflow.rating.models import InsuranceLine
        from insureflow.underwriting.personal_lines import _blob as _package_blob

        # Prefer cascading picker (commercial_product_id / insurance_line) so UI
        # choice is not overwritten by document keyword re-detection.
        quote_blob = " ".join(
            [
                _package_blob(bundle),
                schedule_of_values or "",
                loss_run or "",
                acord_xml or "",
                json_payload or "",
                " ".join(inspection_reports or []),
                " ".join(supplemental_docs or []),
            ]
        )
        if life_checklist_lob:
            line_for_quote = InsuranceLine.LIFE
        elif health_checklist_lob:
            line_for_quote = InsuranceLine.HEALTH
        elif general_checklist_lob:
            line_for_quote = InsuranceLine.GENERAL
        else:
            line_for_quote = resolve_quote_line(
                commercial_product_id=commercial_product_id,
                insurance_line=insurance_line or (resolved_line.value if resolved_line else None),
                product_hint=insurance_line,
                text_blob=quote_blob,
            )
        if not isinstance(line_for_quote, InsuranceLine):
            line_for_quote = InsuranceLine.COMMERCIAL_PROPERTY
        experience_mod = getattr(self.oracle_agent, "last_ncci_emod", None)
        quote = self.rating.quote(
            bundle,
            memo,
            line=line_for_quote,
            commercial_product_id=commercial_product_id or life_product_id or health_product_id or general_product_id,
            commercial_coverage_id=selected_coverage_id,
            experience_mod=experience_mod,
        )
        qmeta = dict(quote.metadata or {})
        if ofac_meta:
            qmeta["ofac"] = ofac_meta
            qmeta["ofac_cleared"] = ofac_meta.get("ofac_cleared")
            if ofac_meta.get("ofac_hits"):
                quote.eligible = False
                reason = "OFAC / sanctions hit — cannot quote"
                if reason not in (quote.ineligibility_reasons or []):
                    quote.ineligibility_reasons = list(quote.ineligibility_reasons or []) + [reason]
        if life_reinsurance_meta:
            qmeta["life_reinsurance"] = life_reinsurance_meta
            qmeta["facultative_required"] = life_reinsurance_meta.get("facultative_required")
        if line_for_quote.value in {"commercial_auto", "personal_auto"} or str(qmeta.get("mvr_required")):
            cleared = getattr(self.oracle_agent, "last_mvr_cleared", None)
            qmeta["mvr_required"] = True
            qmeta["mvr_cleared"] = cleared
            from insureflow.billing.plan import current_plan

            if cleared is False and current_plan().require_live_oracles:
                quote.eligible = False
                reason = "Commercial auto MVR not cleared — live MVR required on this plan"
                if reason not in (quote.ineligibility_reasons or []):
                    quote.ineligibility_reasons = list(quote.ineligibility_reasons or []) + [reason]
        try:
            from insureflow.underwriting.surplus_lines import classify_surplus_lines

            sl = classify_surplus_lines(
                bundle,
                line=line_for_quote,
                state=self.rating._primary_state(bundle) if hasattr(self.rating, "_primary_state") else "",
                product_id=commercial_product_id or "",
            )
            qmeta["surplus_lines"] = sl.to_metadata()
            for f in sl.findings:
                memo.key_findings.append(f)
        except Exception:
            pass
        quote.metadata = qmeta
        uw_worksheet: dict[str, Any] | None = None
        specialty_retrieval: dict[str, Any] | None = None
        commercial_uw_summary: dict[str, Any] | None = None
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
        elif line_for_quote in (
            InsuranceLine.COMMERCIAL_PROPERTY,
            InsuranceLine.BOP,
            InsuranceLine.WORKERS_COMP,
            InsuranceLine.DIRECTORS_AND_OFFICERS,
            InsuranceLine.TRADE_CREDIT,
            InsuranceLine.ERRORS_AND_OMISSIONS,
            InsuranceLine.KEY_PERSON,
        ):
            from insureflow.underwriting.memo_sync import dedupe_findings, resync_memo_narrative, worst_decision

            is_specialty = line_for_quote in (
                InsuranceLine.DIRECTORS_AND_OFFICERS,
                InsuranceLine.TRADE_CREDIT,
                InsuranceLine.ERRORS_AND_OMISSIONS,
                InsuranceLine.KEY_PERSON,
            )
            if is_specialty:
                from insureflow.rag.rag_agent import RAGAgent as HybridRAG
                from insureflow.rag.vector_store import get_vector_store
                from insureflow.rating.commercial_specialty import underwrite_specialty

                specialty = underwrite_specialty(bundle, line_for_quote)
                commercial_uw_summary = specialty.checklist_summary or {
                    "line": line_for_quote.value,
                    "decision": specialty.decision.value,
                    "premium_mod_pct": specialty.premium_mod_pct,
                    "scenario_codes": specialty.scenario_codes,
                    "story": specialty.story,
                }
                for f in specialty.findings:
                    memo.key_findings.append(f)
                memo.decision = worst_decision(memo.decision, specialty.decision)
                memo.human_review_reasons.extend(specialty.referral_flags)
                if specialty.story and specialty.story not in memo.human_review_reasons:
                    memo.human_review_reasons.append(specialty.story)
                if specialty.referral_flags or specialty.scenario_codes:
                    memo.human_review_required = True
                for detail in specialty.referral_flags:
                    if detail and detail not in memo.conditions and not detail.startswith(("PROP_", "DO_", "WC_", "TC_", "EO_", "KP_")):
                        # Action detail strings become open conditions
                        if any(k in detail.lower() for k in ("require", "cap", "exclusion", "deductible", "quarterly", "safety", "medical")):
                            memo.conditions.append(detail)
                premium_mod = specialty.premium_mod_pct
                if (quote.metadata or {}).get("used_default_exposure"):
                    memo.human_review_reasons.append(f"Rated on default exposure ({(quote.metadata or {}).get('exposure_basis')}) — confirm limit/AR/face amount")
                    memo.human_review_required = True
                try:
                    specialty_retrieval = HybridRAG(
                        vector_store=get_vector_store(),
                        use_knowledge_graph=True,
                    ).retrieve_contexts(
                        f"{line_for_quote.value} underwriting risk assessment {quote_blob[:1200]}",
                        top_k=5,
                        line_of_business=line_for_quote.value,
                    )
                    ids = specialty_retrieval.get("guideline_ids") or []
                    if ids:
                        memo.human_review_reasons.append(f"Guidelines cited: {', '.join(ids[:5])}")
                except Exception as exc:
                    logger.debug("Specialty RAG retrieval failed: %s", exc)
                    specialty_retrieval = {"error": str(exc), "guideline_ids": []}
            else:
                from insureflow.underwriting.commercial_checklists import evaluate_commercial_checklist

                checklist = evaluate_commercial_checklist(bundle, line_for_quote)
                commercial_uw_summary = checklist.to_summary_dict()
                for f in checklist.findings:
                    memo.key_findings.append(f)
                memo.decision = worst_decision(memo.decision, checklist.decision)
                if checklist.story:
                    memo.human_review_reasons.append(checklist.story)
                for action in checklist.actions:
                    if action.detail:
                        memo.human_review_reasons.append(action.detail)
                        if action.detail not in memo.conditions:
                            memo.conditions.append(action.detail)
                    if action.action_type.value in {
                        "refer",
                        "require_mitigation",
                        "require_doc",
                        "add_exclusion",
                        "cap_coverage",
                        "enhanced_review",
                        "higher_deductible",
                    }:
                        memo.human_review_required = True
                premium_mod = checklist.premium_mod_pct

            if premium_mod and quote.metadata is not None:
                quote.metadata["commercial_checklist_mod_pct"] = premium_mod
                if premium_mod != 0:
                    quote.adjusted_premium = round(
                        float(quote.adjusted_premium) * (1.0 + premium_mod / 100.0),
                        2,
                    )

            memo.key_findings = dedupe_findings(list(memo.key_findings or []))
            resync_memo_narrative(
                memo,
                extra_summary=(
                    f"Commercial checklist line={line_for_quote.value}; "
                    f"scenarios={','.join((commercial_uw_summary or {}).get('scenario_codes') or []) or 'none'}; "
                    f"premium_mod={(commercial_uw_summary or {}).get('premium_mod_pct', 0)}%."
                ),
            )
        elif line_for_quote == InsuranceLine.GENERAL:
            from insureflow.models.agents import UWDecision
            from insureflow.underwriting.general_uw import underwrite_general
            from insureflow.underwriting.memo_sync import resync_memo_narrative, worst_decision

            general_uw = underwrite_general(
                bundle,
                product_id=general_product_id or commercial_product_id,
                coverage_id=selected_coverage_id or general_coverage_id,
            )
            for f in general_uw.findings:
                memo.key_findings.append(f)
            memo.decision = worst_decision(memo.decision, general_uw.decision)
            memo.human_review_reasons.extend(general_uw.reasons)
            memo.conditions.extend(general_uw.conditions)
            if general_uw.decision != UWDecision.ACCEPT:
                memo.human_review_required = True
            qmeta = dict(quote.metadata or {})
            qmeta["general_uw"] = general_uw.to_metadata()
            quote.metadata = qmeta
            resync_memo_narrative(
                memo,
                extra_summary=(f"General {general_uw.product_family} product={general_uw.product_id} coverage={general_uw.coverage_id or '—'} decision={general_uw.decision.value}."),
            )
        elif line_for_quote == InsuranceLine.HEALTH:
            from insureflow.models.agents import UWDecision
            from insureflow.underwriting.health_uw import underwrite_health
            from insureflow.underwriting.memo_sync import resync_memo_narrative, worst_decision

            health_uw = underwrite_health(
                bundle,
                product_id=health_product_id or commercial_product_id,
                coverage_id=selected_coverage_id or health_coverage_id,
            )
            for f in health_uw.findings:
                memo.key_findings.append(f)
            memo.decision = worst_decision(memo.decision, health_uw.decision)
            memo.human_review_reasons.extend(health_uw.reasons)
            memo.conditions.extend(health_uw.conditions)
            if health_uw.decision != UWDecision.ACCEPT:
                memo.human_review_required = True
            qmeta = dict(quote.metadata or {})
            qmeta["health_uw"] = health_uw.to_metadata()
            quote.metadata = qmeta
            resync_memo_narrative(
                memo,
                extra_summary=(f"Health {health_uw.product_family} product={health_uw.product_id} coverage={health_uw.coverage_id or '—'} decision={health_uw.decision.value}."),
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

        from insureflow.underwriting.lob_rating import apply_lob_rating, build_uw_worksheet

        quote = apply_lob_rating(
            quote,
            bundle,
            memo,
            line=line_for_quote,
            insurance_line=insurance_line or line_for_quote.value,
            commercial_coverage_id=commercial_coverage_id,
            commercial_product_id=commercial_product_id,
        )
        uw_worksheet = build_uw_worksheet(
            quote,
            bundle,
            memo,
            line=line_for_quote,
            insurance_line=insurance_line or line_for_quote.value,
            commercial_product_name=commercial_product_name,
            commercial_coverage_name=commercial_coverage_name,
            commercial_coverage_id=commercial_coverage_id,
        )

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
        from insureflow.decisions import normalize_decision, skips_core_push

        skip_core_for_decision = skips_core_push(memo.decision)
        appetite_referral = bool(appetite_result and appetite_result.needs_uw_referral and not appetite_passed)
        if not skip_core_integration and not skip_core_for_decision and not appetite_referral:
            core_results = self.policy_admin.submit_to_core_systems(bundle, memo, quote, self.org_id)
            successful = [r for r in core_results if r.get("success")]
            pas_ref = str((successful[0] or {}).get("external_reference") or "") if successful else ""
            if pas_ref:
                quote.policy_admin_reference = pas_ref
                quote.metadata = dict(quote.metadata or {})
                quote.metadata["pas_job_reference"] = pas_ref
                quote.metadata["pas_system"] = successful[0].get("system")
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

        if not (quote.metadata or {}).get("pas_bind_payload"):
            try:
                built = self.policy_admin._build_payload(bundle, memo, quote, self.org_id)
                quote.metadata = dict(quote.metadata or {})
                quote.metadata["pas_bind_payload"] = built.to_dict()
            except Exception:
                pass

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

        # Production KPI capture (cycle time + routing + catch signals)
        try:
            from insureflow.analytics.business_kpis import get_business_kpi_service
            from insureflow.analytics.metrics import get_pipeline_metrics

            cycle_rec = get_pipeline_metrics().cycle_time.finish_pipeline(bid, status="completed")
            recon_conflicts = 0
            try:
                recon_conflicts = len(getattr(reconciliation, "discrepancies", None) or [])
            except Exception:
                recon_conflicts = 0
            get_business_kpi_service().record_pipeline_result(
                bundle_id=bid,
                decision=memo.decision.value,
                org_id=self.org_id,
                human_review_required=bool(memo.human_review_required),
                missing_docs=list(missing_docs) if missing_docs else False,
                conflict_detected=recon_conflicts > 0,
                cycle_ms=cycle_rec.total_ms if cycle_rec else None,
                source="pipeline",
            )
        except Exception as exc:
            logger.debug("Business KPI capture failed: %s", exc)

        # ── 14. Dispatch status webhooks for broker visibility ──
        webhook_dispatcher.dispatch_async(
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

        state_compliance = None
        if primary_state:
            try:
                reg_engine = StateRegulatoryEngine()
                loc_dicts = [{"state": loc.state, "city": loc.city, "address": loc.address} for loc in (bundle.structured.locations if bundle.structured else [])]
                detected = reg_engine.detect_state(loc_dicts) or primary_state
                is_surplus = bool((quote.metadata or {}).get("surplus_lines"))
                line_hint = resolved_line.value if resolved_line else ""
                state_compliance = reg_engine.evaluate(
                    detected,
                    line_of_business=line_hint,
                    is_surplus_lines=is_surplus,
                    is_windstorm_zone=detected in ("FL", "TX", "LA", "NC", "SC", "NJ", "NY"),
                    has_oral_binder=False,
                )
            except Exception as exc:
                logger.warning("State compliance check failed: %s", exc)
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
        if open_conditions and all(c.get("id") != "subjectivities" for c in human_checkpoints):
            human_checkpoints.append(
                {
                    "id": "subjectivities",
                    "label": "Clear subjectivities",
                    "status": "pending",
                    "reason": "; ".join(open_conditions[:3]),
                }
            )

        # Final consistency gate: never emit ACCEPT with critical decline findings / high severity
        from insureflow.underwriting.memo_sync import enforce_decision_consistency

        enforce_decision_consistency(memo)
        # Keep workflow AI decision aligned with the gated memo
        if wf.ai_decision != memo.decision.value:
            wf.ai_decision = memo.decision.value
            try:
                self.workflow.store.save(wf)
            except Exception:
                pass

        summary = {
            "status": "completed",
            "bundle_id": bid,
            "org_id": self.org_id,
            "insured_name": memo.insured_name,
            "broker_name": broker_name,
            "primary_state": primary_state,
            "state_compliance": state_compliance.model_dump(mode="json") if state_compliance else None,
            "tiv": estimated_tiv,
            "triage_priority": triage_result.priority.value,
            "triage_score": triage_result.score,
            "ai_decision": memo.decision.value,
            "outcome": normalize_decision(memo.decision).value,
            "workflow_state": wf.state.value,
            "insurance_line": line_for_quote.value,
            "product_line": line_for_quote.value,
            "commercial_product_id": commercial_product_id,
            "life_product_id": life_product_id,
            "life_coverage_id": life_coverage_id or (selected_coverage_id if life_checklist_lob else None),
            "health_product_id": health_product_id,
            "health_coverage_id": health_coverage_id or (selected_coverage_id if health_checklist_lob else None),
            "general_product_id": general_product_id,
            "general_coverage_id": general_coverage_id or (selected_coverage_id if general_checklist_lob else None),
            "checklist_lob": checklist_lob,
            "life_checklist_lob": life_checklist_lob,
            "health_checklist_lob": health_checklist_lob,
            "general_checklist_lob": general_checklist_lob,
            "commercial_coverage_id": commercial_coverage_id,
            "commercial_product_name": commercial_product_name,
            "commercial_coverage_name": commercial_coverage_name,
            "commercial_category_id": commercial_category_id,
            "insurance_company_id": (insurance_company_id or "").strip() or None,
            "insurance_company_name": (insurance_company_name or "").strip() or None,
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
            "doc_quality": doc_quality_result,
            "extraction_issues": extraction_issues,
            "extraction_issue_summary": {
                "total": len(extraction_issues),
                "errors": sum(1 for i in extraction_issues if i.get("severity") == "error"),
                "warnings": sum(1 for i in extraction_issues if i.get("severity") == "warning"),
            },
            "pipeline_stages": progress.stages,
            "provenance_summary": {
                "total_fields": provenance.record_count(),
                "verified_fields": provenance.verified_count(),
                "contradicted_fields": provenance.discrepancy_count(),
            },
            "human_checkpoints": human_checkpoints,
            "open_conditions": open_conditions,
            "subjectivities": [],
            "bind_readiness": None,
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
                "coverage_id": commercial_coverage_id,
                "term_years": (quote.metadata or {}).get("term_years"),
                "life_coverage_id": (quote.metadata or {}).get("life_coverage_id"),
                "health_uw": (quote.metadata or {}).get("health_uw"),
                "general_uw": (quote.metadata or {}).get("general_uw"),
                "benefit_type": (quote.metadata or {}).get("benefit_type"),
                "requires_passport": (quote.metadata or {}).get("requires_passport"),
                "specialty": bool((quote.metadata or {}).get("specialty")),
                "exposure_basis": (quote.metadata or {}).get("exposure_basis"),
                "medical": (quote.metadata or {}).get("medical"),
                "ofac_cleared": (quote.metadata or {}).get("ofac_cleared"),
                "ofac": (quote.metadata or {}).get("ofac"),
                "surplus_lines": (quote.metadata or {}).get("surplus_lines"),
                "facultative_required": (quote.metadata or {}).get("facultative_required"),
                "life_reinsurance": (quote.metadata or {}).get("life_reinsurance"),
                "mvr_required": (quote.metadata or {}).get("mvr_required"),
                "mvr_cleared": (quote.metadata or {}).get("mvr_cleared"),
                "iso_forms": (quote.metadata or {}).get("iso_forms"),
                "personal_lines": (quote.metadata or {}).get("personal_lines"),
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
            "specialty_retrieval": {
                "guideline_ids": (specialty_retrieval or {}).get("guideline_ids") or [],
                "mode": (specialty_retrieval or {}).get("mode"),
                "line_of_business": (specialty_retrieval or {}).get("line_of_business"),
                "no_context": bool((specialty_retrieval or {}).get("no_context")),
            }
            if specialty_retrieval is not None
            else None,
            "commercial_uw": commercial_uw_summary,
            "uw_worksheet": uw_worksheet,
            "core_integration": core_results,
            "pas_bind_payload": dict((quote.metadata or {}).get("pas_bind_payload") or {}),
            "encryption_at_rest": self.encryption.enabled,
            "prediction_id": prediction.prediction_id,
            "zta_mode": self.zta_config.mode,
            "zta_report": zta_report,
        }

        # ── Domain analytics: the full insurance taxonomy (financial metrics,
        #    policy architecture, insurability, disclosure, claims lifecycle,
        #    valuation, exposure bases). Each block degrades gracefully.
        try:
            from insureflow.rating.premium_accounting import premium_accounting_for_bundle
            from insureflow.underwriting.causation import analyze_proximate_cause
            from insureflow.underwriting.claims import (
                claims_recovery_review,
                defense_cost_assessment,
                indemnity_valuation,
            )
            from insureflow.underwriting.combined_ratio import combined_ratio_from_bundle
            from insureflow.underwriting.disclosure import assess_disclosure
            from insureflow.underwriting.health_exposure import health_exposure_base
            from insureflow.underwriting.insurability import assess_insurability
            from insureflow.underwriting.legal_remedies import remedy_matrix
            from insureflow.underwriting.policy_architecture import architecture_assessment
            from insureflow.underwriting.solvency import assess_solvency
            from insureflow.underwriting.valuation import valuation_from_bundle

            premium_accounting = premium_accounting_for_bundle(bundle)
            combined = combined_ratio_from_bundle(bundle)
            insurability = assess_insurability(bundle)
            disclosure = assess_disclosure(bundle)
            remedy = remedy_matrix(disclosure)
            claims_recovery = claims_recovery_review(bundle)
            valuation = valuation_from_bundle(bundle)

            claim_analytics: list[dict[str, Any]] = []
            loss_run_claims: list[Any] = []
            if bundle.structured is not None and bundle.structured.financial is not None and bundle.structured.financial.loss_run is not None:
                loss_run_claims = list(bundle.structured.financial.loss_run.claims)
                for claim in loss_run_claims:
                    entry: dict[str, Any] = {"claim_id": claim.claim_id}
                    try:
                        entry["proximate_cause"] = analyze_proximate_cause(cause=claim.cause, description=claim.description).model_dump()
                    except Exception:
                        pass
                    claim_analytics.append(entry)

            solvency = assess_solvency(
                total_assets=0.0,
                total_liabilities=0.0,
                net_written_premium=premium_accounting.written_premium or 0.0,
            )

            domain: dict[str, Any] = {
                "premium_accounting": premium_accounting.model_dump(),
                "combined_ratio": combined.model_dump(),
                "insurability": insurability.model_dump(),
                "disclosure": disclosure.model_dump(),
                "legal_remedy": remedy,
                "claims_recovery": claims_recovery,
                "claim_analytics": claim_analytics,
                "defense_costs": defense_cost_assessment(loss_run_claims),
                "indemnity_valuation": indemnity_valuation(replacement_cost=float(valuation.get("total_effective_value") or 0.0)),
                "valuation": valuation,
                "solvency": solvency.model_dump(),
                "policy_architecture": [architecture_assessment(c) for c in (bundle.structured.coverages if bundle.structured else [])],
                "health_exposure": health_exposure_base(bundle),
            }
            if insurability.insurable is False:
                domain["insurability_blocked"] = insurability.failed_criteria
            if not disclosure.utmost_good_faith:
                domain["disclosure_breached"] = True
            summary["domain_analytics"] = domain
        except Exception as exc:
            logger.debug("domain analytics skipped: %s", exc)

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

        # Add moral-hazard / character screen data if available
        if moral_result:
            summary["moral_hazard"] = moral_result.model_dump()

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
            from insureflow.privacy.decision_memory import get_decision_memory

            remembered = get_decision_memory().remember_from_summary(summary, org_id=self.org_id)
            if remembered:
                summary["decision_memory"] = {
                    "stored": True,
                    "tiv_band": remembered.tiv_band,
                    "line": remembered.line,
                    "state": remembered.state,
                }
        except Exception as exc:
            logger.debug("Decision memory skipped: %s", exc)
        try:
            from insureflow.underwriting.subjectivities import compute_bind_readiness, seed_subjectivities_from_conditions

            summary["subjectivities"] = seed_subjectivities_from_conditions(summary)
            summary["bind_readiness"] = compute_bind_readiness(summary)
        except Exception as exc:
            logger.debug("Bind readiness seed failed: %s", exc)
        try:
            from insureflow.evaluations.pipeline_shadow import run_shadow_eval

            shadow = run_shadow_eval(summary=summary, quote=quote, memo=memo)
            audit.store.save_json(bid, "shadow_eval.json", shadow, org_id=self.org_id)
        except Exception as exc:
            logger.debug("Shadow eval persist failed: %s", exc)
        try:
            audit.store.save_json(bid, "checkpoints.json", human_checkpoints, org_id=self.org_id)
        except Exception as exc:
            logger.warning("Failed to persist checkpoints.json: %s", exc)

        try:
            from insureflow.observability.pipeline_hooks import record_pipeline_observability

            obs = dict(summary)
            if not obs.get("quote"):
                try:
                    obs["quote"] = dataclasses.asdict(quote)
                except Exception:
                    pass
            record_pipeline_observability(obs)
        except Exception:
            pass

        return {
            **summary,
            "memo": memo.model_dump(),
            "quote_full": dataclasses.asdict(quote),
            "quote_html": quote_html,
            "reconciliation": reconciliation.model_dump(),
            "provenance": provenance.model_dump(),
            "verification": verification_meta,
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
        allowed = ["oracles", "portfolio", "selection_standards", "producer_experience", "adverse_selection", "moral_hazard", "reinsurance", "fraud_ml", "premium_ml", "churn_ml"]
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
            results["oracle_failures"] = [f.model_dump() for f in oracle_result.oracle_failures]

        if "portfolio" in include:
            portfolio_result = self.portfolio_risk.run(bundle, org_id=scope)
            results["completed"].append("portfolio")
            results["findings"]["portfolio"] = {
                "risk_score": portfolio_result.risk_score,
                "findings": [f.model_dump() for f in portfolio_result.findings],
            }

        if "producer_experience" in include:
            producer_result = self.producer_experience.run(bundle, org_id=scope)
            results["completed"].append("producer_experience")
            results["findings"]["producer_experience"] = producer_result.model_dump()

        if "selection_standards" in include:
            producer_experiences = self.producer_experience.last_experiences if "producer_experience" in include else None
            selection_result = self.selection_standards.run(
                bundle,
                org_id=scope,
                producer_experiences=producer_experiences,
            )
            results["completed"].append("selection_standards")
            results["findings"]["selection_standards"] = selection_result.model_dump()

        if "adverse_selection" in include:
            adverse_result = self.adverse_selection.run(bundle, org_id=scope)
            results["completed"].append("adverse_selection")
            results["findings"]["adverse_selection"] = adverse_result.model_dump()

        if "moral_hazard" in include:
            moral_result = self.moral_hazard.run(bundle, org_id=scope)
            results["completed"].append("moral_hazard")
            results["findings"]["moral_hazard"] = moral_result.model_dump()

        if "reinsurance" in include:
            reinsurance_result = self.reinsurance.run(bundle, org_id=scope)
            results["completed"].append("reinsurance")
            results["findings"]["reinsurance"] = {
                "risk_score": reinsurance_result.risk_score,
                "findings": [f.model_dump() for f in reinsurance_result.findings],
            }

        ml_inputs = self._deep_dive_ml_inputs(bundle)
        insurance_line = None
        if bundle.structured and bundle.structured.coverages:
            insurance_line = getattr(bundle.structured.coverages[0], "line_of_business", None)
        for ml_name in ("fraud_ml", "premium_ml", "churn_ml"):
            if ml_name not in include:
                continue
            results["completed"].append(ml_name)
            results["findings"][ml_name] = self._run_ml_deep_dive(ml_name, ml_inputs, insurance_line=insurance_line)

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
                from insureflow.underwriting.loss_ratio import loss_ratio_from_bundle

                lr_result = loss_ratio_from_bundle(bundle)
                if lr_result.known:
                    loss_ratio = min(lr_result.ratio, 3.0)
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

    def _run_ml_deep_dive(self, ml_name: str, inputs: dict[str, float], *, insurance_line: str | None = None) -> dict[str, Any]:
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
                    insurance_line=insurance_line,
                )
            if ml_name == "premium_ml":
                return MLTools.predict_premium(
                    tiv=inputs["tiv"],
                    loss_ratio=inputs["loss_ratio"],
                    credit_score=inputs["credit_score"],
                    prior_claims_count=int(inputs["prior_claims_count"]),
                    insurance_line=insurance_line,
                )
            if ml_name == "churn_ml":
                return MLTools.predict_churn(
                    loss_ratio=inputs["loss_ratio"],
                    credit_score=inputs["credit_score"],
                    years_in_business=5.0,
                    insurance_line=insurance_line,
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
        webhook_dispatcher.dispatch_async(
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
