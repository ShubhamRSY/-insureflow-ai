from __future__ import annotations

from pathlib import Path

from insureflow.audit.store import AuditStore
from insureflow.ingestion.insurance.classifier import InsuranceDocumentClassifier, InsuranceDocumentType
from insureflow.insurance.collaboration import CollaborationStore
from insureflow.insurance.package_checklist import detect_lob, package_checklist


def test_do_classifier_types() -> None:
    assert InsuranceDocumentClassifier.classify("Directors and Officers Application", "do_application.txt") == InsuranceDocumentType.DO_APPLICATION
    assert InsuranceDocumentClassifier.classify("D&O Questionnaire for management liability", "do_questionnaire.md") == InsuranceDocumentType.DO_QUESTIONNAIRE
    assert InsuranceDocumentClassifier.classify("Corporate Bylaws", "bylaws.pdf") == InsuranceDocumentType.DO_BYLAWS_CHARTER


def test_package_checklist_do_vs_property() -> None:
    prop = package_checklist(["acord_xml", "loss_run"], lob="property")
    assert "ACORD application (125 / 140)" in prop["present"]
    assert prop["completeness_pct"] < 100
    do = package_checklist(["do_application", "do_questionnaire", "do_bylaws_charter"], lob="do")
    assert do["lob"] == "do"
    assert "D&O application" in do["present"]
    assert detect_lob("Directors & Officers liability") == "do"


def test_collaboration_info_request_loop(tmp_path: Path) -> None:
    store = CollaborationStore(AuditStore(base_path=tmp_path / "audit"))
    req = store.add_info_request("b1", "org1", ["Loss run", "SOV"], notes="Please send 5yr loss runs")
    assert req["status"] == "pending"
    assert len(store.pending_info_requests("b1", "org1")) == 1
    done = store.respond_info_request("b1", "org1", req["request_id"], response_note="Attached via email")
    assert done["status"] == "fulfilled"
    assert store.pending_info_requests("b1", "org1") == []
    note = store.add_note("b1", "org1", "Spoke with broker Jane — strong relationship", role="uw", author="uw1")
    assert note["text"].startswith("Spoke")
    assert len(store.list_notes("b1", "org1")) == 1
