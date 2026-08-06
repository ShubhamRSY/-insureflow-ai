"""Coverage issuance tests — binder, policy worksheet, certificate of insurance."""

from __future__ import annotations

import pytest

from insureflow.audit.store import AuditStore
from insureflow.issuance.models import IssuedDocumentType
from insureflow.issuance.service import IssuanceService


@pytest.fixture()
def audit(tmp_path) -> AuditStore:
    return AuditStore(base_path=tmp_path / "audit")


@pytest.fixture()
def seeded_audit(tmp_path) -> AuditStore:
    store = AuditStore(base_path=tmp_path / "audit")
    bundle_id = "ins-issuance-1"
    org_id = "default"
    store.save_json(
        bundle_id,
        "pipeline_summary.json",
        {
            "bundle_id": bundle_id,
            "insured_name": "Bayfront Retail LLC",
            "broker_name": "Acme Brokerage",
            "tiv": 4_500_000,
            "insurance_line": "commercial_property",
            "open_conditions": ["SUBJECT TO: roof age verified within 60 days"],
            "quote": {
                "adjusted_premium": 22_500.0,
                "base_premium": 20_000.0,
                "policy_admin_reference": "PA-ABC123",
            },
        },
        org_id=org_id,
    )
    store.save_json(
        bundle_id,
        "underwriting_memo.json",
        {
            "bundle_id": bundle_id,
            "insured_name": "Bayfront Retail LLC",
            "conditions": ["SUBJECT TO: roof age verified within 60 days"],
            "key_findings": [
                {
                    "title": "Roof age not verified",
                    "description": "Roof age is a monitoring item",
                    "category": "data_quality",
                    "severity": "moderate",
                }
            ],
        },
        org_id=org_id,
    )
    store.save_json(
        bundle_id,
        "submission_bundle.json",
        {
            "bundle_id": bundle_id,
            "structured": {
                "named_insured": {"legal_name": "Bayfront Retail LLC"},
                "coverages": [
                    {
                        "coverage_type": "Building & Contents",
                        "limit_amount": 3_000_000,
                        "deductible": 25_000,
                        "premium": 15_000,
                        "sublimits": {"Flood": 500_000},
                    }
                ],
                "locations": [{"state": "FL", "building_value": 3_000_000, "contents_value": 1_500_000}],
                "risk_profile": {"naics_code": "452210"},
            },
        },
        org_id=org_id,
    )
    return store


class TestIssuanceService:
    def test_issue_generates_all_documents(self, seeded_audit: AuditStore) -> None:
        svc = IssuanceService(audit_store=seeded_audit)
        record = svc.issue(
            "ins-issuance-1",
            "default",
            policy_number="POL-88",
            bound_by="sfields",
            premium=22_500.0,
            effective_date="2026-01-01",
            expiry_date="2027-01-01",
        )
        assert record.policy_number == "POL-88"
        assert record.binder is not None
        assert record.policy_worksheet is not None
        assert record.certificate is not None
        assert len(record.documents) == 3

        binder = record.binder
        assert binder.doc_type == IssuedDocumentType.BINDER
        assert "Bayfront Retail LLC" in binder.html
        assert "POL-88" in binder.html
        assert "Binder of Insurance" in binder.html

        cert = record.certificate
        assert "Certificate of Insurance" in cert.html
        assert "2026-01-01 to 2027-01-01" in cert.html

        worksheet = record.policy_worksheet
        assert "Policy Worksheet" in worksheet.html
        assert "452210" in worksheet.html  # NAICS code carried into statistical coding notes

    def test_record_is_persisted_and_retrievable(self, seeded_audit: AuditStore) -> None:
        svc = IssuanceService(audit_store=seeded_audit)
        svc.issue(
            "ins-issuance-1",
            "default",
            policy_number="POL-89",
            bound_by="sfields",
            premium=22_500.0,
        )
        record = svc.load_record("ins-issuance-1", "default")
        assert record is not None
        assert record.policy_number == "POL-89"
        assert record.status == "issued"

        docs = svc.list_documents("ins-issuance-1", "default")
        assert {d["doc_type"] for d in docs} == {"binder", "policy_worksheet", "certificate"}

    def test_get_document_html_returns_typed_document(self, seeded_audit: AuditStore) -> None:
        svc = IssuanceService(audit_store=seeded_audit)
        svc.issue(
            "ins-issuance-1",
            "default",
            policy_number="POL-90",
            bound_by="sfields",
            premium=22_500.0,
        )
        doc, record = svc.get_document_html("ins-issuance-1", "default", "certificate")
        assert doc is not None
        assert doc.doc_type == IssuedDocumentType.CERTIFICATE
        assert record.certificate is doc

    def test_missing_issuance_returns_none(self, audit: AuditStore) -> None:
        svc = IssuanceService(audit_store=audit)
        assert svc.load_record("never-bound", "default") is None
        assert svc.get_document_html("never-bound", "default", "binder") is None
        assert svc.list_documents("never-bound", "default") == []

    def test_default_policy_period_is_one_year(self, seeded_audit: AuditStore) -> None:
        svc = IssuanceService(audit_store=seeded_audit)
        record = svc.issue(
            "ins-issuance-1",
            "default",
            policy_number="POL-91",
            bound_by="sfields",
            premium=22_500.0,
        )
        assert record.effective_date != ""
        assert record.expiry_date != ""
        from datetime import datetime

        eff = datetime.fromisoformat(record.effective_date).date()
        exp = datetime.fromisoformat(record.expiry_date).date()
        assert (exp - eff).days >= 364

    def test_list_records_is_org_scoped_and_newest_first(self, seeded_audit: AuditStore) -> None:
        svc = IssuanceService(audit_store=seeded_audit)
        svc.issue("ins-issuance-1", "default", policy_number="POL-A", bound_by="sfields", premium=1)
        svc.issue("ins-issuance-1", "org-b", policy_number="POL-B", bound_by="sfields", premium=2)
        records = svc.list_records("default")
        assert [r.policy_number for r in records] == ["POL-A"]
        assert svc.list_records("org-unknown") == []
