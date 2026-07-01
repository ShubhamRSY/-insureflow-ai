from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from insureflow.models.mortgage import ComplianceViolation, MortgageBundle, ProductLine


@dataclass(frozen=True)
class BankRule:
    rule_id: str
    name: str
    severity: str
    product_lines: tuple[ProductLine, ...]
    check: Callable[[MortgageBundle], ComplianceViolation | None]


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
    from insureflow.models.mortgage import MortgageDocumentType

    w2_count = len(bundle.documents_by_type(MortgageDocumentType.W2))
    tax_count = len(bundle.documents_by_type(MortgageDocumentType.TAX_RETURN_1040))
    if w2_count == 0 and tax_count == 0:
        return ComplianceViolation(
            rule_id="INCOME-001",
            rule_name="Income Documentation Required",
            severity="critical",
            message="No W-2 or tax return found in loan package",
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
    from insureflow.models.mortgage import MortgageDocumentType

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
