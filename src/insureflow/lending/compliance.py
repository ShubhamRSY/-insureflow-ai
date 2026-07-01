from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from insureflow.lending.models import (
    BusinessLoanApplication,
    ConsumerLoanApplication,
    LoanProductType,
)


@dataclass(frozen=True)
class LendingRule:
    rule_id: str
    name: str
    severity: str
    product_types: tuple[LoanProductType, ...]
    description: str
    regulation: str
    check: Callable[[BusinessLoanApplication | ConsumerLoanApplication], dict | None]


def _check_sba_7a_size(biz: BusinessLoanApplication | ConsumerLoanApplication) -> dict | None:
    if isinstance(biz, BusinessLoanApplication) and biz.product_type == LoanProductType.SBA_7A:
        revenue = biz.financials[0].annual_revenue if biz.financials else 0
        if revenue > 15_000_000:
            return {
                "rule_id": "SBA-001",
                "rule_name": "SBA 7(a) Size Standards",
                "severity": "critical",
                "message": f"Revenue ${revenue:,.0f} exceeds SBA 7(a) threshold of $15M",
                "regulation": "13 CFR 121",
            }
    return None


def _check_reg_b_ecoaa(biz: BusinessLoanApplication | ConsumerLoanApplication) -> dict | None:
    return {
        "rule_id": "REG-B-001",
        "rule_name": "Equal Credit Opportunity Act",
        "severity": "info",
        "message": "Adverse action notice required if declined — Reg B §1002.9",
        "regulation": "Regulation B (ECOA) 12 CFR 1002",
    }


def _check_truth_in_lending(biz: BusinessLoanApplication | ConsumerLoanApplication) -> dict | None:
    return {
        "rule_id": "REG-Z-001",
        "rule_name": "TILA Disclosure Required",
        "severity": "info",
        "message": "Truth in Lending Act disclosure required for consumer-purpose loans",
        "regulation": "Regulation Z (TILA) 12 CFR 1026",
    }


def _check_bank_secrecy(biz: BusinessLoanApplication | ConsumerLoanApplication) -> dict | None:
    return {
        "rule_id": "BSA-001",
        "rule_name": "BSA/AML Check Required",
        "severity": "info",
        "message": "Customer due diligence and beneficial ownership identification required",
        "regulation": "Bank Secrecy Act 31 USC 5311",
    }


def _check_business_cip(biz: BusinessLoanApplication | ConsumerLoanApplication) -> dict | None:
    if isinstance(biz, BusinessLoanApplication) and not biz.business_name:
        return {
            "rule_id": "CIP-001",
            "rule_name": "Business Customer Identification",
            "severity": "critical",
            "message": "Business name required for CIP — entity verification needed",
            "regulation": "31 CFR 1020.220",
        }
    return None


def _check_consumer_cip(biz: BusinessLoanApplication | ConsumerLoanApplication) -> dict | None:
    if isinstance(biz, ConsumerLoanApplication) and not biz.first_name:
        return {
            "rule_id": "CIP-002",
            "rule_name": "Consumer Customer Identification",
            "severity": "critical",
            "message": "Consumer name required for CIP — identity verification needed",
            "regulation": "31 CFR 1020.220",
        }
    return None


def _check_udaap_prohibited(biz: BusinessLoanApplication | ConsumerLoanApplication) -> dict | None:
    if isinstance(biz, ConsumerLoanApplication):
        rate = getattr(biz.financial_data, "credit_score", 0)
        if rate == 0:
            return {
                "rule_id": "UDAAP-001",
                "rule_name": "UDAAP Screening",
                "severity": "info",
                "message": ("No credit score — verify fair lending compliance and ensure no prohibited basis discrimination"),
                "regulation": "Dodd-Frank Act Section 1031",
            }
    return None


def _check_business_debt_service(
    biz: BusinessLoanApplication | ConsumerLoanApplication,
) -> dict | None:
    if isinstance(biz, BusinessLoanApplication):
        financials = biz.financials
        if financials:
            latest = financials[0]
            if latest.debt_service > 0 and latest.ebitda > 0:
                dscr = latest.ebitda / latest.debt_service
                if dscr < 1.15:
                    return {
                        "rule_id": "CREDIT-101",
                        "rule_name": "Debt Service Coverage",
                        "severity": "high",
                        "message": f"DSCR {dscr:.2f}x below minimum 1.15x — inadequate cash flow",
                        "regulation": "Interagency CRE Guidelines",
                    }
    return None


def _check_consumer_dti(biz: BusinessLoanApplication | ConsumerLoanApplication) -> dict | None:
    if isinstance(biz, ConsumerLoanApplication):
        fin = biz.financial_data
        if fin.annual_income > 0:
            monthly_income = fin.annual_income / 12
            dti = fin.total_monthly_debt / monthly_income * 100 if monthly_income > 0 else 0
            if dti > 43:
                return {
                    "rule_id": "CREDIT-201",
                    "rule_name": "Maximum DTI Ratio",
                    "severity": "high",
                    "message": f"DTI {dti:.1f}% exceeds 43% — qualified mortgage threshold",
                    "regulation": "ATR/QM Rule 12 CFR 1026.43",
                }
    return None


def _check_collateral_coverage(
    biz: BusinessLoanApplication | ConsumerLoanApplication,
) -> dict | None:
    if isinstance(biz, BusinessLoanApplication) and biz.collateral and biz.requested_amount > 0:
        total_collateral = sum(c.estimated_value for c in biz.collateral)
        ltv = biz.requested_amount / total_collateral * 100 if total_collateral > 0 else 999
        if ltv > 80:
            return {
                "rule_id": "COLLAT-001",
                "rule_name": "Collateral Coverage",
                "severity": "moderate",
                "message": (f"LTV {ltv:.1f}% exceeds 80% — additional collateral or guarantor needed"),
                "regulation": "Interagency Loan Policy",
            }
    return None


def _check_sba_504_requirements(
    biz: BusinessLoanApplication | ConsumerLoanApplication,
) -> dict | None:
    if isinstance(biz, BusinessLoanApplication) and biz.product_type == LoanProductType.SBA_504:
        if biz.requested_amount > 5_000_000:
            return {
                "rule_id": "SBA-002",
                "rule_name": "SBA 504 Maximum Loan",
                "severity": "critical",
                "message": f"Requested ${biz.requested_amount:,.0f} exceeds SBA 504 maximum of $5M",
                "regulation": "13 CFR 120.882",
            }
    return None


def _check_construction_loan(biz: BusinessLoanApplication | ConsumerLoanApplication) -> dict | None:
    if isinstance(biz, BusinessLoanApplication) and biz.product_type in (
        LoanProductType.CONSTRUCTION_LOAN,
        LoanProductType.COMMERCIAL_REAL_ESTATE,
    ):
        if not biz.collateral:
            return {
                "rule_id": "CONST-001",
                "rule_name": "Construction Collateral",
                "severity": "critical",
                "message": "Construction/CRE loans require real estate collateral",
                "regulation": "Interagency CRE Guidelines",
            }
    return None


LENDING_RULES: list[LendingRule] = [
    LendingRule(
        "SBA-001",
        "SBA Size Standards",
        "critical",
        (LoanProductType.SBA_7A,),
        "Revenue must be under $15M for SBA 7(a)",
        "13 CFR 121",
        _check_sba_7a_size,
    ),
    LendingRule(
        "SBA-002",
        "SBA 504 Maximum",
        "critical",
        (LoanProductType.SBA_504,),
        "Maximum SBA 504 loan amount is $5M",
        "13 CFR 120.882",
        _check_sba_504_requirements,
    ),
    LendingRule(
        "REG-B-001",
        "ECOA Compliance",
        "info",
        tuple(LoanProductType),
        "Adverse action notice required on declines",
        "Reg B 12 CFR 1002",
        _check_reg_b_ecoaa,
    ),
    LendingRule(
        "REG-Z-001",
        "TILA Disclosure",
        "info",
        tuple(LoanProductType),
        "Truth in Lending disclosure required",
        "Reg Z 12 CFR 1026",
        _check_truth_in_lending,
    ),
    LendingRule(
        "BSA-001",
        "BSA/AML Check",
        "info",
        tuple(LoanProductType),
        "CDD and beneficial ownership required",
        "BSA 31 USC 5311",
        _check_bank_secrecy,
    ),
    LendingRule(
        "CIP-001",
        "Business CIP",
        "critical",
        (
            LoanProductType.BUSINESS_TERM_LOAN,
            LoanProductType.BUSINESS_LINE_OF_CREDIT,
            LoanProductType.COMMERCIAL_REAL_ESTATE,
            LoanProductType.CONSTRUCTION_LOAN,
            LoanProductType.SBA_7A,
            LoanProductType.SBA_504,
            LoanProductType.EQUIPMENT_FINANCING,
            LoanProductType.INVOICE_FINANCING,
        ),
        "Business entity verification required",
        "31 CFR 1020.220",
        _check_business_cip,
    ),
    LendingRule(
        "CIP-002",
        "Consumer CIP",
        "critical",
        (
            LoanProductType.PERSONAL_TERM_LOAN,
            LoanProductType.PERSONAL_LINE_OF_CREDIT,
            LoanProductType.AUTO_LOAN,
            LoanProductType.BOAT_LOAN,
            LoanProductType.HOME_EQUITY_LOAN,
            LoanProductType.HOME_EQUITY_LINE,
            LoanProductType.SECURED_PERSONAL,
            LoanProductType.UNSECURED_PERSONAL,
        ),
        "Consumer identity verification required",
        "31 CFR 1020.220",
        _check_consumer_cip,
    ),
    LendingRule(
        "UDAAP-001",
        "UDAAP Screening",
        "info",
        (
            LoanProductType.PERSONAL_TERM_LOAN,
            LoanProductType.PERSONAL_LINE_OF_CREDIT,
            LoanProductType.UNSECURED_PERSONAL,
        ),
        "Fair lending compliance check",
        "Dodd-Frank §1031",
        _check_udaap_prohibited,
    ),
    LendingRule(
        "CREDIT-101",
        "Debt Service Coverage",
        "high",
        (
            LoanProductType.BUSINESS_TERM_LOAN,
            LoanProductType.BUSINESS_LINE_OF_CREDIT,
            LoanProductType.COMMERCIAL_REAL_ESTATE,
            LoanProductType.CONSTRUCTION_LOAN,
            LoanProductType.SBA_7A,
            LoanProductType.EQUIPMENT_FINANCING,
        ),
        "DSCR must be above 1.15x",
        "Interagency CRE Guidelines",
        _check_business_debt_service,
    ),
    LendingRule(
        "CREDIT-201",
        "Maximum DTI",
        "high",
        (
            LoanProductType.PERSONAL_TERM_LOAN,
            LoanProductType.PERSONAL_LINE_OF_CREDIT,
            LoanProductType.AUTO_LOAN,
            LoanProductType.BOAT_LOAN,
            LoanProductType.HOME_EQUITY_LOAN,
            LoanProductType.HOME_EQUITY_LINE,
            LoanProductType.UNSECURED_PERSONAL,
        ),
        "DTI must be below 43%",
        "ATR/QM 12 CFR 1026.43",
        _check_consumer_dti,
    ),
    LendingRule(
        "COLLAT-001",
        "Collateral Coverage",
        "moderate",
        (
            LoanProductType.BUSINESS_TERM_LOAN,
            LoanProductType.COMMERCIAL_REAL_ESTATE,
            LoanProductType.CONSTRUCTION_LOAN,
            LoanProductType.SECURED_PERSONAL,
            LoanProductType.AUTO_LOAN,
            LoanProductType.BOAT_LOAN,
        ),
        "LTV should be under 80%",
        "Interagency Loan Policy",
        _check_collateral_coverage,
    ),
    LendingRule(
        "CONST-001",
        "Construction Collateral",
        "critical",
        (LoanProductType.CONSTRUCTION_LOAN, LoanProductType.COMMERCIAL_REAL_ESTATE),
        "Real estate collateral required",
        "Interagency CRE",
        _check_construction_loan,
    ),
]


class LendingComplianceEngine:
    def evaluate(
        self,
        application: BusinessLoanApplication | ConsumerLoanApplication,
    ) -> list[dict]:
        violations: list[dict] = []
        for rule in LENDING_RULES:
            if application.product_type not in rule.product_types:
                continue
            result = rule.check(application)
            if result:
                violations.append(result)
        return violations
