from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from insureflow.models.mortgage import (
    ComplianceViolation,
    MortgageBundle,
    MortgageDocumentType,
    ProductLine,
)


@dataclass(frozen=True)
class BankRule:
    rule_id: str
    name: str
    severity: str
    product_lines: tuple[ProductLine, ...]
    check: Callable[[MortgageBundle], ComplianceViolation | None]


def _has_any(bundle: MortgageBundle, types: Iterable[MortgageDocumentType]) -> bool:
    return any(bundle.documents_by_type(t) for t in types)


def _corpus(bundle: MortgageBundle) -> str:
    parts = [d.source_path for d in bundle.documents]
    parts.extend(d.raw_text[:1500] for d in bundle.documents[:40])
    return "\n".join(parts).lower()


def _min_credit_score_620(bundle: MortgageBundle) -> ComplianceViolation | None:
    if not bundle.credit or not bundle.credit.credit_score:
        return ComplianceViolation(
            rule_id="CREDIT-001",
            rule_name="Minimum Credit Score",
            severity="critical",
            message="Credit report missing or score not extracted — manual review required",
        )
    if bundle.credit.credit_score < 620:
        return ComplianceViolation(
            rule_id="CREDIT-001",
            rule_name="Minimum Credit Score",
            severity="critical",
            message=f"Credit score {bundle.credit.credit_score} below bank minimum of 620",
        )
    return None


def _max_dti_43(bundle: MortgageBundle) -> ComplianceViolation | None:
    if not bundle.credit or not bundle.income:
        return None
    monthly_income = (bundle.income.adjusted_gross_income or bundle.income.total_income) / 12
    if monthly_income <= 0:
        return None
    dti = bundle.credit.total_monthly_payment / monthly_income * 100
    if dti > 43:
        return ComplianceViolation(
            rule_id="DTI-001",
            rule_name="Maximum DTI Ratio",
            severity="high",
            message=f"DTI {dti:.1f}% exceeds bank maximum of 43%",
        )
    return None


def _max_ltv_80(bundle: MortgageBundle) -> ComplianceViolation | None:
    if not bundle.collateral or not bundle.collateral.ltv:
        return None
    if bundle.collateral.ltv > 80:
        return ComplianceViolation(
            rule_id="LTV-001",
            rule_name="Maximum LTV Ratio",
            severity="high",
            message=f"LTV {bundle.collateral.ltv:.1f}% exceeds standard 80% without PMI",
        )
    return None


def _income_documentation(bundle: MortgageBundle) -> ComplianceViolation | None:
    w2_count = len(bundle.documents_by_type(MortgageDocumentType.W2))
    tax_count = len(bundle.documents_by_type(MortgageDocumentType.TAX_RETURN_1040))
    other_income = _has_any(
        bundle,
        (
            MortgageDocumentType.FORM_K1,
            MortgageDocumentType.SSA_1099,
            MortgageDocumentType.FORM_1099_R,
            MortgageDocumentType.SOCIAL_SECURITY_AWARD,
            MortgageDocumentType.CHILD_SUPPORT_ORDER,
            MortgageDocumentType.ALIMONY_DOCUMENTATION,
            MortgageDocumentType.PROFIT_LOSS,
            MortgageDocumentType.SCHEDULE_C,
            MortgageDocumentType.TAX_RETURN_1065,
        ),
    )
    if w2_count == 0 and tax_count == 0 and not other_income:
        return ComplianceViolation(
            rule_id="INCOME-001",
            rule_name="Income Documentation Required",
            severity="critical",
            message="No W-2, tax return, or alternative income docs found in loan package",
        )
    return None


def _asset_reserves(bundle: MortgageBundle) -> ComplianceViolation | None:
    if not bundle.assets:
        return ComplianceViolation(
            rule_id="ASSET-001",
            rule_name="Asset Verification Required",
            severity="warning",
            message="No bank statements found — cannot verify reserves",
        )
    if bundle.assets.total_liquid_assets < 5000:
        return ComplianceViolation(
            rule_id="ASSET-002",
            rule_name="Minimum Reserves",
            severity="high",
            message=f"Liquid assets ${bundle.assets.total_liquid_assets:,.0f} below minimum reserve threshold",
        )
    return None


def _reconciliation_blockers(bundle: MortgageBundle) -> ComplianceViolation | None:
    high_issues = [i for i in bundle.reconciliation_issues if i.severity == "high"]
    if high_issues:
        return ComplianceViolation(
            rule_id="RECON-001",
            rule_name="Cross-Document Reconciliation",
            severity="high",
            message=f"{len(high_issues)} high-severity reconciliation issue(s) require resolution",
            document_refs=[i.source_a for i in high_issues],
        )
    return None


def _commercial_dscr(bundle: MortgageBundle) -> ComplianceViolation | None:
    if bundle.product_line != ProductLine.COMMERCIAL_MORTGAGE:
        return None
    for doc in bundle.documents_by_type(MortgageDocumentType.OPERATING_STATEMENT):
        dscr = doc.get_float("dscr")
        if dscr and dscr < 1.20:
            return ComplianceViolation(
                rule_id="CM-DSCR-001",
                rule_name="Commercial Minimum DSCR",
                severity="critical",
                message=f"DSCR {dscr:.2f}x below bank minimum of 1.20x",
            )
    return None


def _identity_docs(bundle: MortgageBundle) -> ComplianceViolation | None:
    if _has_any(
        bundle,
        (
            MortgageDocumentType.GOVERNMENT_ID,
            MortgageDocumentType.PASSPORT,
            MortgageDocumentType.PERMANENT_RESIDENT_CARD,
            MortgageDocumentType.VISA_DOCUMENT,
            MortgageDocumentType.RESIDENCY_DOCUMENT,
        ),
    ):
        return None
    return ComplianceViolation(
        rule_id="PKG-ID-001",
        rule_name="Borrower Identity",
        severity="high",
        message="Missing government-issued ID, passport, or residency document",
    )


def _ssn_docs(bundle: MortgageBundle) -> ComplianceViolation | None:
    if _has_any(
        bundle,
        (
            MortgageDocumentType.SSN_CARD,
            MortgageDocumentType.SSN_VERIFICATION,
        ),
    ):
        return None
    # 1003 often carries SSN — treat as soft condition, not hard fail
    if _has_any(
        bundle,
        (
            MortgageDocumentType.LOAN_APPLICATION_1003,
            MortgageDocumentType.UNIFORM_RESIDENTIAL_LOAN_APPLICATION,
        ),
    ):
        return ComplianceViolation(
            rule_id="PKG-SSN-001",
            rule_name="SSN Verification",
            severity="warning",
            message="No SSN card/verification on file — confirm SSN from 1003 / SSA docs before closing",
        )
    return ComplianceViolation(
        rule_id="PKG-SSN-001",
        rule_name="SSN Verification",
        severity="high",
        message="Missing SSN card or Social Security verification document",
    )


def _core_package_docs(bundle: MortgageBundle) -> ComplianceViolation | None:
    missing: list[str] = []
    checks: list[tuple[str, tuple[MortgageDocumentType, ...]]] = [
        (
            "loan application (1003/URLA)",
            (
                MortgageDocumentType.LOAN_APPLICATION_1003,
                MortgageDocumentType.UNIFORM_RESIDENTIAL_LOAN_APPLICATION,
            ),
        ),
        ("credit report", (MortgageDocumentType.CREDIT_REPORT,)),
        ("bank / asset statements", (MortgageDocumentType.BANK_STATEMENT, MortgageDocumentType.VOD, MortgageDocumentType.VERIFICATION_OF_DEPOSIT)),
        (
            "purchase agreement or current mortgage statement",
            (MortgageDocumentType.PURCHASE_AGREEMENT, MortgageDocumentType.MORTGAGE_STATEMENT),
        ),
    ]
    for label, types in checks:
        if not _has_any(bundle, types):
            missing.append(label)
    if not missing:
        return None
    return ComplianceViolation(
        rule_id="PKG-CORE-001",
        rule_name="Core Package Completeness",
        severity="high",
        message="Missing core package item(s): " + "; ".join(missing),
    )


def _conditional_specialty_docs(bundle: MortgageBundle) -> ComplianceViolation | None:
    """Issue conditions when package signals specialty docs that are absent."""
    text = _corpus(bundle)
    gaps: list[str] = []

    if ("condo" in text or "hoa" in text) and not _has_any(
        bundle,
        (MortgageDocumentType.CONDO_HOA_QUESTIONNAIRE, MortgageDocumentType.HOA_STATEMENT),
    ):
        gaps.append("condo/HOA questionnaire or HOA dues statement")

    if ("gift" in text or "gift letter" in text) and not _has_any(bundle, (MortgageDocumentType.GIFT_LETTER,)):
        gaps.append("signed gift letter")

    if ("earnest" in text or "emd" in text) and not _has_any(bundle, (MortgageDocumentType.EARNEST_MONEY_RECEIPT,)):
        gaps.append("earnest money receipt / wire confirmation")

    if ("self-employed" in text or "schedule c" in text or "1099" in text) and not _has_any(
        bundle,
        (
            MortgageDocumentType.PROFIT_LOSS,
            MortgageDocumentType.BALANCE_SHEET,
            MortgageDocumentType.TAX_RETURN_1065,
            MortgageDocumentType.SCHEDULE_C,
            MortgageDocumentType.FORM_K1,
        ),
    ):
        gaps.append("self-employed financials (P&L / balance sheet / K-1 / business return)")

    if ("child support" in text or "alimony" in text) and not _has_any(
        bundle,
        (MortgageDocumentType.CHILD_SUPPORT_ORDER, MortgageDocumentType.ALIMONY_DOCUMENTATION, MortgageDocumentType.DIVORCE_DECREE),
    ):
        gaps.append("child support / alimony order + payment proof")

    if ("social security" in text or "retirement income" in text or "pension" in text) and not _has_any(
        bundle,
        (
            MortgageDocumentType.SSA_1099,
            MortgageDocumentType.FORM_1099_R,
            MortgageDocumentType.SOCIAL_SECURITY_AWARD,
        ),
    ):
        gaps.append("SSA-1099 / 1099-R / award letter for retirement or SSA income")

    if ("bankruptcy" in text or "chapter 7" in text or "chapter 13" in text) and not _has_any(
        bundle,
        (MortgageDocumentType.BANKRUPTCY_DISCHARGE,),
    ):
        gaps.append("bankruptcy discharge / court order")

    if ("judgment" in text or "lien" in text) and not _has_any(bundle, (MortgageDocumentType.JUDGMENT_DOCUMENT,)):
        gaps.append("judgment / lien documentation")

    if ("rent" in text or "landlord" in text or "tenant" in text) and not _has_any(
        bundle,
        (
            MortgageDocumentType.LANDLORD_VERIFICATION,
            MortgageDocumentType.RENTAL_HISTORY,
            MortgageDocumentType.RENTAL_HISTORY_LETTER,
            MortgageDocumentType.RENT_HISTORY,
        ),
    ):
        # Only if no purchase agreement (likely renter) — soft
        if not _has_any(bundle, (MortgageDocumentType.PURCHASE_AGREEMENT,)):
            gaps.append("landlord verification / rental payment history")

    if ("permanent resident" in text or "visa" in text or "non-citizen" in text or "alien" in text) and not _has_any(
        bundle,
        (
            MortgageDocumentType.PERMANENT_RESIDENT_CARD,
            MortgageDocumentType.VISA_DOCUMENT,
            MortgageDocumentType.RESIDENCY_DOCUMENT,
        ),
    ):
        gaps.append("residency / green card / visa documentation")

    if not gaps:
        return None
    return ComplianceViolation(
        rule_id="PKG-COND-001",
        rule_name="Specialty Document Conditions",
        severity="warning",
        message="Request from borrower/broker: " + "; ".join(gaps),
    )


def _property_protection_docs(bundle: MortgageBundle) -> ComplianceViolation | None:
    missing: list[str] = []
    if not _has_any(
        bundle,
        (
            MortgageDocumentType.HOMEOWNERS_INSURANCE,
            MortgageDocumentType.HAZARD_INSURANCE,
            MortgageDocumentType.HAZARD_INSURANCE_DECLARATION,
        ),
    ):
        missing.append("homeowners / hazard insurance")
    if not _has_any(
        bundle,
        (MortgageDocumentType.RESIDENTIAL_APPRAISAL, MortgageDocumentType.COMMERCIAL_APPRAISAL),
    ):
        missing.append("appraisal")
    if not missing:
        return None
    return ComplianceViolation(
        rule_id="PKG-PROP-001",
        rule_name="Property Documentation",
        severity="warning",
        message="Missing property item(s): " + "; ".join(missing),
    )


BANK_RULES: list[BankRule] = [
    BankRule(
        "CREDIT-001",
        "Minimum Credit Score",
        "critical",
        (ProductLine.RESIDENTIAL_MORTGAGE,),
        _min_credit_score_620,
    ),
    BankRule("DTI-001", "Maximum DTI Ratio", "high", (ProductLine.RESIDENTIAL_MORTGAGE,), _max_dti_43),
    BankRule("LTV-001", "Maximum LTV Ratio", "high", (ProductLine.RESIDENTIAL_MORTGAGE,), _max_ltv_80),
    BankRule(
        "INCOME-001",
        "Income Documentation",
        "critical",
        (ProductLine.RESIDENTIAL_MORTGAGE, ProductLine.COMMERCIAL_MORTGAGE),
        _income_documentation,
    ),
    BankRule(
        "ASSET-001",
        "Asset Verification",
        "warning",
        (ProductLine.RESIDENTIAL_MORTGAGE,),
        _asset_reserves,
    ),
    BankRule(
        "RECON-001",
        "Reconciliation Blockers",
        "high",
        (ProductLine.RESIDENTIAL_MORTGAGE, ProductLine.COMMERCIAL_MORTGAGE),
        _reconciliation_blockers,
    ),
    BankRule(
        "CM-DSCR-001",
        "Commercial DSCR",
        "critical",
        (ProductLine.COMMERCIAL_MORTGAGE,),
        _commercial_dscr,
    ),
    BankRule(
        "PKG-ID-001",
        "Borrower Identity",
        "high",
        (ProductLine.RESIDENTIAL_MORTGAGE,),
        _identity_docs,
    ),
    BankRule(
        "PKG-SSN-001",
        "SSN Verification",
        "warning",
        (ProductLine.RESIDENTIAL_MORTGAGE,),
        _ssn_docs,
    ),
    BankRule(
        "PKG-CORE-001",
        "Core Package Completeness",
        "high",
        (ProductLine.RESIDENTIAL_MORTGAGE,),
        _core_package_docs,
    ),
    BankRule(
        "PKG-PROP-001",
        "Property Documentation",
        "warning",
        (ProductLine.RESIDENTIAL_MORTGAGE,),
        _property_protection_docs,
    ),
    BankRule(
        "PKG-COND-001",
        "Specialty Document Conditions",
        "warning",
        (ProductLine.RESIDENTIAL_MORTGAGE,),
        _conditional_specialty_docs,
    ),
]


class MortgageComplianceEngine:
    """Enforce bank underwriting rules — deterministic, auditable checks."""

    def evaluate(self, bundle: MortgageBundle) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []
        for rule in BANK_RULES:
            if bundle.product_line not in rule.product_lines:
                continue
            result = rule.check(bundle)
            if result:
                violations.append(result)
        bundle.compliance_violations = violations
        return violations

    def package_checklist(self, bundle: MortgageBundle) -> dict[str, list[str]]:
        """Return present vs missing checklist labels for UI / audit."""
        present: list[str] = []
        missing: list[str] = []
        catalog: list[tuple[str, tuple[MortgageDocumentType, ...]]] = [
            (
                "Government ID / passport / residency",
                (
                    MortgageDocumentType.GOVERNMENT_ID,
                    MortgageDocumentType.PASSPORT,
                    MortgageDocumentType.PERMANENT_RESIDENT_CARD,
                    MortgageDocumentType.VISA_DOCUMENT,
                    MortgageDocumentType.RESIDENCY_DOCUMENT,
                ),
            ),
            ("SSN card / verification", (MortgageDocumentType.SSN_CARD, MortgageDocumentType.SSN_VERIFICATION)),
            ("W-2", (MortgageDocumentType.W2,)),
            ("Pay stubs", (MortgageDocumentType.PAY_STUB,)),
            ("Tax returns", (MortgageDocumentType.TAX_RETURN_1040, MortgageDocumentType.TAX_RETURN_1065)),
            (
                "K-1 / SSA-1099 / 1099-R / award letter",
                (
                    MortgageDocumentType.FORM_K1,
                    MortgageDocumentType.SSA_1099,
                    MortgageDocumentType.FORM_1099_R,
                    MortgageDocumentType.SOCIAL_SECURITY_AWARD,
                ),
            ),
            (
                "Child support / alimony",
                (
                    MortgageDocumentType.CHILD_SUPPORT_ORDER,
                    MortgageDocumentType.ALIMONY_DOCUMENTATION,
                ),
            ),
            ("Bank / asset statements", (MortgageDocumentType.BANK_STATEMENT,)),
            ("Gift letter", (MortgageDocumentType.GIFT_LETTER,)),
            ("Earnest money receipt", (MortgageDocumentType.EARNEST_MONEY_RECEIPT,)),
            ("Credit report", (MortgageDocumentType.CREDIT_REPORT,)),
            (
                "Bankruptcy / judgment",
                (
                    MortgageDocumentType.BANKRUPTCY_DISCHARGE,
                    MortgageDocumentType.JUDGMENT_DOCUMENT,
                ),
            ),
            (
                "Landlord verification",
                (
                    MortgageDocumentType.LANDLORD_VERIFICATION,
                    MortgageDocumentType.RENTAL_HISTORY,
                ),
            ),
            ("Purchase agreement", (MortgageDocumentType.PURCHASE_AGREEMENT,)),
            ("Appraisal", (MortgageDocumentType.RESIDENTIAL_APPRAISAL, MortgageDocumentType.COMMERCIAL_APPRAISAL)),
            (
                "HOI / hazard",
                (
                    MortgageDocumentType.HOMEOWNERS_INSURANCE,
                    MortgageDocumentType.HAZARD_INSURANCE,
                    MortgageDocumentType.HAZARD_INSURANCE_DECLARATION,
                ),
            ),
            (
                "Condo / HOA questionnaire",
                (
                    MortgageDocumentType.CONDO_HOA_QUESTIONNAIRE,
                    MortgageDocumentType.HOA_STATEMENT,
                ),
            ),
            (
                "1003 / URLA",
                (
                    MortgageDocumentType.LOAN_APPLICATION_1003,
                    MortgageDocumentType.UNIFORM_RESIDENTIAL_LOAN_APPLICATION,
                ),
            ),
        ]
        for label, types in catalog:
            if _has_any(bundle, types):
                present.append(label)
            else:
                missing.append(label)
        return {"present": present, "missing": missing}
