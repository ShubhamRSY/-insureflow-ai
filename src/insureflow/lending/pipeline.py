from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from insureflow.analytics.documents import DocumentAnalyticsEngine
from insureflow.decisions import normalize_decision
from insureflow.lending.compliance import LendingComplianceEngine
from insureflow.lending.models import (
    BusinessFinancialData,
    BusinessLoanApplication,
    ConsumerLoanApplication,
    CreditAnalysis,
    LendingPipelineResult,
    LoanDecision,
)
from insureflow.lending.pricing import LendingPricingEngine
from insureflow.lending.risk import LendingRiskEngine

logger = logging.getLogger(__name__)

AUDIT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "audit_logs",
    "lending",
)
os.makedirs(AUDIT_DIR, exist_ok=True)


class LendingPipeline:
    def __init__(self) -> None:
        self._compliance = LendingComplianceEngine()
        self._risk = LendingRiskEngine()
        self._pricing = LendingPricingEngine()
        self._analytics = DocumentAnalyticsEngine()

    def run(
        self,
        application: BusinessLoanApplication | ConsumerLoanApplication,
        documents: list[dict[str, Any]] | None = None,
        pipeline_run_id: str | None = None,
        *,
        require_documents: bool = False,
    ) -> LendingPipelineResult:
        run_id = pipeline_run_id or f"lp-{application.application_id}"
        timeline: list[dict[str, Any]] = []

        try:
            return self._run_inner(
                application,
                documents=documents,
                run_id=run_id,
                timeline=timeline,
                require_documents=require_documents,
            )
        except Exception as exc:
            logger.exception("Lending pipeline failed for %s", application.application_id)
            result = LendingPipelineResult(
                application_id=application.application_id,
                product_type=application.product_type,
                decision=LoanDecision.REFERRED,
                human_review_required=True,
                human_review_reasons=[f"Pipeline error (fail-closed): {exc}"],
                lender_notes="Fail-closed referral due to unhandled exception",
                document_count=len(documents) if documents else 0,
            )
            timeline.append(self._record("error", "failed", run_id, {"error": str(exc)}))
            try:
                self._save_audit(run_id, application, result, timeline, documents)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to persist lending audit after error")
            return result

    def _run_inner(
        self,
        application: BusinessLoanApplication | ConsumerLoanApplication,
        *,
        documents: list[dict[str, Any]] | None,
        run_id: str,
        timeline: list[dict[str, Any]],
        require_documents: bool,
    ) -> LendingPipelineResult:
        timeline.append(self._record("ingest", "start", run_id, application))

        if require_documents and not documents:
            result = LendingPipelineResult(
                application_id=application.application_id,
                product_type=application.product_type,
                decision=LoanDecision.SUSPENDED,
                human_review_required=True,
                human_review_reasons=["No supporting documents provided — cannot underwrite from form fields alone"],
            )
            timeline.append(self._record("ingest", "blocked", run_id, {"reason": "missing_documents"}))
            self._save_audit(run_id, application, result, timeline, documents)
            return result

        # Zero / missing critical financials → refer (fail-closed), not silent approve
        missing_fin = self._missing_financial_signals(application)
        if missing_fin:
            result = LendingPipelineResult(
                application_id=application.application_id,
                product_type=application.product_type,
                decision=LoanDecision.REFERRED,
                human_review_required=True,
                human_review_reasons=missing_fin,
                lender_notes="Insufficient financial evidence for automated decision",
                document_count=len(documents) if documents else 0,
            )
            timeline.append(self._record("validation", "referred", run_id, {"missing": missing_fin}))
            self._save_audit(run_id, application, result, timeline, documents)
            self._record_document_analytics(run_id, application, documents, result)
            return result

        violations = self._compliance.evaluate(application)
        timeline.append(self._record("compliance", "completed", run_id, {"violations_count": len(violations)}))

        critical_violations = [v for v in violations if v.get("severity") == "critical"]
        if critical_violations:
            result = LendingPipelineResult(
                application_id=application.application_id,
                product_type=application.product_type,
                decision=LoanDecision.SUSPENDED,
                compliance_violations=critical_violations,
                human_review_required=True,
                human_review_reasons=["Critical compliance violations detected"],
            )
            timeline.append(
                self._record(
                    "compliance",
                    "blocked",
                    run_id,
                    {"reason": "critical_violations", "violations": critical_violations},
                ),
            )
            self._save_audit(run_id, application, result, timeline, documents)
            self._record_document_analytics(run_id, application, documents, result)
            return result

        risk_analysis = self._risk.analyze(application)
        timeline.append(
            self._record(
                "risk",
                "completed",
                run_id,
                {"score": risk_analysis.overall_risk_score, "rating": risk_analysis.risk_rating},
            )
        )

        ml_default_risk = self._ml_default_risk(application, risk_analysis)
        timeline.append(
            self._record(
                "ml",
                "completed",
                run_id,
                {"risk_level": ml_default_risk.get("risk_level"), "probability": ml_default_risk.get("default_probability")},
            )
        )

        if documents:
            self._ingest_documents(application, documents)
        doc_count = len(documents) if documents else 0
        timeline.append(self._record("documents", "ingested", run_id, {"count": doc_count}))

        pricing = self._pricing.price(
            application.product_type,
            risk_analysis,
            application.requested_term_months,
        )
        timeline.append(
            self._record(
                "pricing",
                "completed",
                run_id,
                {
                    "final_rate": pricing.final_rate,
                    "base_rate": pricing.base_rate,
                    "risk_spread": pricing.risk_spread,
                },
            ),
        )

        decision, approved_amount = self._make_decision(application, risk_analysis)
        timeline.append(
            self._record(
                "decision",
                "completed",
                run_id,
                {"decision": decision.value, "approved_amount": approved_amount},
            ),
        )

        human_review = False
        human_reasons: list[str] = []
        if risk_analysis.risk_rating in ("above_average", "high"):
            human_review = True
            human_reasons.append(f"Risk rating: {risk_analysis.risk_rating}")
        if violations:
            high_sev = [v for v in violations if v.get("severity") in ("high", "critical")]
            if high_sev:
                human_review = True
                human_reasons.extend(v["rule_name"] for v in high_sev)
        if application.requested_amount > 1_000_000:
            human_review = True
            human_reasons.append(f"Loan amount ${application.requested_amount:,.0f} exceeds $1M threshold")

        result = LendingPipelineResult(
            application_id=application.application_id,
            product_type=application.product_type,
            decision=decision,
            risk_score=risk_analysis.overall_risk_score,
            risk_rating=risk_analysis.risk_rating,
            requested_amount=application.requested_amount,
            approved_amount=approved_amount,
            approved_rate=pricing.final_rate,
            approved_term_months=application.requested_term_months,
            conditions=risk_analysis.conditions,
            human_review_required=human_review,
            human_review_reasons=human_reasons,
            compliance_violations=violations,
            credit_analysis=risk_analysis,
            ml_default_risk=ml_default_risk,
            document_count=doc_count,
        )

        self._save_audit(run_id, application, result, timeline, documents)
        self._record_document_analytics(run_id, application, documents, result)
        return result

    def _ml_default_risk(
        self,
        application: BusinessLoanApplication | ConsumerLoanApplication,
        analysis: CreditAnalysis,
    ) -> dict[str, Any]:
        """Run ML lending default-risk model on the application.

        Falls back to deterministic rules when no trained model is available.
        """
        try:
            from insureflow.ml.features import FeatureVector
            from insureflow.ml.models import ModelType
            from insureflow.ml.registry import get_ml_registry

            if isinstance(application, BusinessLoanApplication):
                biz_fin = application.financials[0] if application.financials else BusinessFinancialData()
                fv = FeatureVector(
                    loan_segment="business",
                    credit_score=float(application.guarantors[0].credit_score if application.guarantors else 0),
                    revenue=float(biz_fin.annual_revenue),
                    loan_amount=float(application.requested_amount),
                    years_in_business=float(application.years_in_business),
                    dscr=float(analysis.dscr),
                    current_ratio=float(analysis.liquidity_ratio),
                    leverage_ratio=float(analysis.leverage_ratio),
                    profit_margin=float(analysis.profitability_score),
                    debt_service=float(biz_fin.debt_service),
                    ebitda=float(biz_fin.ebitda),
                    total_assets=float(biz_fin.total_assets),
                    total_liabilities=float(biz_fin.total_liabilities),
                )
            else:
                con_fin = application.financial_data
                fv = FeatureVector(
                    loan_segment="consumer",
                    credit_score=float(con_fin.credit_score),
                    dti_ratio=float(analysis.debt_to_income_ratio),
                    revenue=float(con_fin.annual_income),
                    loan_amount=float(application.requested_amount),
                    employment_years=float(con_fin.employment_years),
                    total_assets=float(con_fin.total_assets),
                    total_liabilities=float(con_fin.total_liabilities),
                    bankruptcies=int(con_fin.bankruptcies_last_7_years),
                    foreclosures=int(con_fin.foreclosures_last_7_years),
                )

            from insureflow.ml.base import BaseMLModel

            model = get_ml_registry().get(ModelType.LENDING_DEFAULT_RISK)
            if model is None or not isinstance(model, BaseMLModel):
                return {"error": "lending_default_risk model unavailable"}
            return model.predict(fv)
        except Exception:  # noqa: BLE001
            logger.warning("Lending ML default-risk prediction failed", exc_info=True)
            from insureflow.ml.models import LendingDefaultScore

            # Fail closed — never report zero default risk on error.
            return LendingDefaultScore(
                default_probability=1.0,
                risk_level="high",
                top_factors=["model_error"],
                recommended_structure="refer_manual_review",
                model_version="error",
            ).model_dump()

    @staticmethod
    def _missing_financial_signals(application: BusinessLoanApplication | ConsumerLoanApplication) -> list[str]:
        reasons: list[str] = []
        if application.requested_amount <= 0:
            reasons.append("Requested amount missing or zero")
        if isinstance(application, BusinessLoanApplication):
            if not application.financials:
                reasons.append("No business financial statements provided")
            else:
                biz_fin = application.financials[0]
                if biz_fin.annual_revenue <= 0 and biz_fin.net_income == 0 and biz_fin.ebitda == 0:
                    reasons.append("Business revenue/income/EBITDA all missing — cannot score DSCR")
        elif isinstance(application, ConsumerLoanApplication):
            consumer_fin = application.financial_data
            if consumer_fin.annual_income <= 0 and consumer_fin.credit_score <= 0:
                reasons.append("Consumer income and credit score both missing")
        return reasons

    def _record(self, phase: str, status: str, run_id: str, data: Any) -> dict[str, Any]:
        return {
            "phase": phase,
            "status": status,
            "run_id": run_id,
            "data": str(data)[:200],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _make_decision(
        self,
        application: BusinessLoanApplication | ConsumerLoanApplication,
        analysis: CreditAnalysis,
    ) -> tuple[LoanDecision, float | None]:
        score = analysis.overall_risk_score
        if score >= 80:
            return LoanDecision.DECLINED, None
        if score >= 65:
            if application.requested_amount <= 50_000:
                return LoanDecision.APPROVED, application.requested_amount * 0.7
            return LoanDecision.APPROVED_WITH_CONDITIONS, application.requested_amount * 0.8
        if score >= 45:
            return LoanDecision.APPROVED_WITH_CONDITIONS, application.requested_amount
        return LoanDecision.APPROVED, application.requested_amount

    def _ingest_documents(
        self,
        application: BusinessLoanApplication | ConsumerLoanApplication,
        documents: list[dict[str, Any]],
    ) -> None:
        for doc in documents:
            doc["application_id"] = application.application_id
            doc["product_type"] = application.product_type.value
            doc["ingested_at"] = datetime.now(timezone.utc).isoformat()

    def _save_audit(
        self,
        run_id: str,
        application: Any,
        result: LendingPipelineResult,
        timeline: list[dict[str, Any]],
        documents: list[dict[str, Any]] | None,
    ) -> None:
        audit = {
            "run_id": run_id,
            "application_type": ("business" if isinstance(application, BusinessLoanApplication) else "consumer"),
            "application": application.model_dump(),
            "result": result.model_dump(mode="json"),
            "outcome": normalize_decision(result.decision).value,
            "timeline": timeline,
            "documents": [{k: v for k, v in d.items() if k != "content"} | {"content_chars": len(str(d.get("content") or ""))} for d in (documents or [])],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        path = os.path.join(AUDIT_DIR, f"{run_id}.json")
        with open(path, "w") as f:
            json.dump(audit, f, indent=2, default=str)

        # Also persist to job store so API results survive process restart
        try:
            from insureflow.storage.job_store import get_job_store

            org_id = getattr(application, "org_id", None) or "default"
            get_job_store().set(
                "lending",
                application.application_id,
                {"status": "completed", "audit": audit, "result": result.model_dump(mode="json")},
                org_id=org_id,
            )
        except Exception:  # noqa: BLE001
            logger.warning("Could not persist lending result to job store", exc_info=True)

    def _record_document_analytics(
        self,
        run_id: str,
        application: Any,
        documents: list[dict[str, Any]] | None,
        result: LendingPipelineResult,
    ) -> None:
        if not documents:
            return
        vertical = "business_lending" if isinstance(application, BusinessLoanApplication) else "consumer_lending"
        self._analytics.record(
            bundle_id=run_id,
            vertical=vertical,
            decision=result.decision.value,
            document_count=len(documents),
        )
