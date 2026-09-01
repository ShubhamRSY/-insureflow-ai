"""Health Insurance LOB catalog: taxonomy + document packs + UW workflow.

US market — individual/family ACA major medical, Medicare supplement /
advantage, employer group, critical illness, supplemental gap coverage,
AD&D / accident indemnity, and disability income. Each leaf has a dedicated
underwriting/rating logic path in insureflow.health.lobs, the same
architecture the life insurance line uses.
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

# Core KYC packet — every retail health leaf starts here.
HEALTH_BASE_PACKET: list[str] = [
    "Government-issued photo ID (driver's license / passport / state ID)",
    "Social Security number (for exchange subsidy eligibility and carrier verification)",
    "Proof of address (utility bill / lease / bank statement)",
    "Date-of-birth verification (birth certificate / passport / driver's license)",
    "Completed application / enrollment form",
]

HEALTH_UW_RESPONSIBILITIES: list[dict[str, str]] = [
    {
        "id": "eligibility",
        "title": "Eligibility & KYC",
        "summary": "Verify identity, age, residency, and applicant authority before underwriting.",
    },
    {
        "id": "medical",
        "title": "Medical underwriting",
        "summary": "Individual/family/group major medical is guaranteed issue (ACA) — no health-status underwriting. Supplemental lines are medically/occupationally underwritten.",
    },
    {
        "id": "benefit_design",
        "title": "Benefit amount & plan design",
        "summary": "Match metal tier / deductible / lump-sum / benefit amount, family vs. self-only tier, and elimination/benefit period to need.",
    },
    {
        "id": "household",
        "title": "Household / covered members",
        "summary": "Confirm spouse/dependent relationships and covered-lives count for family and group tier rating.",
    },
    {
        "id": "state_compliance",
        "title": "State compliance",
        "summary": "Apply the issue state's ACA/NAIC rules — guaranteed issue, community rating, mandated benefits, rate-filing type, SDI coordination.",
    },
    {
        "id": "decision",
        "title": "Decision",
        "summary": "Issue, condition, refer, or decline per the product's own logic path. Rates from HLTH-US-2026-01; unregistered leaves fall back to the legacy engine, never inventing a premium.",
    },
]

HEALTH_CATEGORIES: list[dict[str, str]] = [
    {"id": "individual", "name": "Individual & Family Health Insurance", "summary": "ACA Marketplace metal-tier plans and off-exchange major medical."},
    {"id": "family_floater", "name": "Family Health Plans", "summary": "A single policy covering the household under one aggregate family deductible."},
    {"id": "critical_illness", "name": "Critical Illness Insurance", "summary": "Standalone lump-sum critical illness and disease-specific (cancer / cardiac / diabetes-kidney) cover."},
    {"id": "senior", "name": "Senior Citizen Health Plans", "summary": "Medicare Supplement (Medigap Plans A/G/N) and Medicare Advantage."},
    {"id": "group", "name": "Group / Corporate Health", "summary": "ACA small-group (community-rated) and ERISA large-group (fully insured or self-funded)."},
    {"id": "top_up", "name": "Top-up / Super Top-up", "summary": "Supplemental / gap coverage above a high-deductible base plan — per-incident or annual-aggregate deductible."},
    {"id": "personal_accident", "name": "Personal Accident Insurance", "summary": "Accidental Death & Dismemberment (AD&D) and accident indemnity — individual, family, group."},
    {"id": "disability", "name": "Disability Insurance", "summary": "Short-term and long-term disability income replacement."},
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
    # ===== 1. INDIVIDUAL & FAMILY (ACA MARKETPLACE) =====
    _line(
        id="aca_marketplace_plan",
        slug="aca-marketplace-plan",
        name="ACA Marketplace Plan",
        short_name="Marketplace Plan",
        category_id="individual",
        checklist_lob="aca_marketplace_plan",
        description="Individual/family major medical sold on the ACA exchange — Bronze, Silver, Gold, or Platinum metal tier. Guaranteed issue; premium-tax-credit eligible.",
        uw_focus="No health-status underwriting (ACA §2702). Verify household income for subsidy eligibility and metal-tier fit to expected utilization.",
        additional_documents=["Household income documentation (for premium tax credit eligibility)", "Prior coverage details (for special enrollment period verification, if applicable)"],
        coverages=[
            _coverage("bronze", "Bronze Plan (~60% actuarial value)", "Household income documentation (for premium tax credit eligibility)"),
            _coverage("silver", "Silver Plan (~70% actuarial value)", "Household income documentation (for premium tax credit eligibility)"),
            _coverage("gold", "Gold Plan (~80% actuarial value)", "Household income documentation (for premium tax credit eligibility)"),
            _coverage("platinum", "Platinum Plan (~90% actuarial value)", "Household income documentation (for premium tax credit eligibility)"),
        ],
    ),
    _line(
        id="off_exchange_major_medical",
        slug="off-exchange-major-medical",
        name="Off-Exchange Major Medical",
        short_name="Off-Exchange Medical",
        category_id="individual",
        checklist_lob="off_exchange_major_medical",
        description="ACA-compliant individual major medical sold directly by the carrier — not subsidy-eligible, but the same guaranteed-issue floor as a Marketplace plan.",
        uw_focus="No health-status underwriting. Confirm the applicant understands no subsidy applies off-exchange.",
        additional_documents=["Self-declared health questionnaire (administrative — not a medical underwriting gate)"],
        coverages=[_coverage("off_exchange_standard", "Standard Off-Exchange Plan", "Self-declared health questionnaire (administrative — not a medical underwriting gate)")],
    ),
    _line(
        id="short_term_limited_duration",
        slug="short-term-limited-duration",
        name="Short-Term Limited Duration Insurance",
        short_name="STLDI",
        category_id="individual",
        checklist_lob="short_term_limited_duration",
        description="Not ACA-compliant — the one genuinely medically-underwritten individual health product in the US market. Banned or restricted in several states.",
        uw_focus="Full medical underwriting — pre-existing conditions can be permanently excluded. Confirm the issue state permits STLDI at all.",
        additional_documents=["Health questionnaire", "Prior coverage details"],
        coverages=[_coverage("stldi_standard", "Standard STLDI Plan", "Health questionnaire")],
    ),
    _line(
        id="hdhp_hsa_qualified",
        slug="hdhp-hsa-qualified",
        name="HSA-Qualified HDHP",
        short_name="HSA HDHP",
        category_id="individual",
        checklist_lob="hdhp_hsa_qualified",
        description="Guaranteed-issue ACA plan with a deductible at or above the IRS HSA-qualifying minimum, enabling tax-advantaged HSA contributions.",
        uw_focus="No health-status underwriting. Confirm the chosen deductible actually meets the IRS minimum for HSA eligibility.",
        additional_documents=["Household income documentation (for premium tax credit eligibility)"],
        coverages=[_coverage("hdhp_standard", "Standard HSA-Qualified HDHP", "Household income documentation (for premium tax credit eligibility)")],
    ),
    _line(
        id="catastrophic_plan",
        slug="catastrophic-plan",
        name="ACA Catastrophic Plan",
        short_name="Catastrophic",
        category_id="individual",
        checklist_lob="catastrophic_plan",
        description="Guaranteed-issue, high-deductible ACA plan restricted to applicants under 30 or with a documented hardship/affordability exemption.",
        uw_focus="No health-status underwriting. Verify age-under-30 or hardship exemption documentation before issue.",
        additional_documents=["Hardship or affordability exemption certificate (if applicant is 30 or older)"],
        coverages=[_coverage("catastrophic_standard", "Standard Catastrophic Plan", "Hardship or affordability exemption certificate (if applicant is 30 or older)")],
    ),
    # ===== 2. FAMILY HEALTH PLAN =====
    _line(
        id="family_health_plan",
        slug="family-health-plan",
        name="Family Health Plan",
        short_name="Family Plan",
        category_id="family_floater",
        checklist_lob="family_health_plan",
        description="A single policy covering the applicant and dependents under one aggregate family deductible — the standard structure for a US family major-medical plan.",
        uw_focus="Confirm dependent relationships and covered-lives count; no health-status underwriting on any covered member.",
        additional_documents=["Dependent birth certificates / proof of relationship", "Marriage certificate (if covering a spouse)"],
        coverages=[_coverage("standard_family", "Standard Family Plan", "Dependent birth certificates / proof of relationship", "Marriage certificate (if covering a spouse)")],
    ),
    _line(
        id="family_hdhp_hsa_qualified",
        slug="family-hdhp-hsa-qualified",
        name="Family HSA-Qualified HDHP",
        short_name="Family HSA HDHP",
        category_id="family_floater",
        checklist_lob="family_hdhp_hsa_qualified",
        description="Family-tier HSA-qualified HDHP — aggregate family deductible at or above the IRS family HSA-qualifying minimum.",
        uw_focus="No health-status underwriting. Confirm the chosen family deductible meets the IRS family HSA minimum.",
        additional_documents=["Dependent birth certificates / proof of relationship", "Marriage certificate (if covering a spouse)"],
        coverages=[_coverage("family_hdhp_standard", "Standard Family HSA-Qualified HDHP", "Dependent birth certificates / proof of relationship")],
    ),
    _line(
        id="family_extended_dependents",
        slug="family-extended-dependents",
        name="Family Plan — Extended Dependent Coverage",
        short_name="Extended Dependents",
        category_id="family_floater",
        checklist_lob="family_extended_dependents",
        description="Family plan covering dependents to age 26 automatically, plus disabled adult dependents past 26 with certification on file.",
        uw_focus="No health-status underwriting on any covered member. Verify disability certification for any dependent past age 26.",
        additional_documents=["Dependent birth certificates / proof of relationship", "Disability certification (for dependents past age 26)"],
        coverages=[_coverage("extended_dependents_standard", "Standard Extended Dependent Plan", "Disability certification (for dependents past age 26)")],
    ),
    # ===== 3. CRITICAL ILLNESS =====
    _line(
        id="critical_illness_standalone",
        slug="critical-illness-standalone",
        name="Critical Illness (Standalone)",
        short_name="Critical Illness",
        category_id="critical_illness",
        checklist_lob="critical_illness_standalone",
        description="Lump-sum indemnity payment on first diagnosis of a covered condition (cancer, heart attack, stroke, kidney failure). Supplemental — does not replace major medical.",
        uw_focus="Medically underwritten (health questionnaire). Confirm the lump-sum benefit amount is documented.",
        additional_documents=["Health questionnaire", "Physician statement (if a prior diagnosis is disclosed)"],
        coverages=[_coverage("ci_standalone", "Standalone Critical Illness", "Health questionnaire")],
    ),
    _line(
        id="disease_specific_critical_illness",
        slug="disease-specific-critical-illness",
        name="Disease-Specific Critical Illness",
        short_name="Disease-Specific CI",
        category_id="critical_illness",
        checklist_lob="disease_specific_critical_illness",
        description="Single-condition lump-sum cover — Cancer Care, Cardiac Care, or Diabetes/Kidney Care — narrower and cheaper than standalone CI.",
        uw_focus="Cardiac Care requires a recent ECG on file; Cancer and Diabetes/Kidney Care do not.",
        additional_documents=["Health questionnaire"],
        coverages=[
            _coverage("cancer_care", "Cancer Care", "Health questionnaire", "Prior cancer screening / biopsy records (if any)"),
            _coverage("cardiac_care", "Cardiac Care", "Health questionnaire", "ECG report"),
            _coverage("diabetes_kidney_care", "Diabetes / Kidney Care", "Health questionnaire", "HbA1c / creatinine lab report"),
        ],
    ),
    _line(
        id="critical_illness_rider",
        slug="critical-illness-rider",
        name="Critical Illness Rider",
        short_name="CI Rider",
        category_id="critical_illness",
        checklist_lob="critical_illness_rider",
        description="Attaches to an existing base policy rather than standing alone — no independent free-look period or policy fee; terminates if the base policy lapses.",
        uw_focus="Confirm the base policy exists and is in force before underwriting the rider.",
        additional_documents=["Base policy declarations page", "Health questionnaire"],
        coverages=[_coverage("ci_rider_standard", "Standard Critical Illness Rider", "Base policy declarations page")],
    ),
    _line(
        id="critical_illness_multistage",
        slug="critical-illness-multistage",
        name="Multi-Stage Critical Illness",
        short_name="Multi-Stage CI",
        category_id="critical_illness",
        checklist_lob="critical_illness_multistage",
        description="Pays a graduated percentage of the benefit at increasing severity stages instead of one lump sum on first diagnosis.",
        uw_focus="Medically underwritten. Detailed baseline medical and family history required.",
        additional_documents=["Health questionnaire", "Detailed baseline medical test report", "Family medical history form"],
        coverages=[_coverage("ci_multistage_standard", "Standard Multi-Stage Critical Illness", "Detailed baseline medical test report")],
    ),
    # ===== 4. SENIOR / MEDICARE =====
    _line(
        id="medicare_supplement",
        slug="medicare-supplement",
        name="Medicare Supplement (Medigap)",
        short_name="Medigap",
        category_id="senior",
        checklist_lob="medicare_supplement",
        description="Standardized Plans A, G, and N — pays Original Medicare's cost-sharing gaps. Guaranteed issue for 6 months after Part B starts; medically underwritten outside that window.",
        uw_focus="Determine whether the applicant is inside or outside the federal open-enrollment window — this decides whether medical underwriting applies at all.",
        additional_documents=["Medicare Part B effective date (to determine open-enrollment window)", "Health questionnaire (required only outside the guaranteed-issue window)"],
        coverages=[
            _coverage("plan_a", "Medigap Plan A", "Medicare Part B effective date"),
            _coverage("plan_g", "Medigap Plan G", "Medicare Part B effective date"),
            _coverage("plan_n", "Medigap Plan N", "Medicare Part B effective date"),
            _coverage("open_enrollment_plan_g", "Medigap Plan G — Open Enrollment", "Medicare Part B effective date"),
        ],
    ),
    _line(
        id="medicare_advantage",
        slug="medicare-advantage",
        name="Medicare Advantage (Part C)",
        short_name="Medicare Advantage",
        category_id="senior",
        checklist_lob="medicare_advantage",
        description="A Medicare-replacement plan administered by a private carrier under CMS capitation — always guaranteed issue during an eligible enrollment period.",
        uw_focus="No medical underwriting, ever. Confirm the applicant's Medicare eligibility and enrollment-period timing.",
        additional_documents=["Medicare eligibility verification (Part A & B enrollment)"],
        coverages=[_coverage("ma_standard", "Standard Medicare Advantage Plan", "Medicare eligibility verification (Part A & B enrollment)")],
    ),
    _line(
        id="medigap_high_deductible_plan_g",
        slug="medigap-high-deductible-plan-g",
        name="Medigap High-Deductible Plan G",
        short_name="Medigap HD Plan G",
        category_id="senior",
        checklist_lob="medigap_high_deductible_plan_g",
        description="CMS-standardized Medigap variant — much lower premium in exchange for a high annual deductible (~$2,800) before the plan starts paying.",
        uw_focus="Same guaranteed-issue window logic as standard Plan G. Confirm the applicant understands the deductible mechanic before bind.",
        additional_documents=["Medicare Part B effective date (to determine open-enrollment window)", "Health questionnaire (required only outside the guaranteed-issue window)"],
        coverages=[
            _coverage("hd_plan_g", "Medigap HD Plan G", "Medicare Part B effective date"),
            _coverage("open_enrollment_hd_plan_g", "Medigap HD Plan G — Open Enrollment", "Medicare Part B effective date"),
        ],
    ),
    _line(
        id="medicare_advantage_snp",
        slug="medicare-advantage-snp",
        name="Medicare Advantage Special Needs Plan",
        short_name="MA SNP",
        category_id="senior",
        checklist_lob="medicare_advantage_snp",
        description="Restricted-enrollment Medicare Advantage plan for applicants with a qualifying chronic condition (C-SNP) or dual Medicare/Medicaid eligibility (D-SNP).",
        uw_focus="No health-status decline, but enrollment REQUIRES a documented qualifying chronic condition or dual-eligible status — the inverse of a knockout gate.",
        additional_documents=["Medicare eligibility verification (Part A & B enrollment)", "Chronic condition diagnosis or dual Medicare/Medicaid eligibility documentation"],
        coverages=[_coverage("snp_standard", "Standard Special Needs Plan", "Chronic condition diagnosis or dual Medicare/Medicaid eligibility documentation")],
    ),
    # ===== 5. GROUP / CORPORATE =====
    _line(
        id="small_group_health",
        slug="small-group-health",
        name="Small Group Health Plan",
        short_name="Small Group",
        category_id="group",
        checklist_lob="small_group_health",
        description="ACA small-group market (1-50 FTE employees) — guaranteed issue, community-rated, no group-level experience rating.",
        uw_focus="Verify employer size against the state's small-group threshold; no medical underwriting on any enrolling employee.",
        additional_documents=["Employer census (employee roster with ages)", "Business registration / EIN verification"],
        coverages=[_coverage("small_group_standard", "Standard Small Group Plan", "Employer census (employee roster with ages)")],
    ),
    _line(
        id="large_group_health",
        slug="large-group-health",
        name="Large Group Health Plan",
        short_name="Large Group",
        category_id="group",
        checklist_lob="large_group_health",
        description="51+ employee groups — real experience rating, and (if self-funded) ERISA preemption of most state-mandated-benefit laws.",
        uw_focus="Confirm fully insured vs. self-funded status — it changes which state rules apply at all.",
        additional_documents=["Employer census (employee roster with ages)", "Prior-year claims experience (for experience rating)", "Stop-loss policy details (if self-funded)"],
        coverages=[
            _coverage("fully_insured", "Fully Insured Large Group", "Employer census (employee roster with ages)", "Prior-year claims experience (for experience rating)"),
            _coverage("self_funded", "Self-Funded Large Group", "Employer census (employee roster with ages)", "Stop-loss policy details (if self-funded)"),
        ],
    ),
    _line(
        id="association_health_plan",
        slug="association-health-plan",
        name="Association Health Plan",
        short_name="AHP",
        category_id="group",
        checklist_lob="association_health_plan",
        description="DOL-regulated ERISA multi-employer plan sponsored by a bona fide trade, professional, or industry association covering multiple small employers.",
        uw_focus="Verify bona fide association status (common purpose beyond offering insurance) before treating this as a single risk pool.",
        additional_documents=["Association registration / bylaws", "Member employer roster"],
        coverages=[_coverage("ahp_standard", "Standard Association Health Plan", "Association registration / bylaws")],
    ),
    _line(
        id="public_sector_group_health",
        slug="public-sector-group-health",
        name="Public Sector Group Health",
        short_name="Public Sector Group",
        category_id="group",
        checklist_lob="public_sector_group_health",
        description="Municipal, county, or state-government employer group plan — often self-funded, with different ACA employer-mandate exemption treatment.",
        uw_focus="Verify government/PSU employer status via service record rather than private payroll.",
        additional_documents=["Government employer verification", "Employee service certificate"],
        coverages=[_coverage("public_sector_standard", "Standard Public Sector Group Plan", "Government employer verification")],
    ),
    _line(
        id="level_funded_group_health",
        slug="level-funded-group-health",
        name="Level-Funded Group Health",
        short_name="Level-Funded Group",
        category_id="group",
        checklist_lob="level_funded_group_health",
        description="Structurally self-funded, sized for small employers, with a stop-loss policy capping the employer's claims exposure.",
        uw_focus="Confirm a per-employee stop-loss health questionnaire is on file — required for attachment-point pricing even though enrollment itself is not medically underwritten.",
        additional_documents=["Employer census (employee roster with ages)", "Stop-loss policy details", "Per-employee stop-loss health questionnaire"],
        coverages=[_coverage("level_funded_standard", "Standard Level-Funded Plan", "Per-employee stop-loss health questionnaire")],
    ),
    # ===== 6. TOP-UP / SUPPLEMENTAL GAP =====
    _line(
        id="supplemental_gap_coverage",
        slug="supplemental-gap-coverage",
        name="Supplemental / Gap Health Coverage",
        short_name="Gap Coverage",
        category_id="top_up",
        checklist_lob="supplemental_gap_coverage",
        description="Sits above a high-deductible base plan and pays once its deductible is exhausted — Standard Gap (per-incident) or Super Gap (annual aggregate).",
        uw_focus="Confirm the base plan's deductible amount — the gap policy is priced and triggered relative to it.",
        additional_documents=["Base health plan declarations page (to confirm the underlying deductible)"],
        coverages=[
            _coverage("standard_gap", "Standard Gap (per incident)", "Base health plan declarations page (to confirm the underlying deductible)"),
            _coverage("super_gap", "Super Gap (annual aggregate)", "Base health plan declarations page (to confirm the underlying deductible)"),
        ],
    ),
    _line(
        id="hospital_indemnity",
        slug="hospital-indemnity",
        name="Hospital Indemnity",
        short_name="Hospital Indemnity",
        category_id="top_up",
        checklist_lob="hospital_indemnity",
        description="Fixed dollar-per-day-of-hospitalization cash payout — pays regardless of the base plan's deductible or coinsurance and independent of actual billed charges.",
        uw_focus="Confirm the elected daily benefit amount and bank details for cash payout.",
        additional_documents=["Bank account details (for cash payout)"],
        coverages=[_coverage("hospital_indemnity_standard", "Standard Hospital Indemnity", "Bank account details (for cash payout)")],
    ),
    # ===== 7. PERSONAL ACCIDENT (AD&D) =====
    _line(
        id="add_accident_indemnity",
        slug="add-accident-indemnity",
        name="AD&D / Accident Indemnity",
        short_name="AD&D",
        category_id="personal_accident",
        checklist_lob="add_accident_indemnity",
        description="Accidental Death & Dismemberment and accident indemnity cover — pays only for accidental injury or death, not illness. Individual, family, or group.",
        uw_focus="Occupation class is the dominant rating factor — a hazardous occupation (Class IV) is referred for underwriter review.",
        additional_documents=["Occupation details (job title and duties, for occupation-class rating)"],
        coverages=[
            _coverage("individual", "AD&D — Individual", "Occupation details (job title and duties, for occupation-class rating)"),
            _coverage("family", "AD&D — Family", "Occupation details (job title and duties, for occupation-class rating)"),
            _coverage("group", "AD&D — Group", "Occupation details (job title and duties, for occupation-class rating)"),
        ],
    ),
    _line(
        id="standalone_add",
        slug="standalone-add",
        name="Standalone AD&D",
        short_name="Standalone AD&D",
        category_id="personal_accident",
        checklist_lob="standalone_add",
        description="Pure death/dismemberment schedule only — no accident-medical-expense or weekly-indemnity benefit. Cheaper and narrower than the combined AD&D / Accident Indemnity product.",
        uw_focus="Occupation class is the dominant rating factor — a hazardous occupation (Class IV) is referred for underwriter review.",
        additional_documents=["Occupation details (job title and duties, for occupation-class rating)", "Nominee ID proof"],
        coverages=[_coverage("standalone_add_standard", "Standard Standalone AD&D", "Nominee ID proof")],
    ),
    # ===== 8. DISABILITY INCOME =====
    _line(
        id="short_term_disability",
        slug="short-term-disability",
        name="Short-Term Disability Income",
        short_name="STD",
        category_id="disability",
        checklist_lob="short_term_disability",
        description="Weekly income-replacement benefit, short elimination period, benefit period typically capped at 2 years. Coordinates with mandatory state SDI in CA/NY/NJ/RI/HI.",
        uw_focus="Verify the weekly benefit against documented income (most filings cap replacement at 60-70%); confirm SDI coordination in an SDI state.",
        additional_documents=["Income verification (pay stub or W-2)", "Occupation details (job title and duties, for occupation-class rating)"],
        coverages=[_coverage("std_standard", "Standard Short-Term Disability", "Income verification (pay stub or W-2)")],
    ),
    _line(
        id="long_term_disability",
        slug="long-term-disability",
        name="Long-Term Disability Income",
        short_name="LTD",
        category_id="disability",
        checklist_lob="long_term_disability",
        description="Monthly income-replacement benefit, longer elimination period, benefit period runs to a fixed term or to age 65.",
        uw_focus="Benefit is capped as a percentage of pre-disability income — verify income documentation before issuing above the replacement ceiling.",
        additional_documents=["Income verification (pay stub, W-2, or tax return)", "Occupation details (job title and duties, for occupation-class rating)"],
        coverages=[_coverage("ltd_standard", "Standard Long-Term Disability", "Income verification (pay stub, W-2, or tax return)")],
    ),
    _line(
        id="disability_ptd",
        slug="permanent-total-disability",
        name="Permanent Total Disability",
        short_name="PTD",
        category_id="disability",
        checklist_lob="disability_ptd",
        description="Lump-sum-or-extended-benefit payout triggered by a permanent and total inability to work — not a periodic income-replacement benefit like STD/LTD.",
        uw_focus="Confirm the disability determination is permanent and total, not a recoverable condition better suited to STD/LTD.",
        additional_documents=["Medical fitness certificate", "Occupation details (job title and duties, for occupation-class rating)"],
        coverages=[_coverage("ptd_standard", "Standard Permanent Total Disability", "Medical fitness certificate")],
    ),
    _line(
        id="disability_ppd",
        slug="permanent-partial-disability",
        name="Permanent Partial Disability",
        short_name="PPD",
        category_id="disability",
        checklist_lob="disability_ppd",
        description="Scheduled-injury lump sum (loss of a limb, sight, or hearing) — no income proof required since the payout is fixed by the schedule, not earnings.",
        uw_focus="Match the disclosed injury type to the correct schedule percentage; do not invent a schedule entry that isn't in the filed manual.",
        additional_documents=["Medical fitness certificate"],
        coverages=[_coverage("ppd_standard", "Standard Permanent Partial Disability", "Medical fitness certificate")],
    ),
]

for _ln in HEALTH_LINES:
    _ln["status"] = "live" if _ln["id"] in LIVE_HEALTH_PRODUCT_IDS else "catalog"


# ── Self-describing: stamp every product/coverage with its dedicated LOB
# logic path, the same pattern insureflow.insurance.life_lobs uses. ─────────
def _logic_paths() -> dict[str, str]:
    try:
        from insureflow.health.lobs import PRODUCT_LOGIC_PATHS

        return dict(PRODUCT_LOGIC_PATHS)
    except Exception:
        return {}


_LOGIC_PATHS = _logic_paths()
for _ln in HEALTH_LINES:
    if _ln["id"] in _LOGIC_PATHS:
        _ln["logic_path"] = _LOGIC_PATHS[_ln["id"]]
        for _cov in _ln.get("coverages") or []:
            _cov["logic_path"] = _LOGIC_PATHS[_ln["id"]]


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
            "US health underwriting — ACA Marketplace individual/family, Medicare Supplement/Advantage, "
            "employer group, critical illness, supplemental gap coverage, AD&D, and disability income. "
            "Each leaf has a shared KYC base packet plus product-specific documents, its own dedicated "
            "underwriting/rating logic path, and state rules applied inside that path — "
            "rated from the filed health manual (HLTH-US-2026-01)."
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
