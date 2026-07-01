from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from insureflow.agents.mortgage.supervisor import MortgageSupervisorAgent
from insureflow.analytics.documents import DocumentAnalyticsEngine
from insureflow.audit.store import AuditStore
from insureflow.ingestion.mortgage.loader import MortgageSubmissionLoader
from insureflow.models.audit import PipelineEvent
from insureflow.models.mortgage import (
    MortgageBundle,
    MortgageBundleStatus,
    MortgageMemo,
    ProductLine,
)
from insureflow.mortgage.audit import MortgageAuditLogger
from insureflow.mortgage.bundler import discover_borrower_packages
from insureflow.mortgage.compliance import MortgageComplianceEngine
from insureflow.mortgage.pricing import LoanPricingEngine, LoanProduct
from insureflow.mortgage.reconciliation import MortgageReconciliationEngine
from insureflow.mortgage.webhooks import webhook_dispatcher
from insureflow.storage.encryption import EnvelopeEncryption


class MortgagePipeline:
    """End-to-end mortgage document processing pipeline for bank underwriting."""

    def __init__(
        self,
        use_llm: bool = True,
        audit_store: AuditStore | None = None,
        org_id: str = "default",
    ) -> None:
        self.use_llm = use_llm
        self.org_id = org_id
        self.loader = MortgageSubmissionLoader(use_llm=use_llm)
        self.reconciliation = MortgageReconciliationEngine()
        self.compliance = MortgageComplianceEngine()
        self.pricing = LoanPricingEngine()
        self.supervisor = MortgageSupervisorAgent()
        self.audit_store = audit_store or AuditStore()
        self.encryption = EnvelopeEncryption()

    def run_from_directory(
        self,
        directory: str,
        bundle_id: str | None = None,
        product_line: ProductLine | None = None,
        loan_product: str | None = None,
        loan_amount: float | None = None,
    ) -> dict[str, Any]:
        bid = bundle_id or f"mortgage-{uuid4().hex[:12]}"
        inferred = product_line or self._infer_product_line(directory)
        documents = self.loader.load_from_directory(directory, bundle_id=bid, product_line=inferred)
        return self.run_documents(
            documents, bundle_id=bid, product_line=inferred,
            loan_product=loan_product, loan_amount=loan_amount,
        )

    def run_from_paths(
        self,
        paths: list[str],
        bundle_id: str | None = None,
        product_line: ProductLine | None = None,
        borrower_id: str | None = None,
        loan_product: str | None = None,
        loan_amount: float | None = None,
    ) -> dict[str, Any]:
        bid = bundle_id or f"mortgage-{uuid4().hex[:12]}"
        inferred = product_line or (self._infer_product_line(paths[0]) if paths else ProductLine.RESIDENTIAL_MORTGAGE)
        documents = self.loader.load_from_paths(paths, bundle_id=bid, product_line=inferred)
        return self.run_documents(
            documents, bundle_id=bid, product_line=inferred, borrower_id=borrower_id,
            loan_product=loan_product, loan_amount=loan_amount,
        )

    def run_from_texts(
        self,
        documents: list[dict[str, str]],
        bundle_id: str | None = None,
        product_line: ProductLine = ProductLine.RESIDENTIAL_MORTGAGE,
        borrower_id: str | None = None,
        loan_product: str | None = None,
        loan_amount: float | None = None,
    ) -> dict[str, Any]:
        bid = bundle_id or f"mortgage-{uuid4().hex[:12]}"
        loaded = self.loader.load_from_texts(documents, bundle_id=bid, product_line=product_line)
        return self.run_documents(
            loaded, bundle_id=bid, product_line=product_line, borrower_id=borrower_id,
            loan_product=loan_product, loan_amount=loan_amount,
        )

    def run_per_borrower(
        self,
        directory: str,
        product_line: ProductLine | None = None,
    ) -> dict[str, Any]:
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

        batch_result = {
            "status": "completed",
            "batch_id": batch_id,
            "org_id": self.org_id,
            "borrower_count": len(results),
            "packages": results,
        }
        webhook_dispatcher.dispatch("mortgage.batch.completed", self.org_id, batch_result)
        return batch_result

    def run_documents(
        self,
        documents: list,
        bundle_id: str,
        product_line: ProductLine,
        borrower_id: str | None = None,
        loan_product: str | None = None,
        loan_amount: float | None = None,
    ) -> dict[str, Any]:
        audit = MortgageAuditLogger(self.audit_store, self.encryption)
        audit.start(bundle_id)

        audit.log(
            PipelineEvent.STRUCTURED_PARSE_START,
            f"Parsing {len(documents)} mortgage documents (LLM={'on' if self.use_llm else 'off'})",
            metadata={"use_llm": self.use_llm, "borrower_id": borrower_id, "org_id": self.org_id},
        )

        llm_doc_count = sum(
            1 for d in documents
            if any(
                f.field_name == "extraction_method" and "llm" in f.value
                for f in d.extracted_fields.get("extraction_method", [])
            )
        )
        ocr_doc_count = sum(
            1 for d in documents
            if d.extracted_fields.get("ocr_engine")
        )

        if llm_doc_count:
            audit.log(PipelineEvent.EXTRACTION_COMPLETE, f"LLM extraction on {llm_doc_count} document(s)")
        if ocr_doc_count:
            audit.log(PipelineEvent.EXTRACTION_COMPLETE, f"OCR extraction on {ocr_doc_count} document(s)")

        audit.log(PipelineEvent.STRUCTURED_PARSE_COMPLETE, f"Classified and extracted {len(documents)} documents")

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

        product_enum = LoanProduct(loan_product) if loan_product else None
        rate_quote = self.pricing.quote(bundle, memo, loan_amount=loan_amount, product=product_enum)

        dti_ratio = memo.dti_ratio
        if bundle.income and bundle.credit and rate_quote.monthly_pi:
            monthly_income = (bundle.income.adjusted_gross_income or bundle.income.total_income) / 12
            if monthly_income > 0:
                total_debt = bundle.credit.total_monthly_payment + rate_quote.monthly_pi
                dti_ratio = round(total_debt / monthly_income * 100, 1)

        type_counts: dict[str, int] = {}
        for doc in documents:
            key = doc.document_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        summary = {
            "status": "completed",
            "bundle_id": bundle_id,
            "org_id": self.org_id,
            "borrower_id": borrower_id,
            "product_line": product_line.value,
            "document_count": len(documents),
            "document_types": type_counts,
            "llm_enhanced_documents": llm_doc_count,
            "ocr_documents": ocr_doc_count,
            "borrower": memo.borrower_name,
            "decision": memo.decision.value,
            "risk_score": memo.risk_score,
            "dti_ratio": dti_ratio,
            "ltv_ratio": memo.ltv_ratio,
            "human_review_required": memo.human_review_required,
            "rate_quote": {
                "product": rate_quote.product.value,
                "adjusted_rate": rate_quote.adjusted_rate,
                "rate_lock_expires": rate_quote.rate_lock_expires,
                "monthly_pi": rate_quote.monthly_pi,
                "pmi_required": rate_quote.pmi_required,
                "eligible": rate_quote.eligible,
                "ineligibility_reasons": rate_quote.ineligibility_reasons,
                "adjustments": rate_quote.pricing_adjustments,
            },
            "encryption_at_rest": self.encryption.enabled,
        }

        doc_analytics = DocumentAnalyticsEngine()
        doc_analytics.record(
            bundle_id=bundle_id,
            document_count=len(documents),
            vertical="mortgage",
            unstructured_count=len(documents),
            human_review_required=memo.human_review_required,
            decision=memo.decision.value,
            org_id=self.org_id,
        )

        audit_paths = audit.persist(bundle, memo, extra=summary)

        result = {
            **summary,
            "memo": memo.model_dump(),
            "reconciliation_issues": [i.model_dump() for i in bundle.reconciliation_issues],
            "compliance_violations": [v.model_dump() for v in bundle.compliance_violations],
            "audit_trail_entries": len(audit.trail.entries) if audit.trail else 0,
            "audit_paths": audit_paths,
        }

        webhook_dispatcher.dispatch("mortgage.completed", self.org_id, result)
        return result

    @staticmethod
    def _infer_product_line(path: str) -> ProductLine:
        if "commercial_mortgage" in path.lower():
            return ProductLine.COMMERCIAL_MORTGAGE
        return ProductLine.RESIDENTIAL_MORTGAGE
