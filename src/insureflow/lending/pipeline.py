from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from insureflow.analytics.documents import DocumentAnalyticsEngine
from insureflow.lending.compliance import LendingComplianceEngine
from insureflow.lending.models import (
    BusinessLoanApplication,
    ConsumerLoanApplication,
    CreditAnalysis,
    LendingPipelineResult,
    LoanDecision,
)
from insureflow.lending.pricing import LendingPricingEngine
from insureflow.lending.risk import LendingRiskEngine

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
    ) -> LendingPipelineResult:
        run_id = pipeline_run_id or f"lp-{application.application_id}"
        timeline: list[dict[str, Any]] = []

        timeline.append(self._record("ingest", "start", run_id, application))

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
            document_count=doc_count,
        )

        self._save_audit(run_id, application, result, timeline, documents)
        self._record_document_analytics(run_id, application, documents, result)
        return result

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
            "timeline": timeline,
            "documents": documents or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        path = os.path.join(AUDIT_DIR, f"{run_id}.json")
        with open(path, "w") as f:
            json.dump(audit, f, indent=2, default=str)

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
