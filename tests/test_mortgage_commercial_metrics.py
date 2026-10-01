from __future__ import annotations

from pathlib import Path

import pytest

from insureflow.agents.mortgage.supervisor import MortgageCreditAgent, MortgageSupervisorAgent
from insureflow.audit.store import AuditStore
from insureflow.ingestion.mortgage.classifier import MortgageDocumentClassifier
from insureflow.ingestion.mortgage.extractors import EXTRACTOR_MAP, extract_appraisal, extract_operating_statement
from insureflow.models.mortgage import (
    ExtractedMortgageField,
    IncomeSummary,
    MortgageBundle,
    MortgageDocument,
    MortgageDocumentType,
    ProductLine,
)
from insureflow.mortgage.commercial_metrics import (
    STATED_VS_COMPUTED_TOLERANCE,
    compute_commercial_metrics,
    compute_dscr,
    debt_yield,
)
from insureflow.mortgage.compliance import MortgageComplianceEngine
from insureflow.mortgage.pricing import LoanPricingEngine, LoanProduct
from insureflow.mortgage.reconciliation import MortgageReconciliationEngine

SIM = Path(__file__).resolve().parent.parent / "simulated_documents"
COMMERCIAL = SIM / "commercial_mortgage"
RESIDENTIAL = SIM / "home_mortgage"

STATEMENT = COMMERCIAL / "property_performance" / "property_operating_statement_2025.txt"
DEBT_SCHEDULE = COMMERCIAL / "debt_legal" / "business_debt_schedule.txt"
COMMERCIAL_APPRAISAL = COMMERCIAL / "due_diligence" / "commercial_appraisal.txt"


def _field(name: str, value: str) -> list[ExtractedMortgageField]:
    return [ExtractedMortgageField(field_name=name, value=value)]


@pytest.fixture
def audit_store(tmp_path: Path) -> AuditStore:
    return AuditStore(base_path=tmp_path / "audit_logs")


def _statement_doc(noi: str | None = None, monthly_pi: str | None = None, stated_dscr: str | None = None) -> MortgageDocument:
    """An operating statement built from explicit fields, not from parsing."""
    fields: dict[str, list[ExtractedMortgageField]] = {}
    if noi is not None:
        fields["noi"] = _field("noi", noi)
    if monthly_pi is not None:
        fields["subject_loan_monthly_debt_service"] = _field("subject_loan_monthly_debt_service", monthly_pi)
    if stated_dscr is not None:
        fields["dscr"] = _field("dscr", stated_dscr)
    return MortgageDocument(
        document_id="os",
        source_path=str(STATEMENT),
        document_type=MortgageDocumentType.OPERATING_STATEMENT,
        product_line=ProductLine.COMMERCIAL_MORTGAGE,
        extracted_fields=fields,
    )


def _schedule_doc(subject_monthly: str | None, total_monthly: str | None = None) -> MortgageDocument:
    fields: dict[str, list[ExtractedMortgageField]] = {}
    if subject_monthly is not None:
        fields["subject_loan_monthly_debt_service"] = _field("subject_loan_monthly_debt_service", subject_monthly)
    if total_monthly is not None:
        fields["total_monthly_debt_service"] = _field("total_monthly_debt_service", total_monthly)
    return MortgageDocument(
        document_id="ds",
        source_path=str(DEBT_SCHEDULE),
        document_type=MortgageDocumentType.BUSINESS_DEBT_SCHEDULE,
        product_line=ProductLine.COMMERCIAL_MORTGAGE,
        extracted_fields=fields,
    )


def _commercial_bundle(documents: list[MortgageDocument]) -> MortgageBundle:
    return MortgageBundle(
        bundle_id="cm-test",
        product_line=ProductLine.COMMERCIAL_MORTGAGE,
        documents=documents,
    )


def _real_bundle() -> MortgageBundle:
    documents: list[MortgageDocument] = []
    for path in sorted(COMMERCIAL.rglob("*.txt")):
        text = path.read_text(errors="replace")
        doc_type = MortgageDocumentClassifier.classify(text, path.name)
        extractor = EXTRACTOR_MAP.get(doc_type)
        if extractor is None:
            continue
        documents.append(
            MortgageDocument(
                document_id=path.name,
                source_path=str(path),
                document_type=doc_type,
                product_line=ProductLine.COMMERCIAL_MORTGAGE,
                raw_text=text,
                extracted_fields=extractor(text),
            )
        )
    return _commercial_bundle(documents)


class TestOperatingStatementExtraction:
    def test_extracts_current_year_columns_from_real_statement(self) -> None:
        fields = extract_operating_statement(STATEMENT.read_text())
        # The statement is laid out PRIOR | CURRENT | VARIANCE | %. Taking
        # the wrong column silently understates or overstates coverage.
        assert fields["noi"][0].value == "158542.00"
        assert fields["effective_gross_income"][0].value == "267700.00"
        assert fields["total_operating_expenses"][0].value == "109158.00"
        assert fields["dscr"][0].value == "1.12"
        assert fields["subject_loan_monthly_debt_service"][0].value == "11,848.40"

    def test_records_which_column_was_used(self) -> None:
        fields = extract_operating_statement(STATEMENT.read_text())
        assert "column 2" in fields["noi"][0].context

    def test_percentage_is_not_read_as_a_dollar_amount(self) -> None:
        """A single-amount line with a trailing percentage must not shift columns."""
        text = "NET OPERATING INCOME    $158,542.00    -2.9%\n"
        fields = extract_operating_statement(text)
        assert fields["noi"][0].value == "158542.00"

    def test_dscr_expanded_label_is_read(self) -> None:
        text = "DSCR (Debt Service Coverage Ratio):  1.12x\n"
        assert extract_operating_statement(text)["dscr"][0].value == "1.12"

    def test_absent_statement_yields_no_fields(self) -> None:
        result = extract_operating_statement("rent roll only, no income statement here")
        assert result.get("noi", []) == []


class TestAppraisalExtraction:
    def test_uses_reconciled_value_not_an_approach_figure(self) -> None:
        fields = extract_appraisal(COMMERCIAL_APPRAISAL.read_text(), commercial=True)
        assert fields["appraised_value"][0].value == "2,300,000"
        assert fields["final_appraised_value"][0].value == "2,300,000"

    def test_noi_is_not_potential_gross_income(self) -> None:
        """The NOI label is followed by a gross income line; only the
        labelled NOI row may be read."""
        fields = extract_appraisal(COMMERCIAL_APPRAISAL.read_text(), commercial=True)
        assert fields["noi"][0].value == "161,150.40"
        assert fields["noi"][0].value != "273,600"

    def test_address_does_not_swallow_the_document(self) -> None:
        fields = extract_appraisal(COMMERCIAL_APPRAISAL.read_text(), commercial=True)
        address = fields["property_address"][0].value
        assert address == "5678 Commerce Boulevard, Springfield, IL 62702"
        assert len(address) < 120

    def test_residential_appraised_value_unchanged(self) -> None:
        """Residential LTV feeds the golden outcomes; commercial fixes must not move it."""
        path = RESIDENTIAL / "johnson_marcus_imani" / "property" / "appraisal_478_pine.txt"
        fields = extract_appraisal(path.read_text(), commercial=False)
        assert fields["appraised_value"][0].value == "275,000"


class TestDSCRComputation:
    def test_computes_dscr_from_noi_over_annual_debt_service(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="158542", monthly_pi="11848.40")])
        result = compute_dscr(bundle)
        assert result.computable
        assert result.dscr == pytest.approx(158542 / (11848.40 * 12), rel=1e-6)
        assert result.basis == "computed"

    def test_monthly_debt_service_is_annualised(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="240000", monthly_pi="10000")])
        result = compute_dscr(bundle)
        assert result.annual_debt_service == 120000
        assert result.dscr == pytest.approx(2.0)

    def test_debt_schedule_is_preferred_over_statement(self) -> None:
        bundle = _commercial_bundle(
            [
                _statement_doc(noi="240000", monthly_pi="99999"),
                _schedule_doc(subject_monthly="10000"),
            ]
        )
        result = compute_dscr(bundle)
        assert result.annual_debt_service == 120000
        assert result.dscr == pytest.approx(2.0)

    def test_provenance_names_both_inputs(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="240000", monthly_pi="10000")])
        text = compute_dscr(bundle).provenance()
        assert "operating_statement.noi" in text
        assert "240,000" in text and "120,000" in text

    def test_reconciles_with_the_stated_dscr_on_the_fixture(self) -> None:
        result = compute_dscr(_real_bundle())
        assert result.computable
        assert result.stated_dscr == pytest.approx(1.12)
        assert abs(result.variance or 0) <= STATED_VS_COMPUTED_TOLERANCE

    def test_flags_a_stated_dscr_that_contradicts_the_arithmetic(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="240000", monthly_pi="10000", stated_dscr="2.50")])
        result = compute_dscr(bundle)
        assert result.dscr == pytest.approx(2.0)
        assert result.variance == pytest.approx(0.5)
        assert any("disagrees" in note for note in result.notes)

    def test_rebuilds_noi_from_egi_less_expenses(self) -> None:
        doc = _statement_doc()
        doc.extracted_fields["effective_gross_income"] = _field("effective_gross_income", "300000")
        doc.extracted_fields["total_operating_expenses"] = _field("total_operating_expenses", "100000")
        bundle = _commercial_bundle([doc, _schedule_doc(subject_monthly="10000")])
        result = compute_dscr(bundle)
        assert result.noi == pytest.approx(200000)
        assert result.noi_source is not None and result.noi_source.basis == "derived"

    def test_missing_debt_service_is_unavailable_not_zero(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="240000")])
        result = compute_dscr(bundle)
        assert not result.computable
        assert result.dscr is None
        assert result.basis == "unavailable"

    def test_missing_noi_is_unavailable_not_zero(self) -> None:
        bundle = _commercial_bundle([_schedule_doc(subject_monthly="10000")])
        result = compute_dscr(bundle)
        assert not result.computable
        assert result.dscr is None

    def test_empty_bundle_is_unavailable(self) -> None:
        result = compute_dscr(_commercial_bundle([]))
        assert not result.computable
        assert result.dscr is None

    def test_zero_debt_service_is_unavailable(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="240000", monthly_pi="0")])
        assert not compute_dscr(bundle).computable

    def test_stated_dscr_alone_does_not_count_as_computable(self) -> None:
        """The old rule read only the stated number; a printed ratio with no
        underlying figures must not pass as verified."""
        bundle = _commercial_bundle([_statement_doc(stated_dscr="1.12")])
        result = compute_dscr(bundle)
        assert not result.computable
        assert result.stated_dscr == pytest.approx(1.12)

    def test_reports_the_stricter_all_debt_view(self) -> None:
        bundle = _commercial_bundle(
            [
                _statement_doc(noi="240000", monthly_pi="10000"),
                _schedule_doc(subject_monthly="10000", total_monthly="12000"),
            ]
        )
        result = compute_dscr(bundle)
        assert result.total_annual_debt_service == 144000
        assert result.dscr_on_total_debt == pytest.approx(240000 / 144000)


class TestDebtYield:
    def test_debt_yield_is_noi_over_loan_amount(self) -> None:
        assert debt_yield(160000, 2000000) == pytest.approx(0.08)

    def test_debt_yield_unknown_without_noi(self) -> None:
        assert debt_yield(None, 2000000) is None

    def test_debt_yield_unknown_without_loan_amount(self) -> None:
        assert debt_yield(160000, 0) is None

    def test_metrics_report_missing_criteria(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="240000", monthly_pi="10000")])
        metrics = compute_commercial_metrics(bundle, loan_amount=2000000)
        assert metrics.debt_yield == pytest.approx(0.12)
        assert "ltv" in metrics.missing()


class TestCommercialDscrCompliance:
    def _violation(self, bundle: MortgageBundle):
        MortgageComplianceEngine().evaluate(bundle)
        return next((v for v in bundle.compliance_violations if v.rule_id == "CM-DSCR-001"), None)

    def test_low_dscr_is_critical(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="120000", monthly_pi="10000")])
        violation = self._violation(bundle)
        assert violation is not None
        assert violation.severity == "critical"

    def test_adequate_dscr_passes(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="240000", monthly_pi="10000")])
        assert self._violation(bundle) is None

    def test_fails_closed_when_dscr_cannot_be_computed(self) -> None:
        """The reported bug: a statement with no DSCR silently passed."""
        bundle = _commercial_bundle([_statement_doc(noi="240000")])
        violation = self._violation(bundle)
        assert violation is not None
        assert violation.severity == "critical"
        assert "unavailable" in violation.message.lower()

    def test_fails_closed_on_an_empty_commercial_package(self) -> None:
        violation = self._violation(_commercial_bundle([]))
        assert violation is not None
        assert violation.severity == "critical"

    def test_does_not_apply_to_residential(self) -> None:
        bundle = MortgageBundle(bundle_id="resi", product_line=ProductLine.RESIDENTIAL_MORTGAGE)
        MortgageComplianceEngine().evaluate(bundle)
        assert not [v for v in bundle.compliance_violations if v.rule_id == "CM-DSCR-001"]

    def test_uses_computed_value_not_the_stated_one(self) -> None:
        """A borrower cannot pass by printing a healthy ratio on the statement."""
        bundle = _commercial_bundle([_statement_doc(noi="120000", monthly_pi="10000", stated_dscr="1.45")])
        violation = self._violation(bundle)
        assert violation is not None
        assert "1.00x" in violation.message


class TestCommercialDebtYieldCompliance:
    def _violation(self, bundle: MortgageBundle):
        MortgageComplianceEngine().evaluate(bundle)
        return next((v for v in bundle.compliance_violations if v.rule_id == "CM-DY-001"), None)

    def test_low_debt_yield_is_critical(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="120000", monthly_pi="10000")])
        bundle.collateral = None
        bundle.documents.append(_schedule_doc(subject_monthly="10000"))
        MortgageReconciliationEngine().reconcile(bundle)
        violation = self._violation(bundle)
        assert violation is not None and violation.severity == "critical"

    def test_unknown_debt_yield_is_critical(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="120000", monthly_pi="10000")])
        violation = self._violation(bundle)
        assert violation is not None
        assert "unavailable" in violation.message.lower()


class TestCommercialCreditDecision:
    def test_absent_personal_credit_is_not_reported_as_a_credit_gap(self) -> None:
        """The reported bug: a commercial entity with no FICO file was
        flagged 'No credit report' at critical, which denies the deal."""
        bundle = _real_bundle()
        bundle.credit = None
        result = MortgageCreditAgent().analyze(bundle)
        assert not any("no credit report" in f.title.lower() for f in result.findings)

    def test_no_finding_mentions_a_personal_credit_score(self) -> None:
        from insureflow.models.mortgage import CreditSummary

        bundle = _real_bundle()
        bundle.credit = CreditSummary(credit_score=540)
        result = MortgageCreditAgent().analyze(bundle)
        text = " ".join(f"{f.title} {f.description}".lower() for f in result.findings)
        assert "score 540" not in text
        assert "credit score" not in text

    def test_reports_dscr_and_debt_yield(self) -> None:
        result = MortgageCreditAgent().analyze(_real_bundle())
        titles = " ".join(f.title.lower() for f in result.findings)
        assert "dscr" in titles
        assert "debt yield" in titles

    def test_thin_dscr_is_flagged_critical(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="120000", monthly_pi="10000")])
        result = MortgageCreditAgent().analyze(bundle)
        assert any(f.severity == "critical" for f in result.findings)

    def test_residential_still_uses_credit_score(self) -> None:
        bundle = MortgageBundle(bundle_id="resi", product_line=ProductLine.RESIDENTIAL_MORTGAGE)
        result = MortgageCreditAgent().analyze(bundle)
        assert any("credit" in f.title.lower() for f in result.findings)

    def test_commercial_memo_carries_no_dti(self) -> None:
        bundle = _real_bundle()
        bundle.income = IncomeSummary(adjusted_gross_income=90000)
        bundle.credit = None
        memo = MortgageSupervisorAgent().analyze(bundle)
        assert memo.dti_ratio is None

    def test_commercial_memo_summary_reports_commercial_metrics(self) -> None:
        memo = MortgageSupervisorAgent().analyze(_real_bundle())
        assert "commercial credit" in memo.summary
        assert "DSCR" in memo.summary


class TestCommercialPricing:
    def _memo(self, decision=None):
        from insureflow.models.mortgage import MortgageDecision, MortgageMemo

        return MortgageMemo(
            bundle_id="cm",
            product_line=ProductLine.COMMERCIAL_MORTGAGE,
            decision=decision or MortgageDecision.APPROVE,
        )

    def test_prices_on_dscr_not_credit_score(self) -> None:
        bundle = _real_bundle()
        quote = LoanPricingEngine().quote(
            bundle,
            self._memo(),
            loan_amount=1_850_000,
            product=LoanProduct.COMMERCIAL_5_1_ARM,
        )
        reasons = " ".join(quote.ineligibility_reasons)
        adjustments = " ".join(a["reason"] for a in quote.pricing_adjustments)
        assert "credit score" not in reasons.lower()
        assert "dti" not in reasons.lower()
        assert "credit" not in adjustments

    def test_ignores_a_bad_personal_credit_score(self) -> None:
        from insureflow.models.mortgage import CreditSummary

        bundle = _real_bundle()
        bundle.credit = CreditSummary(credit_score=540, total_monthly_payment=4200)
        quote = LoanPricingEngine().quote(
            bundle,
            self._memo(),
            loan_amount=1_850_000,
            product=LoanProduct.COMMERCIAL_5_1_ARM,
        )
        assert not any("credit" in r.lower() for r in quote.ineligibility_reasons)

    def test_thin_dscr_prices_wider_and_fails_eligibility(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="120000", monthly_pi="10000")])
        quote = LoanPricingEngine().quote(
            bundle,
            self._memo(),
            loan_amount=1_850_000,
            product=LoanProduct.COMMERCIAL_5_1_ARM,
        )
        assert any("dscr" in r.lower() for r in quote.ineligibility_reasons)
        assert quote.adjusted_rate > quote.base_rate

    def test_uncomputable_dscr_is_ineligible_not_a_pass(self) -> None:
        bundle = _commercial_bundle([_statement_doc(noi="240000")])
        quote = LoanPricingEngine().quote(
            bundle,
            self._memo(),
            loan_amount=1_850_000,
            product=LoanProduct.COMMERCIAL_5_1_ARM,
        )
        assert any("dscr" in r.lower() for r in quote.ineligibility_reasons)
        assert not quote.eligible

    def test_no_pmi_on_a_commercial_quote(self) -> None:
        quote = LoanPricingEngine().quote(
            _real_bundle(),
            self._memo(),
            loan_amount=1_850_000,
            product=LoanProduct.COMMERCIAL_5_1_ARM,
        )
        assert quote.pmi_required is False

    def test_residential_pricing_unchanged(self) -> None:
        from insureflow.models.mortgage import CreditSummary, MortgageDecision, MortgageMemo

        bundle = MortgageBundle(bundle_id="resi", product_line=ProductLine.RESIDENTIAL_MORTGAGE)
        bundle.credit = CreditSummary(credit_score=760)
        memo = MortgageMemo(bundle_id="resi", product_line=ProductLine.RESIDENTIAL_MORTGAGE, decision=MortgageDecision.APPROVE)
        quote = LoanPricingEngine().quote(bundle, memo, loan_amount=400000, product=LoanProduct.CONVENTIONAL_30_FIXED)
        assert quote.base_rate == 6.75
        assert quote.adjusted_rate == 6.50  # excellent_credit, -25bps
        assert any(a["reason"] == "excellent_credit" for a in quote.pricing_adjustments)


class TestCommercialPipeline:
    def test_reports_commercial_credit_metrics(self, audit_store) -> None:
        from insureflow.mortgage.pipeline import MortgagePipeline

        results = MortgagePipeline(use_llm=False, audit_store=audit_store).run_from_directory(str(COMMERCIAL), bundle_id="cm-pipeline")
        credit = results["commercial_credit"]
        assert credit["dscr"] is not None
        assert credit["noi"] is not None
        assert credit["annual_debt_service"] is not None
        assert "operating_statement" in credit["dscr_provenance"]

    def test_does_not_report_a_dti_for_a_commercial_deal(self, audit_store) -> None:
        from insureflow.mortgage.pipeline import MortgagePipeline

        results = MortgagePipeline(use_llm=False, audit_store=audit_store).run_from_directory(str(COMMERCIAL), bundle_id="cm-pipeline-2")
        assert results["dti_ratio"] is None

    def test_residential_pipeline_reports_dti(self, audit_store) -> None:
        from insureflow.mortgage.pipeline import MortgagePipeline

        results = MortgagePipeline(use_llm=False, audit_store=audit_store).run_from_directory(str(RESIDENTIAL), bundle_id="resi-pipeline")
        assert "commercial_credit" not in results
