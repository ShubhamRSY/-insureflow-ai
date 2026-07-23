from __future__ import annotations

import logging
from typing import Any, cast
from uuid import uuid4

from insureflow.audit.logger import AuditLogger
from insureflow.audit.store import AuditStore
from insureflow.graph.state import PipelineState, default_state
from insureflow.ingestion.classifier import DocumentClassifier
from insureflow.ingestion.loader import SubmissionLoader
from insureflow.llm.client import LLMClient
from insureflow.models.audit import EventSeverity, PipelineEvent
from insureflow.models.submissions import DocumentType, SubmissionBundle
from insureflow.provenance.hierarchy import ProvenanceEngine
from insureflow.reconciliation.engine import ReconciliationEngine

logger = logging.getLogger(__name__)

_AUDIT_LOGGER = AuditLogger()

_metrics: Any = None


def _get_metrics() -> Any:
    global _metrics
    if _metrics is None:
        try:
            from insureflow.analytics.metrics import get_pipeline_metrics

            _metrics = get_pipeline_metrics()
        except Exception:
            pass
    return _metrics


def _track_stage(bundle_id: str, stage: str) -> None:
    m = _get_metrics()
    if m is not None:
        m.cycle_time.start_stage(bundle_id, stage)


def _finish_stage(bundle_id: str, stage: str) -> None:
    m = _get_metrics()
    if m is not None:
        m.cycle_time.finish_stage(bundle_id, stage)


def _track_fill_rate(bundle_id: str, fields: dict[str, Any], agent: str = "") -> None:
    m = _get_metrics()
    if m is not None:
        m.fill_rate.record_bundle_fields(bundle_id, fields, agent=agent)


def create_initial_state(**kwargs: Any) -> dict[str, Any]:
    return default_state(**kwargs)


def ingest_docs(state: PipelineState) -> dict[str, Any]:
    _log_state("ingest_docs", state)
    bundle_id = state.get("bundle_id") or f"graph-{uuid4().hex[:12]}"
    _track_stage(bundle_id, "ingest")
    loader = SubmissionLoader()

    bundle = loader.load_bundle(
        acord_xml=state.get("acord_xml"),
        inspection_reports=state.get("inspection_reports"),
        supplemental_docs=state.get("supplemental_docs"),
        json_payload=state.get("json_payload"),
        loss_run=state.get("loss_run"),
        schedule_of_values=state.get("schedule_of_values"),
        raw_docs=state.get("raw_docs"),
        auto_classify=state.get("auto_classify", False),
        bundle_id=bundle_id,
    )

    _finish_stage(bundle_id, "ingest")
    _log_event(bundle_id, PipelineEvent.SUBMISSION_RECEIVED, "ingest_docs", f"Bundle loaded: {bundle_id}")

    return {
        "bundle": bundle,
        "bundle_id": bundle_id,
    }


def classify_docs(state: PipelineState) -> dict[str, Any]:
    bundle: SubmissionBundle | None = state.get("bundle")
    _log_state("classify_docs", state)

    routes: list[str] = []

    if state.get("acord_xml"):
        if "parse_acord" not in routes:
            routes.append("parse_acord")
    if state.get("json_payload"):
        if "parse_json" not in routes:
            routes.append("parse_json")

    input_routes = {
        "loss_run": "parse_loss_run",
        "schedule_of_values": "parse_sov",
    }
    for field, route in input_routes.items():
        if state.get(field) and route not in routes:
            routes.append(route)

    if state.get("inspection_reports"):
        if "parse_inspection" not in routes:
            routes.append("parse_inspection")

    if bundle:
        if bundle.structured:
            src = bundle.structured.source
            if "acord" in src and "parse_acord" not in routes:
                routes.append("parse_acord")
            elif ("json" in src or "broker_api" in src) and "parse_json" not in routes:
                routes.append("parse_json")

        for doc in list(bundle.unstructured or []) + list(bundle.supplemental or []):
            doc_type = DocumentClassifier.classify(doc.raw_text, doc.submission_id)
            route = _doc_type_to_route(doc_type)
            if route and route not in routes:
                routes.append(route)

    if not routes:
        routes.append("parse_supplemental")

    _log_event(
        state["bundle_id"],
        PipelineEvent.STRUCTURED_PARSE_START,
        "classify_docs",
        f"Routes determined: {routes}",
    )

    return {"classification_routes": routes}


def _doc_type_to_route(doc_type: DocumentType) -> str:
    mapping = {
        DocumentType.ACORD_XML: "parse_acord",
        DocumentType.BROKER_API_JSON: "parse_json",
        DocumentType.LOSS_RUN: "parse_loss_run",
        DocumentType.SCHEDULE_OF_VALUES: "parse_sov",
        DocumentType.INSPECTION_REPORT: "parse_inspection",
        DocumentType.SUPPLEMENTAL: "",
    }
    return mapping.get(doc_type, "")


def route_by_classification(state: PipelineState) -> str:
    routes = state.get("classification_routes", [])
    _log_state("route_by_classification", state)
    if not routes:
        return "parse_supplemental"
    remaining = [r for r in routes if not state.get(f"parsed_{r.replace('parse_', '')}")]
    if remaining:
        return str(remaining[0])
    return "merge_structured"


def parse_acord(state: PipelineState) -> dict[str, Any]:
    _log_state("parse_acord", state)
    bundle: SubmissionBundle = state["bundle"]
    bundle_id = state["bundle_id"]

    if bundle.structured and bundle.structured.source == "broker_acord_xml":
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_acord",
            "ACORD already parsed in bundle",
        )
        return {"parsed_acord": True}

    acord_xml = state.get("acord_xml")
    if not acord_xml:
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_START,
            "parse_acord",
            "No ACORD XML provided, skipping",
        )
        return {"parsed_acord": True}

    from insureflow.ingestion.acord_parser import ACORDParser

    try:
        parser = ACORDParser()
        structured = parser.parse(acord_xml, f"{bundle_id}-acord")
        bundle.structured = structured
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_acord",
            "ACORD XML parsed successfully",
        )
    except Exception as exc:
        logger.error("ACORD parse failed: %s", exc)
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_acord",
            f"ACORD parse failed: {exc}",
            severity=EventSeverity.ERROR,
        )

    return {"bundle": bundle, "parsed_acord": True}


def parse_json(state: PipelineState) -> dict[str, Any]:
    _log_state("parse_json", state)
    bundle: SubmissionBundle = state["bundle"]
    bundle_id = state["bundle_id"]
    json_payload = state.get("json_payload")

    if not json_payload:
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_START,
            "parse_json",
            "No JSON payload, skipping",
        )
        return {"parsed_json": True}

    if bundle.structured and bundle.structured.source == "broker_api_json":
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_json",
            "JSON already parsed in bundle",
        )
        return {"parsed_json": True}

    from insureflow.ingestion.json_parser import JSONBrokerParser

    try:
        parser = JSONBrokerParser()
        structured = parser.parse(json_payload, f"{bundle_id}-json")
        bundle.structured = structured
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_json",
            "JSON payload parsed successfully",
        )
    except Exception as exc:
        logger.error("JSON parse failed: %s", exc)
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_json",
            f"JSON parse failed: {exc}",
            severity=EventSeverity.ERROR,
        )

    return {"bundle": bundle, "parsed_json": True}


def parse_loss_run(state: PipelineState) -> dict[str, Any]:
    _log_state("parse_loss_run", state)
    bundle: SubmissionBundle = state["bundle"]
    bundle_id = state["bundle_id"]
    loss_run_text = state.get("loss_run")

    if not loss_run_text:
        for doc in bundle.unstructured or []:
            if "loss_run" in doc.source.lower() or "loss" in doc.document_type.lower():
                loss_run_text = doc.raw_text
                break

    if not loss_run_text:
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_START,
            "parse_loss_run",
            "No loss run data, skipping",
        )
        return {"parsed_loss_run": True}

    from insureflow.ingestion.loss_run_parser import LossRunParser

    try:
        parser = LossRunParser()
        parsed = parser.parse(loss_run_text, f"{bundle_id}-loss-run")
        bundle.unstructured.append(parsed)
        loss_run_data = parser.parse_structured(loss_run_text)
        if bundle.structured and loss_run_data:
            if not bundle.structured.financial:
                from insureflow.models.submissions import FinancialData

                bundle.structured.financial = FinancialData()
            bundle.structured.financial.loss_run = loss_run_data
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_loss_run",
            f"Loss run parsed: {len(loss_run_data.claims)} claims",
        )
    except Exception as exc:
        logger.error("Loss run parse failed: %s", exc)
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_loss_run",
            f"Loss run parse failed: {exc}",
            severity=EventSeverity.ERROR,
        )

    return {"bundle": bundle, "parsed_loss_run": True}


def parse_sov(state: PipelineState) -> dict[str, Any]:
    _log_state("parse_sov", state)
    bundle: SubmissionBundle = state["bundle"]
    bundle_id = state["bundle_id"]
    sov_text = state.get("schedule_of_values")

    if not sov_text:
        for doc in bundle.unstructured or []:
            if "sov" in doc.source.lower() or "schedule_of_values" in doc.document_type.lower():
                sov_text = doc.raw_text
                break

    if not sov_text:
        _log_event(bundle_id, PipelineEvent.STRUCTURED_PARSE_START, "parse_sov", "No SOV data, skipping")
        return {"parsed_sov": True}

    from insureflow.ingestion.sov_parser import SOVParser

    try:
        parser = SOVParser()
        parsed = parser.parse(sov_text, f"{bundle_id}-sov")
        bundle.unstructured.append(parsed)
        sov_result = parser.parse_structured(sov_text)
        if bundle.structured:
            bundle.structured.schedule_of_values = sov_result
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_sov",
            f"SOV parsed: {len(sov_result)} schedules",
        )
    except Exception as exc:
        logger.error("SOV parse failed: %s", exc)
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_sov",
            f"SOV parse failed: {exc}",
            severity=EventSeverity.ERROR,
        )

    return {"bundle": bundle, "parsed_sov": True}


def parse_inspection(state: PipelineState) -> dict[str, Any]:
    _log_state("parse_inspection", state)
    bundle: SubmissionBundle = state["bundle"]
    bundle_id = state["bundle_id"]

    if not (bundle.unstructured or []):
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_START,
            "parse_inspection",
            "No unstructured docs, skipping",
        )
        return {"parsed_inspection": True}

    from insureflow.ingestion.report_extractor import InspectionReportExtractor

    try:
        extractor = InspectionReportExtractor()
        for doc in bundle.unstructured:
            if "inspection" in doc.source.lower() or "inspection" in doc.document_type.lower():
                extracted = extractor.parse(doc.raw_text, doc.submission_id)
                doc.extracted_fields = extracted.extracted_fields
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_inspection",
            "Inspection reports parsed",
        )
    except Exception as exc:
        logger.error("Inspection parse failed: %s", exc)
        _log_event(
            bundle_id,
            PipelineEvent.STRUCTURED_PARSE_COMPLETE,
            "parse_inspection",
            f"Inspection parse failed: {exc}",
            severity=EventSeverity.ERROR,
        )

    return {"bundle": bundle, "parsed_inspection": True}


def parse_supplemental(state: PipelineState) -> dict[str, Any]:
    _log_state("parse_supplemental", state)
    _log_event(
        state["bundle_id"],
        PipelineEvent.STRUCTURED_PARSE_COMPLETE,
        "parse_supplemental",
        "Supplemental documents noted",
    )
    return {}


def merge_structured(state: PipelineState) -> dict[str, Any]:
    _log_state("merge_structured", state)
    bundle_id = state["bundle_id"]
    _track_stage(bundle_id, "merge")
    bundle: SubmissionBundle = state["bundle"]

    if not bundle.structured:
        from insureflow.models.submissions import StructuredSubmission

        bundle.structured = StructuredSubmission(
            submission_id=f"{bundle_id}-merged",
        )

    _track_fill_rate(bundle_id, _extract_fields_from_bundle(bundle), agent="merge_structured")

    _finish_stage(bundle_id, "merge")
    _log_event(
        bundle_id,
        PipelineEvent.STRUCTURED_PARSE_COMPLETE,
        "merge_structured",
        "All parsed data merged into bundle",
    )
    return {"bundle": bundle}


def _extract_fields_from_bundle(bundle: SubmissionBundle) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if not bundle.structured:
        return fields
    s = bundle.structured
    if s.named_insured:
        fields["named_insured"] = s.named_insured.legal_name
    if s.broker:
        fields["broker_name"] = s.broker.broker_name
    if s.policy_period:
        fields["effective_date"] = str(s.policy_period.effective_date) if s.policy_period.effective_date else ""
        fields["expiration_date"] = str(s.policy_period.expiration_date) if s.policy_period.expiration_date else ""
    if s.risk_profile:
        fields["naics_code"] = s.risk_profile.naics_code or ""
        fields["construction_type"] = s.risk_profile.construction_type or ""
        fields["occupancy_type"] = s.risk_profile.occupancy_type or ""
        fields["year_built"] = s.risk_profile.total_square_footage or 0
    if s.locations:
        loc = s.locations[0]
        fields["state"] = loc.state or ""
    if s.coverages:
        cov = s.coverages[0]
        fields["coverage_type"] = cov.coverage_type or ""
        fields["limit_amount"] = cov.limit_amount or 0
        fields["deductible"] = cov.deductible or 0
        fields["premium"] = cov.premium or 0
    if s.financial:
        fields["total_claims"] = len(s.financial.prior_losses) if s.financial.prior_losses else 0
        fields["total_incurred"] = sum(loss.get("incurred_amount", 0) for loss in s.financial.prior_losses) if s.financial.prior_losses else 0
    return fields


def extract_agents(state: PipelineState) -> dict[str, Any]:
    bundle: SubmissionBundle = state["bundle"]
    bundle_id = state["bundle_id"]
    _log_state("extract_agents", state)
    _track_stage(bundle_id, "extract")
    _log_event(bundle_id, PipelineEvent.EXTRACTION_START, "extract_agents", "Running agent extraction")

    llm = LLMClient()

    from insureflow.agents.extraction_agent import ExtractionAgent

    agent = ExtractionAgent(llm)

    try:
        bundle = agent.process_bundle(bundle)
        retries = 0
    except Exception as exc:
        logger.error("Extraction failed (attempt %d): %s", state.get("extraction_retries", 0) + 1, exc)
        _log_event(
            bundle_id,
            PipelineEvent.EXTRACTION_COMPLETE,
            "extract_agents",
            f"Extraction failed: {exc}",
            severity=EventSeverity.ERROR,
        )
        retries = state.get("extraction_retries", 0) + 1

    _finish_stage(bundle_id, "extract")
    return {
        "bundle": bundle,
        "extraction_retries": retries,
    }


def should_retry_extraction(state: PipelineState) -> str:
    retries = state.get("extraction_retries", 0)
    max_retries = state.get("max_extraction_retries", 3)

    if retries > 0 and retries <= max_retries:
        logger.info("Retrying extraction (attempt %d/%d)", retries, max_retries)
        return "extract_agents"
    if retries > max_retries:
        logger.error("Extraction failed after %d retries", max_retries)
        state.setdefault("errors", []).append(f"Extraction failed after {max_retries} retries")
    return "build_provenance"


def build_provenance(state: PipelineState) -> dict[str, Any]:
    bundle: SubmissionBundle = state["bundle"]
    bundle_id = state["bundle_id"]
    _log_state("build_provenance", state)
    _track_stage(bundle_id, "provenance")
    _log_event(bundle_id, PipelineEvent.PROVENANCE_CHECK, "build_provenance", "Building provenance records")

    engine = ProvenanceEngine()

    try:
        record = engine.build_provenance(bundle)
        _log_event(
            bundle_id,
            PipelineEvent.PROVENANCE_CHECK,
            "build_provenance",
            f"Provenance built: {record.record_count()} nodes",
        )
    except Exception as exc:
        logger.error("Provenance build failed: %s", exc)
        _log_event(
            bundle_id,
            PipelineEvent.PROVENANCE_CHECK,
            "build_provenance",
            f"Provenance failed: {exc}",
            severity=EventSeverity.ERROR,
        )
        record = None

    _finish_stage(bundle_id, "provenance")
    return {"provenance": record}


def reconcile(state: PipelineState) -> dict[str, Any]:
    provenance = state.get("provenance")
    bundle_id = state["bundle_id"]
    _log_state("reconcile", state)
    _track_stage(bundle_id, "reconcile")
    _log_event(bundle_id, PipelineEvent.RECONCILIATION_START, "reconcile", "Running reconciliation")

    if not provenance:
        _log_event(
            bundle_id,
            PipelineEvent.RECONCILIATION_COMPLETE,
            "reconcile",
            "No provenance to reconcile",
            severity=EventSeverity.WARNING,
        )
        return {"reconciliation": None, "human_review_needed": False}

    engine = ReconciliationEngine()

    try:
        result = engine.reconcile(provenance)
        _log_event(
            bundle_id,
            PipelineEvent.DISCREPANCY_DETECTED,
            "reconcile",
            f"Discrepancies: {len(result.discrepancies)}",
        )

        critical = any(d.severity.value == "critical" for d in result.discrepancies if hasattr(d.severity, "value"))
        human_review = critical

        _log_event(
            bundle_id,
            PipelineEvent.RECONCILIATION_COMPLETE,
            "reconcile",
            f"Match rate: {result.match_rate:.1%}, human_review={human_review}",
        )

        if human_review:
            _log_event(
                bundle_id,
                PipelineEvent.HUMAN_REVIEW_REQUIRED,
                "reconcile",
                "Critical discrepancies found",
            )

    except Exception as exc:
        logger.error("Reconciliation failed: %s", exc)
        _log_event(
            bundle_id,
            PipelineEvent.RECONCILIATION_COMPLETE,
            "reconcile",
            f"Reconciliation failed: {exc}",
            severity=EventSeverity.ERROR,
        )
        result = None
        human_review = True

    _finish_stage(bundle_id, "reconcile")
    return {
        "reconciliation": result,
        "human_review_needed": human_review,
    }


def check_human_review(state: PipelineState) -> str:
    if state.get("human_review_needed", False):
        _log_state("check_human_review → human_review", state)
        return "human_review"
    _log_state("check_human_review → query_rag", state)
    return "query_rag"


def query_rag(state: PipelineState) -> dict[str, Any]:
    bundle_id = state["bundle_id"]
    _log_state("query_rag", state)

    bundle = state.get("bundle")
    query_parts = []

    if bundle and bundle.structured and bundle.structured.risk_profile:
        rp = bundle.structured.risk_profile
        if rp.occupancy_type:
            query_parts.append(str(rp.occupancy_type))
        if rp.construction_type:
            query_parts.append(str(rp.construction_type))

    query = " ".join(query_parts) if query_parts else "general commercial property underwriting guidelines"
    _log_event(bundle_id, PipelineEvent.SYNTHESIS_START, "query_rag", f"Querying RAG for: '{query}'")

    from insureflow.agents.rag_agent import RAGAgent

    agent = RAGAgent()
    matches = agent.retrieve_guidelines(query)

    guidelines = ""
    if matches:
        guidelines = "\n\n".join(matches)
        _log_event(
            bundle_id,
            PipelineEvent.SYNTHESIS_START,
            "query_rag",
            f"Retrieved {len(matches)} hybrid RAG+KG context blocks",
        )

    return {"rag_context": guidelines}


def human_review(state: PipelineState) -> dict[str, Any]:
    bundle_id = state["bundle_id"]
    _log_state("human_review", state)
    _log_event(bundle_id, PipelineEvent.HUMAN_REVIEW_REQUIRED, "human_review", "Waiting for human review")

    reconciliation = state.get("reconciliation")
    reasons: list[str] = []
    if reconciliation and reconciliation.discrepancies:
        for d in reconciliation.discrepancies:
            if d.severity.value == "critical":
                reasons.append(f"[{d.field_path}] {d.description} (src_a={d.source_a}, src_b={d.source_b})")

    return {"human_review_reasons": reasons}


def synthesize(state: PipelineState) -> dict[str, Any]:
    bundle_id = state["bundle_id"]
    provenance = state.get("provenance")
    reconciliation = state.get("reconciliation")
    _log_state("synthesize", state)
    _track_stage(bundle_id, "synthesize")
    _log_event(bundle_id, PipelineEvent.SYNTHESIS_START, "synthesize", "Building synthesis output")

    if not reconciliation:
        from insureflow.models.audit import SynthesisOutput

        synthesis = SynthesisOutput(bundle_id=bundle_id)
        _log_event(
            bundle_id,
            PipelineEvent.SYNTHESIS_COMPLETE,
            "synthesize",
            "No reconciliation data for synthesis",
            severity=EventSeverity.WARNING,
        )
        return {"synthesis": synthesis}

    llm = LLMClient()

    from insureflow.agents.synthesis_agent import SynthesisAgent

    agent = SynthesisAgent(llm)

    try:
        from insureflow.models.provenance import ProvenanceRecord

        synthesis = agent.synthesize(
            cast(ProvenanceRecord, provenance),
            reconciliation,
        )
        _log_event(
            bundle_id,
            PipelineEvent.SYNTHESIS_COMPLETE,
            "synthesize",
            f"Synthesis done: {synthesis.discrepancies_found} discrepancies, human_review={synthesis.human_review_required}",
        )
    except Exception as exc:
        logger.error("Synthesis failed: %s", exc)
        from insureflow.models.audit import SynthesisOutput

        synthesis = SynthesisOutput(bundle_id=bundle_id)
        _log_event(
            bundle_id,
            PipelineEvent.SYNTHESIS_COMPLETE,
            "synthesize",
            f"Synthesis failed: {exc}",
            severity=EventSeverity.ERROR,
        )

    _finish_stage(bundle_id, "synthesize")
    return {"synthesis": synthesis}


def audit(state: PipelineState) -> dict[str, Any]:
    bundle_id = state["bundle_id"]
    _log_state("audit", state)
    _track_stage(bundle_id, "audit")

    audit_store = AuditStore()

    if state.get("bundle"):
        audit_store.persist_bundle(state["bundle"])
    if state.get("provenance"):
        audit_store.persist_provenance(state["provenance"])
    if state.get("reconciliation"):
        audit_store.persist_reconciliation(state["reconciliation"])
    if state.get("synthesis"):
        audit_store.persist_synthesis(state["synthesis"])

    _log_event(
        bundle_id,
        PipelineEvent.PIPELINE_COMPLETE,
        "graph_orchestrator",
        f"Pipeline complete. human_review={state.get('human_review_needed', False)}, errors={len(state.get('errors', []))}",
        severity=EventSeverity.INFO,
    )

    trail = _AUDIT_LOGGER.get_trail(bundle_id)
    if trail is None:
        trail = _AUDIT_LOGGER.create_trail(bundle_id)

    _AUDIT_LOGGER.complete_trail(bundle_id)
    audit_store.persist_audit_trail(trail)

    _finish_stage(bundle_id, "audit")
    m = _get_metrics()
    if m is not None:
        status = "completed" if not state.get("errors") else "failed"
        m.cycle_time.finish_pipeline(bundle_id, status=status)

    return {"audit_trail": trail}


def _log_state(node: str, state: PipelineState) -> None:
    logger.debug(
        "[Graph] Entering node '%s' (bundle_id=%s, retries=%d)",
        node,
        state.get("bundle_id", "?"),
        state.get("extraction_retries", 0),
    )


def _log_event(
    bundle_or_state: str | dict[str, Any],
    event: PipelineEvent,
    agent: str,
    message: str,
    severity: EventSeverity = EventSeverity.INFO,
) -> None:
    logger.debug("[Graph] %s: %s", event.value, message)

    if isinstance(bundle_or_state, dict):
        bundle_id = bundle_or_state.get("bundle_id", "")
        entries = bundle_or_state.setdefault("audit_entries", [])
        from insureflow.models.audit import AuditEntry

        try:
            entry = AuditEntry(
                entry_id=f"graph-{uuid4().hex[:8]}",
                bundle_id=bundle_id,
                event=event,
                severity=severity,
                agent_name=agent,
                message=message,
            )
            entries.append(entry.model_dump())
        except Exception:
            pass
    else:
        _AUDIT_LOGGER.log(
            bundle_or_state,
            event,
            agent_name=agent,
            message=message,
            severity=severity,
        )
