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
