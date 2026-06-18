from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from insureflow.agents.mortgage.supervisor import MortgageSupervisorAgent
from insureflow.audit.store import AuditStore
from insureflow.ingestion.mortgage.loader import MortgageSubmissionLoader
from insureflow.models.audit import EventSeverity, PipelineEvent
from insureflow.models.mortgage import (
    MortgageBundle,
    MortgageBundleStatus,
    MortgageMemo,
    ProductLine,
)
from insureflow.mortgage.audit import MortgageAuditLogger
from insureflow.mortgage.bundler import BorrowerPackage, discover_borrower_packages
from insureflow.mortgage.compliance import MortgageComplianceEngine
from insureflow.mortgage.reconciliation import MortgageReconciliationEngine
from insureflow.redaction.redactor import PIIRedactor


class MortgagePipeline:
    """End-to-end mortgage document processing pipeline for bank underwriting."""

    def __init__(
        self,
        use_llm: bool = True,
        audit_store: AuditStore | None = None,
    ) -> None:
        self.use_llm = use_llm
        self.loader = MortgageSubmissionLoader(use_llm=use_llm)
        self.reconciliation = MortgageReconciliationEngine()
        self.compliance = MortgageComplianceEngine()
        self.supervisor = MortgageSupervisorAgent()
        self.audit_store = audit_store or AuditStore()

    def run_from_directory(
        self,
        directory: str,
        bundle_id: str | None = None,
        product_line: ProductLine | None = None,
    ) -> dict[str, Any]:
        bid = bundle_id or f"mortgage-{uuid4().hex[:12]}"
        inferred = product_line or self._infer_product_line(directory)
        documents = self.loader.load_from_directory(directory, bundle_id=bid, product_line=inferred)
        return self.run_documents(documents, bundle_id=bid, product_line=inferred)

    def run_from_paths(
        self,
        paths: list[str],
        bundle_id: str | None = None,
        product_line: ProductLine | None = None,
        borrower_id: str | None = None,
    ) -> dict[str, Any]:
        bid = bundle_id or f"mortgage-{uuid4().hex[:12]}"
        inferred = product_line or (self._infer_product_line(paths[0]) if paths else ProductLine.RESIDENTIAL_MORTGAGE)
        documents = self.loader.load_from_paths(paths, bundle_id=bid, product_line=inferred)
        return self.run_documents(
            documents, bundle_id=bid, product_line=inferred, borrower_id=borrower_id
        )

    def run_from_texts(
        self,
        documents: list[dict[str, str]],
        bundle_id: str | None = None,
        product_line: ProductLine = ProductLine.RESIDENTIAL_MORTGAGE,
        borrower_id: str | None = None,
    ) -> dict[str, Any]:
        bid = bundle_id or f"mortgage-{uuid4().hex[:12]}"
        loaded = self.loader.load_from_texts(documents, bundle_id=bid, product_line=product_line)
        return self.run_documents(
            loaded, bundle_id=bid, product_line=product_line, borrower_id=borrower_id
        )

    def run_per_borrower(
        self,
        directory: str,
        product_line: ProductLine | None = None,
    ) -> dict[str, Any]:
        """Process each borrower package separately (John vs Maria vs Chen, etc.)."""
        packages = discover_borrower_packages(directory, product_line=product_line)
        batch_id = f"batch-{uuid4().hex[:12]}"
        results: list[dict[str, Any]] = []

        for pkg in packages:
            bid = f"{batch_id}-{pkg.borrower_id}"
            result = self.run_from_paths(
                pkg.paths,
                bundle_id=bid,
                product_line=pkg.product_line,
                borrower_id=pkg.borrower_id,
            )
            result["borrower_id"] = pkg.borrower_id
            result["borrower_display_name"] = pkg.display_name
            results.append(result)

        return {
            "status": "completed",
            "batch_id": batch_id,
            "borrower_count": len(results),
            "packages": results,
        }

    def run_documents(
        self,
        documents: list,
        bundle_id: str,
        product_line: ProductLine,
        borrower_id: str | None = None,
    ) -> dict[str, Any]:
        audit = MortgageAuditLogger(self.audit_store)
        audit.start(bundle_id)

        audit.log(
            PipelineEvent.STRUCTURED_PARSE_START,
            f"Parsing {len(documents)} mortgage documents (LLM={'on' if self.use_llm else 'off'})",
            metadata={"use_llm": self.use_llm, "borrower_id": borrower_id},
        )

        llm_doc_count = sum(
            1 for d in documents
            if any(f.field_name == "extraction_method" and f.value == "regex+llm"
                   for f in d.extracted_fields.get("extraction_method", []))
        )
        if llm_doc_count:
            audit.log(
                PipelineEvent.EXTRACTION_COMPLETE,
                f"LLM extraction applied to {llm_doc_count} document(s)",
                metadata={"llm_documents": llm_doc_count},
            )

        audit.log(PipelineEvent.STRUCTURED_PARSE_COMPLETE, f"Classified and extracted {len(documents)} documents")

        redactor = PIIRedactor()
        redacted_count = 0
        for doc in documents:
            if doc.raw_text:
                redacted = redactor.redact(doc.raw_text)
                if redacted != doc.raw_text:
                    doc.raw_text = redacted
                    redacted_count += 1
        if redacted_count:
            audit.log(
                PipelineEvent.PROVENANCE_CHECK,
                f"PII redacted in {redacted_count} document(s)",
                metadata={"redacted_count": redacted_count},
            )

        bundle = MortgageBundle(
            bundle_id=bundle_id,
            product_line=product_line,
            documents=documents,
            status=MortgageBundleStatus.PARSED,
        )

        audit.log(PipelineEvent.RECONCILIATION_START, "Building summaries and cross-document reconciliation")
        self.reconciliation.build_summaries(bundle)
        self.reconciliation.reconcile(bundle)
        audit.log(
            PipelineEvent.RECONCILIATION_COMPLETE,
            f"Reconciliation complete: {len(bundle.reconciliation_issues)} issue(s)",
        )

        audit.log(PipelineEvent.PROVENANCE_CHECK, "Running bank compliance rules")
        self.compliance.evaluate(bundle)

        memo = self.supervisor.analyze(bundle)
        bundle.status = MortgageBundleStatus.COMPLETED

        type_counts: dict[str, int] = {}
        for doc in documents:
            key = doc.document_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        summary = {
            "status": "completed",
            "bundle_id": bundle_id,
            "borrower_id": borrower_id,
            "product_line": product_line.value,
            "document_count": len(documents),
            "document_types": type_counts,
            "llm_enhanced_documents": llm_doc_count,
            "borrower": memo.borrower_name,
            "decision": memo.decision.value,
            "risk_score": memo.risk_score,
            "dti_ratio": memo.dti_ratio,
            "ltv_ratio": memo.ltv_ratio,
            "human_review_required": memo.human_review_required,
        }

        audit_paths = audit.persist(bundle, memo, extra=summary)

        return {
            **summary,
            "memo": memo.model_dump(),
            "reconciliation_issues": [i.model_dump() for i in bundle.reconciliation_issues],
            "compliance_violations": [v.model_dump() for v in bundle.compliance_violations],
            "audit_trail_entries": len(audit.trail.entries) if audit.trail else 0,
            "audit_paths": audit_paths,
        }

    @staticmethod
    def _infer_product_line(path: str) -> ProductLine:
        if "commercial_mortgage" in path.lower():
            return ProductLine.COMMERCIAL_MORTGAGE
        return ProductLine.RESIDENTIAL_MORTGAGE
