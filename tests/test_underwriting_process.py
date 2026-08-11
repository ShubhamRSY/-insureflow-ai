"""Tests for the Chapter 4 underwriting-process additions.

Covers: preliminary processing (producer license verification, existing-records
search, FCRA pre-notification gate), case assignment systems, the four-hazard
aggregate, financial condition analysis, claim-file review, and MIB reports.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import (
    BrokerInfo,
    ClaimRecord,
    ClaimStatus,
    FinancialData,
    LocationData,
    NamedInsured,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
)
from insureflow.underwriting.case_assignment import (
    AssignmentMethod,
    CaseAssignmentEngine,
    CaseType,
    assign_by_face_amount,
    assign_by_geography,
    assign_by_last_name,
    assign_by_rotation,
)
from insureflow.underwriting.claim_file import (
    ClaimFileSignalType,
    review_claim_files,
)
from insureflow.underwriting.financial import FinancialGrade, assess_financial_condition
from insureflow.underwriting.hazards import (
    HazardCategory,
    assess_hazards,
    assess_legal_hazard,
    assess_morale_hazard,
)
from insureflow.underwriting.mib import (
    MibCode,
    MibCodeType,
    process_mib_codes,
    request_mib_report,
)
from insureflow.underwriting.preliminary import (
    ExistingRecord,
    ExistingRecordKind,
    ExistingRecordStatus,
    PreliminaryStepStatus,
    ProducerLicenseType,
    ProducerRecord,
    ProducerVerificationStatus,
    get_producer_registry,
    record_prior_application,
    reset_producer_registry,
    run_preliminary_check,
    search_existing_records,
    verify_producer,
)


def _bundle(insured: str = "Acme Manufacturing Co.", **overrides: Any) -> SubmissionBundle:
    data: dict[str, Any] = dict(
        bundle_id="bundle-ch4",
        structured=StructuredSubmission(
            submission_id="sub-ch4",
            named_insured=NamedInsured(legal_name=insured),
            broker=BrokerInfo(broker_name="Acme Insurance Agency", broker_id="pr-001"),
            locations=[LocationData(address="1 Main St", city="Dallas", state="TX", zip_code="75201")],
        ),
    )
    data.update(overrides)
    return SubmissionBundle(**data)


# ── 1. Producer / agent license verification ──────────────────────────────


def test_verify_verified_agent():
    reset_producer_registry()
    bundle = _bundle()
    broker = bundle.structured.broker if bundle.structured else None
    result = verify_producer(broker, line="commercial_property", state="TX")
    assert result.status == ProducerVerificationStatus.VERIFIED
    assert result.severity == RiskSeverity.LOW


def test_verify_broker_requires_referral():
    reset_producer_registry()
    broker = BrokerInfo(broker_name="Brighton & Wills Brokerage", broker_id="pr-002")
    result = verify_producer(broker, line="general_liability", state="TX")
    assert result.status == ProducerVerificationStatus.BROKER_REQUIRES_REFERRAL
    assert result.is_broker is True


def test_verify_not_appointed():
    reset_producer_registry()
    broker = BrokerInfo(broker_name="Gulf Coast Risk Partners", broker_id="pr-003")
    result = verify_producer(broker, line="general_liability", state="LA")
    assert result.status == ProducerVerificationStatus.NOT_APPOINTED
    assert result.severity == RiskSeverity.HIGH


def test_verify_not_licensed_state():
    reset_producer_registry()
    broker = BrokerInfo(broker_name="Brighton & Wills Brokerage", broker_id="pr-002")
    result = verify_producer(broker, line="general_liability", state="FL")
    assert result.status == ProducerVerificationStatus.NOT_LICENSED_STATE


def test_verify_not_licensed_life_line():
    reset_producer_registry()
    broker = BrokerInfo(broker_name="Brighton & Wills Brokerage", broker_id="pr-002")
    result = verify_producer(broker, line="life", state="TX")
    assert result.status == ProducerVerificationStatus.NOT_LICENSED_LINE


def test_verify_unknown_producer():
    reset_producer_registry()
    broker = BrokerInfo(broker_name="No Such Broker", broker_id="pr-999")
    result = verify_producer(broker, line="commercial_property", state="TX")
    assert result.status == ProducerVerificationStatus.NOT_FOUND


def test_producer_registry_upsert_roundtrip():
    reset_producer_registry()
    org = f"org-{uuid.uuid4().hex[:8]}"
    registry = get_producer_registry()
    prod = ProducerRecord(
        producer_id="pr-004",
        name="New Agency",
        license_types=[ProducerLicenseType.PROPERTY_CASUALTY_AGENT],
        licensed_states=["TX"],
        appointed_carriers=["insureflow"],
    )
    registry.upsert(prod, org_id=org)
    found = registry.lookup("pr-004", org_id=org)
    assert found is not None
    assert found.name == "New Agency"
    registry.remove("pr-004", org_id=org)
    reset_producer_registry()
    assert get_producer_registry().lookup("pr-004", org_id=org) is None


# ── 2. Existing-records search ─────────────────────────────────────────────


def test_search_no_records():
    bundle = _bundle(insured="Unique No-Record Co.")
    result = search_existing_records(bundle)
    assert not result.has_prior_application
    assert not result.has_prior_declination
    assert "No prior records" in result.summary


def test_search_finds_prior_declination():
    bundle = _bundle(insured="Declined Risk Inc.")
    key = "declined risk inc."
    record_prior_application(
        key,
        ExistingRecord(kind=ExistingRecordKind.PRIOR_DECLINATION, status=ExistingRecordStatus.DECLINED, carrier="OtherCo"),
    )
    result = search_existing_records(bundle)
    assert result.has_prior_declination
    assert "prior declination" in result.summary


def test_search_folds_in_loss_run():
    claim = ClaimRecord(
        claim_id="CL-1",
        date_of_loss=date(2023, 1, 1),
        line_of_business="general_liability",
        cause="slip and fall",
        incurred_amount=15_000,
        claim_status=ClaimStatus.CLOSED,
    )
    bundle = _bundle(
        insured="Loss Run Co.",
        structured=StructuredSubmission(
            submission_id="sub-ch4",
            named_insured=NamedInsured(legal_name="Loss Run Co."),
            broker=BrokerInfo(broker_name="Acme Insurance Agency", broker_id="pr-001"),
            risk_profile=RiskProfile(prior_claims=[claim]),
        ),
    )
    result = search_existing_records(bundle)
    assert result.records
    assert any(r.kind == ExistingRecordKind.PRIOR_LOSS for r in result.records)


# ── 3. Preliminary processing gate ─────────────────────────────────────────


def test_preliminary_check_holds_on_missing_documents():
    bundle = _bundle(insured="Prelim Hold Co.")
    completeness = {"completeness_pct": 40.0, "missing": ["Loss run", "Schedule of values"]}
    result = run_preliminary_check(bundle, line="commercial_property", state="TX", completeness=completeness)
    assert result.status == PreliminaryStepStatus.HOLD
    assert result.checks["completeness"] == PreliminaryStepStatus.HOLD


def test_preliminary_check_flags_fcra_without_disclosure():
    bundle = _bundle(insured="Prelim FCRA Co.")
    completeness = {"completeness_pct": 100.0, "missing": []}
    result = run_preliminary_check(bundle, line="personal_auto", state="TX", completeness=completeness, fcra_pre_notification_given=False)
    assert result.checks["fcra"] == PreliminaryStepStatus.FLAG
    assert result.fcra_pre_notification_required


def test_preliminary_check_passes_clean_case():
    bundle = _bundle(insured="Prelim Clean Co.")
    completeness = {"completeness_pct": 100.0, "missing": []}
    result = run_preliminary_check(bundle, line="commercial_property", state="TX", completeness=completeness, fcra_pre_notification_given=True)
    assert result.status == PreliminaryStepStatus.PASS
    assert result.checks["agent"] == PreliminaryStepStatus.PASS


# ── 4. Case assignment systems ─────────────────────────────────────────────


def test_assign_by_face_amount_bands():
    assert assign_by_face_amount(100_000).assigned_desk == "junior_desk"
    assert assign_by_face_amount(500_000).assigned_desk == "standard_desk"
    assert assign_by_face_amount(2_000_000).assigned_desk == "senior_desk"
    assert assign_by_face_amount(50_000_000).assigned_desk == "executive_desk"


def test_assign_by_geography():
    assert assign_by_geography("TX").assigned_desk == "southwest_desk"
    assert assign_by_geography("CA").assigned_desk == "west_desk"
    assert assign_by_geography("ZZ").assigned_desk == "general_desk"


def test_assign_by_last_name():
    assert assign_by_last_name("Archer").assigned_desk == "desk_af"
    assert assign_by_last_name("Miller").assigned_desk == "desk_gm"
    assert assign_by_last_name("Zebra").assigned_desk == "desk_sz"


def test_assign_by_rotation_cycles():
    desks = {assign_by_rotation(i).assigned_desk for i in range(12)}
    assert len(desks) == 4


def test_engine_priority_face_amount_first():
    engine = CaseAssignmentEngine()
    result = engine.assign(case_id="C-1", face_amount=2_000_000, state="CA", insured_name="Miller")
    assert result.method == AssignmentMethod.FACE_AMOUNT
    assert result.case_id == "C-1"


def test_engine_forced_method():
    engine = CaseAssignmentEngine(method=AssignmentMethod.GEOGRAPHIC)
    result = engine.assign(case_id="C-2", face_amount=2_000_000, state="FL")
    assert result.method == AssignmentMethod.GEOGRAPHIC
    assert result.assigned_desk == "gulf_desk"


def test_engine_application_type():
    engine = CaseAssignmentEngine(method=AssignmentMethod.APPLICATION_TYPE)
    result = engine.assign(case_id="C-3", case_type=CaseType.RENEWAL)
    assert result.assigned_desk == "renewal_desk"


# ── 5. Four-hazard aggregate ───────────────────────────────────────────────


def _prop_bundle() -> SubmissionBundle:
    return _bundle(
        structured=StructuredSubmission(
            submission_id="sub-ch4",
            named_insured=NamedInsured(legal_name="Acme Manufacturing Co."),
            broker=BrokerInfo(broker_name="Acme Insurance Agency", broker_id="pr-001"),
            risk_profile=RiskProfile(
                construction_type="wood frame",
                occupancy_type="manufacturing",
                protection_class=9,
                sprinklered=False,
            ),
            locations=[LocationData(address="1 Main St", city="Dallas", state="TX", zip_code="75201", year_built=1950, protection_class=9)],
        )
    )


def test_hazard_profile_has_all_four_categories():
    profile = assess_hazards(_prop_bundle())
    assert profile.physical is not None
    assert profile.moral is not None
    assert profile.morale is not None
    assert profile.legal is not None
    assert profile.worst_severity() in ("low", "flagged", "high", "critical")


def test_morale_hazard_detects_markers():
    bundle = _bundle(
        structured=StructuredSubmission(
            submission_id="sub-ch4",
            named_insured=NamedInsured(legal_name="Acme Manufacturing Co."),
            broker=BrokerInfo(broker_name="Acme Insurance Agency", broker_id="pr-001"),
        )
    )
    bundle.unstructured = [
        type(
            "Doc",
            (),
            {
                "document_type": "inspection_report",
                "raw_text": "Inspection notes: poor housekeeping, clutter, debris and deferred maintenance throughout the facility.",
                "extracted_fields": {},
            },
        )()
    ]
    assessment = assess_morale_hazard(bundle)
    assert assessment.status in ("flagged", "high")
    assert any(s.category == HazardCategory.MORALE for s in assessment.signals)


def test_legal_hazard_detects_litigation():
    bundle = _bundle(
        structured=StructuredSubmission(
            submission_id="sub-ch4",
            named_insured=NamedInsured(legal_name="Acme Manufacturing Co."),
            broker=BrokerInfo(broker_name="Acme Insurance Agency", broker_id="pr-001"),
        )
    )
    bundle.unstructured = [
        type(
            "Doc",
            (),
            {
                "document_type": "supplemental",
                "raw_text": "The insured is engaged in active litigation; claimant's attorney filed suit last quarter.",
                "extracted_fields": {},
            },
        )()
    ]
    assessment = assess_legal_hazard(bundle)
    assert assessment.status in ("flagged", "high")
    assert assessment.signals


# ── 6. Financial condition analysis ────────────────────────────────────────


def test_financial_strong_ratios():
    financial = FinancialData(total_asset_value=1_000_000, annual_revenue=500_000, credit_rating="AA")
    bundle = _bundle(structured=StructuredSubmission(submission_id="s", financial=financial))
    result = assess_financial_condition(bundle)
    assert result.grade in (FinancialGrade.STRONG, FinancialGrade.ADEQUATE)


def test_financial_critical_credit_rating():
    financial = FinancialData(credit_rating="CCC")
    bundle = _bundle(structured=StructuredSubmission(submission_id="s", financial=financial))
    result = assess_financial_condition(bundle)
    assert result.grade == FinancialGrade.CRITICAL
    assert result.severity == RiskSeverity.CRITICAL


def test_financial_ratio_from_balance_figures():
    bundle = _bundle()
    doc = type(
        "Doc",
        (),
        {
            "document_type": "financial_statement",
            "raw_text": "",
            "extracted_fields": {
                "current_assets": [type("F", (), {"value": "200000"})()],
                "current_liabilities": [type("F", (), {"value": "100000"})()],
                "total_assets": [type("F", (), {"value": "1000000"})()],
                "total_liabilities": [type("F", (), {"value": "900000"})()],
            },
        },
    )()
    bundle.unstructured = [doc]
    result = assess_financial_condition(bundle)
    assert result.ratios is not None
    assert result.ratios.current_ratio == 2.0
    assert result.ratios.debt_ratio == 0.9
    assert result.grade == FinancialGrade.ADEQUATE  # single weakness → adequate, not weak


def test_financial_insufficient_data():
    bundle = _bundle(structured=StructuredSubmission(submission_id="s"))
    result = assess_financial_condition(bundle)
    assert result.grade == FinancialGrade.ADEQUATE
    assert result.findings


# ── 7. Claim-file review ───────────────────────────────────────────────────


def _claim_bundle() -> SubmissionBundle:
    claims = [
        ClaimRecord(
            claim_id="CL-1",
            date_of_loss=date(2022, 1, 1),
            line_of_business="property",
            cause="leak",
            description="water leak around old pipes",
            incurred_amount=1_200,
            claim_status=ClaimStatus.CLOSED,
        ),
        ClaimRecord(
            claim_id="CL-2",
            date_of_loss=date(2022, 6, 1),
            line_of_business="property",
            cause="wear and tear",
            description="roof wear and tear",
            incurred_amount=900,
            claim_status=ClaimStatus.CLOSED,
        ),
    ]
    return _bundle(
        structured=StructuredSubmission(
            submission_id="sub-ch4",
            named_insured=NamedInsured(legal_name="Acme Manufacturing Co."),
            broker=BrokerInfo(broker_name="Acme Insurance Agency", broker_id="pr-001"),
            risk_profile=RiskProfile(prior_claims=claims),
        )
    )


def test_claim_file_review_detects_small_claims():
    review = review_claim_files(_claim_bundle())
    assert review.small_claim_count == 2
    assert any(s.signal_type == ClaimFileSignalType.SMALL_CLAIM_PATTERN for s in review.signals)


def test_claim_file_review_detects_wear_and_tear():
    review = review_claim_files(_claim_bundle())
    assert review.wear_tear_count == 2
    assert review.status in ("flagged", "high")


def test_claim_file_review_clean():
    bundle = _bundle(structured=StructuredSubmission(submission_id="s"))
    review = review_claim_files(bundle)
    assert review.total_claims == 0
    assert review.status == "low"
    assert "no concerning" in review.summary.lower()


# ── 8. MIB report handling ─────────────────────────────────────────────────


def test_mib_report_no_hit():
    bundle = _bundle(structured=StructuredSubmission(submission_id="s"))
    report = request_mib_report(bundle)
    assert report.no_hit
    assert report.codes == []


def test_mib_discrepancy_undisclosed_condition():
    codes = [MibCode(code="HD", code_type=MibCodeType.HEART_DISEASE, description="Heart disease", reported_date=date(2021, 1, 1))]
    discrepancies = process_mib_codes(codes, disclosed_conditions=["diabetes"])
    assert len(discrepancies) == 1
    assert discrepancies[0].severity == RiskSeverity.CRITICAL


def test_mib_disclosed_condition_matches():
    codes = [MibCode(code="DIA", code_type=MibCodeType.DIABETES, description="Diabetes", reported_date=date(2021, 1, 1))]
    discrepancies = process_mib_codes(codes, disclosed_conditions=["diabetes"])
    assert discrepancies == []
