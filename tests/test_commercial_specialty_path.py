"""Commercial specialty lines: detect → rate → decide (not property collapse)."""

from __future__ import annotations

from insureflow.ingestion.insurance.classifier import InsuranceDocumentClassifier, InsuranceDocumentType
from insureflow.models.agents import Recommendation, UnderwritingMemo, UWDecision
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rag.guidelines import builtin_guidelines
from insureflow.rating.commercial_specialty import rate_specialty_line, underwrite_specialty
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.rating.models import COMMERCIAL_SPECIALTY_LINES, InsuranceLine
from insureflow.underwriting.personal_lines import detect_insurance_line, parse_insurance_line


def _bundle(text: str, filename: str = "app.md") -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="specialty-test",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                source=filename,
                raw_text=text,
                document_type="supplemental",
            )
        ],
    )


def _memo() -> UnderwritingMemo:
    return UnderwritingMemo(
        bundle_id="specialty-test",
        decision=UWDecision.ACCEPT,
        summary="Clean specialty submission",
        recommendation=Recommendation(action="accept", rationale="test"),
    )


def test_parse_specialty_lines_not_none() -> None:
    assert parse_insurance_line("trade_credit") == InsuranceLine.TRADE_CREDIT
    assert parse_insurance_line("errors_and_omissions") == InsuranceLine.ERRORS_AND_OMISSIONS
    assert parse_insurance_line("key_person") == InsuranceLine.KEY_PERSON
    assert parse_insurance_line("directors_and_officers") == InsuranceLine.DIRECTORS_AND_OFFICERS
    assert parse_insurance_line("do") == InsuranceLine.DIRECTORS_AND_OFFICERS
    assert parse_insurance_line("eo") == InsuranceLine.ERRORS_AND_OMISSIONS


def test_detect_respects_specialty_hint() -> None:
    # Thin package + hub tag must not collapse to commercial_property
    assert detect_insurance_line("named insured Acme LLC", "trade_credit") == InsuranceLine.TRADE_CREDIT
    assert detect_insurance_line("named insured Acme LLC", "errors_and_omissions") == InsuranceLine.ERRORS_AND_OMISSIONS
    assert detect_insurance_line("named insured Acme LLC", "key_person") == InsuranceLine.KEY_PERSON
    assert detect_insurance_line("named insured Acme LLC", "directors_and_officers") == InsuranceLine.DIRECTORS_AND_OFFICERS


def test_detect_content_specialty_not_property() -> None:
    assert detect_insurance_line("Directors & Officers liability application management liability") == InsuranceLine.DIRECTORS_AND_OFFICERS
    assert detect_insurance_line("trade credit insurance accounts receivable aging") == InsuranceLine.TRADE_CREDIT
    assert detect_insurance_line("errors and omissions professional liability application") == InsuranceLine.ERRORS_AND_OMISSIONS
    assert detect_insurance_line("key person insurance face amount buy-sell") == InsuranceLine.KEY_PERSON


def test_property_heavy_still_wins_over_specialty_hint() -> None:
    blob = "schedule of values commercial property building value total insurable value warehouse"
    assert detect_insurance_line(blob, "trade_credit") == InsuranceLine.COMMERCIAL_PROPERTY


def test_specialty_rating_skips_cope_and_stays_eligible() -> None:
    engine = InsuranceRatingEngine()
    for line in sorted(COMMERCIAL_SPECIALTY_LINES, key=lambda x: x.value):
        quote = engine.quote(_bundle(f"insurance_line: {line.value}"), _memo(), line=line)
        assert quote.line == line
        assert quote.eligible is True
        assert quote.adjusted_premium > 0
        assert (quote.metadata or {}).get("specialty") is True
        assert (quote.metadata or {}).get("cope_grade") == "n/a"
        assert (quote.metadata or {}).get("insurance_line") == line.value


def test_trade_credit_rates_on_stated_ar() -> None:
    text = "Trade credit application. Accounts receivable: $2,000,000. AR aging attached."
    quote = rate_specialty_line(_bundle(text), InsuranceLine.TRADE_CREDIT)
    assert quote.metadata["exposure"] == 2_000_000.0
    assert quote.metadata["exposure_basis"] == "receivables"
    assert quote.adjusted_premium >= 1500.0


def test_do_decision_refers_on_litigation() -> None:
    text = "Directors and Officers application. Pending litigation: securities class action. Financial statements attached. Balance sheet included."
    result = underwrite_specialty(_bundle(text), InsuranceLine.DIRECTORS_AND_OFFICERS)
    assert result.decision == UWDecision.REFER
    assert any("litigation" in r.lower() for r in result.reasons)


def test_trade_credit_refers_on_concentration() -> None:
    text = "Trade credit. Accounts receivable aging provided. Top buyer concentration: 55%."
    result = underwrite_specialty(_bundle(text), InsuranceLine.TRADE_CREDIT)
    assert result.decision == UWDecision.REFER
    assert any("concentration" in r.lower() for r in result.reasons)


def test_key_person_refers_on_medical() -> None:
    text = "Key person application. Face amount: $1,000,000. Job description: CEO. History of heart attack."
    result = underwrite_specialty(_bundle(text), InsuranceLine.KEY_PERSON)
    assert result.decision == UWDecision.REFER


def test_specialty_guidelines_in_corpus() -> None:
    g = builtin_guidelines()
    do = g.for_line("directors_and_officers")
    assert any(x.id == "DO-001" for x in do)
    tc = g.for_line("trade_credit")
    assert any(x.id == "TC-001" for x in tc)
    eo = g.for_line("errors_and_omissions")
    assert any(x.id == "EO-001" for x in eo)
    kp = g.for_line("key_person")
    assert any(x.id == "KP-001" for x in kp)
    # Property-only query set should still include universal guides
    prop = {x.id for x in g.for_line("commercial_property")}
    assert "CON-001" in prop
    assert "DO-001" not in prop


def test_classifier_specialty_types() -> None:
    assert InsuranceDocumentClassifier.classify("Trade credit application for Acme", "tc_app.pdf") == InsuranceDocumentType.TRADE_CREDIT_APPLICATION
    assert InsuranceDocumentClassifier.classify("Accounts receivable aging as of March", "ar.md") == InsuranceDocumentType.AR_AGING_REPORT
    assert InsuranceDocumentClassifier.classify("E&O application professional services", "eo.pdf") == InsuranceDocumentType.EO_APPLICATION
    assert InsuranceDocumentClassifier.classify("Corporate resolution authorizing key person policy", "res.pdf") == InsuranceDocumentType.CORPORATE_RESOLUTION


def test_intake_rate_decide_smoke_do() -> None:
    """Mini golden: tagged D&O package → detect → rate → specialty decide."""
    text = "Directors & Officers application. Aggregate limit: $1,000,000. Financial statements and balance sheet for last 3 years. No pending litigation."
    line = detect_insurance_line(text, "directors_and_officers")
    assert line == InsuranceLine.DIRECTORS_AND_OFFICERS
    quote = InsuranceRatingEngine().quote(_bundle(text), _memo(), line=line)
    assert quote.adjusted_premium > 0
    assert quote.metadata["specialty"] is True
    uw = underwrite_specialty(_bundle(text), line)
    # Clean package may still refer if financials keyword weak — accept or refer OK, not decline
    assert uw.decision in (UWDecision.ACCEPT, UWDecision.REFER, UWDecision.CONDITIONAL_ACCEPT)
