"""Issuance service — puts approved coverage into effect (Step 5b).

Generates and persists the binder, policy worksheet, and certificate of
insurance for a bound policy, and records the issuance package on the
workflow so it can be downloaded or re-issued later.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from insureflow.audit.store import AuditStore
from insureflow.issuance.documents import build_issuance_context, generate_binder_html, generate_certificate_html, generate_policy_worksheet_html
from insureflow.issuance.models import IssuanceRecord, IssuedDocument, IssuedDocumentType
from insureflow.workflow.store import WorkflowStore


class IssuanceService:
    """Create and retrieve coverage-in-effect documents for a bound policy."""

    ISSUANCE_FILE = "issuance.json"

    def __init__(self, audit_store: AuditStore | None = None, workflow_store: WorkflowStore | None = None) -> None:
        self.audit = audit_store or AuditStore()
        self.workflows = workflow_store or WorkflowStore()

    def load_record(self, bundle_id: str, org_id: str) -> IssuanceRecord | None:
        raw = self.audit.load_json(bundle_id, self.ISSUANCE_FILE, org_id=org_id)
        if not raw:
            return None
        try:
            return IssuanceRecord.model_validate(raw)
        except Exception:
            return None

    def list_records(self, org_id: str) -> list[IssuanceRecord]:
        """All issuance packages issued for an org, newest first."""
        base = self.audit.base_path / org_id
        if not base.is_dir():
            return []
        records: list[IssuanceRecord] = []
        for bundle_dir in sorted(base.iterdir()):
            if not bundle_dir.is_dir():
                continue
            raw = self.audit.load_json(bundle_dir.name, self.ISSUANCE_FILE, org_id=org_id)
            if not raw:
                continue
            try:
                records.append(IssuanceRecord.model_validate(raw))
            except Exception:
                continue
        records.sort(key=lambda r: r.bound_at, reverse=True)
        return records

    def issue(
        self,
        bundle_id: str,
        org_id: str,
        *,
        policy_number: str,
        bound_by: str,
        premium: float,
        effective_date: str = "",
        expiry_date: str = "",
        certificate_holder: str = "",
        policy_admin_reference: str = "",
    ) -> IssuanceRecord:
        """Generate all issuance documents for a bound policy and persist them."""
        summary = self.audit.load_json(bundle_id, "pipeline_summary.json", org_id=org_id) or {}
        memo = self.audit.load_json(bundle_id, "underwriting_memo.json", org_id=org_id) or {}
        bundle = self.audit.load_json(bundle_id, "submission_bundle.json", org_id=org_id)

        now = datetime.now(tz=timezone.utc)
        eff = effective_date or now.strftime("%Y-%m-%d")
        exp = expiry_date or (now + timedelta(days=365)).strftime("%Y-%m-%d")

        policy = {
            "policy_number": policy_number,
            "bound_by": bound_by,
            "bound_at": now.strftime("%Y-%m-%d"),
            "premium": float(premium or 0),
            "effective_date": eff,
            "expiry_date": exp,
            "certificate_holder": certificate_holder,
            "policy_admin_reference": policy_admin_reference,
        }
        ctx = build_issuance_context(summary, memo, bundle, policy)

        docs = [
            IssuedDocument(
                doc_id=f"doc-{uuid4().hex[:10]}",
                doc_type=IssuedDocumentType.BINDER,
                title="Binder of Insurance",
                filename=f"Binder_{policy_number or bundle_id}.html",
                html=generate_binder_html(ctx),
            ),
            IssuedDocument(
                doc_id=f"doc-{uuid4().hex[:10]}",
                doc_type=IssuedDocumentType.POLICY_WORKSHEET,
                title="Policy Worksheet",
                filename=f"PolicyWorksheet_{policy_number or bundle_id}.html",
                html=generate_policy_worksheet_html(ctx),
            ),
            IssuedDocument(
                doc_id=f"doc-{uuid4().hex[:10]}",
                doc_type=IssuedDocumentType.CERTIFICATE,
                title="Certificate of Insurance",
                filename=f"Certificate_{policy_number or bundle_id}.html",
                html=generate_certificate_html(ctx),
            ),
        ]

        record = IssuanceRecord(
            issuance_id=f"iss-{uuid4().hex[:10]}",
            bundle_id=bundle_id,
            org_id=org_id,
            policy_number=policy_number,
            insured_name=ctx.get("insured_name") or "",
            broker_name=ctx.get("broker_name") or "",
            line_of_business=ctx.get("line_of_business") or "",
            premium=float(premium or 0),
            tiv=float(ctx.get("tiv") or 0),
            effective_date=eff,
            expiry_date=exp,
            bound_by=bound_by,
            bound_at=now,
            status="issued",
            documents=docs,
        )

        self.audit.save_json(bundle_id, self.ISSUANCE_FILE, record.model_dump(mode="json"), org_id=org_id)

        try:
            record_meta = self.workflows.get(bundle_id, org_id)
            if record_meta:
                record_meta.metadata["issuance"] = {
                    "issuance_id": record.issuance_id,
                    "policy_number": policy_number,
                    "effective_date": eff,
                    "expiry_date": exp,
                    "documents": [d.model_dump(mode="json") for d in docs],
                }
                self.workflows.save(record_meta)
        except Exception:
            pass

        return record

    def get_document_html(self, bundle_id: str, org_id: str, doc_type: str) -> tuple[IssuedDocument, IssuanceRecord] | None:
        record = self.load_record(bundle_id, org_id)
        if not record:
            return None
        try:
            dt = IssuedDocumentType(doc_type)
        except ValueError:
            return None
        doc = next((d for d in record.documents if d.doc_type == dt), None)
        if doc is None:
            return None
        return doc, record

    def list_documents(self, bundle_id: str, org_id: str) -> list[dict[str, Any]]:
        record = self.load_record(bundle_id, org_id)
        if not record:
            return []
        return [
            {
                "doc_type": d.doc_type.value,
                "title": d.title,
                "filename": d.filename,
                "generated_at": d.generated_at.isoformat(),
                "content_type": d.content_type,
            }
            for d in record.documents
        ]
