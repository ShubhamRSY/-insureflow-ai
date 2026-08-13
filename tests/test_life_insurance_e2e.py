"""End-to-end: every life product's document set flows through the pipeline.

Covers:
- Per-product catalogs track base packet + additional + coverage documents.
- The generic ``life`` catalog (used by triage / pipeline) tracks the union of
  every product's required documents, so no life document is untracked.
- Uploading every classified document reaches 100% completeness.
- The classifier recognizes the base set and product-specific add-ons.
- The hub / line API endpoints expose the full document set.
- A full pipeline run classifies the package and reports a complete checklist.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.auth import Role
from insureflow.auth.jwt import create_access_token
from insureflow.auth.models import User
from insureflow.auth.store import clear_user_store, get_user_store
from insureflow.ingestion.insurance.classifier import InsuranceDocumentClassifier, InsuranceDocumentType
from insureflow.insurance.commercial_lobs import flatten_line_documents
from insureflow.insurance.life_lobs import LIFE_LINES, life_hub_payload
from insureflow.insurance.package_checklist import CATALOGS, package_checklist


def _all_life_docs() -> list[str]:
    docs: list[str] = []
    seen: set[str] = set()
    for line in LIFE_LINES:
        for doc in flatten_line_documents(line):
            if doc not in seen:
                seen.add(doc)
                docs.append(doc)
    return docs


def _union_types() -> list[InsuranceDocumentType]:
    return sorted({t for _, tup in CATALOGS["life"] for t in tup}, key=lambda t: t.value)


# filename -> classifier keyword trigger (verified: zero mismatches)
FILENAME_MAP = {
    "acord_xml": "life_acord_100.xml",
    "aml_declaration": "aml_declaration.txt",
    "aps_records": "aps_records.txt",
    "attorney_documentation": "attorney_documentation.txt",
    "bank_ach_form": "bank_ach_form.txt",
    "beneficiary_form": "beneficiary_designation_form.txt",
    "broker_dealer_form": "broker_dealer_form.txt",
    "child_birth_certificate": "child_birth_certificate.txt",
    "conversion_request_form": "conversion_request_form.txt",
    "court_order": "court_order.txt",
    "dividend_election": "dividend_election.txt",
    "enrollment_form": "enrollment_form.txt",
    "financial_statement": "financial_statement.txt",
    "graded_benefit_disclosure": "graded_benefit_disclosure.txt",
    "health_questionnaire": "health_questionnaire.txt",
    "hipaa_authorization": "hipaa_authorization.txt",
    "illustration_acknowledgment": "illustration_acknowledgment.txt",
    "income_proof": "income_proof.txt",
    "index_allocation_election": "index_allocation_election.txt",
    "lender_information": "lender_information.txt",
    "life_application": "life_application.txt",
    "loan_agreement": "loan_agreement.txt",
    "medical_exam": "paramedical_exam.txt",
    "mib_rx_authorization": "mib_rx_authorization.txt",
    "mortgage_statement": "mortgage_statement.txt",
    "photo_id": "photo_id.txt",
    "premium_waiver_rider": "premium_waiver_rider.txt",
    "proof_of_address": "proof_of_address.txt",
    "prospectus_acknowledgment": "prospectus_acknowledgment.txt",
    "renewal_form": "renewal_form.txt",
    "retirement_account_statement": "retirement_account_statement.txt",
    "social_security_number": "social_security_number.txt",
    "source_of_funds": "source_of_funds.txt",
    "sub_account_election": "sub_account_election.txt",
    "suitability_questionnaire": "suitability_questionnaire.txt",
    "tax_form_1098q": "tax_form_1098q.txt",
}

# InsuranceDocumentType values with no classifier path (label-heuristic artifacts).
NO_CLASSIFIER_PATH = {InsuranceDocumentType.PROPERTY_PHOTOS}


def _classifiable_life_documents() -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for doc_type in _union_types():
        if doc_type in NO_CLASSIFIER_PATH:
            continue
        filename = FILENAME_MAP[doc_type.value]
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n<ACORD><InsuranceSvcRq><txnId>life-e2e</txnId>'
            "<BusinessApplication>ACORD810</BusinessApplication><Policy><LifeApplication>"
            "<Person><GeneralInfo><FullName>Jane Doe</FullName></GeneralInfo></Person></LifeApplication>"
            "</Policy></InsuranceSvcRq></ACORD>"
            if doc_type == InsuranceDocumentType.ACORD_XML
            else f"life insurance package — {doc_type.value}"
        )
        docs.append({"filename": filename, "content": content})
    return docs


# ---------------------------------------------------------------------------
# Catalog completeness (unit + classification-backed)
# ---------------------------------------------------------------------------


def test_every_product_catalog_covers_base_plus_additional_docs():
    for line in LIFE_LINES:
        lob = line["checklist_lob"]
        labels = {label for label, _ in CATALOGS[lob]}
        flat = set(flatten_line_documents(line))
        assert flat <= labels, line["id"]
        missing = set(package_checklist([], lob=lob)["missing"])
        assert flat <= missing, line["id"]


def test_generic_life_catalog_covers_all_product_docs():
    labels = {label for label, _ in CATALOGS["life"]}
    assert set(_all_life_docs()) <= labels
    missing = set(package_checklist([], lob="life")["missing"])
    assert set(_all_life_docs()) <= missing


def test_all_required_docs_present_reaches_full_completeness():
    lobs = ["life"] + [line["checklist_lob"] for line in LIFE_LINES]
    for lob in lobs:
        catalog = CATALOGS[lob]
        assert catalog, lob
        types = [tup[0].value for _, tup in catalog if tup]
        result = package_checklist(types, lob=lob)
        assert result["completeness_pct"] == 100.0, lob
        assert result["missing"] == [], lob


def test_classifier_recognizes_base_and_product_specific_docs():
    reverse_map = {filename: key for key, filename in FILENAME_MAP.items()}
    for doc in _classifiable_life_documents():
        classified = InsuranceDocumentClassifier.classify(doc["content"], doc["filename"])
        assert classified.value == reverse_map[doc["filename"]], doc["filename"]


def test_classifier_satisfies_every_union_label():
    classified_types = [InsuranceDocumentClassifier.classify(d["content"], d["filename"]).value for d in _classifiable_life_documents()]
    result = package_checklist(classified_types, lob="life")
    assert result["completeness_pct"] == 100.0
    assert result["missing"] == []
    assert len(classified_types) == len(set(classified_types)), "classifier must produce distinct types"


# ---------------------------------------------------------------------------
# API end-to-end
# ---------------------------------------------------------------------------


class TestLifeAPIEndToEnd:
    @pytest.fixture(autouse=True)
    def reset_users(self) -> None:
        clear_user_store()

    def _headers(self, role: Role = Role.VIEWER) -> dict[str, str]:
        get_user_store()["uw"] = User(username="uw", hashed_password="x", role=role, org_id="acme")
        token = create_access_token({"sub": "uw", "role": role.value, "org_id": "acme"})
        return {"Authorization": f"Bearer {token}"}

    def test_life_hub_serves_full_catalog(self) -> None:
        client = TestClient(app)
        resp = client.get("/insurance/life", headers=self._headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["segment"] == "personal_life"
        assert len(data["lines"]) == len(LIFE_LINES)
        assert len(data["base_packet"]) >= 9
        for line in data["lines"]:
            assert line["insurance_line"] == "life"
            assert line["all_documents"]
            assert line["document_count"] >= len(data["base_packet"])

    def test_every_line_endpoint_tracks_full_document_set(self) -> None:
        client = TestClient(app)
        headers = self._headers()
        hub = client.get("/insurance/life", headers=headers).json()
        for line in hub["lines"]:
            resp = client.get(f"/insurance/life/lines/{line['slug']}", headers=headers)
            assert resp.status_code == 200, line["slug"]
            body = resp.json()
            assert body["checklist_lob"] == line["checklist_lob"]
            template = body["checklist_template"]
            assert template["lob"] == line["checklist_lob"]
            flat = set(flatten_line_documents(body))
            assert flat <= set(template["missing"]), line["slug"]
            assert template["completeness_pct"] == 0.0

    def test_taxonomy_endpoint_nests_all_products(self) -> None:
        client = TestClient(app)
        resp = client.get("/insurance/life/taxonomy", headers=self._headers())
        assert resp.status_code == 200
        tree = resp.json()["taxonomy"]
        assert len(tree) == 7
        total = sum(len(cat["products"]) for cat in tree)
        assert total == len(LIFE_LINES)


# ---------------------------------------------------------------------------
# Full pipeline end-to-end
# ---------------------------------------------------------------------------


class TestLifePipelineEndToEnd:
    def test_pipeline_runs_full_package_on_product_catalog(self, tmp_path: Path) -> None:
        from insureflow.audit.store import AuditStore
        from insureflow.insurance.pipeline import InsurancePipeline

        documents = _classifiable_life_documents()
        result = InsurancePipeline(
            org_id="life-e2e",
            use_llm=False,
            audit_store=AuditStore(base_path=tmp_path / "audit"),
        ).run(
            bundle_id="life-e2e",
            insurance_line="life",
            life_product_id="single_premium_ulip",
            documents=documents,
        )
        assert result["status"] == "completed"
        assert result["insurance_line"] == "life"
        assert result["checklist_lob"] == "single_premium_ulip"
        assert result["life_checklist_lob"] == "single_premium_ulip"
        checklist = result["document_checklist"]
        assert checklist["lob"] == "single_premium_ulip"
        assert checklist["completeness_pct"] == 1.0
        assert checklist["missing_documents"] == []
        assert len(checklist["present_documents"]) == len(CATALOGS["single_premium_ulip"])
        assert result["ai_decision"] in ("accept", "conditional_accept", "refer", "decline")

    def test_pipeline_auto_detects_life_product_from_documents(self, tmp_path: Path) -> None:
        from insureflow.audit.store import AuditStore
        from insureflow.insurance.pipeline import InsurancePipeline

        result = InsurancePipeline(
            org_id="life-e2e",
            use_llm=False,
            audit_store=AuditStore(base_path=tmp_path / "audit"),
        ).run(
            bundle_id="life-e2e-autodetect",
            insurance_line="life",
            documents=[{"filename": "single_premium_ulip.txt", "content": "single premium ulip unit linked plan funded by one lump sum premium source of funds"}],
        )
        assert result["status"] == "completed"
        assert result["checklist_lob"] == "single_premium_ulip"
        assert result["document_checklist"]["lob"] == "single_premium_ulip"

    def test_pipeline_falls_back_to_generic_life_without_product_hint(self, tmp_path: Path) -> None:
        from insureflow.audit.store import AuditStore
        from insureflow.insurance.pipeline import InsurancePipeline

        result = InsurancePipeline(
            org_id="life-e2e",
            use_llm=False,
            audit_store=AuditStore(base_path=tmp_path / "audit"),
        ).run(
            bundle_id="life-e2e-generic",
            insurance_line="life",
            documents=[{"filename": "life_application.txt", "content": "life insurance application beneficiary designation paramedical exam"}],
        )
        assert result["status"] == "completed"
        assert result["checklist_lob"] == "life"
        assert result["document_checklist"]["lob"] == "life"

    def test_pipeline_reports_missing_life_docs(self, tmp_path: Path) -> None:
        from insureflow.audit.store import AuditStore
        from insureflow.insurance.pipeline import InsurancePipeline

        result = InsurancePipeline(
            org_id="life-e2e",
            use_llm=False,
            audit_store=AuditStore(base_path=tmp_path / "audit"),
        ).run(
            bundle_id="life-e2e-incomplete",
            insurance_line="life",
            documents=[{"filename": "life_application.txt", "content": "term life application face amount 750000"}],
        )
        assert result["status"] == "completed"
        checklist = result["document_checklist"]
        assert checklist["lob"] == "life"
        assert checklist["completeness_pct"] < 1.0
        assert "Life application" in checklist["present_documents"]
        assert any("Medical" in m or "Param" in m or "APS" in m or "Beneficiary" in m for m in checklist["missing_documents"])


def test_life_document_structuring_extracts_fields() -> None:
    """Native life docs produce structured fields via the loader, not empty."""
    from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader

    bundle = InsuranceDocumentLoader().load_from_documents(
        [
            {
                "filename": "life_application.txt",
                "content": (
                    "Completed Life Insurance Application\n"
                    "Insured: John Q. Public\n"
                    "Date of Birth: 03/14/1985\n"
                    "Sex: Male\n"
                    "Smoker: No\n"
                    "Face Amount: $750,000\n"
                    "Annual Premium: $4,350\n"
                    "Beneficiary: Jane Public\n"
                    "Relationship to Insured: Spouse\n"
                ),
            },
            {"filename": "beneficiary_designation_form.txt", "content": ("Beneficiary Designation\nPrimary Beneficiary: Jane Public\nRelationship: Spouse\nAllocation: 100%\n")},
            {"filename": "health_questionnaire.txt", "content": ("Health Questionnaire\nHeight: 5 ft 10 in\nWeight: 185 lbs\nSmoker: No\nMedications: Lisinopril\n")},
            {"filename": "income_proof.txt", "content": ("Proof of Income\nEmployer: Acme Corp\nAnnual Income: $125,000\n")},
            {"filename": "medical_exam.txt", "content": ("Paramedical Exam\nExaminee: John Q. Public\nHeight: 5 ft 10 in\nWeight: 185 lbs\nBlood Pressure: 120/80\nPulse: 68\n")},
        ],
        bundle_id="struct-test",
    )

    docs = {d.document_type: d for d in bundle.unstructured}
    assert set(docs) == {
        "life_application",
        "beneficiary_form",
        "health_questionnaire",
        "income_proof",
        "medical_exam",
    }

    app_fields = {k: f[0].value for k, f in docs["life_application"].extracted_fields.items()}
    assert app_fields["insured_name"] == "John Q. Public"
    assert app_fields["dob"] == "03/14/1985"
    assert app_fields["face_amount"] == "750,000"
    assert app_fields["premium"] == "4,350"
    assert app_fields["beneficiary"] == "Jane Public"
    assert app_fields["beneficiary_relationship"] == "Spouse"

    ben_fields = {k: f[0].value for k, f in docs["beneficiary_form"].extracted_fields.items()}
    assert ben_fields["beneficiary_name"] == "Jane Public"
    assert ben_fields["allocation_percent"] == "100"

    hq_fields = {k: f[0].value for k, f in docs["health_questionnaire"].extracted_fields.items()}
    assert "185" in hq_fields["weight"]
    assert hq_fields["medications"] == "Lisinopril"

    inc_fields = {k: f[0].value for k, f in docs["income_proof"].extracted_fields.items()}
    assert inc_fields["income_amount"] == "125,000"
    assert inc_fields["employer"] == "Acme Corp"

    med_fields = {k: f[0].value for k, f in docs["medical_exam"].extracted_fields.items()}
    assert med_fields["blood_pressure"] == "120/80"
    assert med_fields["pulse"] == "68"


def test_zta_life_expected_fields_present() -> None:
    from insureflow.zta.router import DEFAULT_EXPECTED_FIELDS

    for doc_type in ("life_application", "beneficiary_form", "health_questionnaire", "income_proof", "medical_exam"):
        assert doc_type in DEFAULT_EXPECTED_FIELDS


def test_resolve_life_checklist_lob_accepts_slug_id_and_name() -> None:
    from insureflow.insurance.life_lobs import resolve_life_checklist_lob

    assert resolve_life_checklist_lob("single-premium-ulip") == "single_premium_ulip"
    assert resolve_life_checklist_lob("single_premium_ulip") == "single_premium_ulip"
    assert resolve_life_checklist_lob("Single Premium ULIP") == "single_premium_ulip"
    assert resolve_life_checklist_lob("traditional_whole_life") == "traditional_whole_life"
    assert resolve_life_checklist_lob("nonsense-product-xyz") is None
    assert resolve_life_checklist_lob(None) is None


def test_detect_life_product_matches_known_products() -> None:
    from insureflow.insurance.life_lobs import detect_life_product

    assert detect_life_product("single premium ulip unit linked lump sum") == "single_premium_ulip"
    assert detect_life_product("indexed universal life tied to index performance") == "indexed_universal_life"
    assert detect_life_product("traditional ordinary whole life fixed premium guaranteed cash value") == "traditional_whole_life"
    assert detect_life_product("a generic package with no product signals") is None
    assert detect_life_product("") is None


def test_hub_payload_product_count_stable() -> None:
    hub = life_hub_payload()
    assert hub["stats"]["product_count"] == len(LIFE_LINES)
    assert hub["stats"]["live_count"] == len(LIFE_LINES)
