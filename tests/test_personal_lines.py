from __future__ import annotations

from insureflow.ingestion.insurance.classifier import InsuranceDocumentClassifier, InsuranceDocumentType
from insureflow.insurance.package_checklist import detect_lob, package_checklist
from insureflow.models.agents import Recommendation, UnderwritingMemo, UWDecision
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.rating.models import InsuranceLine
from insureflow.underwriting.personal_lines import detect_insurance_line, extract_auto_factors, extract_home_factors, extract_life_factors


def _bundle(text: str, filename: str = "app.md") -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="test-personal",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                source=filename,
                raw_text=text,
                document_type="supplemental",
            )
        ],
    )


def test_detect_personal_lines() -> None:
    assert detect_insurance_line("homeowners application dwelling coverage") == InsuranceLine.PERSONAL_HOMEOWNERS
    assert detect_insurance_line("personal auto application VIN: 123 MVR") == InsuranceLine.PERSONAL_AUTO
    assert detect_insurance_line("term life application face amount beneficiary") == InsuranceLine.LIFE


def test_classifier_personal_doc_types() -> None:
    assert InsuranceDocumentClassifier.classify("Homeowners Application HO-3", "homeowners_application.md") == InsuranceDocumentType.HOMEOWNERS_APPLICATION
    assert InsuranceDocumentClassifier.classify("Motor Vehicle Report", "mvr_report.md") == InsuranceDocumentType.MVR_REPORT
    assert InsuranceDocumentClassifier.classify("Term Life Insurance Application", "life_application.md") == InsuranceDocumentType.LIFE_APPLICATION


def test_package_checklists_personal() -> None:
    assert detect_lob("dwelling coverage homeowners") == "homeowners"
    assert detect_lob("mvr driving record personal auto") == "auto"
    assert detect_lob("face amount paramedical") == "life"
    home = package_checklist(["homeowners_application", "dwelling_inspection"], lob="homeowners")
    assert home["completeness_pct"] < 100
    assert "Homeowners application" in home["present"]


def test_personal_rating_produces_premium() -> None:
    engine = InsuranceRatingEngine()
    memo = UnderwritingMemo(
        bundle_id="t",
        insured_name="Test",
        decision=UWDecision.ACCEPT,
        recommendation=Recommendation(action="accept", rationale="ok", suggested_premium_modification=0),
    )

    home_text = """
    Homeowners application. Dwelling coverage: $400000. Year built: 2005.
    Construction: masonry. Protection class: 3. State implied TX.
    """
    home = _bundle(home_text, "homeowners_application.md")
    # Inject state via unstructured only — engine may have empty state territory 1.0
    hq = engine.quote(home, memo, line=InsuranceLine.PERSONAL_HOMEOWNERS)
    assert hq.adjusted_premium > 0
    assert hq.metadata.get("personal_lines") is True
    assert extract_home_factors(home).dwelling_limit == 400000

    auto_text = """
    Personal auto application. Driver age: 35. Years licensed: 15.
    Vehicle year: 2020. Vehicle value: $25000. Annual mileage: 8000.
    Intended use: personal. Clean record.
    """
    aq = engine.quote(_bundle(auto_text, "auto_application.md"), memo, line=InsuranceLine.PERSONAL_AUTO)
    assert aq.adjusted_premium > 0
    assert extract_auto_factors(_bundle(auto_text)).driver_age == 35

    life_text = """
    Term life application. Applicant age: 40. Face amount: $500000.
    Annual income: $120000. Non-smoker. Preferred. No criminal history.
    """
    lq = engine.quote(_bundle(life_text, "life_application.md"), memo, line=InsuranceLine.LIFE)
    assert lq.adjusted_premium > 0
    assert extract_life_factors(_bundle(life_text)).face_amount == 500000
