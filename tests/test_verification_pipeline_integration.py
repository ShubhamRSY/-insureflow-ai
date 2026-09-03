from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.audit.store import AuditStore
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import get_user_store
from insureflow.config import settings
from insureflow.insurance.pipeline import InsurancePipeline
from insureflow.models.submissions import (
    SubmissionBundle,
    UnstructuredSubmission,
    VerificationIssue,
    VerificationReport,
)
from insureflow.verification.aggregate import (
    aggregate_verification,
    exception_queue_for,
    flagged_submissions,
    verification_findings,
)


def _doc(
    submission_id: str,
    *,
    issues: list[VerificationIssue] | None = None,
    auto_approve: bool = True,
    flagged: bool = False,
) -> UnstructuredSubmission:
    return UnstructuredSubmission(
        submission_id=submission_id,
        source="loss_run",
        document_type="loss_run",
        raw_text="sample text",
        verification=VerificationReport(
            passed=not flagged,
            auto_approve=auto_approve,
            flagged_for_review=flagged,
            checks_run=["balance_sheet", "sum_to_total", "range_checks"],
            issues=issues or [],
        ),
    )


class TestVerificationAggregate:
    def test_rollup_mixed_bundle(self) -> None:
        error_issue = VerificationIssue(
            code="sum_to_total",
            severity="error",
            message="Total premium 1,250 does not equal the sum of the policy lines (1,100)",
            field_name="premium.total",
            page_number=2,
            bbox=[0.1, 0.2, 0.5, 0.3],
        )
        bundle = SubmissionBundle(
            bundle_id="b1",
            structured=None,
            unstructured=[
                _doc("clean-1"),
                _doc("flagged-1", issues=[error_issue], auto_approve=False, flagged=True),
            ],
        )
        summary = aggregate_verification(bundle)

        assert summary["checked_docs"] == 2
        assert summary["flagged_doc_count"] == 1
        assert summary["flagged_docs"][0]["submission_id"] == "flagged-1"
        assert summary["exception_count"] == 1
        assert summary["issues_by_code"] == {"sum_to_total": 1}
        assert summary["error_count"] == 1
        assert summary["warning_count"] == 0
        assert summary["auto_approve"] is False
        assert summary["straight_through_processing"] is False

    def test_clean_bundle_auto_approves(self) -> None:
        bundle = SubmissionBundle(
            bundle_id="b2",
            structured=None,
            unstructured=[_doc("a"), _doc("b")],
        )
        summary = aggregate_verification(bundle)
        assert summary["checked_docs"] == 2
        assert summary["flagged_doc_count"] == 0
        assert summary["exception_count"] == 0
        assert summary["auto_approve"] is True
        assert summary["straight_through_processing"] is True

    def test_exception_queue_entry_carries_source_box(self) -> None:
        issue = VerificationIssue(
            code="aba_checksum",
            severity="warning",
            message="Routing number fails mod-10 checksum",
            field_name="bank.routing_number",
            page_number=3,
            bbox=[0.0, 0.1, 0.4, 0.2],
        )
        doc = _doc("pay-1", issues=[issue], auto_approve=False, flagged=True)
        entry = exception_queue_for(doc)[0]
        assert entry["page_number"] == 3
        assert entry["bbox"] == [0.0, 0.1, 0.4, 0.2]
        assert entry["field_name"] == "bank.routing_number"
        assert entry["severity"] == "warning"

    def test_flagged_submissions_and_findings(self) -> None:
        err = VerificationIssue(code="range_checks", severity="error", message="TIV out of range")
        bundle = SubmissionBundle(
            bundle_id="b3",
            structured=None,
            unstructured=[_doc("ok"), _doc("bad", issues=[err], auto_approve=False, flagged=True)],
        )
        assert [d.submission_id for d in flagged_submissions(bundle)] == ["bad"]

        findings = verification_findings(bundle)
        assert len(findings) == 1
        assert findings[0]["severity"] == "high"
        assert findings[0]["category"] == "data_quality"
        assert findings[0]["evidence"] == ["bad"]

    def test_aggregate_empty_bundle(self) -> None:
        summary = aggregate_verification(SubmissionBundle(bundle_id="b0", structured=None, unstructured=[]))
        assert summary["checked_docs"] == 0
        assert summary["straight_through_processing"] is False


class TestVerificationPipelineWiring:
    @pytest.fixture
    def audit_store(self, tmp_path: Path) -> AuditStore:
        return AuditStore(base_path=tmp_path / "audit")

    def test_pipeline_result_includes_verification(self, audit_store: AuditStore) -> None:
        result = InsurancePipeline(org_id="test", use_llm=False, audit_store=audit_store).run(
            documents=[
                {
                    "filename": "loss_run.txt",
                    "content": "Loss Run\nPremium 12,500\nTotal 12,500",
                    "encoding": "utf-8",
                }
            ],
            bundle_id="verif-integration-clean",
        )
        assert result["status"] == "completed"
        assert "verification" in result
        assert result["verification"]["checked_docs"] >= 1
        assert result["verification"]["straight_through_processing"] in (True, False)

    def test_pipeline_flags_flagged_verification(self, audit_store: AuditStore, monkeypatch: pytest.MonkeyPatch) -> None:
        from insureflow.verification import engine as verification_engine
        from insureflow.verification.engine import VerificationEngine

        def fake_run(self, fields, raw_text="", document_type="", spatial_lines=None, pdf_bytes=None, markdown=None):
            return VerificationReport(
                passed=False,
                auto_approve=False,
                flagged_for_review=True,
                checks_run=["balance_sheet", "sum_to_total"],
                issues=[
                    VerificationIssue(
                        code="sum_to_total",
                        severity="error",
                        message="Column totals do not reconcile",
                        field_name="premium.total",
                        page_number=1,
                        bbox=[0.1, 0.2, 0.5, 0.3],
                    )
                ],
            )

        monkeypatch.setattr(verification_engine, "verification_enabled", lambda: True)
        monkeypatch.setattr(VerificationEngine, "run", fake_run)

        result = InsurancePipeline(org_id="test", use_llm=False, audit_store=audit_store).run(
            documents=[
                {
                    "filename": "financial.txt",
                    "content": "Balance Sheet\nAssets 1000\nLiabilities 500",
                    "encoding": "utf-8",
                }
            ],
            bundle_id="verif-integration-flagged",
        )
        assert result["status"] == "completed"
        assert result["verification"]["checked_docs"] >= 1
        assert result["verification"]["flagged_doc_count"] >= 1
        assert result["verification"]["exception_count"] >= 1


class TestVerificationAPI:
    @pytest.fixture(autouse=True)
    def redirect_audit_log(self, tmp_path: Path) -> Iterator[None]:
        original = settings.audit_log_path
        object.__setattr__(settings, "audit_log_path", tmp_path)
        yield
        object.__setattr__(settings, "audit_log_path", original)

    def _headers(self, role: Role = Role.VIEWER, org_id: str = "acme") -> tuple[dict[str, str], str]:
        """Returns (auth headers, resolved org_id).

        A Postgres-backed user store (real multi-tenancy) resolves an
        org_id like "acme" as an org NAME to its canonical UUID on write —
        callers that need the org_id a saved record will actually be
        scoped under (e.g. to save an audit record under the same org the
        request will read it back from) must use the resolved value, not
        the literal string, or the two diverge in a Postgres-backed
        environment even though they'd trivially match in file-backed mode.
        """
        store = get_user_store()
        store["uw"] = User(username="uw", hashed_password="x", role=role, org_id=org_id)
        resolved_org_id = store.get("uw").org_id
        token = create_access_token({"sub": "uw", "role": role.value, "org_id": resolved_org_id})
        return {"Authorization": f"Bearer {token}"}, resolved_org_id

    def test_endpoint_returns_persisted_report(self, tmp_path: Path) -> None:
        headers, resolved_org_id = self._headers(Role.VIEWER)
        report = aggregate_verification(
            SubmissionBundle(
                bundle_id="endpoint-b1",
                structured=None,
                unstructured=[_doc("f", issues=[VerificationIssue(code="pattern_checks", severity="error", message="Bad EIN")], auto_approve=False, flagged=True)],
            )
        )
        store = AuditStore()
        store.save_json("endpoint-b1", "verification.json", report, org_id=resolved_org_id)

        client = TestClient(app)
        resp = client.get("/verification/endpoint-b1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["bundle_id"] == "endpoint-b1"
        assert data["review_required"] is True
        assert data["report"]["flagged_doc_count"] == 1
        assert data["report"]["exception_queue"][0]["code"] == "pattern_checks"

    def test_endpoint_404_when_no_verification(self) -> None:
        client = TestClient(app)
        headers, _resolved_org_id = self._headers(Role.VIEWER)
        resp = client.get("/verification/does-not-exist", headers=headers)
        assert resp.status_code == 404
