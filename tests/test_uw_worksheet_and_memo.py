"""Regression tests for the live in-app result-view root-cause fixes:

- Insured Name must never silently become the internal bundle/job id.
- Premium buildup "Mod %" must reflect a real percentage swing, not a flat 0.0%.
- The Underwriting Worksheet must show life-specific fields (and hide P&C-only
  ones) for life insurance, instead of P&C concepts that don't apply.
- Document completeness must be folded into the primary decision rationale.
- Beneficiary review must actually run (not silently return dead data).
"""

from __future__ import annotations

from insureflow.agents.uw_decision_agent import UWDecisionAgent
from insureflow.models.agents import AgentResult, AgentType, RiskSeverity, UWDecision
from insureflow.models.submissions import NamedInsured, StructuredSubmission, SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.underwriting.beneficiary_review import review_beneficiaries
from insureflow.underwriting.lob_rating import _derived_modifier_pct, build_uw_worksheet
from insureflow.underwriting.memo_sync import build_memo_summary


def _uw_result() -> AgentResult:
    return AgentResult(agent_type=AgentType.UW_DECISION, agent_name="UWDecisionAgent")


def test_insured_name_never_equals_bundle_id_when_extraction_finds_nothing() -> None:
    bundle = SubmissionBundle(bundle_id="demo-978117349bca", structured=None)
    memo = UWDecisionAgent().produce_underwriting_memo(bundle, [], _uw_result())

    assert memo.insured_name != bundle.bundle_id
    assert memo.insured_name == ""
    assert any(f.title == "Insured name not extracted" for f in memo.key_findings)


def test_insured_name_extracted_when_present() -> None:
    bundle = SubmissionBundle(
        bundle_id="demo-978117349bca",
        structured=StructuredSubmission(submission_id="s1", named_insured=NamedInsured(legal_name="Jane Applicant")),
    )
    memo = UWDecisionAgent().produce_underwriting_memo(bundle, [], _uw_result())

    assert memo.insured_name == "Jane Applicant"
    assert not any(f.title == "Insured name not extracted" for f in memo.key_findings)


def test_derived_modifier_pct_for_multiplicative_life_factors() -> None:
    # Real cases from life_rating.py's schedule_modifications
    assert _derived_modifier_pct(RateComponent(name="underwriting_class", amount=0.82)) == -18.0
    assert _derived_modifier_pct(RateComponent(name="sex_factor", amount=0.88)) == -12.0
    assert _derived_modifier_pct(RateComponent(name="band_discount", amount=1.0)) == 0.0
    # Component that already has a real modifier_pct (commercial-lines convention) wins
    assert _derived_modifier_pct(RateComponent(name="cope_mod_pct", amount=1.0, modifier_pct=15.0)) == 15.0


def test_derived_modifier_pct_none_for_non_factor_components() -> None:
    # mortality_per_1000 / flat_extras / policy_fee are rates or dollar amounts,
    # not a factor away from 1.0 — (amount - 1) * 100 would be nonsense here.
    assert _derived_modifier_pct(RateComponent(name="mortality_per_1000", amount=1.5)) is None
    assert _derived_modifier_pct(RateComponent(name="policy_fee", amount=60.0)) is None
    assert _derived_modifier_pct(RateComponent(name="flat_extras", amount=0.0)) is None


def _life_bundle(text: str) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="test-worksheet",
        structured=StructuredSubmission(submission_id="s1", named_insured=NamedInsured(legal_name="Jane Applicant")),
        unstructured=[],
    )


def test_uw_worksheet_hides_pc_fields_and_shows_life_fields_for_life() -> None:
    quote = QuoteResult(
        bundle_id="b1",
        line=InsuranceLine.LIFE,
        base_premium=1000.0,
        adjusted_premium=900.0,
        schedule_modifications=[RateComponent(name="mortality_per_1000", amount=1.5)],
        metadata={"face_amount": 750000, "medical": {}, "life_reinsurance": {"cession_amount": 0, "applicable": True}},
    )
    from insureflow.models.agents import Recommendation, UnderwritingMemo

    memo = UnderwritingMemo(bundle_id="b1", decision=UWDecision.ACCEPT, recommendation=Recommendation(action="accept"))
    bundle = SubmissionBundle(bundle_id="b1", structured=None)

    worksheet = build_uw_worksheet(quote, bundle, memo, line=InsuranceLine.LIFE, insurance_line="life")

    assert worksheet["applicable_fields"]["deductible"] is False
    assert worksheet["applicable_fields"]["loss_ratio"] is False
    assert worksheet["applicable_fields"]["net_amount_at_risk"] is True
    assert worksheet["indicated_terms"]["deductible"] is None
    assert worksheet["life_terms"]["net_amount_at_risk"] == 750000
    assert worksheet["life_terms"]["mortality_rate_per_1000"] == 1.5
    assert "not applicable" in worksheet["loss_experience"]["basis"].lower()


def test_uw_worksheet_shows_pc_fields_for_commercial_property() -> None:
    quote = QuoteResult(bundle_id="b1", line=InsuranceLine.COMMERCIAL_PROPERTY, base_premium=1000.0, adjusted_premium=1000.0, metadata={})
    from insureflow.models.agents import Recommendation, UnderwritingMemo

    memo = UnderwritingMemo(bundle_id="b1", decision=UWDecision.ACCEPT, recommendation=Recommendation(action="accept"))
    bundle = SubmissionBundle(bundle_id="b1", structured=None)

    worksheet = build_uw_worksheet(quote, bundle, memo, line=InsuranceLine.COMMERCIAL_PROPERTY, insurance_line="commercial_property")

    assert worksheet["applicable_fields"]["deductible"] is True
    assert worksheet["applicable_fields"]["net_amount_at_risk"] is False
    assert worksheet["life_terms"] is None
    assert worksheet["indicated_terms"]["deductible"] is not None


def test_build_memo_summary_promotes_document_completeness_when_material() -> None:
    text = build_memo_summary(
        UWDecision.REFER,
        0.6,
        [],
        document_completeness_pct=0.4,
        missing_document_count=6,
        total_document_count=10,
    )
    assert "DOCUMENT COMPLETENESS" in text
    assert "40%" in text
    assert "6 of 10" in text


def test_build_memo_summary_omits_completeness_when_package_is_complete() -> None:
    text = build_memo_summary(
        UWDecision.ACCEPT,
        0.1,
        [],
        document_completeness_pct=1.0,
        missing_document_count=0,
        total_document_count=10,
    )
    assert "DOCUMENT COMPLETENESS" not in text


def test_review_beneficiaries_does_not_crash_on_missing_designation() -> None:
    # Regression guard for the dataclass/pydantic Field() mixup that made this
    # raise AttributeError('FieldInfo' object has no attribute 'isoformat')
    # on every call — this function was previously dead code (never invoked
    # by the pipeline) so the bug was never exercised.
    bundle = SubmissionBundle(bundle_id="b1", structured=None, unstructured=[])
    result = review_beneficiaries(bundle)

    assert result.record.beneficiaries == []
    assert any(f.severity == RiskSeverity.CRITICAL for f in result.findings)
    # Must serialize cleanly (this is what crashed before the fix)
    result.to_dict()
    result.record.to_dict()


def test_review_beneficiaries_extracts_named_beneficiary() -> None:
    from insureflow.models.submissions import UnstructuredSubmission

    bundle = SubmissionBundle(
        bundle_id="b1",
        structured=None,
        unstructured=[UnstructuredSubmission(submission_id="d1", source="beneficiary_form.md", raw_text="Primary beneficiary: John Smith")],
    )
    result = review_beneficiaries(bundle)
    assert len(result.record.beneficiaries) >= 1
    assert all(b.name == "john smith" for b in result.record.beneficiaries)
