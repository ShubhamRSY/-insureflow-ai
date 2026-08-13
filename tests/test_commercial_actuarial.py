"""Actuarial pricing depth — extended LOBs, NCCI WC, packages, line resolution."""

from __future__ import annotations

from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import (
    FinancialData,
    LocationData,
    NamedInsured,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
)
from insureflow.rating.commercial_actuarial import (
    rate_extended_commercial,
    rate_package_policy,
    rate_workers_comp_ncci,
    resolve_quote_line,
)
from insureflow.rating.models import InsuranceLine
from insureflow.underwriting.subjectivities import compute_bind_readiness, seed_subjectivities_from_conditions


def _bundle(**kwargs) -> SubmissionBundle:
    structured = StructuredSubmission(
        submission_id="t1",
        named_insured=NamedInsured(legal_name="Test Co"),
        locations=[LocationData(address="1 Main St", city="Austin", state="TX", zip_code="78701", building_value=2_000_000, contents_value=500_000)],
        financial=FinancialData(annual_revenue=10_000_000, payroll=2_400_000),
        risk_profile=RiskProfile(ncci_class_code="5403"),
    )
    return SubmissionBundle(bundle_id="ins-test", structured=structured, **kwargs)


def test_resolve_quote_line_prefers_product_id():
    line = resolve_quote_line(commercial_product_id="cyber_liability", text_blob="property SOV building value")
    assert line == InsuranceLine.CYBER


def test_resolve_quote_line_commercial_auto():
    line = resolve_quote_line(insurance_line="commercial_auto")
    assert line == InsuranceLine.COMMERCIAL_AUTO


def test_rate_cyber_manual():
    b = _bundle()
    m = UnderwritingMemo(bundle_id=b.bundle_id, insured_name="Test")
    from insureflow.models.submissions import CoverageDetail

    b.structured.coverages = [CoverageDetail(coverage_type="cyber", limit_amount=2_000_000, deductible=25_000, premium=0)]
    q = rate_extended_commercial(b, m, InsuranceLine.CYBER)
    assert q is not None
    assert q.eligible is True
    assert q.metadata["rating_engine"] == "cyber_manual"
    assert q.adjusted_premium >= 2500


def test_cyber_without_limit_is_ineligible():
    b = _bundle()
    m = UnderwritingMemo(bundle_id=b.bundle_id, insured_name="Test")
    q = rate_extended_commercial(b, m, InsuranceLine.CYBER)
    assert q is not None
    assert q.eligible is False
    assert any("limit" in r.lower() for r in q.ineligibility_reasons)


def test_rate_commercial_auto_units():
    b = _bundle()
    m = UnderwritingMemo(bundle_id=b.bundle_id, insured_name="Test")
    # inject fleet size via unstructured
    from insureflow.models.submissions import UnstructuredSubmission

    b.unstructured = [UnstructuredSubmission(submission_id="u1", raw_text="Fleet size: 12 power units Vehicles: 12")]
    q = rate_extended_commercial(b, m, InsuranceLine.COMMERCIAL_AUTO)
    assert q is not None
    assert q.metadata["units"] >= 12
    assert q.metadata["rating_engine"] == "commercial_auto_manual"


def test_ncci_wc_uses_class_and_payroll():
    b = _bundle()
    m = UnderwritingMemo(bundle_id=b.bundle_id, insured_name="Test")
    from insureflow.models.submissions import UnstructuredSubmission

    b.unstructured = [UnstructuredSubmission(submission_id="u1", raw_text="Experience modification: 1.12 e-mod: 1.12")]
    q = rate_workers_comp_ncci(b, m, state="IL")
    assert q.eligible is True
    assert q.metadata["ncci_class_code"] == "5403"
    assert q.metadata["rating_engine"] == "ncci_class_emod"
    assert q.metadata["payroll"] > 0
    assert q.metadata["experience_mod"] == 1.12
    assert q.adjusted_premium >= 1000


def test_ncci_wc_without_emod_is_ineligible():
    b = _bundle()
    m = UnderwritingMemo(bundle_id=b.bundle_id, insured_name="Test")
    q = rate_workers_comp_ncci(b, m, state="IL")
    assert q.eligible is False
    assert any("modification" in r.lower() or "e-mod" in r.lower() for r in q.ineligibility_reasons)


def test_gl_uses_sales_not_tiv():
    from insureflow.models.submissions import CoverageDetail
    from insureflow.rating.commercial_actuarial import rate_general_liability_iso

    b = _bundle()
    b.structured.coverages = [CoverageDetail(coverage_type="gl", limit_amount=1_000_000, deductible=5_000, premium=0)]
    m = UnderwritingMemo(bundle_id=b.bundle_id, insured_name="Test")
    q = rate_general_liability_iso(b, m, state="TX")
    assert q.eligible is True
    assert q.metadata["rating_engine"] == "iso_gl_sales"
    assert q.metadata["sales"] == 10_000_000


def test_bop_package_sections():
    b = _bundle()
    m = UnderwritingMemo(bundle_id=b.bundle_id, insured_name="Test")
    q = rate_package_policy(b, m, InsuranceLine.BOP)
    sections = q.metadata["package_sections"]
    assert len(sections) >= 3
    assert q.metadata["rating_engine"] == "package_section_rating"
    assert sum(s["adjusted_premium"] for s in sections) > 0


def test_cpp_skips_crime_and_auto_without_exposures():
    b = _bundle()
    m = UnderwritingMemo(bundle_id=b.bundle_id, insured_name="Test")
    q = rate_package_policy(b, m, InsuranceLine.COMMERCIAL_PACKAGE)
    assert q.eligible is True
    ids = {s["section"] for s in q.metadata["package_sections"]}
    assert "property" in ids and "general_liability" in ids
    assert "crime" not in ids and "commercial_auto" not in ids
    skipped = " ".join(q.metadata.get("skipped_sections") or [])
    assert "crime" in skipped and "commercial_auto" in skipped


def test_bind_readiness_from_conditions():
    results = {
        "quote": {"eligible": True},
        "open_conditions": ["Provide updated loss runs", "Confirm sprinkler certificate"],
        "human_checkpoints": [{"id": "uw_signoff", "status": "pending"}],
        "workflow_state": "pending_review",
    }
    results["subjectivities"] = seed_subjectivities_from_conditions(results)
    assert len(results["subjectivities"]) == 2
    br = compute_bind_readiness(results)
    assert br["ready_to_bind"] is False
    assert br["open_subjectivities"] == 2
