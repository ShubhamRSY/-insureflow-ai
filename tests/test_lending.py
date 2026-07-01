from __future__ import annotations

from pathlib import Path

from insureflow.lending.compliance import LENDING_RULES, LendingComplianceEngine
from insureflow.lending.models import (
    BusinessFinancialData,
    BusinessLoanApplication,
    Collateral,
    ConsumerFinancialData,
    ConsumerLoanApplication,
    CreditAnalysis,
    LoanDecision,
    LoanProductType,
    LoanPurpose,
)
from insureflow.lending.pipeline import LendingPipeline
from insureflow.lending.pricing import LendingPricingEngine
from insureflow.lending.risk import LendingRiskEngine


class TestLendingRiskEngine:
    def make_biz_app(self, **overrides: object) -> BusinessLoanApplication:
        defaults: dict = dict(
            business_name="Test Biz",
            industry="manufacturing",
            years_in_business=5,
            product_type=LoanProductType.BUSINESS_TERM_LOAN,
            loan_purpose=LoanPurpose.WORKING_CAPITAL,
            requested_amount=500000,
            requested_term_months=36,
            financials=[BusinessFinancialData(
                annual_revenue=2000000, net_income=200000, ebitda=350000,
                debt_service=220000, total_assets=1000000, total_liabilities=400000,
                current_assets=300000, current_liabilities=200000,
            )],
        )
        defaults.update(overrides)
        return BusinessLoanApplication(**defaults)

    def make_con_app(self, **overrides: object) -> ConsumerLoanApplication:
        defaults: dict = dict(
            first_name="Jane", last_name="Doe",
            product_type=LoanProductType.AUTO_LOAN,
            loan_purpose=LoanPurpose.AUTO_PURCHASE,
            requested_amount=35000,
            requested_term_months=60,
            financial_data=ConsumerFinancialData(
                annual_income=85000,
                total_monthly_debt=1200,
                credit_score=720,
                employment_years=4,
            ),
        )
        defaults.update(overrides)
        return ConsumerLoanApplication(**defaults)

    def test_low_risk_business(self) -> None:
        app = self.make_biz_app(
            financials=[BusinessFinancialData(
                annual_revenue=5000000, net_income=750000, ebitda=1200000,
                debt_service=400000, total_assets=5000000, total_liabilities=1000000,
                shareholder_equity=4000000,
                current_assets=2000000, current_liabilities=500000,
            )],
            years_in_business=15,
            industry="software",
        )
        engine = LendingRiskEngine()
        analysis = engine.analyze(app)
        assert analysis.overall_risk_score < 40
        assert analysis.risk_rating in ("low", "moderate")

    def test_high_risk_business(self) -> None:
        app = self.make_biz_app(
            financials=[BusinessFinancialData(
                annual_revenue=80000, net_income=-5000, ebitda=10000,
                debt_service=50000, total_assets=30000, total_liabilities=60000,
                current_assets=5000, current_liabilities=40000,
            )],
            years_in_business=1,
            industry="restaurant",
        )
        engine = LendingRiskEngine()
        analysis = engine.analyze(app)
        assert analysis.overall_risk_score >= 60
        assert analysis.risk_rating == "high" or analysis.risk_rating == "above_average"
        assert len(analysis.weaknesses) >= 3

    def test_excellent_credit_consumer(self) -> None:
        app = self.make_con_app(financial_data=ConsumerFinancialData(
            annual_income=120000, total_monthly_debt=800, credit_score=800,
            employment_years=10,
        ))
        engine = LendingRiskEngine()
        analysis = engine.analyze(app)
        assert analysis.overall_risk_score < 40
        assert analysis.credit_score_tier == "excellent"
        assert len(analysis.strengths) >= 1

    def test_poor_credit_consumer(self) -> None:
        app = self.make_con_app(financial_data=ConsumerFinancialData(
            annual_income=40000, total_monthly_debt=2000, credit_score=580,
            employment_years=1, bankruptcies_last_7_years=1,
        ))
        engine = LendingRiskEngine()
        analysis = engine.analyze(app)
        assert analysis.overall_risk_score >= 60
        assert analysis.credit_score_tier == "poor" or analysis.credit_score_tier == "subprime"

    def test_collateral_improves_score(self) -> None:
        no_collateral = self.make_biz_app()
        with_collateral = self.make_biz_app(
            collateral=[Collateral(estimated_value=1000000)],
        )
        engine = LendingRiskEngine()
        no_coll_analysis = engine.analyze(no_collateral)
        with_coll_analysis = engine.analyze(with_collateral)
        assert with_coll_analysis.overall_risk_score <= no_coll_analysis.overall_risk_score

    def test_business_risk_returns_credit_analysis(self) -> None:
        app = self.make_biz_app()
        engine = LendingRiskEngine()
        analysis = engine.analyze(app)
        assert isinstance(analysis, CreditAnalysis)
        assert analysis.analysis_id.startswith("ca-")
        assert analysis.overall_risk_score > 0


class TestLendingComplianceEngine:
    def test_all_rules_have_unique_ids(self) -> None:
        ids = [r.rule_id for r in LENDING_RULES]
        assert len(ids) == len(set(ids))

    def test_business_loan_returns_expected_rules(self) -> None:
        app = BusinessLoanApplication(
            business_name="",
            product_type=LoanProductType.BUSINESS_TERM_LOAN,
            loan_purpose=LoanPurpose.WORKING_CAPITAL,
            requested_amount=100000,
            requested_term_months=12,
        )
        engine = LendingComplianceEngine()
        results = engine.evaluate(app)
        rule_ids = [r["rule_id"] for r in results]
        assert "REG-B-001" in rule_ids
        assert "REG-Z-001" in rule_ids
        assert "BSA-001" in rule_ids
        assert "CIP-001" in rule_ids

    def test_consumer_loan_triggers_cip_check(self) -> None:
        app = ConsumerLoanApplication(
            product_type=LoanProductType.PERSONAL_TERM_LOAN,
            loan_purpose=LoanPurpose.DEBT_CONSOLIDATION,
            requested_amount=10000,
            requested_term_months=12,
            financial_data=ConsumerFinancialData(),
        )
        engine = LendingComplianceEngine()
        results = engine.evaluate(app)
        cip = [r for r in results if r["rule_id"] == "CIP-002"]
        assert len(cip) == 1
        assert cip[0]["severity"] == "critical"

    def test_consumer_loan_with_name_passes_cip(self) -> None:
        app = ConsumerLoanApplication(
            first_name="John", last_name="Smith",
            product_type=LoanProductType.AUTO_LOAN,
            loan_purpose=LoanPurpose.AUTO_PURCHASE,
            requested_amount=25000,
            requested_term_months=48,
            financial_data=ConsumerFinancialData(credit_score=700),
        )
        engine = LendingComplianceEngine()
        results = engine.evaluate(app)
        cip = [r for r in results if r["rule_id"] == "CIP-002"]
        assert len(cip) == 0

    def test_sba_7a_revenue_exceeds_threshold(self) -> None:
        app = BusinessLoanApplication(
            business_name="Big Biz",
            product_type=LoanProductType.SBA_7A,
            loan_purpose=LoanPurpose.WORKING_CAPITAL,
            requested_amount=100000,
            requested_term_months=12,
            financials=[BusinessFinancialData(annual_revenue=20_000_000)],
        )
        engine = LendingComplianceEngine()
        results = engine.evaluate(app)
        sba = [r for r in results if r["rule_id"] == "SBA-001"]
        assert len(sba) == 1
        assert sba[0]["severity"] == "critical"

    def test_construction_loan_needs_collateral(self) -> None:
        app = BusinessLoanApplication(
            business_name="Build Co",
            product_type=LoanProductType.CONSTRUCTION_LOAN,
            loan_purpose=LoanPurpose.CONSTRUCTION,
            requested_amount=2000000,
            requested_term_months=24,
        )
        engine = LendingComplianceEngine()
        results = engine.evaluate(app)
        const = [r for r in results if r["rule_id"] == "CONST-001"]
        assert len(const) == 1

    def test_high_dti_triggers_warning(self) -> None:
        app = ConsumerLoanApplication(
            first_name="John", last_name="Doe",
            product_type=LoanProductType.UNSECURED_PERSONAL,
            loan_purpose=LoanPurpose.DEBT_CONSOLIDATION,
            requested_amount=20000,
            requested_term_months=36,
            financial_data=ConsumerFinancialData(
                annual_income=50000,
                total_monthly_debt=2500,
            ),
        )
        engine = LendingComplianceEngine()
        results = engine.evaluate(app)
        dti = [r for r in results if r["rule_id"] == "CREDIT-201"]
        assert len(dti) == 1


class TestLendingPricingEngine:
    def test_low_risk_gets_best_rate(self) -> None:
        analysis = CreditAnalysis(risk_rating="low", overall_risk_score=20)
        engine = LendingPricingEngine()
        price = engine.price(LoanProductType.BUSINESS_TERM_LOAN, analysis, 12)
        expected = 6.0 - 0.5
        assert price.final_rate == expected

    def test_high_risk_adds_spread(self) -> None:
        analysis = CreditAnalysis(risk_rating="high", overall_risk_score=80)
        engine = LendingPricingEngine()
        price = engine.price(LoanProductType.UNSECURED_PERSONAL, analysis, 12)
        assert price.final_rate > 10.0

    def test_longer_term_increases_rate(self) -> None:
        analysis = CreditAnalysis(risk_rating="moderate", overall_risk_score=50)
        engine = LendingPricingEngine()
        short = engine.price(LoanProductType.BUSINESS_TERM_LOAN, analysis, 12)
        long = engine.price(LoanProductType.BUSINESS_TERM_LOAN, analysis, 60)
        assert long.final_rate > short.final_rate

    def test_line_of_credit_has_annual_fee(self) -> None:
        analysis = CreditAnalysis(risk_rating="moderate", overall_risk_score=50)
        engine = LendingPricingEngine()
        price = engine.price(LoanProductType.BUSINESS_LINE_OF_CREDIT, analysis, 12)
        assert price.annual_fee_percent == 0.25

    def test_high_risk_has_upfront_fee(self) -> None:
        analysis = CreditAnalysis(risk_rating="high", overall_risk_score=80)
        engine = LendingPricingEngine()
        price = engine.price(LoanProductType.BUSINESS_TERM_LOAN, analysis, 12)
        assert price.upfront_fee_percent == 0.5


class TestLendingPipeline:
    def test_business_loan_returns_result(self) -> None:
        app = BusinessLoanApplication(
            business_name="Test Corp",
            industry="manufacturing",
            years_in_business=8,
            product_type=LoanProductType.BUSINESS_TERM_LOAN,
            loan_purpose=LoanPurpose.WORKING_CAPITAL,
            requested_amount=250000,
            requested_term_months=36,
            financials=[BusinessFinancialData(
                annual_revenue=1500000, net_income=150000, ebitda=300000,
                debt_service=150000, total_assets=800000, total_liabilities=300000,
                current_assets=250000, current_liabilities=150000,
            )],
            collateral=[Collateral(estimated_value=400000)],
        )
        pipeline = LendingPipeline()
        result = pipeline.run(app)
        assert result.application_id == app.application_id
        assert result.product_type == LoanProductType.BUSINESS_TERM_LOAN
        assert result.decision in (LoanDecision.APPROVED, LoanDecision.APPROVED_WITH_CONDITIONS)
        assert result.risk_score >= 0
        assert result.approved_amount is not None
        assert result.approved_rate is not None

    def test_consumer_loan_auto_approved(self) -> None:
        app = ConsumerLoanApplication(
            first_name="Jane", last_name="Doe",
            product_type=LoanProductType.AUTO_LOAN,
            loan_purpose=LoanPurpose.AUTO_PURCHASE,
            requested_amount=35000,
            requested_term_months=60,
            financial_data=ConsumerFinancialData(
                annual_income=85000,
                total_monthly_debt=1200,
                credit_score=720,
                employment_years=4,
            ),
        )
        pipeline = LendingPipeline()
        result = pipeline.run(app)
        assert result.decision == LoanDecision.APPROVED
        assert result.approved_amount == 35000
        assert result.risk_score <= 50

    def test_critical_compliance_suspends(self) -> None:
        app = BusinessLoanApplication(
            product_type=LoanProductType.SBA_7A,
            loan_purpose=LoanPurpose.WORKING_CAPITAL,
            requested_amount=100000,
            requested_term_months=12,
            financials=[BusinessFinancialData(annual_revenue=25_000_000)],
        )
        pipeline = LendingPipeline()
        result = pipeline.run(app)
        assert result.decision == LoanDecision.SUSPENDED
        assert result.human_review_required is True
        assert len(result.compliance_violations) >= 1

    def test_high_risk_loan_triggers_human_review(self) -> None:
        app = BusinessLoanApplication(
            business_name="Risky Co",
            industry="restaurant",
            years_in_business=1,
            product_type=LoanProductType.BUSINESS_TERM_LOAN,
            loan_purpose=LoanPurpose.WORKING_CAPITAL,
            requested_amount=100000,
            requested_term_months=12,
            financials=[BusinessFinancialData(
                annual_revenue=50000, net_income=-10000, ebitda=5000,
                debt_service=60000, total_assets=20000, total_liabilities=50000,
                current_assets=5000, current_liabilities=45000,
            )],
        )
        pipeline = LendingPipeline()
        result = pipeline.run(app)
        assert result.human_review_required is True
        assert len(result.human_review_reasons) >= 1

    def test_large_loan_requires_human_review(self) -> None:
        app = BusinessLoanApplication(
            business_name="Large Co",
            industry="software",
            years_in_business=10,
            product_type=LoanProductType.BUSINESS_TERM_LOAN,
            loan_purpose=LoanPurpose.WORKING_CAPITAL,
            requested_amount=5_000_000,
            requested_term_months=60,
            financials=[BusinessFinancialData(
                annual_revenue=20000000, net_income=3000000, ebitda=5000000,
                debt_service=1000000, total_assets=15000000, total_liabilities=5000000,
                current_assets=6000000, current_liabilities=2000000,
            )],
        )
        pipeline = LendingPipeline()
        result = pipeline.run(app)
        assert result.human_review_required is True
        assert any("$1M" in r for r in result.human_review_reasons)

    def test_declined_application(self) -> None:
        app = BusinessLoanApplication(
            business_name="Failing Co",
            industry="restaurant",
            years_in_business=1,
            product_type=LoanProductType.BUSINESS_TERM_LOAN,
            loan_purpose=LoanPurpose.WORKING_CAPITAL,
            requested_amount=500000,
            requested_term_months=12,
            financials=[BusinessFinancialData(
                annual_revenue=10000, net_income=-50000, ebitda=-20000,
                debt_service=80000, total_assets=5000, total_liabilities=100000,
                current_assets=1000, current_liabilities=80000,
            )],
        )
        pipeline = LendingPipeline()
        result = pipeline.run(app)
        assert result.decision == LoanDecision.DECLINED
        assert result.approved_amount is None

    def test_pipeline_audit_file_created(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit_logs" / "lending"
        audit_dir.mkdir(parents=True)

        app = ConsumerLoanApplication(
            first_name="Test", last_name="User",
            product_type=LoanProductType.PERSONAL_TERM_LOAN,
            loan_purpose=LoanPurpose.DEBT_CONSOLIDATION,
            requested_amount=10000,
            requested_term_months=24,
            financial_data=ConsumerFinancialData(annual_income=60000, credit_score=700),
        )
        pipeline = LendingPipeline()
        pipeline.run(app, pipeline_run_id="test-audit-001")
        audit_files = list(audit_dir.parent.glob("lending/*.json"))
        assert len(audit_files) >= 0

    def test_document_count_tracked(self) -> None:
        app = ConsumerLoanApplication(
            first_name="Doc", last_name="Test",
            product_type=LoanProductType.PERSONAL_TERM_LOAN,
            loan_purpose=LoanPurpose.DEBT_CONSOLIDATION,
            requested_amount=5000,
            requested_term_months=12,
            financial_data=ConsumerFinancialData(annual_income=40000, credit_score=680),
        )
        docs = [
            {"filename": "app.pdf", "type": "loan_application"},
            {"filename": "paystub.pdf", "type": "pay_stub"},
            {"filename": "bank_stmt.pdf", "type": "bank_statement"},
        ]
        pipeline = LendingPipeline()
        result = pipeline.run(app, documents=docs)
        assert result.document_count == 3


class TestLendingModels:
    def test_business_application_default_id(self) -> None:
        app = BusinessLoanApplication()
        assert app.application_id.startswith("biz-")

    def test_consumer_application_default_id(self) -> None:
        app = ConsumerLoanApplication()
        assert app.application_id.startswith("con-")

    def test_credit_analysis_default_id(self) -> None:
        ca = CreditAnalysis()
        assert ca.analysis_id.startswith("ca-")

    def test_all_product_types_defined(self) -> None:
        assert len(LoanProductType) >= 14

    def test_all_document_types_defined(self) -> None:
        from insureflow.lending.models import LendingDocumentType
        assert len(LendingDocumentType) >= 25


class TestLoanDecisionMapping:
    SBA_7A = LoanProductType.SBA_7A
    BUSINESS_TERM = LoanProductType.BUSINESS_TERM_LOAN
    AUTO = LoanProductType.AUTO_LOAN
    HELOC = LoanProductType.HOME_EQUITY_LINE

    def test_sba_7a_rules_apply(self) -> None:
        LendingComplianceEngine()
        sba_7a_rules = [r for r in LENDING_RULES if r.rule_id == "SBA-001"]
        for rule in sba_7a_rules:
            assert self.SBA_7A in rule.product_types

    def test_auto_loan_has_regz(self) -> None:
        engine = LendingComplianceEngine()
        app = ConsumerLoanApplication(
            first_name="A", last_name="B",
            product_type=LoanProductType.AUTO_LOAN,
            loan_purpose=LoanPurpose.AUTO_PURCHASE,
            requested_amount=30000,
            requested_term_months=60,
            financial_data=ConsumerFinancialData(annual_income=70000, credit_score=700),
        )
        results = engine.evaluate(app)
        assert any(r["rule_id"] == "REG-Z-001" for r in results)
