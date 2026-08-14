"""Health Insurance LOB catalog: taxonomy + document packs + UW workflow.

Personal / retail health (mediclaim, floater, CI, senior, PA, disability).
Employer stop-loss / US group health stays under commercial ``group_health``.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.insurance.commercial_lobs import (
    _coverage,
    _normalize_coverages,
    flatten_line_documents,
)
from insureflow.underwriting.health_product import LIVE_HEALTH_PRODUCT_IDS

# Core 4 + proposal — every retail health leaf starts here.
HEALTH_BASE_PACKET: list[str] = [
    "Identity proof (Aadhaar / PAN / passport / voter ID / driver's license)",
    "Address proof (utility bill / Aadhaar / passport)",
    "Age proof (birth certificate / 10th marksheet / passport / Aadhaar)",
    "Passport-size photograph",
    "Proposal form (duly filled)",
]

HEALTH_UW_RESPONSIBILITIES: list[dict[str, str]] = [
    {
        "id": "eligibility",
        "title": "Eligibility & KYC",
        "summary": "Verify identity, age, address, and proposer authority before medical UW.",
    },
    {
        "id": "medical",
        "title": "Medical underwriting",
        "summary": "Review declarations, pre-policy check-ups, pre-existing conditions, and waiting periods.",
    },
    {
        "id": "sum_insured",
        "title": "Sum insured & deductible",
        "summary": "Match SI, floater vs individual, top-up deductible, and restore / multi-year terms to need.",
    },
    {
        "id": "relationships",
        "title": "Insured members",
        "summary": "Confirm spouse/child/parent relationships and dependent ages for floater and maternity.",
    },
    {
        "id": "portability",
        "title": "Portability & prior cover",
        "summary": "Review existing policy, claim history, and PED continuity when porting or topping up.",
    },
    {
        "id": "decision",
        "title": "Decision",
        "summary": "Issue, load, impose waiting periods / exclusions, refer, or decline. Filed health leaves rate from HLTH-2026-01; do not invent premium off the manual.",
    },
]

HEALTH_CATEGORIES: list[dict[str, str]] = [
    {"id": "individual", "name": "Individual Health Insurance", "summary": "Basic, comprehensive, maternity, OPD, and unit-linked individual mediclaim."},
    {"id": "family_floater", "name": "Family Floater Plans", "summary": "Shared SI for self + spouse + kids, parent-inclusive, multi-year, and restore benefit."},
    {"id": "critical_illness", "name": "Critical Illness Insurance", "summary": "Standalone CI, riders, disease-specific (cancer / cardiac / diabetes-kidney), multi-stage."},
    {"id": "senior", "name": "Senior Citizen Health Plans", "summary": "60+ mediclaim, PED cover, no-medical-check, and senior top-up."},
    {"id": "group", "name": "Group / Corporate Health", "summary": "Employer mediclaim, affinity, government/PSU, and group PA + health combo."},
    {"id": "top_up", "name": "Top-up / Super Top-up", "summary": "Deductible per hospitalization vs aggregate annual deductible."},
    {"id": "personal_accident", "name": "Personal Accident Insurance", "summary": "Individual, family, group PA, and AD&D."},
    {"id": "disability", "name": "Disability Insurance", "summary": "PTD, PPD, TTD, and income-replacement / disability income."},
    {"id": "other", "name": "Other Health Covers", "summary": "Hospital cash, basic mediclaim, maternity standalone, overseas, OPD-only, wellness."},
]


def _line(
    *,
    id: str,
    slug: str,
    name: str,
    short_name: str,
    category_id: str,
    checklist_lob: str,
    description: str,
    uw_focus: str,
    additional_documents: list[str],
    coverages: list[dict[str, Any]] | None = None,
    status: str = "catalog",
) -> dict[str, Any]:
    additional = [str(d).strip() for d in additional_documents if str(d).strip()]
    documents = list(HEALTH_BASE_PACKET)
    for doc in additional:
        if doc not in documents:
            documents.append(doc)
    covs = _normalize_coverages(coverages)
    return {
        "id": id,
        "slug": slug,
        "name": name,
        "short_name": short_name,
        "category_id": category_id,
        "checklist_lob": checklist_lob,
        "insurance_line": "health",
        "rating_line": "health",
        "description": description,
        "uw_focus": uw_focus,
        "acord_forms": [],
        "documents": documents,
        "additional_documents": additional,
        "coverages": covs,
        "status": status,
    }


HEALTH_LINES: list[dict[str, Any]] = [
    _line(
        id="individual_basic",
        slug="individual-basic",
        name="Basic / Standard Individual Plan",
        short_name="Individual Basic",
        category_id="individual",
        checklist_lob="individual_basic",
        description="Standard individual mediclaim — hospitalization indemnity with self-declared health status.",
        uw_focus="KYC + medical declaration. No invented SI; refer if declaration is incomplete.",
        additional_documents=["Medical declaration form (self-declared health status)"],
        coverages=[_coverage("individual_basic_std", "Standard Individual Mediclaim", "Medical declaration form (self-declared health status)")],
    ),
    _line(
        id="individual_comprehensive",
        slug="individual-comprehensive",
        name="Comprehensive Individual Plan",
        short_name="Individual Comprehensive",
        category_id="individual",
        checklist_lob="individual_comprehensive",
        description="Higher SI individual cover — income proof and pre-policy medical often mandatory.",
        uw_focus="Financial suitability for high SI; pre-policy check-up above age/SI thresholds; portability if existing cover.",
        additional_documents=[
            "Income proof (since sum insured is usually higher)",
            "Pre-policy medical check-up report (often mandatory above certain sum insured / age)",
            "Existing policy details (if porting or already insured)",
        ],
        coverages=[
            _coverage(
                "individual_comp_high_si",
                "Comprehensive High SI",
                "Income proof (since sum insured is usually higher)",
                "Pre-policy medical check-up report (often mandatory above certain sum insured / age)",
            ),
            _coverage("individual_comp_port", "Comprehensive with Portability", "Existing policy details (if porting or already insured)", "Income proof (since sum insured is usually higher)"),
        ],
    ),
    _line(
        id="maternity_inclusive",
        slug="maternity-inclusive",
        name="Maternity-inclusive Plan",
        short_name="Maternity Inclusive",
        category_id="individual",
        checklist_lob="maternity_inclusive",
        description="Individual health with maternity — marital status and pregnancy stage affect waiting period / eligibility.",
        uw_focus="Marriage certificate required. If already pregnant, doctor's confirmation may make the risk ineligible or extend waiting period.",
        additional_documents=[
            "Marriage certificate (mandatory — maternity cover needs proof of marital status)",
            "Medical history declaration",
            "Doctor's confirmation (if already pregnant at proposal — may affect eligibility / waiting period)",
        ],
        coverages=[
            _coverage(
                "maternity_inclusive_std",
                "Maternity-inclusive Mediclaim",
                "Marriage certificate (mandatory — maternity cover needs proof of marital status)",
                "Doctor's confirmation (if already pregnant at proposal — may affect eligibility / waiting period)",
            )
        ],
    ),
    _line(
        id="opd_cover",
        slug="opd-cover",
        name="OPD (Out-Patient) Cover Plan",
        short_name="OPD Cover",
        category_id="individual",
        checklist_lob="opd_cover",
        description="Out-patient reimbursement rider or plan — bank details needed for claims payout.",
        uw_focus="Confirm OPD sub-limits; bank account for reimbursement.",
        additional_documents=["Bank account details (for OPD reimbursement claims later)"],
        coverages=[_coverage("opd_reimbursement", "OPD Reimbursement", "Bank account details (for OPD reimbursement claims later)")],
    ),
    _line(
        id="ulip_health",
        slug="ulip-health",
        name="Unit-Linked Health Plan",
        short_name="ULIP Health",
        category_id="individual",
        checklist_lob="ulip_health",
        description="Investment + health cover — KYC, PAN, income, and suitability like a ULIP.",
        uw_focus="Financial suitability and AML/KYC for the investment component. Do not invent fund returns.",
        additional_documents=[
            "Income proof (mandatory — investment component needs financial suitability check)",
            "Bank account / cancelled cheque (for fund-linked transactions)",
            "PAN card (mandatory for investment-linked products, KYC norm)",
            "Risk profile / suitability form (specific to ULIP-type products)",
        ],
        coverages=[
            _coverage(
                "ulip_health_std",
                "Unit-Linked Health",
                "Income proof (mandatory — investment component needs financial suitability check)",
                "Risk profile / suitability form (specific to ULIP-type products)",
                "PAN card (mandatory for investment-linked products, KYC norm)",
            )
        ],
    ),
    _line(
        id="family_floater_standard",
        slug="family-floater-standard",
        name="Standard Family Floater",
        short_name="Family Floater",
        category_id="family_floater",
        checklist_lob="family_floater_standard",
        description="Shared SI for self + spouse + kids.",
        uw_focus="Age proof for every member; marriage + birth certificates for relationships.",
        additional_documents=[
            "Age proof of all members (self, spouse, kids)",
            "Marriage certificate (to prove spouse relationship)",
            "Birth certificates of children",
            "Photographs of all members",
            "Medical declaration for each member",
        ],
        coverages=[
            _coverage(
                "floater_self_spouse_kids", "Self + Spouse + Kids", "Marriage certificate (to prove spouse relationship)", "Birth certificates of children", "Medical declaration for each member"
            )
        ],
    ),
    _line(
        id="family_floater_parent",
        slug="family-floater-parent",
        name="Parent-inclusive Floater",
        short_name="Parent Floater",
        category_id="family_floater",
        checklist_lob="family_floater_parent",
        description="Floater that adds parents — age-related medical check-ups usually mandatory.",
        uw_focus="Relationship proof for parents; pre-policy medical and existing-illness declaration for older lives.",
        additional_documents=[
            "Age proof of all members including parents",
            "Relationship proof (birth certificate / ration card showing parent-child link)",
            "Pre-policy medical check-up of parents (mandatory, age-related risk)",
            "Photographs of all members",
            "Existing illness declaration (especially for parents)",
        ],
        coverages=[
            _coverage(
                "floater_with_parents",
                "Floater with Parents",
                "Relationship proof (birth certificate / ration card showing parent-child link)",
                "Pre-policy medical check-up of parents (mandatory, age-related risk)",
                "Existing illness declaration (especially for parents)",
            )
        ],
    ),
    _line(
        id="family_floater_multiyear",
        slug="family-floater-multiyear",
        name="Multi-year Floater",
        short_name="Multi-year Floater",
        category_id="family_floater",
        checklist_lob="family_floater_multiyear",
        description="2–3 year lock-in family floater; auto-debit instrument if opted.",
        uw_focus="Confirm multi-year premium funding and auto-debit mandate.",
        additional_documents=[
            "Age proof of all members",
            "Photographs of all members",
            "Medical declaration for each member",
            "Bank / payment instrument details (for multi-year premium auto-debit, if opted)",
        ],
        coverages=[_coverage("floater_multiyear", "2–3 Year Floater", "Bank / payment instrument details (for multi-year premium auto-debit, if opted)", "Medical declaration for each member")],
    ),
    _line(
        id="family_floater_restore",
        slug="family-floater-restore",
        name="Restore Benefit Floater",
        short_name="Restore Floater",
        category_id="family_floater",
        checklist_lob="family_floater_restore",
        description="SI auto-refills after claims — prior claim history matters if porting.",
        uw_focus="Review prior claims when porting; restore terms are filing-specific (catalog until filed).",
        additional_documents=[
            "Age proof of all members",
            "Photographs of all members",
            "Medical declaration for each member",
            "Previous claim history (if porting from another insurer)",
        ],
        coverages=[_coverage("floater_restore", "Restore Benefit", "Previous claim history (if porting from another insurer)", "Medical declaration for each member")],
    ),
    _line(
        id="critical_illness_standalone",
        slug="critical-illness-standalone",
        name="Standalone Critical Illness Plan",
        short_name="Standalone CI",
        category_id="critical_illness",
        checklist_lob="critical_illness_standalone",
        description="Lump-sum CI cover independent of hospitalization mediclaim.",
        uw_focus="Baseline labs / ECG often mandatory; family history drives loadings.",
        additional_documents=[
            "Medical test reports (ECG, blood sugar, lipid profile — often mandatory)",
            "Family medical history form",
        ],
        coverages=[_coverage("ci_standalone", "Standalone CI Lump Sum", "Medical test reports (ECG, blood sugar, lipid profile — often mandatory)", "Family medical history form")],
    ),
    _line(
        id="critical_illness_rider",
        slug="critical-illness-rider",
        name="Critical Illness Rider",
        short_name="CI Rider",
        category_id="critical_illness",
        checklist_lob="critical_illness_rider",
        description="CI add-on attached to an existing base policy.",
        uw_focus="Must attach to a live base policy — collect the base policy copy.",
        additional_documents=[
            "Existing base policy copy (rider attaches to this)",
            "Medical declaration form",
        ],
        coverages=[_coverage("ci_rider", "CI Rider on Base Policy", "Existing base policy copy (rider attaches to this)", "Medical declaration form")],
    ),
    _line(
        id="disease_specific",
        slug="disease-specific",
        name="Disease-specific Plan",
        short_name="Disease-specific",
        category_id="critical_illness",
        checklist_lob="disease_specific",
        description="Cancer, cardiac, or diabetes/kidney care — disease-specific medical evidence.",
        uw_focus="Do not quote without the disease-specific screening reports for that coverage.",
        additional_documents=[
            "Family history of cancer / cardiac / diabetes declaration",
            "Medical test reports (as advised by insurer)",
            "Existing medication details",
        ],
        coverages=[
            _coverage("cancer_care", "Cancer Care Plan", "Family history of cancer declaration", "Medical test reports (as advised by insurer)"),
            _coverage("cardiac_care", "Cardiac / Heart Care Plan", "ECG / cardiac screening report (usually mandatory)", "Family cardiac history declaration"),
            _coverage("diabetes_kidney_care", "Diabetes / Kidney Care Plan", "Blood sugar / kidney function test reports (mandatory)", "Existing medication details"),
        ],
    ),
    _line(
        id="critical_illness_multistage",
        slug="critical-illness-multistage",
        name="Multi-stage Critical Illness Plan",
        short_name="Multi-stage CI",
        category_id="critical_illness",
        checklist_lob="critical_illness_multistage",
        description="Pays at diagnosis stages — needs a documented health baseline.",
        uw_focus="Detailed baseline medicals; stage definitions are filing-specific (catalog).",
        additional_documents=[
            "Detailed medical test reports (baseline health status)",
            "Family medical history form",
        ],
        coverages=[_coverage("ci_multistage", "Multi-stage CI", "Detailed medical test reports (baseline health status)", "Family medical history form")],
    ),
    _line(
        id="senior_standard",
        slug="senior-standard",
        name="Standard Senior Citizen Plan",
        short_name="Senior Standard",
        category_id="senior",
        checklist_lob="senior_standard",
        description="Mediclaim for 60+ — strict age proof and mandatory pre-policy medical.",
        uw_focus="Age verification (Aadhaar/passport preferred); pre-policy medical is mandatory; nominee required.",
        additional_documents=[
            "Pre-policy medical check-up report (mandatory)",
            "Nominee details + ID proof",
        ],
        coverages=[_coverage("senior_60_plus", "Senior 60+", "Pre-policy medical check-up report (mandatory)", "Nominee details + ID proof")],
    ),
    _line(
        id="senior_preexisting",
        slug="senior-preexisting",
        name="Pre-existing Disease Cover Plan",
        short_name="Senior PED Cover",
        category_id="senior",
        checklist_lob="senior_preexisting",
        description="Senior cover that contemplates known PEDs — full clinical file required.",
        uw_focus="Treating doctor's certificate + meds list. Waiting periods are filing-specific.",
        additional_documents=[
            "Detailed medical reports of existing condition(s)",
            "Current medication / prescription list",
            "Treating doctor's certificate",
        ],
        coverages=[_coverage("senior_ped", "PED Cover", "Detailed medical reports of existing condition(s)", "Current medication / prescription list", "Treating doctor's certificate")],
    ),
    _line(
        id="senior_no_medical",
        slug="senior-no-medical",
        name="No Medical Check-up Plan",
        short_name="Senior No Medical",
        category_id="senior",
        checklist_lob="senior_no_medical",
        description="Senior issue on self-declaration of good health instead of labs.",
        uw_focus="Self-declaration replaces medical test — still collect nominee. Do not invent preferred class.",
        additional_documents=[
            "Self-declaration of good health form (replaces medical test)",
            "Nominee details + ID proof",
        ],
        coverages=[_coverage("senior_simplified", "Senior Simplified Issue", "Self-declaration of good health form (replaces medical test)", "Nominee details + ID proof")],
    ),
    _line(
        id="senior_topup",
        slug="senior-topup",
        name="Senior Citizen Top-up Plan",
        short_name="Senior Top-up",
        category_id="senior",
        checklist_lob="senior_topup",
        description="Top-up over an existing senior base policy — deductible from the base.",
        uw_focus="Base policy copy establishes deductible. Pre-policy medical often still required.",
        additional_documents=[
            "Existing base policy copy (to establish deductible)",
            "Pre-policy medical check-up (often mandatory for seniors)",
        ],
        coverages=[_coverage("senior_topup_std", "Senior Top-up", "Existing base policy copy (to establish deductible)", "Pre-policy medical check-up (often mandatory for seniors)")],
    ),
    _line(
        id="group_employer_mediclaim",
        slug="group-employer-mediclaim",
        name="Employer-Employee Group Mediclaim",
        short_name="Employer Group Mediclaim",
        category_id="group",
        checklist_lob="group_employer_mediclaim",
        description="Master policy on the employer — census + GST/PAN + nominations. Distinct from US commercial group_health.",
        uw_focus="Employer KYC + employee census. Occupation mix drives accident loadings if combo.",
        additional_documents=[
            "Company registration certificate / GST certificate",
            "Company PAN card",
            "Employee list with ID + age proof",
            "Payroll / offer letter (proof of employment)",
            "Master policy proposal form (employer signs)",
            "Nomination form for each employee",
        ],
        coverages=[
            _coverage(
                "group_mediclaim_ee",
                "Employer Group Mediclaim",
                "Company registration certificate / GST certificate",
                "Employee list with ID + age proof",
                "Master policy proposal form (employer signs)",
            )
        ],
    ),
    _line(
        id="group_association",
        slug="group-association",
        name="Group Plan for Associations / Affinity",
        short_name="Affinity Group",
        category_id="group",
        checklist_lob="group_association",
        description="Affinity / association master policy — membership proof required.",
        uw_focus="Confirm association registration and that insureds are bona fide members.",
        additional_documents=[
            "Association registration certificate",
            "Member list with ID + age proof",
            "Proof of association membership (membership card / certificate)",
            "Master proposal form",
        ],
        coverages=[
            _coverage(
                "affinity_group",
                "Affinity Group Mediclaim",
                "Association registration certificate",
                "Member list with ID + age proof",
                "Proof of association membership (membership card / certificate)",
            )
        ],
    ),
    _line(
        id="group_government_psu",
        slug="group-government-psu",
        name="Government / PSU Group Health Scheme",
        short_name="Govt / PSU Group",
        category_id="group",
        checklist_lob="group_government_psu",
        description="PSU / government employee scheme with dependents.",
        uw_focus="Employee ID + service certificate; family details for dependents.",
        additional_documents=[
            "Government / PSU employee ID card",
            "Service certificate / employment proof",
            "Family details (for dependents covered)",
            "Nomination form",
        ],
        coverages=[_coverage("psu_group", "PSU / Government Scheme", "Government / PSU employee ID card", "Service certificate / employment proof", "Family details (for dependents covered)")],
    ),
    _line(
        id="group_pa_health_combo",
        slug="group-pa-health-combo",
        name="Group Personal Accident + Health Combo",
        short_name="Group PA + Health",
        category_id="group",
        checklist_lob="group_pa_health_combo",
        description="Group mediclaim bundled with PA — occupation risk class for accident.",
        uw_focus="Occupation / job-role census for PA rating class. Catalog until a filed combo manual exists.",
        additional_documents=[
            "Company registration / GST certificate",
            "Employee list with ID + age proof",
            "Occupation details (risk classification for accident cover)",
            "Master policy proposal form",
        ],
        coverages=[_coverage("group_pa_health", "Group PA + Health Combo", "Occupation details (risk classification for accident cover)", "Employee list with ID + age proof")],
    ),
    _line(
        id="topup_plan",
        slug="topup-plan",
        name="Top-up Plan",
        short_name="Top-up",
        category_id="top_up",
        checklist_lob="topup_plan",
        description="Deductible per claim / hospitalization over a base mediclaim.",
        uw_focus="Base policy copy shows deductible threshold.",
        additional_documents=[
            "Existing base policy copy (shows deductible threshold)",
            "Medical declaration form",
        ],
        coverages=[_coverage("topup_per_claim", "Per-claim Top-up", "Existing base policy copy (shows deductible threshold)", "Medical declaration form")],
    ),
    _line(
        id="super_topup_plan",
        slug="super-topup-plan",
        name="Super Top-up Plan",
        short_name="Super Top-up",
        category_id="top_up",
        checklist_lob="super_topup_plan",
        description="Deductible on aggregate annual claims — prior claim history helps UW.",
        uw_focus="Aggregate deductible; request base-policy claim history when available.",
        additional_documents=[
            "Existing base policy copy",
            "Claim history of base policy (if available, for underwriting)",
            "Medical declaration form",
        ],
        coverages=[_coverage("super_topup_aggregate", "Aggregate Super Top-up", "Existing base policy copy", "Claim history of base policy (if available, for underwriting)")],
    ),
    _line(
        id="pa_individual",
        slug="pa-individual",
        name="Individual Personal Accident Plan",
        short_name="Individual PA",
        category_id="personal_accident",
        checklist_lob="pa_individual",
        description="Individual PA — occupation class drives rate; nominee is critical.",
        uw_focus="Occupation proof for risk category; nominee + ID for AD payout.",
        additional_documents=[
            "Occupation proof (salary slip / business registration — risk category)",
            "Nominee details + ID proof",
        ],
        coverages=[_coverage("pa_individual_std", "Individual PA", "Occupation proof (salary slip / business registration — risk category)", "Nominee details + ID proof")],
    ),
    _line(
        id="pa_family",
        slug="pa-family",
        name="Family Personal Accident Cover",
        short_name="Family PA",
        category_id="personal_accident",
        checklist_lob="pa_family",
        description="PA for family members — relationship + occupation of earners.",
        uw_focus="Relationship proofs; occupation of earning members.",
        additional_documents=[
            "Age proof of all members",
            "Relationship proof (marriage / birth certificates)",
            "Occupation proof of earning members",
            "Photographs of all members",
        ],
        coverages=[_coverage("pa_family_std", "Family PA", "Relationship proof (marriage / birth certificates)", "Occupation proof of earning members")],
    ),
    _line(
        id="pa_group",
        slug="pa-group",
        name="Group Personal Accident Plan",
        short_name="Group PA",
        category_id="personal_accident",
        checklist_lob="pa_group",
        description="Employer group PA — occupation mix for rating class.",
        uw_focus="Job-role census; do not invent occupation class.",
        additional_documents=[
            "Company registration / GST certificate",
            "Employee list with ID + age proof",
            "Occupation / job role details (for risk rating)",
            "Master policy proposal form",
        ],
        coverages=[_coverage("pa_group_std", "Group PA", "Occupation / job role details (for risk rating)", "Employee list with ID + age proof")],
    ),
    _line(
        id="pa_add",
        slug="pa-add",
        name="Accidental Death & Dismemberment (AD&D)",
        short_name="AD&D",
        category_id="personal_accident",
        checklist_lob="pa_add",
        description="AD&D — nominee documentation is critical because payout goes to nominee.",
        uw_focus="Nominee + ID must be on file before bind.",
        additional_documents=[
            "Occupation proof",
            "Nominee details + ID proof (critical, since payout is to nominee)",
        ],
        coverages=[_coverage("add_std", "AD&D", "Occupation proof", "Nominee details + ID proof (critical, since payout is to nominee)")],
    ),
    _line(
        id="disability_ptd",
        slug="disability-ptd",
        name="Permanent Total Disability (PTD) Cover",
        short_name="PTD",
        category_id="disability",
        checklist_lob="disability_ptd",
        description="PTD benefit — occupation, income, and fitness at proposal.",
        uw_focus="Income vs benefit sanity; medical fitness at proposal.",
        additional_documents=[
            "Occupation & income proof",
            "Medical fitness certificate (at proposal stage)",
            "Nominee details + ID proof",
        ],
        coverages=[_coverage("ptd_std", "PTD", "Occupation & income proof", "Medical fitness certificate (at proposal stage)")],
    ),
    _line(
        id="disability_ppd",
        slug="disability-ppd",
        name="Permanent Partial Disability (PPD) Cover",
        short_name="PPD",
        category_id="disability",
        checklist_lob="disability_ppd",
        description="PPD schedule benefits — occupation and fitness.",
        uw_focus="Occupation class; fitness certificate.",
        additional_documents=[
            "Occupation proof",
            "Medical fitness certificate",
            "Nominee details + ID proof",
        ],
        coverages=[_coverage("ppd_std", "PPD", "Occupation proof", "Medical fitness certificate")],
    ),
    _line(
        id="disability_ttd",
        slug="disability-ttd",
        name="Temporary Total Disability (TTD) Cover",
        short_name="TTD",
        category_id="disability",
        checklist_lob="disability_ttd",
        description="TTD / weekly indemnity — income proof drives benefit cap.",
        uw_focus="Income proof required; do not invent weekly benefit.",
        additional_documents=[
            "Occupation & income proof",
            "Medical fitness certificate",
            "Nominee details + ID proof",
        ],
        coverages=[_coverage("ttd_std", "TTD", "Occupation & income proof", "Medical fitness certificate")],
    ),
    _line(
        id="disability_income",
        slug="disability-income",
        name="Income Replacement / Disability Income Plan",
        short_name="Disability Income",
        category_id="disability",
        checklist_lob="disability_income",
        description="Income replacement DI — payout sized to documented earnings.",
        uw_focus="Salary slips / ITR mandatory. Benefit cannot exceed documented income multiples.",
        additional_documents=[
            "Income proof (mandatory — determines payout amount, e.g. salary slips / ITR)",
            "Occupation proof",
            "Medical fitness certificate",
            "Nominee details + ID proof",
        ],
        coverages=[_coverage("di_income", "Disability Income", "Income proof (mandatory — determines payout amount, e.g. salary slips / ITR)", "Occupation proof", "Medical fitness certificate")],
    ),
    _line(
        id="hospital_cash",
        slug="hospital-cash",
        name="Hospital Cash / Daily Cash Allowance",
        short_name="Hospital Cash",
        category_id="other",
        checklist_lob="hospital_cash",
        description="Fixed daily cash while hospitalized — bank details for payout.",
        uw_focus="Bank account for cash payout.",
        additional_documents=["Bank account details (for cash payout)"],
        coverages=[_coverage("hospital_cash_std", "Daily Hospital Cash", "Bank account details (for cash payout)")],
    ),
    _line(
        id="mediclaim_basic",
        slug="mediclaim-basic",
        name="Mediclaim Policy (hospitalization-only)",
        short_name="Basic Mediclaim",
        category_id="other",
        checklist_lob="mediclaim_basic",
        description="Basic hospitalization-only indemnity.",
        uw_focus="Medical declaration; catalog until a filed mediclaim manual exists.",
        additional_documents=["Medical declaration form"],
        coverages=[_coverage("mediclaim_hosp", "Hospitalization-only Mediclaim", "Medical declaration form")],
    ),
    _line(
        id="maternity_newborn_standalone",
        slug="maternity-newborn-standalone",
        name="Maternity & Newborn Insurance (standalone)",
        short_name="Maternity Standalone",
        category_id="other",
        checklist_lob="maternity_newborn_standalone",
        description="Standalone maternity + newborn — marriage + pregnancy stage.",
        uw_focus="Marriage certificate; doctor's confirmation if already pregnant.",
        additional_documents=[
            "Marriage certificate",
            "Doctor's confirmation (pregnancy stage, if applicable)",
        ],
        coverages=[_coverage("maternity_standalone", "Standalone Maternity + Newborn", "Marriage certificate", "Doctor's confirmation (pregnancy stage, if applicable)")],
    ),
    _line(
        id="overseas_health",
        slug="overseas-health",
        name="International / Overseas Health Insurance",
        short_name="Overseas Health",
        category_id="other",
        checklist_lob="overseas_health",
        description="Travel medical — passport, visa, and itinerary are mandatory.",
        uw_focus="Trip dates and destination from itinerary/ticket. Passport mandatory.",
        additional_documents=[
            "Passport (mandatory)",
            "Visa copy",
            "Travel itinerary / ticket",
        ],
        coverages=[_coverage("overseas_travel_medical", "Overseas Travel Medical", "Passport (mandatory)", "Visa copy", "Travel itinerary / ticket")],
    ),
    _line(
        id="opd_only",
        slug="opd-only",
        name="OPD-only Plan",
        short_name="OPD-only",
        category_id="other",
        checklist_lob="opd_only",
        description="Standalone OPD reimbursement — bank details for payout.",
        uw_focus="Bank account for reimbursement.",
        additional_documents=["Bank account details (for reimbursement)"],
        coverages=[_coverage("opd_only_std", "OPD-only Reimbursement", "Bank account details (for reimbursement)")],
    ),
    _line(
        id="wellness_savings",
        slug="wellness-savings",
        name="Health Savings / Wellness Plan",
        short_name="Wellness / Savings",
        category_id="other",
        checklist_lob="wellness_savings",
        description="Cashback for healthy habits — bank + wellness-app consent if tracking-based.",
        uw_focus="Consent for any fitness tracking. Do not invent cashback rates.",
        additional_documents=[
            "Bank account details (for cashback credit)",
            "Wellness / fitness app consent form (if tracking-based)",
        ],
        coverages=[_coverage("wellness_cashback", "Wellness Cashback", "Bank account details (for cashback credit)", "Wellness / fitness app consent form (if tracking-based)")],
    ),
]

for _ln in HEALTH_LINES:
    _ln["status"] = "live" if _ln["id"] in LIVE_HEALTH_PRODUCT_IDS else "catalog"


def list_health_categories() -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    live_counts: dict[str, int] = {}
    for line in HEALTH_LINES:
        cid = line["category_id"]
        counts[cid] = counts.get(cid, 0) + 1
        if line.get("status") == "live":
            live_counts[cid] = live_counts.get(cid, 0) + 1
    return [{**cat, "product_count": counts.get(cat["id"], 0), "live_count": live_counts.get(cat["id"], 0)} for cat in HEALTH_CATEGORIES]


def list_health_lines(*, category_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in HEALTH_LINES:
        if category_id and line["category_id"] != category_id:
            continue
        if status and line.get("status") != status:
            continue
        coverages = _normalize_coverages(line.get("coverages"))
        rows.append(
            {
                "id": line["id"],
                "slug": line["slug"],
                "name": line["name"],
                "short_name": line["short_name"],
                "category_id": line["category_id"],
                "checklist_lob": line["checklist_lob"],
                "insurance_line": line["insurance_line"],
                "rating_line": line.get("rating_line") or line["insurance_line"],
                "description": line["description"],
                "document_count": len(line["documents"]),
                "additional_document_count": len(line["additional_documents"]),
                "coverage_count": len(coverages),
                "coverages": coverages,
                "all_documents": flatten_line_documents({**line, "coverages": coverages}),
                "acord_forms": list(line["acord_forms"]),
                "status": line.get("status") or "catalog",
            }
        )
    return rows


def health_taxonomy_tree() -> list[dict[str, Any]]:
    by_cat: dict[str, list[dict[str, Any]]] = {c["id"]: [] for c in HEALTH_CATEGORIES}
    for row in list_health_lines():
        by_cat.setdefault(row["category_id"], []).append(
            {
                "id": row["id"],
                "slug": row["slug"],
                "name": row["name"],
                "short_name": row["short_name"],
                "insurance_line": row["insurance_line"],
                "checklist_lob": row["checklist_lob"],
                "status": row["status"],
                "document_count": row["document_count"],
                "all_documents": list(row.get("all_documents") or []),
                "coverages": [
                    {
                        "id": cov["id"],
                        "name": cov["name"],
                        "documents": list(cov.get("documents") or []),
                        "document_count": int(cov.get("document_count") or len(cov.get("documents") or [])),
                    }
                    for cov in row.get("coverages") or []
                ],
            }
        )
    return [{**cat, "products": by_cat.get(cat["id"], [])} for cat in list_health_categories()]


def get_health_line(line_id_or_slug: str) -> dict[str, Any] | None:
    raw = (line_id_or_slug or "").strip().lower()
    if not raw:
        return None
    variants = {raw, raw.replace("_", "-"), raw.replace("-", "_")}
    for line in HEALTH_LINES:
        candidates = {
            line["id"],
            line["slug"],
            line["checklist_lob"],
            line["insurance_line"],
            line["id"].replace("_", "-"),
            line["checklist_lob"].replace("_", "-"),
        }
        if variants & candidates:
            coverages = _normalize_coverages(line.get("coverages"))
            return {
                **line,
                "coverages": coverages,
                "all_documents": flatten_line_documents({**line, "coverages": coverages}),
                "base_packet": list(HEALTH_BASE_PACKET),
                "uw_responsibilities": list(HEALTH_UW_RESPONSIBILITIES),
                "uw_question": "Is this applicant eligible for the selected health product, at what SI / deductible, and are KYC + medical proofs complete?",
            }
    return None


def resolve_health_checklist_lob(identifier: str | None) -> str | None:
    if not identifier:
        return None
    target = re.sub(r"[\s_-]+", " ", str(identifier).strip().lower())
    if not target:
        return None
    for line in HEALTH_LINES:
        lob = str(line.get("checklist_lob") or "").strip()
        if not lob:
            continue
        candidates = {
            re.sub(r"[\s_-]+", " ", str(line.get("id") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", str(line.get("slug") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", str(line.get("name") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", str(line.get("short_name") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", lob.lower()),
        }
        if target in candidates:
            return lob
        for cov in line.get("coverages") or []:
            if not isinstance(cov, dict):
                continue
            cov_ids = {
                re.sub(r"[\s_-]+", " ", str(cov.get("id") or "").strip().lower()),
                re.sub(r"[\s_-]+", " ", str(cov.get("name") or "").strip().lower()),
            }
            if target in cov_ids:
                return lob
    return None


def get_health_coverage(
    product_id: str | None = None,
    coverage_id: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    from insureflow.insurance.commercial_lobs import get_line_coverage

    line = get_health_line(product_id or "") if product_id else None
    if line is None and coverage_id:
        key = (coverage_id or "").strip().lower().replace("-", "_").replace(" ", "_")
        for candidate in HEALTH_LINES:
            for cov in candidate.get("coverages") or []:
                if not isinstance(cov, dict):
                    continue
                cid = str(cov.get("id") or "").strip().lower().replace("-", "_").replace(" ", "_")
                if cid == key:
                    return get_health_line(str(candidate.get("id") or "")), cov
        return None, None
    if line is None:
        return None, None
    return line, get_line_coverage(line, coverage_id)


def detect_health_product(text_blob: str = "") -> str | None:
    blob = re.sub(r"[^a-z0-9 ]", " ", (text_blob or "").lower())
    if not blob.strip():
        return None
    best: str | None = None
    best_score = 0
    for line in HEALTH_LINES:
        score = 0
        for part in (line.get("name"), line.get("short_name"), line.get("checklist_lob")):
            phrase = re.sub(r"[^a-z0-9 ]", " ", str(part or "").lower()).strip()
            if len(phrase) >= 6 and phrase in blob:
                score += 2
        if score > best_score:
            best = str(line.get("checklist_lob") or "").strip() or None
            best_score = score
    return best if best_score >= 2 else None


def health_hub_payload() -> dict[str, Any]:
    lines = list_health_lines()
    live = [ln for ln in lines if ln["status"] == "live"]
    return {
        "segment": "personal_health",
        "title": "Health Insurance",
        "summary": (
            "Retail health underwriting — individual mediclaim, family floater, critical illness, "
            "senior, group/affinity, top-up, personal accident, disability, and related covers. "
            "Each leaf has a shared KYC base packet plus product-specific documents and rates "
            "from the filed health manual (HLTH-2026-01) — all 37 leaves are live."
        ),
        "base_packet": list(HEALTH_BASE_PACKET),
        "uw_responsibilities": list(HEALTH_UW_RESPONSIBILITIES),
        "categories": list_health_categories(),
        "taxonomy": health_taxonomy_tree(),
        "lines": lines,
        "live_lines": live,
        "production_lines": ["health"],
        "stats": {
            "category_count": len(HEALTH_CATEGORIES),
            "product_count": len(HEALTH_LINES),
            "live_count": len(live),
            "catalog_count": max(0, len(lines) - len(live)),
            "lob_model_count": 0,
        },
    }
