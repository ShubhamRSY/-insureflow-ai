"""Life Insurance LOB catalog: taxonomy + document packs + UW workflow.

Source of truth for the Life Insurance hub UI and LOB-aware package checklists.
Organized as categories → products → coverages for underwriter navigation.

Document model (US-focused):
- Every policy requires LIFE_BASE_PACKET at minimum.
- Each product lists only the ADDITIONAL documents required beyond that base
  set; `documents` exposes the full required set (base + additional) so the
  pipeline package checklist covers every item a submission may be missing.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.insurance.commercial_lobs import (
    _coverage,
    _normalize_coverages,
    flatten_line_documents,
)

# BASE DOCUMENT SET — required for every life insurance policy (US)
LIFE_BASE_PACKET: list[str] = [
    "Government-issued photo ID (driver's license, state ID, or passport)",
    "Social Security Number (SSN)",
    "Proof of address (utility bill, bank statement, or lease — last 3 months)",
    "Completed life insurance application",
    "Signed HIPAA authorization (medical records release)",
    "Signed MIB (Medical Information Bureau) and Rx database check authorization",
    "Health questionnaire (part of application)",
    "Beneficiary's full name, DOB, SSN, and relationship to insured",
    "Income proof (pay stubs, W-2, or tax returns) — required above coverage thresholds",
]

LIFE_UW_RESPONSIBILITIES: list[dict[str, str]] = [
    {
        "id": "suitability",
        "title": "Needs & suitability",
        "summary": "Confirm the coverage amount, purpose, and product fit against documented need, income, and insurable interest.",
    },
    {
        "id": "medical",
        "title": "Medical underwriting",
        "summary": "Assign an underwriting class (preferred → substandard), apply ratings / flat extras, and decline uninsurable conditions.",
    },
    {
        "id": "financial",
        "title": "Financial underwriting",
        "summary": "Sanity-check face amount against income, net worth, and business value multiples; review source of funds for large premiums.",
    },
    {
        "id": "riders",
        "title": "Product fit & riders",
        "summary": "Validate structure: term vs cash value, living benefit riders, ownership, and beneficiary arrangements.",
    },
    {
        "id": "avocation",
        "title": "Avocation / hazardous activity",
        "summary": "Review aviation, diving, motorsports, and hazardous avocations that drive flat extras or refer.",
    },
    {
        "id": "decision",
        "title": "Decision",
        "summary": "Issue standard / preferred, rated (tables, flat extras), condition (APS / exam), refer, or decline.",
    },
    {
        "id": "portfolio",
        "title": "Retention & reinsurance",
        "summary": "Respect line retention; route jumbo / facultative and impaired risks to reinsurers.",
    },
]

LIFE_CATEGORIES: list[dict[str, str]] = [
    {
        "id": "term",
        "name": "Term Life Insurance",
        "summary": "Temporary coverage — level, decreasing (incl. mortgage), increasing, renewable, convertible, ROP, group, and credit life.",
    },
    {
        "id": "whole",
        "name": "Whole Life Insurance",
        "summary": "Guaranteed permanent coverage — ordinary, limited-pay, single-premium, par, non-par, modified, and graded / guaranteed issue.",
    },
    {
        "id": "universal",
        "name": "Universal Life Insurance",
        "summary": "Interest-sensitive permanent coverage — GUL, indexed (IUL), variable (VUL), and current assumption / adjustable.",
    },
    {
        "id": "endowment",
        "name": "Endowment Plans",
        "summary": "Rare / largely discontinued in the US market — pure, with-profit, and guaranteed / fixed endowments.",
    },
    {
        "id": "ulip",
        "name": "Unit-Linked Insurance Plans (ULIPs)",
        "summary": "US equivalent: variable universal life (VUL) — single / regular premium, Type I & II, pension, and child ULIPs.",
    },
    {
        "id": "money_back",
        "name": "Money-Back Policies",
        "summary": "Rare in the US (closer to return-of-premium riders) — traditional, with-profit, and children's money-back plans.",
    },
    {
        "id": "annuity",
        "name": "Annuities / Pension Plans",
        "summary": "Income and retirement products — immediate, deferred, fixed, variable, indexed, life, joint / survivor, QLAC, and structured settlements.",
    },
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
    acord_forms: list[str] | None = None,
    coverages: list[dict[str, Any]] | None = None,
    status: str = "live",
) -> dict[str, Any]:
    additional = [str(d).strip() for d in additional_documents if str(d).strip()]
    documents = list(LIFE_BASE_PACKET)
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
        "insurance_line": "life",
        "rating_line": "life",
        "description": description,
        "uw_focus": uw_focus,
        "acord_forms": list(acord_forms or []),
        "documents": documents,
        "additional_documents": additional,
        "coverages": covs,
        "status": status,  # live = full UW + LOB-scoped ML path
    }


# ---------------------------------------------------------------------------
# Life insurance product catalog
# ---------------------------------------------------------------------------

LIFE_LINES: list[dict[str, Any]] = [
    # ===== 1. TERM LIFE =====================================================
    _line(
        id="level_term",
        slug="level-term",
        name="Level Term Life Insurance",
        short_name="Level Term",
        category_id="term",
        checklist_lob="level_term",
        description="Guaranteed level premium and death benefit for a fixed term. Base set only — a paramedical exam is required above ~$100K–$250K (insurer-dependent).",
        uw_focus="Standard medical underwriting with class assignment; verify duration choice matches the need horizon and confirm the paramedical threshold for the requested face.",
        acord_forms=["ACORD 100"],
        additional_documents=[],
        coverages=[
            _coverage("level_term_10", "10-Year Level Term", "Completed life insurance application", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
            _coverage("level_term_20", "20-Year Level Term", "Completed life insurance application", "Income proof (pay stubs, W-2, or tax returns) — required above coverage thresholds"),
            _coverage("level_term_30", "30-Year Level Term", "Paramedical exam report (required above ~$100K–$250K)", "Completed life insurance application"),
        ],
    ),
    _line(
        id="decreasing_term",
        slug="decreasing-term",
        name="Decreasing Term Life Insurance",
        short_name="Decreasing Term",
        category_id="term",
        checklist_lob="decreasing_term",
        description="Death benefit declines over time — typically matches a mortgage or other declining debt balance.",
        uw_focus="Confirm the reducing benefit tracks the underlying debt schedule; mortgage statements and payoff tables required.",
        acord_forms=["ACORD 100"],
        additional_documents=[
            "Loan / mortgage statement (to match coverage to the declining balance)",
        ],
        coverages=[
            _coverage("mortgage_term", "Mortgage Protection Term", "Loan / mortgage statement (to match coverage to the declining balance)", "Completed life insurance application"),
            _coverage("debt_term", "Debt-Reducing Term", "Loan / mortgage statement (to match coverage to the declining balance)", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    _line(
        id="mortgage_life",
        slug="mortgage-life",
        name="Mortgage Life Insurance",
        short_name="Mortgage Life",
        category_id="term",
        checklist_lob="mortgage_life",
        description="Decreasing term tied to the mortgage so the balance is paid off if the insured dies.",
        uw_focus="Match coverage to the outstanding mortgage balance and confirm the lender's interest and account details.",
        acord_forms=["ACORD 100"],
        additional_documents=[
            "Mortgage statement / loan documents",
            "Lender information (name, loan account number)",
        ],
        coverages=[
            _coverage("mortgage_balance", "Mortgage Balance Protection", "Mortgage statement / loan documents", "Lender information (name, loan account number)"),
            _coverage("lender_assign", "Lender-Assigned Benefit", "Lender information (name, loan account number)", "Completed life insurance application"),
        ],
    ),
    _line(
        id="increasing_term",
        slug="increasing-term",
        name="Increasing Term Life Insurance",
        short_name="Increasing Term",
        category_id="term",
        checklist_lob="increasing_term",
        description="Death benefit rises on a scheduled basis (often tracking CPI or a fixed annual percentage).",
        uw_focus="Confirm the scheduled benefit increases, premium impact, and affordability over the projected term.",
        acord_forms=["ACORD 100"],
        additional_documents=[],
        coverages=[
            _coverage("cpi_term", "CPI-Linked Increasing Term", "Completed life insurance application", "Income proof (pay stubs, W-2, or tax returns) — required above coverage thresholds"),
            _coverage("step_term", "Step-Up Increasing Term", "Completed life insurance application", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    _line(
        id="renewable_term",
        slug="renewable-term",
        name="Renewable Term Life Insurance",
        short_name="Renewable Term",
        category_id="term",
        checklist_lob="renewable_term",
        description="Term coverage that renews at the end of each period without a new medical exam; premium rises with age.",
        uw_focus="Base set only at issue; a renewal form is signed at each renewal with no new medical exam required.",
        acord_forms=["ACORD 100"],
        additional_documents=[
            "Renewal form (signed at each renewal; no new medical exam required)",
        ],
        coverages=[
            _coverage("renewal_period", "Renewable Term (Renewal)", "Renewal form (signed at each renewal; no new medical exam required)", "Completed life insurance application"),
            _coverage("art_style", "Annual Renewable Style", "Completed life insurance application", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    _line(
        id="convertible_term",
        slug="convertible-term",
        name="Convertible Term Life Insurance",
        short_name="Convertible Term",
        category_id="term",
        checklist_lob="convertible_term",
        description="Term coverage convertible to permanent coverage without new medical underwriting during the conversion window.",
        uw_focus="Base set only at issue; a conversion request form is required at conversion with no new medical underwriting.",
        acord_forms=["ACORD 100"],
        additional_documents=[
            "Conversion request form (signed at conversion; no new medical underwriting required)",
        ],
        coverages=[
            _coverage(
                "convert_period", "Convertible Term (Conversion)", "Conversion request form (signed at conversion; no new medical underwriting required)", "Completed life insurance application"
            ),
            _coverage("permanent_conversion", "Convert-to-Permanent", "Completed life insurance application", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    _line(
        id="rop_term",
        slug="return-of-premium-term",
        name="Return of Premium (ROP) Term Life Insurance",
        short_name="ROP Term",
        category_id="term",
        checklist_lob="rop_term",
        description="Level term that returns a portion or all premiums paid if the insured outlives the term.",
        uw_focus="Higher premium offset by the cash-back feature; verify the refund schedule and persistency assumptions.",
        acord_forms=["ACORD 100"],
        additional_documents=[
            "Illustration acknowledgment showing the refund schedule",
        ],
        coverages=[
            _coverage("full_rop", "Full Return-of-Premium Rider", "Illustration acknowledgment showing the refund schedule", "Completed life insurance application"),
            _coverage("partial_rop", "Partial Return-of-Premium Rider", "Illustration acknowledgment showing the refund schedule", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    _line(
        id="group_term_life",
        slug="group-term-life",
        name="Group Term Life Insurance",
        short_name="Group Term",
        category_id="term",
        checklist_lob="group_term_life",
        description="Employer-sponsored term life typically 1x salary with supplemental buy-up options.",
        uw_focus="Group eligibility, participation requirements, $50k imputed income (IRC 79), and evidence of insurability thresholds.",
        acord_forms=["Group life certificate / application"],
        additional_documents=[
            "Enrollment form (via employer — beneficiary designation is a separate, individual form)",
        ],
        coverages=[
            _coverage("basic_group", "Basic Group Term Life", "Enrollment form (via employer — beneficiary designation is a separate, individual form)", "Health questionnaire (part of application)"),
            _coverage(
                "supplemental_group", "Supplemental Group Term Life", "Enrollment form (via employer — beneficiary designation is a separate, individual form)", "Completed life insurance application"
            ),
            _coverage("dependent_group", "Dependent Group Term Life", "Health questionnaire (part of application)", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    _line(
        id="credit_life",
        slug="credit-life",
        name="Credit Life Insurance",
        short_name="Credit Life",
        category_id="term",
        checklist_lob="credit_life",
        description="Pays outstanding loan balance if the borrower dies — often declining term aligned to the debt.",
        uw_focus="Debt schedule, creditor relationship, and declining-balance alignment; typically simplified health only (often no exam).",
        acord_forms=["Credit life certificate / application"],
        additional_documents=[
            "Loan agreement / credit account documents",
            "Lender's name and account number",
            "Simplified health declaration (often no exam)",
        ],
        coverages=[
            _coverage("loan_balance", "Outstanding Balance Credit Life", "Loan agreement / credit account documents", "Lender's name and account number"),
            _coverage("simplified_credit", "Simplified Issue Credit Life", "Simplified health declaration (often no exam)", "Loan agreement / credit account documents"),
        ],
    ),
    # ===== 2. WHOLE LIFE ====================================================
    _line(
        id="traditional_whole_life",
        slug="traditional-whole-life",
        name="Traditional / Ordinary Whole Life",
        short_name="Whole Life",
        category_id="whole",
        checklist_lob="traditional_whole_life",
        description="Guaranteed permanent coverage with fixed premium and guaranteed cash value.",
        uw_focus="Standard medical underwriting; verify dividend / participating status, premium mode, and paid-up features.",
        acord_forms=["ACORD 100 (Parts I-III)"],
        additional_documents=[
            "Illustration acknowledgment (signed, confirming you understand the cash value projections)",
            "Paramedical exam report (age / coverage dependent)",
        ],
        coverages=[
            _coverage(
                "guaranteed_whole", "Guaranteed Whole Life", "Illustration acknowledgment (signed, confirming you understand the cash value projections)", "Completed life insurance application"
            ),
            _coverage("ordinary_whole", "Ordinary Whole Life", "Paramedical exam report (age / coverage dependent)", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    _line(
        id="limited_pay_whole_life",
        slug="limited-pay-whole-life",
        name="Limited-Pay Whole Life (10-Pay, 20-Pay, etc.)",
        short_name="Limited-Pay",
        category_id="whole",
        checklist_lob="limited_pay_whole_life",
        description="Whole life fully paid up after a limited number of premium payments (e.g., 10 or 20 years).",
        uw_focus="Verify the premium payment schedule and affordability during the limited-pay period.",
        acord_forms=["ACORD 100"],
        additional_documents=[
            "Illustration acknowledgment showing the premium payment schedule",
        ],
        coverages=[
            _coverage(
                "ten_pay", "10-Pay Whole Life", "Illustration acknowledgment showing the premium payment schedule", "Income proof (pay stubs, W-2, or tax returns) — required above coverage thresholds"
            ),
            _coverage("twenty_pay", "20-Pay Whole Life", "Illustration acknowledgment showing the premium payment schedule", "Completed life insurance application"),
            _coverage("paid_up", "Paid-Up-at-65 Whole Life", "Illustration acknowledgment showing the premium payment schedule", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    _line(
        id="single_premium_whole_life",
        slug="single-premium-whole-life",
        name="Single-Premium Whole Life",
        short_name="Single-Premium",
        category_id="whole",
        checklist_lob="single_premium_whole_life",
        description="Whole life funded by one large lump-sum premium payment.",
        uw_focus="Source of funds review and AML compliance for large lump-sum premium payments.",
        acord_forms=["ACORD 100"],
        additional_documents=[
            "Source of funds documentation (proof of lump sum — bank statement, sale proceeds, etc.)",
            "Anti-money laundering (AML) declaration (large lump sum payments trigger this)",
        ],
        coverages=[
            _coverage(
                "lump_sum",
                "Single-Premium Whole Life",
                "Source of funds documentation (proof of lump sum — bank statement, sale proceeds, etc.)",
                "Anti-money laundering (AML) declaration (large lump sum payments trigger this)",
            ),
            _coverage(
                "instant_cash", "Immediate Cash Value Single-Premium", "Source of funds documentation (proof of lump sum — bank statement, sale proceeds, etc.)", "Completed life insurance application"
            ),
        ],
    ),
    _line(
        id="participating_whole_life",
        slug="participating-whole-life",
        name="Participating (Par) Whole Life",
        short_name="Par Whole Life",
        category_id="whole",
        checklist_lob="participating_whole_life",
        description="Whole life that pays dividends to policyholders from insurer profits.",
        uw_focus="Dividend scale assumptions, option elections, and non-guaranteed nature of dividends.",
        acord_forms=["ACORD 100 (Parts I-III)"],
        additional_documents=[
            "Dividend option election form (cash, paid-up additions, premium reduction, or accumulation)",
        ],
        coverages=[
            _coverage("div_cash", "Dividend Cash Option", "Dividend option election form (cash, paid-up additions, premium reduction, or accumulation)", "Completed life insurance application"),
            _coverage(
                "div_pua",
                "Dividend Paid-Up Additions (PUA)",
                "Dividend option election form (cash, paid-up additions, premium reduction, or accumulation)",
                "Beneficiary's full name, DOB, SSN, and relationship to insured",
            ),
        ],
    ),
    _line(
        id="non_participating_whole_life",
        slug="non-participating-whole-life",
        name="Non-Participating (Non-Par) Whole Life",
        short_name="Non-Par Whole Life",
        category_id="whole",
        checklist_lob="non_participating_whole_life",
        description="Whole life with guaranteed values and no dividend participation.",
        uw_focus="Base set only; confirm guaranteed values, premium structure, and paid-up features.",
        acord_forms=["ACORD 100"],
        additional_documents=[],
        coverages=[
            _coverage("non_par_whole", "Non-Par Whole Life", "Completed life insurance application", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
            _coverage("non_par_paid_up", "Non-Par Paid-Up at 65", "Completed life insurance application", "Income proof (pay stubs, W-2, or tax returns) — required above coverage thresholds"),
        ],
    ),
    _line(
        id="modified_whole_life",
        slug="modified-whole-life",
        name="Modified Whole Life",
        short_name="Modified Whole Life",
        category_id="whole",
        checklist_lob="modified_whole_life",
        description="Whole life with lower early premiums that step up to a higher level after a set number of years.",
        uw_focus="Confirm the premium step-up schedule and that the insured can afford the higher later premiums.",
        acord_forms=["ACORD 100"],
        additional_documents=[
            "Illustration acknowledgment showing the premium step-up schedule",
        ],
        coverages=[
            _coverage("modified_step", "Modified Whole Life (Step-Up)", "Illustration acknowledgment showing the premium step-up schedule", "Completed life insurance application"),
            _coverage("modified_5_10", "Modified 5/10 Pay", "Illustration acknowledgment showing the premium step-up schedule", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    _line(
        id="graded_guaranteed_issue_whole_life",
        slug="graded-guaranteed-issue-whole-life",
        name="Graded / Guaranteed Issue Whole Life",
        short_name="Graded / GI",
        category_id="whole",
        checklist_lob="graded_guaranteed_issue_whole_life",
        description="Whole life with limited or no health questions and a graded death benefit in the first years.",
        uw_focus="Graded vs immediate benefit, limited face amounts, and anti-selection controls; no paramedical exam required.",
        acord_forms=["Graded / guaranteed issue application"],
        additional_documents=[
            "Simplified / no-exam application (fewer health questions)",
            "Graded benefit disclosure (acknowledgment that the death benefit is limited / refund-only in the first 2 years)",
        ],
        coverages=[
            _coverage(
                "graded_benefit",
                "Graded Benefit Whole Life",
                "Graded benefit disclosure (acknowledgment that the death benefit is limited / refund-only in the first 2 years)",
                "Simplified / no-exam application (fewer health questions)",
            ),
            _coverage("guaranteed_issue", "Guaranteed Issue Whole Life", "Simplified / no-exam application (fewer health questions)", "Completed life insurance application"),
        ],
    ),
    # ===== 3. UNIVERSAL LIFE ================================================
    _line(
        id="guaranteed_universal_life",
        slug="guaranteed-universal-life",
        name="Guaranteed Universal Life (GUL)",
        short_name="GUL",
        category_id="universal",
        checklist_lob="guaranteed_universal_life",
        description="Universal life with a no-lapse guarantee — premium and death benefit guaranteed to a stated age or lifetime.",
        uw_focus="Guaranteed premium / coverage schedule, lapse-protection mechanics, and funding discipline.",
        acord_forms=["ACORD 100 + GUL supplement"],
        additional_documents=[
            "Illustration acknowledgment (guaranteed premium / coverage schedule)",
        ],
        coverages=[
            _coverage("no_lapse", "No-Lapse Guarantee", "Illustration acknowledgment (guaranteed premium / coverage schedule)", "Completed life insurance application"),
            _coverage("gul_to_120", "GUL to Age 120", "Illustration acknowledgment (guaranteed premium / coverage schedule)", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    _line(
        id="indexed_universal_life",
        slug="indexed-universal-life",
        name="Indexed Universal Life (IUL)",
        short_name="IUL",
        category_id="universal",
        checklist_lob="indexed_universal_life",
        description="Universal life whose cash value credits are linked to an equity index with a floor and cap.",
        uw_focus="Scrutinize cap / floor / participation assumptions, backtest illustration versus historical index, and lapse risk.",
        acord_forms=["ACORD 100 + IUL supplement"],
        additional_documents=[
            "Illustration acknowledgment (cap / floor / participation rate disclosure)",
            "Index allocation election form (choice of indexed vs. fixed account)",
        ],
        coverages=[
            _coverage(
                "indexed_account",
                "Indexed Account (Cap / Floor)",
                "Index allocation election form (choice of indexed vs. fixed account)",
                "Illustration acknowledgment (cap / floor / participation rate disclosure)",
            ),
            _coverage("fixed_account", "Fixed Account Allocation", "Index allocation election form (choice of indexed vs. fixed account)", "Completed life insurance application"),
            _coverage(
                "blend", "Indexed + Fixed Blend", "Illustration acknowledgment (cap / floor / participation rate disclosure)", "Index allocation election form (choice of indexed vs. fixed account)"
            ),
        ],
    ),
    _line(
        id="variable_universal_life",
        slug="variable-universal-life",
        name="Variable Universal Life (VUL)",
        short_name="VUL",
        category_id="universal",
        checklist_lob="variable_universal_life",
        description="Universal life with cash value invested in sub-accounts (securities). Must be sold by an agent holding Series 6 or 7 plus an insurance license.",
        uw_focus="Suitability and FINRA / Series 6-7 requirements; review sub-account allocations, fund expenses, and NAIC illustration standards.",
        acord_forms=["ACORD 100 + VUL prospectus / suitability"],
        additional_documents=[
            "Prospectus acknowledgment (SEC-required — VUL is regulated as a security)",
            "FINRA suitability questionnaire (risk tolerance, investment objectives, net worth)",
            "Sub-account / fund allocation election form",
            "Broker-dealer new account form (since it involves a securities account)",
        ],
        coverages=[
            _coverage("vx_account", "Variable Sub-Accounts", "Sub-account / fund allocation election form", "Prospectus acknowledgment (SEC-required — VUL is regulated as a security)"),
            _coverage(
                "finra_suitability",
                "FINRA-Screened Suitability",
                "FINRA suitability questionnaire (risk tolerance, investment objectives, net worth)",
                "Broker-dealer new account form (since it involves a securities account)",
            ),
            _coverage("gmdb", "Guaranteed Minimum Death Benefit", "Prospectus acknowledgment (SEC-required — VUL is regulated as a security)", "Completed life insurance application"),
        ],
    ),
    _line(
        id="current_assumption_universal_life",
        slug="current-assumption-universal-life",
        name="Current Assumption / Adjustable Universal Life",
        short_name="Adjustable UL",
        category_id="universal",
        checklist_lob="current_assumption_universal_life",
        description="Universal life with flexible premiums and an interest rate based on current market assumptions.",
        uw_focus="Flexible premium / interest rate disclosure, adjustable coverage, and lapse risk under current vs guaranteed rates.",
        acord_forms=["ACORD 100 + UL supplement"],
        additional_documents=[
            "Illustration acknowledgment (flexible premium / interest rate disclosure)",
        ],
        coverages=[
            _coverage("adjustable", "Adjustable Coverage UL", "Illustration acknowledgment (flexible premium / interest rate disclosure)", "Completed life insurance application"),
            _coverage("current_rate", "Current-Rate UL", "Illustration acknowledgment (flexible premium / interest rate disclosure)", "Beneficiary's full name, DOB, SSN, and relationship to insured"),
        ],
    ),
    # ===== 4. ENDOWMENT PLANS ===============================================
    _line(
        id="pure_endowment",
        slug="pure-endowment",
        name="Pure Endowment",
        short_name="Pure Endowment",
        category_id="endowment",
        checklist_lob="pure_endowment",
        description="Pays the policy amount only at maturity (end of term) if the insured survives; rare / largely discontinued in the US.",
        uw_focus="Rare product in the US; confirm maturity date, payout mechanics, and the bank account for the maturity payout.",
        acord_forms=["Endowment application"],
        additional_documents=[
            "Bank account / ACH form (for the maturity payout)",
        ],
        coverages=[
            _coverage("pure_maturity", "Pure Endowment (Maturity)", "Bank account / ACH form (for the maturity payout)", "Completed life insurance application"),
        ],
    ),
    _line(
        id="full_endowment",
        slug="full-with-profit-endowment",
        name="Full / With-Profit Endowment",
        short_name="With-Profit Endowment",
        category_id="endowment",
        checklist_lob="full_endowment",
        description="Endowment paying the sum assured plus accumulated dividends / bonuses at maturity.",
        uw_focus="Dividend / bonus scale and option election; payout mechanics and bank details.",
        acord_forms=["Endowment application"],
        additional_documents=[
            "Bank account / ACH form (for the maturity payout)",
            "Dividend / bonus option election form",
        ],
        coverages=[
            _coverage("with_profit", "With-Profit Endowment", "Dividend / bonus option election form", "Bank account / ACH form (for the maturity payout)"),
        ],
    ),
    _line(
        id="guaranteed_fixed_endowment",
        slug="guaranteed-fixed-endowment",
        name="Guaranteed / Fixed Endowment",
        short_name="Fixed Endowment",
        category_id="endowment",
        checklist_lob="guaranteed_fixed_endowment",
        description="Endowment with guaranteed fixed returns payable at maturity.",
        uw_focus="Guaranteed values and maturity payout mechanics.",
        acord_forms=["Endowment application"],
        additional_documents=[
            "Bank account / ACH form (for the maturity payout)",
        ],
        coverages=[
            _coverage("fixed_endowment", "Guaranteed Fixed Endowment", "Bank account / ACH form (for the maturity payout)", "Completed life insurance application"),
        ],
    ),
    # ===== 5. UNIT-LINKED INSURANCE PLANS (ULIPs) — US: VUL =================
    _line(
        id="single_premium_ulip",
        slug="single-premium-ulip",
        name="Single Premium ULIP",
        short_name="Single-Premium ULIP",
        category_id="ulip",
        checklist_lob="single_premium_ulip",
        description="Unit-linked plan funded by one lump-sum premium; the US equivalent is single-premium variable life.",
        uw_focus="Source of funds, prospectus acknowledgment, and risk profiling / suitability for the lump-sum investment.",
        acord_forms=["ULIP / variable life application"],
        additional_documents=[
            "Source of funds documentation",
            "Prospectus acknowledgment",
            "Risk profiling / suitability questionnaire",
        ],
        coverages=[
            _coverage("sp_ulip", "Single-Premium ULIP", "Source of funds documentation", "Risk profiling / suitability questionnaire"),
        ],
    ),
    _line(
        id="regular_premium_ulip",
        slug="regular-premium-ulip",
        name="Regular Premium ULIP",
        short_name="Regular ULIP",
        category_id="ulip",
        checklist_lob="regular_premium_ulip",
        description="Unit-linked plan funded by regular premiums; the US equivalent is flexible-premium variable universal life.",
        uw_focus="Suitability, ongoing premium funding, and auto-debit (ACH) authorization for regular premiums.",
        acord_forms=["ULIP / variable life application"],
        additional_documents=[
            "Prospectus acknowledgment",
            "Risk profiling / suitability questionnaire",
            "Bank account / auto-debit (ACH) authorization",
        ],
        coverages=[
            _coverage("rp_ulip", "Regular-Premium ULIP", "Bank account / auto-debit (ACH) authorization", "Risk profiling / suitability questionnaire"),
        ],
    ),
    _line(
        id="ulip_type_i",
        slug="ulip-type-i",
        name="Type I ULIP (higher of sum assured or fund value)",
        short_name="Type I ULIP",
        category_id="ulip",
        checklist_lob="ulip_type_i",
        description="Death benefit is the higher of the sum assured or the fund value.",
        uw_focus="Same requirements as regular / single premium ULIP; verify the death-benefit basis is understood.",
        acord_forms=["ULIP / variable life application"],
        additional_documents=[
            "Source of funds documentation",
            "Prospectus acknowledgment",
            "Risk profiling / suitability questionnaire",
        ],
        coverages=[
            _coverage("type_i", "Type I ULIP — Higher of Sum Assured or Fund Value", "Prospectus acknowledgment", "Risk profiling / suitability questionnaire"),
        ],
    ),
    _line(
        id="ulip_type_ii",
        slug="ulip-type-ii",
        name="Type II ULIP (sum assured + fund value)",
        short_name="Type II ULIP",
        category_id="ulip",
        checklist_lob="ulip_type_ii",
        description="Death benefit is the sum assured plus the fund value.",
        uw_focus="Same requirements as regular / single premium ULIP; verify the death-benefit basis is understood.",
        acord_forms=["ULIP / variable life application"],
        additional_documents=[
            "Source of funds documentation",
            "Prospectus acknowledgment",
            "Risk profiling / suitability questionnaire",
        ],
        coverages=[
            _coverage("type_ii", "Type II ULIP — Sum Assured Plus Fund Value", "Prospectus acknowledgment", "Risk profiling / suitability questionnaire"),
        ],
    ),
    _line(
        id="pension_ulip",
        slug="pension-ulip",
        name="Pension / Retirement ULIP",
        short_name="Pension ULIP",
        category_id="ulip",
        checklist_lob="pension_ulip",
        description="Unit-linked plan designed for retirement accumulation with tax advantages.",
        uw_focus="Retirement goal suitability, rollover documentation, and long-term investment horizon.",
        acord_forms=["ULIP / variable life application"],
        additional_documents=[
            "Prospectus acknowledgment",
            "Retirement goal / suitability questionnaire",
            "Existing retirement account statements (if rolling over funds)",
        ],
        coverages=[
            _coverage("pension_ulip", "Pension ULIP", "Retirement goal / suitability questionnaire", "Existing retirement account statements (if rolling over funds)"),
        ],
    ),
    _line(
        id="child_ulip",
        slug="child-ulip",
        name="Child ULIP",
        short_name="Child ULIP",
        category_id="ulip",
        checklist_lob="child_ulip",
        description="Unit-linked plan on a child with the parent / proposer paying premiums.",
        uw_focus="Base set applies to the parent / proposer (not the child); verify the child's details and premium waiver rider.",
        acord_forms=["ULIP / variable life application (proposer)"],
        additional_documents=[
            "Child's birth certificate",
            "Prospectus acknowledgment",
            "Premium waiver rider disclosure (waiver on parent's death)",
        ],
        coverages=[
            _coverage("child_ulip", "Child ULIP (Parent-Paid)", "Child's birth certificate", "Premium waiver rider disclosure (waiver on parent's death)"),
        ],
    ),
    # ===== 6. MONEY-BACK POLICIES ===========================================
    _line(
        id="traditional_money_back",
        slug="traditional-money-back",
        name="Traditional Money-Back Policy",
        short_name="Money-Back",
        category_id="money_back",
        checklist_lob="traditional_money_back",
        description="Policy paying periodic survival benefits at stated milestones with full death benefit if the insured dies earlier.",
        uw_focus="Rare in the US (closer to return-of-premium riders); verify payout schedule and bank details for survival benefits.",
        acord_forms=["Money-back application"],
        additional_documents=[
            "Bank account / ACH form (for periodic survival benefit payouts)",
        ],
        coverages=[
            _coverage("traditional_mb", "Traditional Money-Back", "Bank account / ACH form (for periodic survival benefit payouts)", "Completed life insurance application"),
        ],
    ),
    _line(
        id="with_profit_money_back",
        slug="with-profit-money-back",
        name="With-Profit Money-Back Policy",
        short_name="With-Profit Money-Back",
        category_id="money_back",
        checklist_lob="with_profit_money_back",
        description="Money-back policy with an added dividend / bonus component.",
        uw_focus="Dividend / bonus option election and survival benefit payout mechanics.",
        acord_forms=["Money-back application"],
        additional_documents=[
            "Bank account / ACH form (for periodic survival benefit payouts)",
            "Dividend / bonus option election form",
        ],
        coverages=[
            _coverage("with_profit_mb", "With-Profit Money-Back", "Dividend / bonus option election form", "Bank account / ACH form (for periodic survival benefit payouts)"),
        ],
    ),
    _line(
        id="children_money_back",
        slug="children-money-back",
        name="Children's Money-Back Plan",
        short_name="Children's Money-Back",
        category_id="money_back",
        checklist_lob="children_money_back",
        description="Money-back plan on a child with the parent / proposer paying premiums; payouts are timed to milestones.",
        uw_focus="Base set applies to the parent / proposer; verify the child's details and milestone payout schedule.",
        acord_forms=["Money-back application (proposer)"],
        additional_documents=[
            "Child's birth certificate",
            "Bank account / ACH form (payouts timed to milestones)",
        ],
        coverages=[
            _coverage("children_mb", "Children's Money-Back", "Child's birth certificate", "Bank account / ACH form (payouts timed to milestones)"),
        ],
    ),
    # ===== 7. ANNUITIES / PENSION PLANS =====================================
    _line(
        id="immediate_annuity",
        slug="immediate-annuity",
        name="Immediate Annuity",
        short_name="Immediate Annuity",
        category_id="annuity",
        checklist_lob="immediate_annuity",
        description="Converts a single lump sum into guaranteed income payments starting immediately (typically within one year).",
        uw_focus="Suitability for income needs, source of funds, and payout (annuitization) mechanics.",
        acord_forms=["Annuity application"],
        additional_documents=[
            "Suitability questionnaire",
            "Source of funds documentation",
            "Bank account / ACH form (for the payout phase)",
        ],
        coverages=[
            _coverage("life_income", "Life Income (Single Life)", "Suitability questionnaire", "Source of funds documentation"),
            _coverage("period_certain", "Life with Period Certain", "Suitability questionnaire", "Bank account / ACH form (for the payout phase)"),
        ],
    ),
    _line(
        id="deferred_annuity",
        slug="deferred-annuity",
        name="Deferred Annuity",
        short_name="Deferred Annuity",
        category_id="annuity",
        checklist_lob="deferred_annuity",
        description="Accumulates money now for income payments that begin later.",
        uw_focus="Suitability, source of funds, and future payout-phase banking details.",
        acord_forms=["Annuity application"],
        additional_documents=[
            "Suitability questionnaire",
            "Source of funds documentation",
            "Bank account / ACH form (for the future payout phase)",
        ],
        coverages=[
            _coverage("deferred_accum", "Deferred Annuity (Accumulation)", "Suitability questionnaire", "Source of funds documentation"),
            _coverage("deferred_income", "Deferred Annuity (Income)", "Suitability questionnaire", "Bank account / ACH form (for the future payout phase)"),
        ],
    ),
    _line(
        id="fixed_annuity",
        slug="fixed-annuity",
        name="Fixed Annuity",
        short_name="Fixed Annuity",
        category_id="annuity",
        checklist_lob="fixed_annuity",
        description="Annuity with guaranteed fixed interest and predictable income.",
        uw_focus="Same requirements as immediate / deferred annuities depending on type.",
        acord_forms=["Annuity application"],
        additional_documents=[
            "Suitability questionnaire",
            "Source of funds documentation",
            "Bank account / ACH form (for the payout phase)",
        ],
        coverages=[
            _coverage("fixed_income", "Fixed Annuity (Income)", "Suitability questionnaire", "Bank account / ACH form (for the payout phase)"),
            _coverage("fixed_accum", "Fixed Annuity (Accumulation)", "Suitability questionnaire", "Source of funds documentation"),
        ],
    ),
    _line(
        id="variable_annuity",
        slug="variable-annuity",
        name="Variable Annuity",
        short_name="Variable Annuity",
        category_id="annuity",
        checklist_lob="variable_annuity",
        description="Annuity with sub-account investment options; SEC-regulated security requiring Series 6 / 7 licensing.",
        uw_focus="FINRA suitability, prospectus acknowledgment, and sub-account allocation review.",
        acord_forms=["Variable annuity application + prospectus"],
        additional_documents=[
            "Prospectus acknowledgment (SEC-regulated security)",
            "FINRA suitability questionnaire",
            "Sub-account / fund allocation election form",
        ],
        coverages=[
            _coverage("var_annuity", "Variable Annuity (Sub-Accounts)", "Sub-account / fund allocation election form", "Prospectus acknowledgment (SEC-regulated security)"),
            _coverage("var_gmwb", "Variable Annuity with GMWB", "FINRA suitability questionnaire", "Prospectus acknowledgment (SEC-regulated security)"),
        ],
    ),
    _line(
        id="indexed_annuity",
        slug="indexed-annuity",
        name="Indexed Annuity",
        short_name="Indexed Annuity",
        category_id="annuity",
        checklist_lob="indexed_annuity",
        description="Fixed-index annuity crediting interest linked to an equity index with a cap and floor.",
        uw_focus="Suitability and cap / floor / participation rate disclosure for the crediting strategy.",
        acord_forms=["Indexed annuity application"],
        additional_documents=[
            "Suitability questionnaire",
            "Illustration acknowledgment (cap / floor / participation rate disclosure)",
        ],
        coverages=[
            _coverage("indexed_crediting", "Indexed Annuity (Cap / Floor)", "Illustration acknowledgment (cap / floor / participation rate disclosure)", "Suitability questionnaire"),
            _coverage("fixed_indexed", "Fixed + Indexed Annuity", "Suitability questionnaire", "Completed life insurance application"),
        ],
    ),
    _line(
        id="life_annuity",
        slug="life-annuity",
        name="Life Annuity",
        short_name="Life Annuity",
        category_id="annuity",
        checklist_lob="life_annuity",
        description="Annuity paying income for life — same requirements as an immediate annuity.",
        uw_focus="Same as immediate annuity requirements; verify income-for-life structure and payout banking.",
        acord_forms=["Annuity application"],
        additional_documents=[
            "Suitability questionnaire",
            "Source of funds documentation",
            "Bank account / ACH form (for the payout phase)",
        ],
        coverages=[
            _coverage("single_life_income", "Single Life Annuity", "Suitability questionnaire", "Bank account / ACH form (for the payout phase)"),
            _coverage("life_refund", "Life Annuity with Refund", "Suitability questionnaire", "Source of funds documentation"),
        ],
    ),
    _line(
        id="joint_survivor_annuity",
        slug="joint-life-survivor-annuity",
        name="Joint Life / Survivor Annuity",
        short_name="Joint Survivor Annuity",
        category_id="annuity",
        checklist_lob="joint_survivor_annuity",
        description="Annuity covering two lives, typically paying while either annuitant is alive.",
        uw_focus="Second annuitant details and beneficiary documentation for remaining guaranteed payments if an annuitant dies early.",
        acord_forms=["Annuity application (two annuitants)"],
        additional_documents=[
            "Second annuitant's base information (DOB, SSN, and relationship to the primary annuitant)",
            "Beneficiary documentation (for remaining guaranteed payments if an annuitant dies early)",
        ],
        coverages=[
            _coverage(
                "joint_100",
                "Joint & 100% Survivor",
                "Second annuitant's base information (DOB, SSN, and relationship to the primary annuitant)",
                "Beneficiary documentation (for remaining guaranteed payments if an annuitant dies early)",
            ),
            _coverage("joint_50", "Joint & 50% Survivor", "Second annuitant's base information (DOB, SSN, and relationship to the primary annuitant)", "Completed life insurance application"),
        ],
    ),
    _line(
        id="qlac",
        slug="qualified-longevity-annuity-contract",
        name="Qualified Longevity Annuity Contract (QLAC)",
        short_name="QLAC",
        category_id="annuity",
        checklist_lob="qlac",
        description="Deferred income annuity funded from a qualified retirement account, starting at an advanced age.",
        uw_focus="Funding must come from a 401(k) / IRA; verify custodian transfer paperwork and annual Form 1098-Q reporting.",
        acord_forms=["QLAC / deferred annuity application"],
        additional_documents=[
            "Proof of funding source (must come from 401(k) / IRA)",
            "IRS Form 1098-Q (issued annually once funded)",
            "Retirement account custodian transfer paperwork",
        ],
        coverages=[
            _coverage("qlac_deferred", "QLAC (Deferred Income)", "Proof of funding source (must come from 401(k) / IRA)", "Retirement account custodian transfer paperwork"),
            _coverage("qlac_lifetime", "QLAC Lifetime Income", "Proof of funding source (must come from 401(k) / IRA)", "IRS Form 1098-Q (issued annually once funded)"),
        ],
    ),
    _line(
        id="structured_settlement_annuity",
        slug="structured-settlement-annuity",
        name="Structured Settlement Annuity",
        short_name="Structured Settlement",
        category_id="annuity",
        checklist_lob="structured_settlement_annuity",
        description="Annuity funding periodic payments under a legal settlement, typically for personal-injury awards.",
        uw_focus="Court order / settlement agreement documentation and legal representative involvement.",
        acord_forms=["Structured settlement annuity application"],
        additional_documents=[
            "Court order / settlement agreement documentation",
            "Attorney / legal representative documentation (if applicable)",
        ],
        coverages=[
            _coverage(
                "structured_payments", "Structured Settlement (Periodic Payments)", "Court order / settlement agreement documentation", "Attorney / legal representative documentation (if applicable)"
            ),
            _coverage("structured_lump", "Structured Settlement (Lump-Sum)", "Court order / settlement agreement documentation", "Completed life insurance application"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Catalog queries (mirror commercial_lobs)
# ---------------------------------------------------------------------------


def list_life_categories() -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    live_counts: dict[str, int] = {}
    for line in LIFE_LINES:
        cid = line["category_id"]
        counts[cid] = counts.get(cid, 0) + 1
        if line.get("status") == "live":
            live_counts[cid] = live_counts.get(cid, 0) + 1
    return [
        {
            **cat,
            "product_count": counts.get(cat["id"], 0),
            "live_count": live_counts.get(cat["id"], 0),
        }
        for cat in LIFE_CATEGORIES
    ]


def list_life_lines(*, category_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in LIFE_LINES:
        if category_id and line["category_id"] != category_id:
            continue
        if status and line.get("status") != status:
            continue
        coverages = _normalize_coverages(line.get("coverages"))
        all_docs = flatten_line_documents(line)
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
                "all_documents": all_docs,
                "acord_forms": list(line["acord_forms"]),
                "status": line.get("status") or "catalog",
            }
        )
    return rows


def life_taxonomy_tree() -> list[dict[str, Any]]:
    """Nested categories → products → coverages for UW navigation."""
    by_cat: dict[str, list[dict[str, Any]]] = {c["id"]: [] for c in LIFE_CATEGORIES}
    for row in list_life_lines():
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
    return [
        {
            **cat,
            "products": by_cat.get(cat["id"], []),
        }
        for cat in list_life_categories()
    ]


def get_life_line(line_id_or_slug: str) -> dict[str, Any] | None:
    raw = (line_id_or_slug or "").strip().lower()
    if not raw:
        return None
    dashed = raw.replace("_", "-")
    underscored = raw.replace("-", "_")
    variants = {raw, dashed, underscored}
    for line in LIFE_LINES:
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
                "base_packet": list(LIFE_BASE_PACKET),
                "uw_responsibilities": list(LIFE_UW_RESPONSIBILITIES),
                "uw_question": ("How risky is this life to insure, at what class and premium, and does the face amount make sense for the stated need?"),
            }
    return None


def resolve_life_checklist_lob(identifier: str | None) -> str | None:
    """Resolve a life product identifier (slug / id / checklist_lob / name) to its checklist_lob."""
    if not identifier:
        return None
    target = re.sub(r"[\s_-]+", " ", str(identifier).strip().lower())
    if not target:
        return None
    for line in LIFE_LINES:
        lob = str(line.get("checklist_lob") or "").strip()
        if not lob:
            continue
        candidates = {
            re.sub(r"[\s_-]+", " ", str(line.get("id") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", str(line.get("slug") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", str(line.get("name") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", str(line.get("short_name") or "").strip().lower()),
        }
        if target in candidates:
            return lob
    return None


def _product_keywords(line: dict[str, Any]) -> set[str]:
    """Distinct 2/3-word normalized phrases for a life product used to match free text."""
    parts = [
        str(line.get("name") or ""),
        str(line.get("short_name") or ""),
        str(line.get("description") or ""),
        str(line.get("uw_focus") or ""),
        " ".join(str(f) for f in (line.get("acord_forms") or [])),
        " ".join(str(d) for d in (line.get("additional_documents") or [])),
    ]
    phrases: set[str] = set()
    for part in parts:
        words = [w for w in re.sub(r"[^a-z0-9 ]", " ", part.lower()).split() if len(w) >= 3]
        for n in (2, 3):
            for i in range(len(words) - n + 1):
                phrases.add(" ".join(words[i : i + n]))
    return phrases


def detect_life_product(text_blob: str = "") -> str | None:
    """Best-effort product detection from a submission's text.

    A product is selected when the blob matches at least two of its keyword
    phrases, including at least one three-word phrase. This keeps generic life
    packages (e.g. ``life application`` + ``paramedical exam``) on the generic
    ``life`` catalog instead of a false product match.
    """
    blob = re.sub(r"[^a-z0-9 ]", " ", (text_blob or "").lower())
    if not blob.strip():
        return None
    best: str | None = None
    best_score = 0
    best_trigrams = 0
    for line in LIFE_LINES:
        tri_matches = 0
        score = 0
        for kw in _product_keywords(line):
            if kw not in blob:
                continue
            score += 1
            if len(kw.split()) == 3:
                tri_matches += 1
        if score < 2 or tri_matches < 1:
            continue
        if score > best_score or (score == best_score and tri_matches > best_trigrams):
            best = str(line.get("checklist_lob") or "").strip() or None
            best_score = score
            best_trigrams = tri_matches
    return best


def life_hub_payload() -> dict[str, Any]:
    lines = list_life_lines()
    live = [ln for ln in lines if ln["status"] == "live"]
    return {
        "segment": "personal_life",
        "title": "Life Insurance",
        "summary": (
            "Production life underwriting across term, whole, universal, endowment, unit-linked (VUL), "
            "money-back, and annuity lines — each with a shared base document set plus product-specific "
            "add-ons, medical / financial / suitability UW workflow, and LOB-scoped ML models."
        ),
        "base_packet": list(LIFE_BASE_PACKET),
        "uw_responsibilities": list(LIFE_UW_RESPONSIBILITIES),
        "categories": list_life_categories(),
        "taxonomy": life_taxonomy_tree(),
        "lines": lines,
        "live_lines": live,
        "production_lines": sorted({ln["insurance_line"] for ln in LIFE_LINES}),
        "stats": {
            "category_count": len(LIFE_CATEGORIES),
            "product_count": len(LIFE_LINES),
            "live_count": len(live),
            "catalog_count": 0,
            "lob_model_count": 0,
        },
    }
