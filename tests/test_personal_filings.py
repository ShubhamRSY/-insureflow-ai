from __future__ import annotations

from insureflow.models.agents import Recommendation, UnderwritingMemo, UWDecision
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.rating.models import InsuranceLine
from insureflow.rating.personal import rate_personal_line
from insureflow.underwriting.life_medical import underwrite_life


def _bundle(*docs: tuple[str, str]) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="filing-test",
        unstructured=[UnstructuredSubmission(submission_id=f"d{i}", source=name, raw_text=text, document_type="supplemental") for i, (name, text) in enumerate(docs)],
    )


def test_homeowners_filing_rates_from_manual() -> None:
    b = _bundle(
        (
            "homeowners_application.md",
            "Homeowners application. Dwelling coverage: $485000. Year built: 1998. Construction: masonry. Protection class: 4. State: TX. Deductible: 2500. New roof.",
        )
    )
    q = rate_personal_line(b, InsuranceLine.PERSONAL_HOMEOWNERS, state="TX", deductible=2500)
    assert q.metadata["filing_id"] == "RYT-HO-2026-01"
    assert q.metadata["rating_engine"] == "homeowners_filing"
    assert q.adjusted_premium >= 450
    assert any(c.name == "ho3_base_rate_per_1000" for c in q.schedule_modifications)


def test_auto_filing_rates_from_manual() -> None:
    b = _bundle(
        (
            "auto_application.md",
            "Personal auto application. Driver age: 34. Years licensed: 16. Vehicle value: $28500. Annual mileage: 9200. Intended use: personal. State: IL.",
        )
    )
    q = rate_personal_line(b, InsuranceLine.PERSONAL_AUTO, state="IL")
    assert q.metadata["filing_id"] == "RYT-PA-2026-01"
    assert q.adjusted_premium >= 650
    assert q.metadata.get("state_minimum_bi")


def test_life_term_duration_factors() -> None:
    from insureflow.rating.personal.life_rating import rate_life
    from insureflow.rating.personal.manuals import clear_manual_cache

    clear_manual_cache()

    b = _bundle(
        (
            "life_application.md",
            "Term life application. Applicant age: 42. Sex: female. Face amount: $750000. Annual income: 145000. Non-smoker. Preferred. Blood pressure: 118/76. BMI: 23.4. Cholesterol: 185.",
        )
    )
    q10 = rate_life(b, coverage_id="level_term_10")
    q20 = rate_life(b, coverage_id="level_term_20")
    q30 = rate_life(b, coverage_id="level_term_30")
    assert q10.metadata["term_years"] == 10
    assert q20.metadata["term_years"] == 20
    assert q30.metadata["term_years"] == 30
    assert q10.adjusted_premium < q20.adjusted_premium < q30.adjusted_premium
    assert any(c.name == "term_duration" for c in q10.schedule_modifications)
    assert q10.metadata["product"] == "10-Year Level Term"


def test_life_medical_and_filing() -> None:
    clean = _bundle(
        (
            "life_application.md",
            "Term life application. Applicant age: 42. Sex: female. Face amount: $750000. Annual income: 145000. Non-smoker. Preferred. Blood pressure: 118/76. BMI: 23.4. Cholesterol: 185.",
        )
    )
    med = underwrite_life(clean)
    assert med.decision in (UWDecision.ACCEPT, UWDecision.CONDITIONAL_ACCEPT)
    assert med.underwriting_class in ("preferred", "super_preferred", "standard", "standard_plus")
    q = rate_personal_line(clean, InsuranceLine.LIFE)
    assert q.metadata["filing_id"] == "RYT-LIFE-2026-01"
    # No product/coverage hint -> generic (catalog-only) path, which is
    # ineligible (unfiled) so the premium contract is $0 (C1); the computed
    # term premium is preserved on the illustrated premium.
    assert q.eligible is False
    assert q.adjusted_premium == 0
    assert q.metadata["illustrated_adjusted_premium"] >= 250
    assert q.metadata["medical"]["underwriting_class"]

    knockout = _bundle(
        (
            "life_application.md",
            "Term life application. Applicant age: 50. Face amount: $500000. Active cancer on chemotherapy. Felony.",
        )
    )
    declined = underwrite_life(knockout)
    assert declined.decision == UWDecision.DECLINE


def test_engine_routes_personal_to_filings() -> None:
    engine = InsuranceRatingEngine()
    memo = UnderwritingMemo(
        bundle_id="t",
        insured_name="Test",
        decision=UWDecision.ACCEPT,
        recommendation=Recommendation(action="accept", rationale="ok"),
    )
    b = _bundle(
        (
            "homeowners_application.md",
            "Homeowners application dwelling coverage: $400000. Year built: 2005. Construction: frame. Protection class: 5. State: IL.",
        )
    )
    q = engine.quote(b, memo, line=InsuranceLine.PERSONAL_HOMEOWNERS)
    assert q.metadata.get("rating_engine") == "homeowners_filing"
    assert q.adjusted_premium > 0
