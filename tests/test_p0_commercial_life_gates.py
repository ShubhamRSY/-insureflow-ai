"""P0 commercial + life honesty gates: exposures, quote issuance, OFAC, life path."""

from __future__ import annotations

from insureflow.ingestion.insurance.classifier import InsuranceDocumentClassifier, InsuranceDocumentType
from insureflow.insurance.package_checklist import _types_for_label
from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import (
    CoverageDetail,
    FinancialData,
    LocationData,
    NamedInsured,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)
from insureflow.rating.commercial_actuarial import rate_extended_commercial, rate_workers_comp_ncci
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.rating.iso_forms import iso_form_schedule
from insureflow.rating.models import InsuranceLine, QuoteResult
from insureflow.rating.personal.life_rating import rate_life
from insureflow.underwriting.bind_gates import life_evidence_holds, quote_issuance_error
from insureflow.underwriting.life_financial import evaluate_life_financial
from insureflow.underwriting.life_reinsurance import evaluate_life_reinsurance
from insureflow.underwriting.lob_rating import apply_lob_rating
from insureflow.underwriting.personal_lines import extract_life_factors
from insureflow.underwriting.sanctions_gate import screen_submission
from insureflow.underwriting.surplus_lines import classify_surplus_lines


def _bundle(text: str = "", **fin) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="p0-1",
        structured=StructuredSubmission(
            submission_id="s1",
            named_insured=NamedInsured(legal_name=fin.pop("name", "Acme Manufacturing LLC")),
            locations=[LocationData(address="1 Main", city="Austin", state="TX", zip_code="78701", building_value=2_000_000, contents_value=500_000)],
            financial=FinancialData(annual_revenue=fin.get("revenue", 8_000_000), payroll=fin.get("payroll"), employee_count=fin.get("employees")),
            coverages=[CoverageDetail(coverage_type="gl", limit_amount=fin.get("limit", 0) or 0, deductible=0, premium=0)] if fin.get("limit") else [],
        ),
        unstructured=[UnstructuredSubmission(submission_id="u1", raw_text=text)] if text else [],
    )


def test_auto_without_units_is_ineligible():
    q = rate_extended_commercial(_bundle(), UnderwritingMemo(bundle_id="p0-1"), InsuranceLine.COMMERCIAL_AUTO)
    assert q is not None and q.eligible is False
    assert any("vehicle" in r.lower() or "power" in r.lower() for r in q.ineligibility_reasons)


def test_wc_oracle_emod_is_used():
    b = _bundle(payroll=1_200_000)
    b.structured.risk_profile = RiskProfile(ncci_class_code="5403")
    q = rate_workers_comp_ncci(b, UnderwritingMemo(bundle_id="p0-1"), state="IL", experience_mod=1.25)
    assert q.eligible is True
    assert q.metadata["experience_mod"] == 1.25
    assert q.metadata["emod_source"] == "ncci_oracle"


def test_catalog_only_commercial_product_not_quoted():
    engine = InsuranceRatingEngine()
    q = engine.quote(_bundle(), UnderwritingMemo(bundle_id="p0-1"), line=InsuranceLine.COMMERCIAL_PROPERTY, commercial_product_id="aviation")
    assert q.eligible is False
    assert q.metadata.get("rating_engine") == "catalog_only"
    assert any("catalog" in r.lower() for r in q.ineligibility_reasons)


def test_quote_issuance_blocks_ineligible_without_override():
    summary = {"quote": {"eligible": False, "ineligibility_reasons": ["Pilot manuals are not your SERFF filing"]}}
    err = quote_issuance_error(summary, action="quote", override_reason="")
    assert err and "ineligible" in err.lower()
    assert quote_issuance_error(summary, action="no_quote") is None


def test_ofac_hits_named_insured():
    b = _bundle(name="Rytera Sanctioned Test Person")
    result = screen_submission(b)
    assert result.cleared is False
    assert result.hits


def test_iso_forms_for_cgl():
    forms = iso_form_schedule(InsuranceLine.GENERAL_LIABILITY)
    assert any(f["number"] == "CG 00 01" for f in forms)


def test_es_requires_diligent_search():
    b = _bundle(text="This risk is surplus lines / E&S non-admitted after admitted decline.")
    sl = classify_surplus_lines(b, line=InsuranceLine.CYBER, state="NY", product_id="cyber_liability")
    assert sl.status == "surplus_lines"
    assert sl.can_bind is False
    assert sl.missing_documents


def test_checklist_matches_osha_esa_liquor_emod():
    assert InsuranceDocumentType.OSHA_LOG in _types_for_label("OSHA 300 log / 300A summary")
    assert InsuranceDocumentType.ENVIRONMENTAL_SITE_ASSESSMENT in _types_for_label("Phase I ESA environmental site assessment")
    assert InsuranceDocumentType.LIQUOR_LICENSE in _types_for_label("Liquor license / ABC license")
    assert InsuranceDocumentType.EXPERIENCE_MOD_WORKSHEET in _types_for_label("NCCI experience modification worksheet")
    assert InsuranceDocumentClassifier.classify("OSHA 300A summary for 2025", "osha-300a.pdf") == InsuranceDocumentType.OSHA_LOG


def test_lob_rating_does_not_overwrite_life_filing():
    quote = QuoteResult(
        bundle_id="p0-1",
        line=InsuranceLine.LIFE,
        base_premium=200.0,
        adjusted_premium=250.0,
        eligible=True,
        metadata={"rating_engine": "life_filing", "minimum_premium": 250.0},
    )
    out = apply_lob_rating(quote, _bundle(), UnderwritingMemo(bundle_id="p0-1"), line=InsuranceLine.LIFE)
    assert out.adjusted_premium == 250.0


def test_term_life_rates_and_wl_is_not_filed():
    text = "Face amount: $500000 Applicant age: 40 Sex: male Annual income: 120000 Beneficiary relationship: spouse"
    term = rate_life(_bundle(text), coverage_id="term_20", coverage_name="20-Year Level Term", product_id="level_term", state="IL")
    assert term.eligible is True
    assert term.metadata["rating_engine"] == "life_filing"
    assert term.adjusted_premium >= 250
    wl = rate_life(_bundle(text), coverage_id="wl", coverage_name="Traditional Whole Life", product_id="traditional_whole_life", state="IL")
    assert wl.eligible is False
    assert wl.metadata["product_family"] == "whole_life"
    assert any("filed" in r.lower() or "illustrative" in r.lower() for r in wl.ineligibility_reasons)


def test_life_income_not_net_worth():
    text = "Face amount: 1000000 Annual income: 80000 Net worth: 5000000 Beneficiary relationship: spouse Applicant age: 45"
    factors = extract_life_factors(_bundle(text))
    assert factors.income == 80_000
    assert factors.net_worth == 5_000_000
    fin = evaluate_life_financial(_bundle(text), factors=factors, product_id="level_term")
    assert fin.income == 80_000
    assert fin.net_worth == 5_000_000


def test_life_reinsurance_facultative_and_aps_hold():
    text = "Face amount: 12000000 Applicant age: 40 Annual income: 900000 Beneficiary relationship: spouse"
    re = evaluate_life_reinsurance(_bundle(text))
    assert re.facultative_required is True
    assert re.cession > 0
    holds = life_evidence_holds(
        _bundle(text),
        {"medical": {"require_aps": True, "require_paramed": True}, "facultative_required": True},
    )
    assert any("APS" in h for h in holds)
    assert any("Paramed" in h for h in holds)
    assert any("Facultative" in h for h in holds)


def test_replacement_1035_and_suitability_flags():
    text = (
        "Face amount: 250000 Applicant age: 68 Annual income: 90000 Beneficiary relationship: spouse "
        "This is a 1035 exchange replacing existing annuity. Variable universal life."
    )
    fin = evaluate_life_financial(_bundle(text), product_id="variable_universal_life")
    assert fin.exchange_1035 is True
    assert any("1035" in r or "Replacement" in r for r in fin.reasons)
    assert any("Suitability" in r or "suitability" in r.lower() for r in fin.reasons)
