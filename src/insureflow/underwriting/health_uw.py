"""Product-specific retail health underwriting.

One pipeline, distinct gates per leaf. Does not invent premium — eligibility,
waiting periods, and missing-document referrals only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.personal_lines import _blob, _int_field, _money

# Hazardous PA / disability occupations — class IV / uninsurable on standard PA.
_HAZARDOUS_OCCUPATION = (
    "mining",
    "underground mine",
    "blasting",
    "explosives",
    "stunt",
    "circus",
    "oil rig",
    "offshore rig",
    "high tension",
    "high-voltage",
    "armed forces combat",
    "combat duty",
    "window cleaning high rise",
)

_PREGNANT = (
    r"\bpregnant\b",
    r"\bpregnancy\b",
    r"\bgravida\b",
    r"weeks?\s+gestation",
    r"\blmp\b",
    r"already pregnant",
)

_KYC_NEEDLES = {
    "identity": ("identity proof", "aadhaar", "passport", "voter id", "photo id", "pan card", "driver"),
    "address": ("address proof", "utility bill", "proof of address"),
    "age": ("age proof", "birth certificate", "10th marksheet", "date of birth", "dob", "age:"),
    "photo": ("photograph", "passport-size", "passport size photo"),
    "proposal": ("proposal form", "health application", "mediclaim proposal", "master proposal"),
}


@dataclass
class HealthUWDecision:
    decision: UWDecision
    product_id: str
    coverage_id: str
    category_id: str
    product_family: str
    reasons: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    gates: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "product_id": self.product_id,
            "coverage_id": self.coverage_id,
            "category_id": self.category_id,
            "product_family": self.product_family,
            "reasons": list(self.reasons),
            "conditions": list(self.conditions),
            "gates": dict(self.gates),
            **dict(self.metadata or {}),
        }


@dataclass
class _Ctx:
    bundle: SubmissionBundle
    blob: str
    types: set[str]
    product_id: str
    coverage_id: str
    category_id: str
    age: int | None
    sum_insured: float


def _doc_types(bundle: SubmissionBundle) -> set[str]:
    out: set[str] = set()
    for doc in bundle.unstructured or []:
        dt = str(getattr(doc, "document_type", "") or "").strip().lower()
        if dt:
            out.add(dt)
    return out


def _has_text(blob: str, *needles: str) -> bool:
    return any(n.lower() in blob for n in needles if n)


def _has_type(types: set[str], *wanted: str) -> bool:
    return any(w in types for w in wanted)


def _present(ctx: _Ctx, *, types: tuple[str, ...] = (), needles: tuple[str, ...] = ()) -> bool:
    if types and _has_type(ctx.types, *types):
        return True
    if needles and _has_text(ctx.blob, *needles):
        return True
    return False


def _kyc_gates(ctx: _Ctx) -> list[tuple[str, bool, str]]:
    gates: list[tuple[str, bool, str]] = []
    for key, needles in _KYC_NEEDLES.items():
        ok = _has_text(ctx.blob, *needles)
        if key == "identity":
            ok = ok or _has_type(ctx.types, "photo_id", "health_application")
        elif key == "address":
            ok = ok or _has_type(ctx.types, "proof_of_address")
        elif key == "age":
            ok = ok or _has_type(ctx.types, "age_proof", "child_birth_certificate") or ctx.age is not None
        elif key == "photo":
            ok = ok or _has_type(ctx.types, "passport_photo")
        elif key == "proposal":
            ok = ok or _has_type(ctx.types, "health_application", "enrollment_form")
        gates.append((f"kyc_{key}", ok, f"Missing {key} proof" if not ok else f"{key} present"))
    return gates


def _is_pregnant(blob: str) -> bool:
    if re.search(r"\b(?:not|no)\s+(?:currently\s+)?pregnant\b", blob, re.I):
        return False
    return any(re.search(p, blob, re.I) for p in _PREGNANT)


def _occupation_class(blob: str) -> str:
    if any(k in blob for k in _HAZARDOUS_OCCUPATION):
        return "IV"
    if any(k in blob for k in ("factory worker", "driver", "mechanic", "construction labour", "welder")):
        return "III"
    if any(k in blob for k in ("supervisor", "sales executive", "field sales", "teacher")):
        return "II"
    if any(k in blob for k in ("office", "accountant", "software", "clerk", "manager", "desk")):
        return "I"
    return ""


def _finding(title: str, description: str, severity: RiskSeverity, family: str) -> Finding:
    return Finding(title=title, description=description, severity=severity, category=f"health_{family}")


def _finalize(
    ctx: _Ctx,
    *,
    family: str,
    extra_gates: list[tuple[str, bool, str, RiskSeverity]],
    conditions: list[str] | None = None,
    extra_reasons: list[str] | None = None,
    extra_findings: list[Finding] | None = None,
    metadata: dict[str, Any] | None = None,
) -> HealthUWDecision:
    findings = list(extra_findings or [])
    reasons = list(extra_reasons or [])
    conds = list(conditions or [])
    gate_map: dict[str, str] = {}

    decline = False
    refer = False
    conditional = False

    for gid, ok, msg in _kyc_gates(ctx):
        gate_map[gid] = "pass" if ok else "fail"
        if not ok:
            refer = True
            reasons.append(msg)
            findings.append(_finding("KYC incomplete", msg, RiskSeverity.HIGH, family))

    for gid, ok, msg, sev in extra_gates:
        gate_map[gid] = "pass" if ok else "fail"
        if ok:
            continue
        reasons.append(msg)
        findings.append(_finding(gid.replace("_", " ").title(), msg, sev, family))
        if sev == RiskSeverity.CRITICAL:
            decline = True
        elif sev == RiskSeverity.HIGH:
            refer = True
        else:
            conditional = True

    if decline:
        decision = UWDecision.DECLINE
    elif refer:
        decision = UWDecision.REFER
    elif conditional:
        decision = UWDecision.CONDITIONAL_ACCEPT
    else:
        decision = UWDecision.ACCEPT
        conds.append("Eligibility clear — filed health rate manual applies (filing HLTH-2026-01)")

    terms = health_product_terms(ctx.product_id, ctx.coverage_id)
    meta = {
        "age": ctx.age,
        "sum_insured": ctx.sum_insured,
        "occupation_class": _occupation_class(ctx.blob) or None,
        "pregnant": _is_pregnant(ctx.blob),
        **terms,
        **(metadata or {}),
    }
    return HealthUWDecision(
        decision=decision,
        product_id=ctx.product_id,
        coverage_id=ctx.coverage_id,
        category_id=ctx.category_id,
        product_family=family,
        reasons=reasons,
        conditions=conds,
        findings=findings,
        gates=gate_map,
        metadata=meta,
    )


# ── leaf handlers ───────────────────────────────────────────────────────────


def _uw_individual_basic(ctx: _Ctx) -> HealthUWDecision:
    decl = _present(
        ctx,
        types=("health_questionnaire",),
        needles=("medical declaration", "self-declared health", "self declared health", "good health"),
    )
    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        ("medical_declaration", decl, "Medical declaration (self-declared health status) required", RiskSeverity.HIGH),
    ]
    if ctx.age is not None and ctx.age >= 60:
        extra.append(
            (
                "age_fit",
                False,
                "Age 60+ — route to senior citizen health, not individual basic",
                RiskSeverity.HIGH,
            )
        )
    conds = ["Standard initial waiting period / PED waiting period apply per filing"]
    return _finalize(ctx, family="individual_basic", extra_gates=extra, conditions=conds)


def _uw_individual_comprehensive(ctx: _Ctx) -> HealthUWDecision:
    income = _present(ctx, types=("income_proof", "financial_statement"), needles=("income proof", "salary slip", "itr", "form 16"))
    medical = _present(ctx, types=("medical_exam",), needles=("pre-policy medical", "pre policy medical", "medical check-up", "medical checkup"))
    porting = _has_text(ctx.blob, "porting", "portability", "existing policy", "already insured")
    existing = _present(ctx, types=("dec_page",), needles=("existing policy", "prior policy", "policy copy"))
    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        ("income_proof", income, "Income proof required for higher sum insured comprehensive cover", RiskSeverity.HIGH),
    ]
    needs_medical = (ctx.age is not None and ctx.age >= 45) or (ctx.sum_insured >= 500_000)
    extra.append(
        (
            "pre_policy_medical",
            medical or not needs_medical,
            "Pre-policy medical check-up required above age 45 / SI ₹5L",
            RiskSeverity.HIGH,
        )
    )
    extra.append(
        (
            "portability_file",
            existing or not porting,
            "Existing policy details required when porting / already insured",
            RiskSeverity.HIGH,
        )
    )
    return _finalize(
        ctx,
        family="individual_comprehensive",
        extra_gates=extra,
        conditions=["High-SI financial suitability; PED / portability continuity per filing"],
    )


def _uw_maternity(ctx: _Ctx) -> HealthUWDecision:
    marriage = _present(
        ctx,
        types=("marriage_certificate",),
        needles=("marriage certificate", "marital status married", "proof of marriage"),
    )
    doctor = _present(
        ctx,
        types=("doctor_certificate",),
        needles=("doctor's confirmation", "doctors confirmation", "obstetric", "pregnancy confirmation"),
    )
    pregnant = _is_pregnant(ctx.blob)
    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        ("marriage_certificate", marriage, "Marriage certificate mandatory for maternity cover", RiskSeverity.HIGH),
        (
            "medical_history",
            _present(ctx, types=("health_questionnaire", "pre_existing_declaration"), needles=("medical history", "medical declaration")),
            "Medical history declaration required",
            RiskSeverity.HIGH,
        ),
    ]
    conds = ["Maternity waiting period typically 9–36 months per filing — do not invent the term"]
    extra_findings: list[Finding] = []
    extra_reasons: list[str] = []
    if pregnant:
        extra.append(
            (
                "not_currently_pregnant",
                doctor,  # confirmation must be on file even if we decline
                "Doctor's confirmation required when already pregnant at proposal",
                RiskSeverity.HIGH,
            )
        )
        extra.append(
            (
                "current_pregnancy_ineligible",
                False,
                "Already pregnant at proposal — current pregnancy is ineligible; waiting period / decline maternity benefit",
                RiskSeverity.CRITICAL,
            )
        )
        extra_reasons.append("Maternity benefit cannot incept for a pregnancy already in progress")
        extra_findings.append(
            _finding(
                "Current pregnancy",
                "In-force pregnancy at proposal is a maternity knockout on this product.",
                RiskSeverity.CRITICAL,
                "maternity",
            )
        )
    return _finalize(
        ctx,
        family="maternity",
        extra_gates=extra,
        conditions=conds,
        extra_reasons=extra_reasons,
        extra_findings=extra_findings,
        metadata={"pregnant_at_proposal": pregnant, "requires_marital_status": True},
    )


def _uw_opd(ctx: _Ctx) -> HealthUWDecision:
    bank = _present(
        ctx,
        types=("bank_ach_form",),
        needles=("bank account", "cancelled cheque", "ifsc", "reimbursement account", "account number"),
    )
    extra = [
        ("bank_reimbursement", bank, "Bank account details required for OPD reimbursement payouts", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="opd",
        extra_gates=extra,
        conditions=["OPD sub-limits and per-consult caps are filing-specific — do not invent"],
        metadata={"payout_channel": "bank_reimbursement", "hospitalization_not_required": True},
    )


def _uw_ulip_health(ctx: _Ctx) -> HealthUWDecision:
    income = _present(ctx, types=("income_proof",), needles=("income proof", "salary slip", "itr", "form 16"))
    pan = _present(ctx, types=("photo_id",), needles=("pan card", "permanent account number", "pan "))
    bank = _present(ctx, types=("bank_ach_form",), needles=("cancelled cheque", "bank account", "ifsc"))
    suitability = _present(
        ctx,
        types=("suitability_questionnaire",),
        needles=("risk profile", "suitability form", "suitability questionnaire", "risk appetite"),
    )
    extra = [
        ("income_proof", income, "Income proof mandatory — investment component needs financial suitability", RiskSeverity.HIGH),
        ("pan_kyc", pan, "PAN mandatory for investment-linked health (KYC)", RiskSeverity.HIGH),
        ("bank_fund", bank, "Bank / cancelled cheque required for fund-linked transactions", RiskSeverity.HIGH),
        ("suitability", suitability, "Risk profile / suitability form required for ULIP-type health", RiskSeverity.HIGH),
    ]
    if not income and _has_text(ctx.blob, "high risk", "aggressive"):
        extra.append(("suitability_income", False, "Aggressive risk profile without income proof — not suitable", RiskSeverity.CRITICAL))
    return _finalize(
        ctx,
        family="ulip_health",
        extra_gates=extra,
        conditions=["Do not invent fund returns or ULIP charges"],
        metadata={"has_investment_component": True},
    )


def _uw_floater_standard(ctx: _Ctx) -> HealthUWDecision:
    marriage = _present(ctx, types=("marriage_certificate",), needles=("marriage certificate", "spouse", "marital"))
    kids = _present(ctx, types=("child_birth_certificate", "age_proof"), needles=("birth certificate", "child dob", "children age"))
    member_decl = _present(
        ctx,
        types=("health_questionnaire",),
        needles=("medical declaration", "each member", "all members"),
    )
    extra = [
        ("spouse_relationship", marriage, "Marriage certificate required to prove spouse relationship", RiskSeverity.HIGH),
        ("child_age_proof", kids or not _has_text(ctx.blob, "child", "son", "daughter", "kids"), "Birth certificates of children required", RiskSeverity.HIGH),
        ("member_medicals", member_decl, "Medical declaration required for each floater member", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="family_floater", extra_gates=extra, conditions=["Shared SI floater — member ages drive rating once filed"])


def _uw_floater_parent(ctx: _Ctx) -> HealthUWDecision:
    rel = _present(
        ctx,
        types=("child_birth_certificate",),
        needles=("relationship proof", "ration card", "parent-child", "birth certificate showing parent"),
    )
    parent_med = _present(
        ctx,
        types=("medical_exam",),
        needles=("pre-policy medical", "parent medical", "parents check-up", "parent checkup"),
    )
    illness = _present(
        ctx,
        types=("pre_existing_declaration", "health_questionnaire"),
        needles=("existing illness", "pre-existing", "parent illness"),
    )
    extra = [
        ("relationship_proof", rel, "Relationship proof required for parent-inclusive floater", RiskSeverity.HIGH),
        ("parent_pre_policy_medical", parent_med, "Pre-policy medical of parents is mandatory (age-related risk)", RiskSeverity.HIGH),
        ("parent_illness_decl", illness, "Existing illness declaration required especially for parents", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="family_floater_parent", extra_gates=extra, conditions=["Parent PED waiting / loading per filing"])


def _uw_floater_multiyear(ctx: _Ctx) -> HealthUWDecision:
    decl = _present(ctx, types=("health_questionnaire",), needles=("medical declaration",))
    bank = _present(ctx, types=("bank_ach_form",), needles=("auto-debit", "auto debit", "ecs", "nach", "bank", "cancelled cheque"))
    extra = [
        ("medical_declaration", decl, "Medical declaration required", RiskSeverity.HIGH),
        ("multi_year_payment", bank, "Bank / payment instrument needed if multi-year premium auto-debit opted", RiskSeverity.MODERATE),
    ]
    conds = []
    if not bank:
        conds.append("Issue annual-pay only until auto-debit instrument is on file")
    return _finalize(ctx, family="family_floater_multiyear", extra_gates=extra, conditions=conds)


def _uw_floater_restore(ctx: _Ctx) -> HealthUWDecision:
    decl = _present(ctx, types=("health_questionnaire",), needles=("medical declaration",))
    porting = _has_text(ctx.blob, "porting", "portability", "previous insurer", "another insurer")
    claims = _present(ctx, types=("loss_run",), needles=("claim history", "previous claim", "loss run", "claims experience"))
    extra = [
        ("medical_declaration", decl, "Medical declaration required", RiskSeverity.HIGH),
        ("prior_claims", claims or not porting, "Previous claim history required when porting a restore floater", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="family_floater_restore",
        extra_gates=extra,
        conditions=["Restore / refill is filing-specific — do not invent refill count"],
    )


def _uw_ci_standalone(ctx: _Ctx) -> HealthUWDecision:
    labs = _present(
        ctx,
        types=("medical_exam",),
        needles=("ecg", "blood sugar", "lipid profile", "medical test report"),
    )
    family = _present(
        ctx,
        types=("family_medical_history",),
        needles=("family medical history", "family history"),
    )
    extra = [
        ("ci_labs", labs, "ECG / blood sugar / lipid profile often mandatory for standalone CI", RiskSeverity.HIGH),
        ("family_history", family, "Family medical history form required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="critical_illness", extra_gates=extra, conditions=["CI definitions and survival period are filing-specific"])


def _uw_ci_rider(ctx: _Ctx) -> HealthUWDecision:
    base = _present(ctx, types=("dec_page",), needles=("base policy", "existing policy copy", "policy number", "base mediclaim"))
    decl = _present(ctx, types=("health_questionnaire",), needles=("medical declaration",))
    extra = [
        ("base_policy", base, "Existing base policy copy required — rider cannot attach without it", RiskSeverity.HIGH),
        ("medical_declaration", decl, "Medical declaration form required for CI rider", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="critical_illness_rider", extra_gates=extra, conditions=["Rider follows base policy terms"])


def _uw_cancer_care(ctx: _Ctx) -> HealthUWDecision:
    family = _present(
        ctx,
        types=("family_medical_history",),
        needles=("family history of cancer", "cancer family", "family history"),
    )
    labs = _present(ctx, types=("medical_exam",), needles=("medical test", "biopsy", "oncology", "as advised"))
    extra = [
        ("cancer_family_history", family, "Family history of cancer declaration required", RiskSeverity.HIGH),
        ("cancer_labs", labs, "Medical test reports as advised by insurer required", RiskSeverity.MODERATE),
    ]
    return _finalize(
        ctx,
        family="cancer_care",
        extra_gates=extra,
        conditions=["Cancer-care definitions / staging per filing"],
        metadata={"requires_ecg": False, "disease": "cancer"},
    )


def _uw_cardiac_care(ctx: _Ctx) -> HealthUWDecision:
    ecg = _present(ctx, types=("medical_exam",), needles=("ecg", "ekg", "cardiac screening", "echo", "tmt"))
    family = _present(
        ctx,
        types=("family_medical_history",),
        needles=("family cardiac", "family history of heart", "cardiac history", "family history"),
    )
    extra = [
        ("ecg_mandatory", ecg, "ECG / cardiac screening report is mandatory for heart care", RiskSeverity.HIGH),
        ("cardiac_family_history", family, "Family cardiac history declaration required", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="cardiac_care",
        extra_gates=extra,
        conditions=["Cardiac event definitions per filing"],
        metadata={"requires_ecg": True, "disease": "cardiac"},
    )


def _uw_diabetes_kidney(ctx: _Ctx) -> HealthUWDecision:
    labs = _present(
        ctx,
        types=("medical_exam",),
        needles=("blood sugar", "hba1c", "a1c", "kidney function", "kft", "creatinine", "egfr"),
    )
    meds = _present(ctx, types=("medication_list",), needles=("medication", "prescription", "insulin", "metformin"))
    extra = [
        ("sugar_kft", labs, "Blood sugar / kidney function test reports are mandatory", RiskSeverity.HIGH),
        ("medication_list", meds, "Existing medication details required", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="diabetes_kidney_care",
        extra_gates=extra,
        conditions=["Diabetes/CKD staging and exclusions per filing"],
        metadata={"disease": "diabetes_kidney"},
    )


def _uw_ci_multistage(ctx: _Ctx) -> HealthUWDecision:
    labs = _present(ctx, types=("medical_exam",), needles=("detailed medical", "baseline", "medical test report"))
    family = _present(ctx, types=("family_medical_history",), needles=("family medical history", "family history"))
    extra = [
        ("baseline_medicals", labs, "Detailed baseline medical test reports required for multi-stage CI", RiskSeverity.HIGH),
        ("family_history", family, "Family medical history form required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="critical_illness_multistage", extra_gates=extra, conditions=["Stage definitions are filing-specific"])


def _uw_senior_standard(ctx: _Ctx) -> HealthUWDecision:
    extra: list[tuple[str, bool, str, RiskSeverity]] = []
    if ctx.age is not None and ctx.age < 60:
        extra.append(("age_60_plus", False, "Standard senior plan is for ages 60+ — decline / redirect to individual", RiskSeverity.CRITICAL))
    medical = _present(ctx, types=("medical_exam",), needles=("pre-policy medical", "pre policy medical", "medical check-up"))
    nominee = _present(ctx, types=("nominee_form", "beneficiary_form"), needles=("nominee", "nomination"))
    extra.append(("pre_policy_medical", medical, "Pre-policy medical check-up is mandatory for senior standard", RiskSeverity.HIGH))
    extra.append(("nominee", nominee, "Nominee details + ID proof required", RiskSeverity.HIGH))
    return _finalize(ctx, family="senior_standard", extra_gates=extra, conditions=["Senior PED waiting periods per filing"])


def _uw_senior_ped(ctx: _Ctx) -> HealthUWDecision:
    reports = _present(
        ctx,
        types=("medical_exam", "aps_records", "pre_existing_declaration"),
        needles=("medical reports of existing", "existing condition", "detailed medical"),
    )
    meds = _present(ctx, types=("medication_list",), needles=("medication", "prescription list", "current medication"))
    doctor = _present(ctx, types=("doctor_certificate",), needles=("treating doctor", "doctor's certificate", "doctors certificate"))
    extra = [
        ("ped_reports", reports, "Detailed medical reports of existing condition(s) required", RiskSeverity.HIGH),
        ("medication_list", meds, "Current medication / prescription list required", RiskSeverity.HIGH),
        ("treating_doctor", doctor, "Treating doctor's certificate required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="senior_preexisting", extra_gates=extra, conditions=["PED cover waiting / sub-limits per filing"])


def _uw_senior_no_medical(ctx: _Ctx) -> HealthUWDecision:
    decl = _present(
        ctx,
        types=("health_questionnaire",),
        needles=("self-declaration of good health", "self declaration of good health", "good health form", "simplified issue"),
    )
    nominee = _present(ctx, types=("nominee_form", "beneficiary_form"), needles=("nominee", "nomination"))
    knockout = any(k in ctx.blob for k in ("cancer", "heart attack", "stroke", "dialysis", "organ transplant", "hiv"))
    extra = [
        ("good_health_decl", decl, "Self-declaration of good health form replaces medical test", RiskSeverity.HIGH),
        ("nominee", nominee, "Nominee details required", RiskSeverity.HIGH),
        ("no_severe_declared_disease", not knockout, "Declared severe disease — simplified senior issue not available", RiskSeverity.CRITICAL),
    ]
    return _finalize(
        ctx,
        family="senior_no_medical",
        extra_gates=extra,
        conditions=["Do not invent preferred class; declaration is the medical file"],
    )


def _uw_senior_topup(ctx: _Ctx) -> HealthUWDecision:
    base = _present(ctx, types=("dec_page",), needles=("base policy", "existing policy", "deductible", "policy copy"))
    medical = _present(ctx, types=("medical_exam",), needles=("pre-policy medical", "medical check-up"))
    extra = [
        ("base_policy_deductible", base, "Existing base policy copy required to establish deductible", RiskSeverity.HIGH),
        ("senior_medical", medical, "Pre-policy medical often mandatory for senior top-up", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="senior_topup",
        extra_gates=extra,
        conditions=["Deductible equals base SI / stated threshold — do not invent"],
        metadata={"deductible_basis": "base_policy"},
    )


def _uw_group_employer(ctx: _Ctx) -> HealthUWDecision:
    gst = _present(ctx, types=("company_registration",), needles=("gst", "company registration", "certificate of incorporation"))
    pan = _has_text(ctx.blob, "company pan", "pan card") or gst
    census = _present(ctx, types=("employee_census",), needles=("employee list", "census", "payroll"))
    employment = _present(ctx, types=("employee_census",), needles=("offer letter", "payroll", "proof of employment"))
    extra = [
        ("company_kyc", gst, "Company registration / GST certificate required", RiskSeverity.HIGH),
        ("company_pan", pan, "Company PAN required", RiskSeverity.HIGH),
        ("employee_census", census, "Employee list with ID + age proof required", RiskSeverity.HIGH),
        ("employment_proof", employment, "Payroll / offer letter (proof of employment) required", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="group_employer", extra_gates=extra, conditions=["Master policy — employer is the proposer"])


def _uw_group_association(ctx: _Ctx) -> HealthUWDecision:
    reg = _present(ctx, types=("company_registration",), needles=("association registration", "society registration", "trust deed"))
    members = _present(ctx, types=("employee_census",), needles=("member list", "membership roster"))
    proof = _has_text(ctx.blob, "membership card", "membership certificate", "proof of association")
    extra = [
        ("association_registration", reg, "Association registration certificate required", RiskSeverity.HIGH),
        ("member_list", members, "Member list with ID + age proof required", RiskSeverity.HIGH),
        ("membership_proof", proof, "Proof of association membership required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="group_association", extra_gates=extra)


def _uw_group_psu(ctx: _Ctx) -> HealthUWDecision:
    emp_id = _has_text(ctx.blob, "employee id", "psu id", "government id card", "govt id")
    service = _has_text(ctx.blob, "service certificate", "employment proof", "joining letter")
    extra = [
        ("govt_employee_id", emp_id, "Government / PSU employee ID card required", RiskSeverity.HIGH),
        ("service_certificate", service, "Service certificate / employment proof required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="group_government_psu", extra_gates=extra)


def _uw_group_pa_health(ctx: _Ctx) -> HealthUWDecision:
    gst = _present(ctx, types=("company_registration",), needles=("gst", "company registration"))
    census = _present(ctx, types=("employee_census",), needles=("employee list", "census"))
    occ = _present(ctx, types=("occupation_proof",), needles=("occupation", "job role", "risk classification"))
    occ_class = _occupation_class(ctx.blob)
    extra = [
        ("company_kyc", gst, "Company registration / GST required", RiskSeverity.HIGH),
        ("employee_census", census, "Employee list with ID + age proof required", RiskSeverity.HIGH),
        ("occupation_risk", occ or bool(occ_class), "Occupation / job role details required for accident risk class", RiskSeverity.HIGH),
        ("not_class_iv", occ_class != "IV", "Class IV / hazardous occupations — refer or exclude PA portion", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="group_pa_health",
        extra_gates=extra,
        metadata={"occupation_class": occ_class or None},
    )


def _uw_topup(ctx: _Ctx) -> HealthUWDecision:
    base = _present(ctx, types=("dec_page",), needles=("base policy", "existing policy", "deductible", "policy copy"))
    decl = _present(ctx, types=("health_questionnaire",), needles=("medical declaration",))
    extra = [
        ("base_policy", base, "Existing base policy copy required (shows per-claim deductible threshold)", RiskSeverity.HIGH),
        ("medical_declaration", decl, "Medical declaration form required", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="topup",
        extra_gates=extra,
        conditions=["Deductible applies per hospitalization / claim"],
        metadata={"deductible_basis": "per_hospitalization"},
    )


def _uw_super_topup(ctx: _Ctx) -> HealthUWDecision:
    base = _present(ctx, types=("dec_page",), needles=("base policy", "existing policy", "policy copy"))
    decl = _present(ctx, types=("health_questionnaire",), needles=("medical declaration",))
    claims = _present(ctx, types=("loss_run",), needles=("claim history", "claims of base", "loss run"))
    extra = [
        ("base_policy", base, "Existing base policy copy required", RiskSeverity.HIGH),
        ("medical_declaration", decl, "Medical declaration form required", RiskSeverity.HIGH),
        ("base_claim_history", claims, "Claim history of base policy needed for aggregate-deductible UW", RiskSeverity.MODERATE),
    ]
    return _finalize(
        ctx,
        family="super_topup",
        extra_gates=extra,
        conditions=["Deductible applies to aggregate annual claims, not per hospitalization"],
        metadata={"deductible_basis": "annual_aggregate"},
    )


def _uw_pa_individual(ctx: _Ctx) -> HealthUWDecision:
    occ = _present(ctx, types=("occupation_proof",), needles=("occupation", "salary slip", "business registration"))
    nominee = _present(ctx, types=("nominee_form", "beneficiary_form"), needles=("nominee", "nomination"))
    occ_class = _occupation_class(ctx.blob)
    extra = [
        ("occupation_proof", occ or bool(occ_class), "Occupation proof required for PA risk category", RiskSeverity.HIGH),
        ("nominee", nominee, "Nominee details + ID proof required", RiskSeverity.HIGH),
        ("not_class_iv", occ_class != "IV", "Hazardous / class IV occupation — refer or decline standard PA", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="personal_accident",
        extra_gates=extra,
        metadata={"occupation_class": occ_class or None, "benefit_type": "pa_capital"},
    )


def _uw_pa_family(ctx: _Ctx) -> HealthUWDecision:
    rel = _present(
        ctx,
        types=("marriage_certificate", "child_birth_certificate"),
        needles=("marriage", "birth certificate", "relationship"),
    )
    occ = _present(ctx, types=("occupation_proof",), needles=("occupation", "salary slip", "earning member"))
    extra = [
        ("relationship_proof", rel, "Relationship proof (marriage / birth certificates) required", RiskSeverity.HIGH),
        ("earner_occupation", occ, "Occupation proof of earning members required", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="family_personal_accident", extra_gates=extra)


def _uw_pa_group(ctx: _Ctx) -> HealthUWDecision:
    gst = _present(ctx, types=("company_registration",), needles=("gst", "company registration"))
    census = _present(ctx, types=("employee_census",), needles=("employee list",))
    occ = _present(ctx, types=("occupation_proof",), needles=("occupation", "job role"))
    extra = [
        ("company_kyc", gst, "Company registration / GST required", RiskSeverity.HIGH),
        ("employee_census", census, "Employee list with ID + age proof required", RiskSeverity.HIGH),
        ("job_roles", occ, "Occupation / job role details required for risk rating", RiskSeverity.HIGH),
    ]
    return _finalize(ctx, family="group_personal_accident", extra_gates=extra)


def _uw_pa_add(ctx: _Ctx) -> HealthUWDecision:
    occ = _present(ctx, types=("occupation_proof",), needles=("occupation", "salary slip"))
    nominee = _present(ctx, types=("nominee_form", "beneficiary_form"), needles=("nominee", "nomination"))
    extra = [
        ("occupation_proof", occ, "Occupation proof required", RiskSeverity.HIGH),
        ("nominee_critical", nominee, "Nominee details + ID are critical — AD&D payout is to the nominee", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="accidental_death_dismemberment",
        extra_gates=extra,
        metadata={"payout_to": "nominee"},
    )


def _uw_disability_indemnity(ctx: _Ctx, *, family: str, need_income: bool) -> HealthUWDecision:
    occ = _present(ctx, types=("occupation_proof",), needles=("occupation", "job", "business registration"))
    fitness = _present(ctx, types=("doctor_certificate", "medical_exam"), needles=("medical fitness", "fitness certificate"))
    nominee = _present(ctx, types=("nominee_form", "beneficiary_form"), needles=("nominee",))
    income = _present(ctx, types=("income_proof",), needles=("income proof", "salary slip", "itr", "form 16", "pay slip"))
    extra: list[tuple[str, bool, str, RiskSeverity]] = [
        ("occupation_proof", occ, "Occupation proof required", RiskSeverity.HIGH),
        ("medical_fitness", fitness, "Medical fitness certificate required at proposal", RiskSeverity.HIGH),
        ("nominee", nominee, "Nominee details required", RiskSeverity.MODERATE),
    ]
    if need_income:
        extra.append(
            (
                "income_proof",
                income,
                "Income proof mandatory — disability income payout is a function of earnings",
                RiskSeverity.HIGH,
            )
        )
    conds = []
    if family == "disability_ttd":
        conds.append("TTD elimination period / weekly indemnity per filing — do not invent")
    elif family == "disability_income":
        conds.append("Benefit amount capped by declared income × filing replacement ratio")
    return _finalize(ctx, family=family, extra_gates=extra, conditions=conds, metadata={"needs_income": need_income})


def _uw_disability_ptd(ctx: _Ctx) -> HealthUWDecision:
    return _uw_disability_indemnity(ctx, family="disability_ptd", need_income=True)


def _uw_disability_ppd(ctx: _Ctx) -> HealthUWDecision:
    return _uw_disability_indemnity(ctx, family="disability_ppd", need_income=False)


def _uw_disability_ttd(ctx: _Ctx) -> HealthUWDecision:
    return _uw_disability_indemnity(ctx, family="disability_ttd", need_income=True)


def _uw_disability_income(ctx: _Ctx) -> HealthUWDecision:
    return _uw_disability_indemnity(ctx, family="disability_income", need_income=True)


def _uw_hospital_cash(ctx: _Ctx) -> HealthUWDecision:
    bank = _present(ctx, types=("bank_ach_form",), needles=("bank account", "cancelled cheque", "ifsc"))
    extra = [("bank_payout", bank, "Bank account details required for daily cash payout", RiskSeverity.HIGH)]
    return _finalize(
        ctx,
        family="hospital_cash",
        extra_gates=extra,
        conditions=["Daily cash amount / day cap per filing"],
        metadata={"payout_channel": "bank_cash", "benefit_type": "daily_cash"},
    )


def _uw_mediclaim_basic(ctx: _Ctx) -> HealthUWDecision:
    decl = _present(ctx, types=("health_questionnaire",), needles=("medical declaration",))
    extra = [("medical_declaration", decl, "Medical declaration form required", RiskSeverity.HIGH)]
    return _finalize(
        ctx,
        family="mediclaim_basic",
        extra_gates=extra,
        conditions=["Hospitalization-only — no OPD unless endorsed"],
        metadata={"benefit_type": "hospitalization_indemnity"},
    )


def _uw_overseas(ctx: _Ctx) -> HealthUWDecision:
    blob_wo_photo = re.sub(r"passport[-\s]?size", " ", ctx.blob)
    passport = _has_type(ctx.types, "travel_documents") or bool(re.search(r"\bpassport\b", blob_wo_photo, re.I))
    visa = _present(ctx, types=("travel_documents",), needles=("visa",))
    itinerary = _present(ctx, types=("travel_documents",), needles=("itinerary", "ticket", "flight", "travel dates"))
    extra = [
        ("passport", passport, "Passport is mandatory for overseas health", RiskSeverity.CRITICAL),
        ("visa", visa, "Visa copy required", RiskSeverity.HIGH),
        ("itinerary", itinerary, "Travel itinerary / ticket required", RiskSeverity.HIGH),
    ]
    return _finalize(
        ctx,
        family="overseas_health",
        extra_gates=extra,
        conditions=["Cover follows trip dates on itinerary — do not invent territory"],
        metadata={"benefit_type": "overseas_medical"},
    )


def _uw_wellness(ctx: _Ctx) -> HealthUWDecision:
    bank = _present(ctx, types=("bank_ach_form",), needles=("bank account", "cancelled cheque", "ifsc"))
    consent = _present(ctx, types=("wellness_consent",), needles=("wellness", "fitness app", "consent"))
    extra = [
        ("bank_cashback", bank, "Bank account required for wellness cashback credit", RiskSeverity.HIGH),
        ("wellness_consent", consent, "Wellness / fitness app consent required if tracking-based", RiskSeverity.MODERATE),
    ]
    return _finalize(ctx, family="wellness_savings", extra_gates=extra, metadata={"benefit_type": "wellness_cashback"})


def _uw_generic(ctx: _Ctx) -> HealthUWDecision:
    return _finalize(ctx, family="health_generic", extra_gates=[], conditions=["Generic health KYC only — unknown leaf"])


_PRODUCT_HANDLERS: dict[str, Callable[[_Ctx], HealthUWDecision]] = {
    "individual_basic": _uw_individual_basic,
    "individual_comprehensive": _uw_individual_comprehensive,
    "maternity_inclusive": _uw_maternity,
    "opd_cover": _uw_opd,
    "ulip_health": _uw_ulip_health,
    "family_floater_standard": _uw_floater_standard,
    "family_floater_parent": _uw_floater_parent,
    "family_floater_multiyear": _uw_floater_multiyear,
    "family_floater_restore": _uw_floater_restore,
    "critical_illness_standalone": _uw_ci_standalone,
    "critical_illness_rider": _uw_ci_rider,
    "disease_specific": _uw_cancer_care,  # coverage override below
    "critical_illness_multistage": _uw_ci_multistage,
    "senior_standard": _uw_senior_standard,
    "senior_preexisting": _uw_senior_ped,
    "senior_no_medical": _uw_senior_no_medical,
    "senior_topup": _uw_senior_topup,
    "group_employer_mediclaim": _uw_group_employer,
    "group_association": _uw_group_association,
    "group_government_psu": _uw_group_psu,
    "group_pa_health_combo": _uw_group_pa_health,
    "topup_plan": _uw_topup,
    "super_topup_plan": _uw_super_topup,
    "pa_individual": _uw_pa_individual,
    "pa_family": _uw_pa_family,
    "pa_group": _uw_pa_group,
    "pa_add": _uw_pa_add,
    "disability_ptd": _uw_disability_ptd,
    "disability_ppd": _uw_disability_ppd,
    "disability_ttd": _uw_disability_ttd,
    "disability_income": _uw_disability_income,
    "hospital_cash": _uw_hospital_cash,
    "mediclaim_basic": _uw_mediclaim_basic,
    "maternity_newborn_standalone": _uw_maternity,
    "overseas_health": _uw_overseas,
    "opd_only": _uw_opd,
    "wellness_savings": _uw_wellness,
}

_COVERAGE_HANDLERS: dict[str, Callable[[_Ctx], HealthUWDecision]] = {
    "cancer_care": _uw_cancer_care,
    "cardiac_care": _uw_cardiac_care,
    "diabetes_kidney_care": _uw_diabetes_kidney,
}


_PRODUCT_TERMS: dict[str, dict[str, Any]] = {
    "individual_basic": {"benefit_type": "hospitalization_indemnity", "member_unit": "individual", "deductible_basis": "none"},
    "individual_comprehensive": {"benefit_type": "hospitalization_indemnity", "member_unit": "individual", "deductible_basis": "none"},
    "maternity_inclusive": {"benefit_type": "hospitalization_indemnity_maternity", "member_unit": "individual", "waiting_period_hint": "maternity_9_to_36_months"},
    "opd_cover": {"benefit_type": "opd_reimbursement", "member_unit": "individual", "payout_channel": "bank_reimbursement"},
    "ulip_health": {"benefit_type": "ulip_linked_health", "member_unit": "individual", "has_investment_component": True},
    "family_floater_standard": {"benefit_type": "hospitalization_indemnity", "member_unit": "floater"},
    "family_floater_parent": {"benefit_type": "hospitalization_indemnity", "member_unit": "floater_with_parents"},
    "family_floater_multiyear": {"benefit_type": "hospitalization_indemnity", "member_unit": "floater", "term_years_hint": "2_or_3"},
    "family_floater_restore": {"benefit_type": "hospitalization_indemnity_restore", "member_unit": "floater"},
    "critical_illness_standalone": {"benefit_type": "lump_sum_ci", "member_unit": "individual"},
    "critical_illness_rider": {"benefit_type": "lump_sum_ci_rider", "member_unit": "individual", "attaches_to": "base_policy"},
    "disease_specific": {"benefit_type": "lump_sum_disease_specific", "member_unit": "individual"},
    "critical_illness_multistage": {"benefit_type": "lump_sum_ci_multistage", "member_unit": "individual"},
    "senior_standard": {"benefit_type": "hospitalization_indemnity", "member_unit": "individual", "min_age": 60},
    "senior_preexisting": {"benefit_type": "hospitalization_indemnity_ped", "member_unit": "individual", "min_age": 60},
    "senior_no_medical": {"benefit_type": "hospitalization_indemnity_simplified", "member_unit": "individual", "min_age": 60},
    "senior_topup": {"benefit_type": "topup", "member_unit": "individual", "deductible_basis": "base_policy", "min_age": 60},
    "group_employer_mediclaim": {"benefit_type": "hospitalization_indemnity", "member_unit": "group_employer"},
    "group_association": {"benefit_type": "hospitalization_indemnity", "member_unit": "group_affinity"},
    "group_government_psu": {"benefit_type": "hospitalization_indemnity", "member_unit": "group_psu"},
    "group_pa_health_combo": {"benefit_type": "hospitalization_plus_pa", "member_unit": "group_employer"},
    "topup_plan": {"benefit_type": "topup", "deductible_basis": "per_hospitalization"},
    "super_topup_plan": {"benefit_type": "super_topup", "deductible_basis": "annual_aggregate"},
    "pa_individual": {"benefit_type": "pa_capital", "member_unit": "individual"},
    "pa_family": {"benefit_type": "pa_capital", "member_unit": "family"},
    "pa_group": {"benefit_type": "pa_capital", "member_unit": "group"},
    "pa_add": {"benefit_type": "accidental_death_dismemberment", "payout_to": "nominee"},
    "disability_ptd": {"benefit_type": "permanent_total_disability"},
    "disability_ppd": {"benefit_type": "permanent_partial_disability"},
    "disability_ttd": {"benefit_type": "temporary_total_disability"},
    "disability_income": {"benefit_type": "disability_income_replacement", "needs_income": True},
    "hospital_cash": {"benefit_type": "daily_cash", "payout_channel": "bank_cash"},
    "mediclaim_basic": {"benefit_type": "hospitalization_indemnity"},
    "maternity_newborn_standalone": {"benefit_type": "maternity_newborn", "waiting_period_hint": "maternity_9_to_36_months"},
    "overseas_health": {"benefit_type": "overseas_medical"},
    "opd_only": {"benefit_type": "opd_reimbursement", "payout_channel": "bank_reimbursement"},
    "wellness_savings": {"benefit_type": "wellness_cashback", "payout_channel": "bank_cashback"},
}

_COVERAGE_TERMS: dict[str, dict[str, Any]] = {
    "cancer_care": {"benefit_type": "lump_sum_cancer", "disease": "cancer", "requires_ecg": False},
    "cardiac_care": {"benefit_type": "lump_sum_cardiac", "disease": "cardiac", "requires_ecg": True},
    "diabetes_kidney_care": {"benefit_type": "lump_sum_diabetes_kidney", "disease": "diabetes_kidney"},
}


def health_product_terms(product_id: str | None = None, coverage_id: str | None = None) -> dict[str, Any]:
    pid = str(product_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    cid = str(coverage_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    out = dict(_PRODUCT_TERMS.get(pid) or {"benefit_type": "hospitalization_indemnity"})
    if cid in _COVERAGE_TERMS:
        out.update(_COVERAGE_TERMS[cid])
    out["product_id"] = pid
    out["coverage_id"] = cid
    return out


def registered_health_uw_products() -> frozenset[str]:
    return frozenset(_PRODUCT_HANDLERS)


def _resolve_ids(product_id: str | None, coverage_id: str | None) -> tuple[str, str, str]:
    from insureflow.insurance.health_lobs import get_health_coverage, resolve_health_checklist_lob

    pid = str(product_id or "").strip()
    cid = str(coverage_id or "").strip()
    line, cov = get_health_coverage(pid or None, cid or None)
    if line:
        pid = str(line.get("id") or pid)
        category = str(line.get("category_id") or "")
        if cov and not cid:
            cid = str(cov.get("id") or "")
        return pid, cid, category
    resolved = resolve_health_checklist_lob(pid) or resolve_health_checklist_lob(cid) or pid.replace("-", "_")
    return resolved, cid, ""


def underwrite_health(
    bundle: SubmissionBundle,
    *,
    product_id: str | None = None,
    coverage_id: str | None = None,
) -> HealthUWDecision:
    pid, cid, category = _resolve_ids(product_id, coverage_id)
    blob = _blob(bundle)
    age = _int_field(blob, "age", "proposer age", "insured age")
    si = _money(blob, "sum insured", "si", "sum_insured")
    ctx = _Ctx(
        bundle=bundle,
        blob=blob,
        types=_doc_types(bundle),
        product_id=pid.replace("-", "_"),
        coverage_id=cid.replace("-", "_"),
        category_id=category,
        age=age,
        sum_insured=float(si or 0.0),
    )
    cov_key = ctx.coverage_id
    if cov_key in _COVERAGE_HANDLERS:
        return _COVERAGE_HANDLERS[cov_key](ctx)
    handler = _PRODUCT_HANDLERS.get(ctx.product_id) or _uw_generic
    return handler(ctx)
