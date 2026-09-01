"""Per-leaf health UW — maternity ≠ OPD ≠ cardiac ≠ senior, etc."""

from __future__ import annotations

from insureflow.insurance.health_lobs import HEALTH_LINES
from insureflow.models.agents import UWDecision
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rating.personal.health_rating import rate_health
from insureflow.underwriting.health_uw import (
    health_product_terms,
    underwrite_health,
)

KYC = "Identity proof Aadhaar. Address proof utility bill. Age proof 10th marksheet. Passport-size photograph. Proposal form duly filled. Age: 34."


def _bundle(text: str, doc_type: str = "health_application") -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="health-uw",
        unstructured=[
            UnstructuredSubmission(submission_id="d1", document_type=doc_type, raw_text=text),
        ],
    )


def test_every_health_leaf_has_dedicated_lob_logic_path():
    # Every catalog leaf owns a dedicated logic path in insureflow.health.lobs
    # (the same architecture life insurance uses) — each of those paths
    # internally reuses one of the handlers below via underwrite_health()
    # rather than every catalog id being a handler key itself.
    from insureflow.health.lobs import PRODUCT_LOGIC_PATHS

    missing = [ln["id"] for ln in HEALTH_LINES if ln["id"] not in PRODUCT_LOGIC_PATHS]
    assert missing == [], missing
    assert len(PRODUCT_LOGIC_PATHS) == len(HEALTH_LINES)


def test_maternity_requires_marriage_opd_does_not():
    kyc_only = _bundle(KYC)
    mat = underwrite_health(kyc_only, product_id="maternity_inclusive")
    opd = underwrite_health(kyc_only, product_id="opd_cover")
    assert mat.product_family == "maternity"
    assert opd.product_family == "opd"
    assert mat.gates.get("marriage_certificate") == "fail"
    assert "marriage_certificate" not in opd.gates
    assert mat.decision == UWDecision.REFER
    assert opd.gates.get("bank_reimbursement") == "fail"
    assert opd.decision == UWDecision.REFER
    assert mat.decision == opd.decision  # both refer, different gates
    assert "bank_reimbursement" not in mat.gates


def test_maternity_pregnant_declines_opd_does_not():
    text = KYC + " Marriage certificate attached. Already pregnant 12 weeks gestation."
    mat = underwrite_health(_bundle(text), product_id="maternity_inclusive")
    opd = underwrite_health(
        _bundle(text + " Bank account IFSC for reimbursement."),
        product_id="opd_cover",
    )
    assert mat.decision == UWDecision.DECLINE
    assert mat.metadata.get("pregnant_at_proposal") is True
    assert any("pregnant" in r.lower() for r in mat.reasons)
    assert opd.product_family == "opd"
    assert opd.decision != UWDecision.DECLINE
    assert opd.gates.get("current_pregnancy_ineligible") is None


def test_maternity_complete_accepts_eligibility():
    text = KYC + " Marriage certificate. Medical history declaration. Not pregnant."
    mat = underwrite_health(_bundle(text), product_id="maternity_inclusive")
    assert mat.decision == UWDecision.ACCEPT
    assert mat.gates.get("marriage_certificate") == "pass"
    assert any("waiting period" in c.lower() for c in mat.conditions)


def test_opd_complete_does_not_require_marriage():
    text = KYC + " Bank account number IFSC cancelled cheque for OPD reimbursement."
    opd = underwrite_health(_bundle(text), product_id="opd_cover")
    assert opd.decision == UWDecision.ACCEPT
    assert opd.gates.get("bank_reimbursement") == "pass"
    assert opd.metadata.get("hospitalization_not_required") is True


def test_cardiac_requires_ecg_cancer_does_not():
    kyc = _bundle(KYC + " Family history of cancer and cardiac disease.")
    cancer = underwrite_health(kyc, product_id="disease_specific", coverage_id="cancer_care")
    cardiac = underwrite_health(kyc, product_id="disease_specific", coverage_id="cardiac_care")
    assert cancer.product_family == "cancer_care"
    assert cardiac.product_family == "cardiac_care"
    assert "ecg_mandatory" not in cancer.gates
    assert cardiac.gates.get("ecg_mandatory") == "fail"
    assert cardiac.decision == UWDecision.REFER
    assert cancer.decision != UWDecision.DECLINE


def test_cardiac_ecg_clears_heart_gate():
    text = KYC + " ECG cardiac screening report. Family cardiac history declaration."
    cardiac = underwrite_health(_bundle(text), product_id="disease_specific", coverage_id="cardiac_care")
    assert cardiac.gates.get("ecg_mandatory") == "pass"
    assert cardiac.decision == UWDecision.ACCEPT


def test_diabetes_requires_labs_and_meds():
    kyc = underwrite_health(_bundle(KYC), product_id="disease_specific", coverage_id="diabetes_kidney_care")
    assert kyc.product_family == "diabetes_kidney_care"
    assert kyc.gates.get("sugar_kft") == "fail"
    full = underwrite_health(
        _bundle(KYC + " Blood sugar HbA1c kidney function creatinine. Medication list metformin."),
        product_id="disease_specific",
        coverage_id="diabetes_kidney_care",
    )
    assert full.gates.get("sugar_kft") == "pass"
    assert full.gates.get("medication_list") == "pass"


def test_senior_under_60_declines_individual_does_not():
    young = _bundle(KYC.replace("Age: 34", "Age: 45") + " Medical declaration good health.")
    senior = underwrite_health(young, product_id="senior_standard")
    basic = underwrite_health(young, product_id="individual_basic")
    assert senior.decision == UWDecision.DECLINE
    assert any("60" in r for r in senior.reasons)
    assert basic.decision != UWDecision.DECLINE
    assert basic.product_family == "individual_basic"


def test_senior_62_requires_pre_policy_medical():
    text = KYC.replace("Age: 34", "Age: 62") + " Nominee details Aadhaar."
    senior = underwrite_health(_bundle(text), product_id="senior_standard")
    assert senior.decision == UWDecision.REFER
    assert senior.gates.get("pre_policy_medical") == "fail"
    complete = underwrite_health(
        _bundle(text + " Pre-policy medical check-up report attached."),
        product_id="senior_standard",
    )
    assert complete.gates.get("pre_policy_medical") == "pass"
    assert complete.decision == UWDecision.ACCEPT


def test_ci_rider_requires_base_policy_standalone_does_not():
    kyc = _bundle(KYC + " Medical declaration. ECG blood sugar lipid profile. Family medical history.")
    rider = underwrite_health(kyc, product_id="critical_illness_rider")
    standalone = underwrite_health(kyc, product_id="critical_illness_standalone")
    assert rider.product_family == "critical_illness_rider"
    assert standalone.product_family == "critical_illness"
    assert rider.gates.get("base_policy") == "fail"
    assert "base_policy" not in standalone.gates
    assert rider.decision == UWDecision.REFER
    assert standalone.decision == UWDecision.ACCEPT


def test_topup_vs_super_topup_deductible_basis():
    text = KYC + " Existing base policy copy. Medical declaration. Claim history of base policy."
    top = underwrite_health(_bundle(text), product_id="topup_plan")
    super_ = underwrite_health(_bundle(text), product_id="super_topup_plan")
    assert top.product_family == "topup"
    assert super_.product_family == "super_topup"
    assert top.metadata.get("deductible_basis") == "per_hospitalization"
    assert super_.metadata.get("deductible_basis") == "annual_aggregate"


def test_pa_hazardous_occupation_refers():
    office = underwrite_health(
        _bundle(KYC + " Occupation proof software office manager. Nominee details Aadhaar."),
        product_id="pa_individual",
    )
    mine = underwrite_health(
        _bundle(KYC + " Occupation proof underground mining blasting. Nominee details Aadhaar."),
        product_id="pa_individual",
    )
    assert office.metadata.get("occupation_class") == "I"
    assert office.decision == UWDecision.ACCEPT
    assert mine.metadata.get("occupation_class") == "IV"
    assert mine.decision == UWDecision.REFER


def test_disability_income_requires_income_ppd_does_not():
    text = KYC + " Occupation proof accountant. Medical fitness certificate. Nominee details."
    di = underwrite_health(_bundle(text), product_id="disability_income")
    ppd = underwrite_health(_bundle(text), product_id="disability_ppd")
    assert di.product_family == "disability_income"
    assert ppd.product_family == "disability_ppd"
    assert di.gates.get("income_proof") == "fail"
    assert "income_proof" not in ppd.gates
    assert di.decision == UWDecision.REFER
    assert ppd.decision == UWDecision.ACCEPT


def test_overseas_missing_passport_declines():
    no_pass = underwrite_health(_bundle(KYC + " Visa copy. Flight itinerary ticket."), product_id="overseas_health")
    full = underwrite_health(
        _bundle(KYC + " Passport number A123. Visa copy. Travel itinerary ticket."),
        product_id="overseas_health",
    )
    assert no_pass.decision == UWDecision.DECLINE
    assert no_pass.gates.get("passport") == "fail"
    assert full.gates.get("passport") == "pass"
    assert full.decision == UWDecision.ACCEPT


def test_ulip_requires_suitability_basic_does_not():
    kyc = _bundle(KYC + " Medical declaration.")
    ulip = underwrite_health(kyc, product_id="ulip_health")
    basic = underwrite_health(kyc, product_id="individual_basic")
    assert ulip.product_family == "ulip_health"
    assert ulip.gates.get("suitability") == "fail"
    assert "suitability" not in basic.gates
    assert ulip.decision == UWDecision.REFER
    assert basic.decision == UWDecision.ACCEPT


def test_group_employer_requires_company_kyc():
    empty = underwrite_health(_bundle(KYC), product_id="group_employer_mediclaim")
    full = underwrite_health(
        _bundle(KYC + " Company GST certificate. Company PAN. Employee list census payroll offer letter."),
        product_id="group_employer_mediclaim",
    )
    assert empty.product_family == "group_employer"
    assert empty.gates.get("company_kyc") == "fail"
    assert full.gates.get("company_kyc") == "pass"
    assert full.decision == UWDecision.ACCEPT


def test_rate_health_terms_differ_by_leaf():
    bundle = _bundle(KYC + " Sum insured 500000. OPD limit 500000.")
    mat = rate_health(bundle, product_id="maternity_inclusive", coverage_id="maternity_inclusive_std")
    opd = rate_health(bundle, product_id="opd_cover", coverage_id="opd_reimbursement")
    assert mat.eligible is True and opd.eligible is True
    assert mat.adjusted_premium > 0 and opd.adjusted_premium > 0
    assert mat.adjusted_premium != opd.adjusted_premium
    assert mat.metadata["benefit_type"] == "hospitalization_indemnity_maternity"
    assert opd.metadata["benefit_type"] == "opd_reimbursement"
    assert opd.metadata["payout_channel"] == "bank_reimbursement"
    assert mat.metadata["benefit_type"] != opd.metadata["benefit_type"]


def test_health_product_terms_coverage_overrides_disease():
    cancer = health_product_terms("disease_specific", "cancer_care")
    cardiac = health_product_terms("disease_specific", "cardiac_care")
    assert cancer["requires_ecg"] is False
    assert cardiac["requires_ecg"] is True
    assert cancer["disease"] == "cancer"
    assert cardiac["disease"] == "cardiac"
