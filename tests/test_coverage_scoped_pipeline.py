"""Selected coverage is the only pipeline scope — life and commercial."""

from __future__ import annotations

from pathlib import Path

from insureflow.audit.store import AuditStore
from insureflow.insurance.pipeline import InsurancePipeline


def _pipeline(tmp_path: Path, org: str = "cov-scope") -> InsurancePipeline:
    return InsurancePipeline(
        org_id=org,
        use_llm=False,
        audit_store=AuditStore(base_path=tmp_path / "audit"),
    )


def test_life_pipeline_runs_only_selected_10_year_term(tmp_path: Path) -> None:
    result = _pipeline(tmp_path).run(
        bundle_id="life-10yr",
        insurance_line="life",
        life_product_id="level_term",
        life_coverage_id="level_term_10",
        documents=[
            {
                "filename": "life_application.txt",
                "content": (
                    "Completed life insurance application. Level term life. "
                    "Applicant age: 40. Sex: male. Face amount: $500000. Non-smoker. "
                    "Beneficiary Jane Doe DOB 1985-01-01 SSN relationship spouse."
                ),
            }
        ],
    )
    assert result["status"] == "completed"
    assert result["insurance_line"] == "life"
    assert result["checklist_lob"] == "level_term"
    assert result["life_checklist_lob"] == "level_term"
    assert result["life_coverage_id"] == "level_term_10"
    assert result["commercial_coverage_id"] == "level_term_10"
    assert result["commercial_coverage_name"] == "10-Year Level Term"
    assert result["commercial_product_name"] == "Level Term Life Insurance"
    missing = result["document_checklist"]["missing_documents"]
    assert not any("Paramedical" in m for m in missing)
    quote = result.get("quote") or {}
    assert quote.get("coverage_id") == "level_term_10"
    assert quote.get("term_years") == 10
    assert any(c.get("name") == "term_duration" for c in (quote.get("components") or []))


def test_life_picker_is_not_overridden_by_commercial_blob(tmp_path: Path) -> None:
    result = _pipeline(tmp_path, "cov-override").run(
        bundle_id="life-vs-sov",
        insurance_line="life",
        life_product_id="level_term",
        life_coverage_id="level_term_10",
        documents=[
            {
                "filename": "sov.txt",
                "content": ("Schedule of values commercial property building value total insurable value ACORD 140 loss run"),
            }
        ],
    )
    assert result["status"] == "completed"
    assert result["insurance_line"] == "life"
    assert result["life_coverage_id"] == "level_term_10"
    assert result["checklist_lob"] == "level_term"


def test_commercial_pipeline_runs_only_selected_bpp_coverage(tmp_path: Path) -> None:
    result = _pipeline(tmp_path, "cov-bpp").run(
        bundle_id="prop-bpp",
        insurance_line="commercial_property",
        commercial_product_id="property_bi",
        commercial_coverage_id="bpp",
        documents=[
            {
                "filename": "acord_140.txt",
                "content": "ACORD 140 Property Section. Statement of Values SOV. Loss run reports 5 years.",
            }
        ],
    )
    assert result["status"] == "completed"
    assert result["commercial_product_id"] == "property_bi"
    assert result["commercial_coverage_id"] == "bpp"
    assert result["commercial_coverage_name"] == "Business Personal Property (BPP)"
    assert result["checklist_lob"] == "property"
    checklist = result["document_checklist"]
    assert checklist.get("coverage_id") == "bpp"
    missing = checklist.get("missing_documents") or []
    assert "Inventory/asset list with values" in missing
    assert "Structure replacement cost appraisal" not in missing


def test_health_pipeline_runs_only_selected_cancer_coverage(tmp_path: Path) -> None:
    result = _pipeline(tmp_path, "cov-health").run(
        bundle_id="health-cancer",
        insurance_line="health",
        health_product_id="disease_specific_critical_illness",
        health_coverage_id="cancer_care",
        documents=[
            {
                "filename": "health_proposal.txt",
                "content": ("Disease-specific cancer care critical illness plan. Government-issued photo ID. Proof of address. Date of birth verification. Family history of cancer declaration."),
            }
        ],
    )
    assert result["status"] == "completed"
    assert result["insurance_line"] == "health"
    assert result["health_checklist_lob"] == "disease_specific_critical_illness"
    assert result["health_coverage_id"] == "cancer_care"
    assert result["commercial_coverage_id"] == "cancer_care"
    missing = result["document_checklist"]["missing_documents"]
    assert not any("ecg" in m.lower() for m in missing)
    quote = result.get("quote") or {}
    assert quote.get("insurance_line") == "health"
    assert quote.get("eligible") is False
    reasons = " ".join(quote.get("ineligibility_reasons") or []).lower()
    assert "catalog" not in reasons
    assert "amount" in reasons or "benefit" in reasons


def test_health_pipeline_maternity_logic_differs_from_opd(tmp_path: Path) -> None:
    kyc = "Identity proof Aadhaar. Address proof utility bill. Age proof 10th marksheet. Passport-size photograph. Proposal form. Age: 30. Already pregnant 10 weeks."
    mat = _pipeline(tmp_path, "cov-mat").run(
        bundle_id="health-mat",
        insurance_line="health",
        health_product_id="maternity_inclusive",
        health_coverage_id="maternity_inclusive_std",
        documents=[{"filename": "maternity.txt", "content": kyc}],
    )
    opd = _pipeline(tmp_path, "cov-opd").run(
        bundle_id="health-opd",
        insurance_line="health",
        health_product_id="opd_cover",
        health_coverage_id="opd_reimbursement",
        documents=[{"filename": "opd.txt", "content": kyc + " Bank account IFSC."}],
    )
    mat_uw = (mat.get("quote") or {}).get("health_uw") or {}
    opd_uw = (opd.get("quote") or {}).get("health_uw") or {}
    assert mat_uw.get("product_family") == "maternity"
    assert opd_uw.get("product_family") == "opd"
    assert mat_uw.get("decision") == "decline"
    assert opd_uw.get("decision") != "decline"
    assert (mat.get("quote") or {}).get("benefit_type") == "hospitalization_indemnity_maternity"
    assert (opd.get("quote") or {}).get("benefit_type") == "opd_reimbursement"


def test_general_pipeline_car_tp_differs_from_comprehensive(tmp_path: Path) -> None:
    text = (
        "Identity proof Aadhaar. Address proof. ID + address proof of owner. "
        "Registration certificate RC of vehicle. Driving license. Chassis number ABC Engine number 123. "
        "Pre-owned used vehicle lapse."
    )
    tp = _pipeline(tmp_path, "cov-gi-tp").run(
        bundle_id="gi-car-tp",
        insurance_line="general",
        general_product_id="car_tp",
        general_coverage_id="car_tp_std",
        documents=[{"filename": "car_tp.txt", "content": text}],
    )
    comp = _pipeline(tmp_path, "cov-gi-comp").run(
        bundle_id="gi-car-comp",
        insurance_line="general",
        general_product_id="car_comprehensive",
        general_coverage_id="car_comp_used",
        documents=[{"filename": "car_comp.txt", "content": text}],
    )
    assert tp["status"] == "completed"
    assert tp["insurance_line"] == "general"
    assert tp["general_checklist_lob"] == "car_tp"
    assert tp["general_coverage_id"] == "car_tp_std"
    assert comp["general_checklist_lob"] == "car_comprehensive"
    tp_uw = (tp.get("quote") or {}).get("general_uw") or {}
    comp_uw = (comp.get("quote") or {}).get("general_uw") or {}
    assert tp_uw.get("product_family") == "car_tp"
    assert comp_uw.get("product_family") == "car_comprehensive"
    assert "inspection_if_used" not in (tp_uw.get("gates") or {})
    assert (comp_uw.get("gates") or {}).get("inspection_if_used") == "fail"
    assert (tp.get("quote") or {}).get("benefit_type") == "motor_third_party"
    assert (comp.get("quote") or {}).get("benefit_type") == "motor_comprehensive"
    missing_comp = comp["document_checklist"]["missing_documents"]
    assert any("inspection" in m.lower() for m in missing_comp)


def test_general_pipeline_travel_domestic_vs_international(tmp_path: Path) -> None:
    text = "Identity proof Aadhaar. Address proof. Age proof. Travel itinerary / ticket. Photograph. Age: 34."
    domestic = _pipeline(tmp_path, "cov-gi-dom").run(
        bundle_id="gi-travel-dom",
        insurance_line="general",
        general_product_id="travel_domestic",
        general_coverage_id="travel_domestic_std",
        documents=[{"filename": "dom.txt", "content": text}],
    )
    intl = _pipeline(tmp_path, "cov-gi-intl").run(
        bundle_id="gi-travel-intl",
        insurance_line="general",
        general_product_id="travel_international",
        general_coverage_id="travel_intl_std",
        documents=[{"filename": "intl.txt", "content": text}],
    )
    assert domestic["insurance_line"] == "general"
    assert intl["insurance_line"] == "general"
    dom_uw = (domestic.get("quote") or {}).get("general_uw") or {}
    intl_uw = (intl.get("quote") or {}).get("general_uw") or {}
    assert dom_uw.get("product_family") == "travel_domestic"
    assert intl_uw.get("product_family") == "travel_international"
    assert intl_uw.get("decision") == "decline"
    assert dom_uw.get("decision") != "decline"
    assert (domestic.get("quote") or {}).get("requires_passport") is False
    assert (intl.get("quote") or {}).get("requires_passport") is True
    missing_intl = intl["document_checklist"]["missing_documents"]
    assert any("passport" in m.lower() for m in missing_intl)
    missing_dom = domestic["document_checklist"]["missing_documents"]
    assert not any("passport" in m.lower() and "photo" not in m.lower() for m in missing_dom)
