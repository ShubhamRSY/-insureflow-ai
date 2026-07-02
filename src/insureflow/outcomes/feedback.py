from __future__ import annotations

from typing import Any
from uuid import uuid4

from insureflow.models.agents import UnderwritingMemo
from insureflow.outcomes.models import BindOutcome, LossExperience, OutcomeStatus, PredictionRecord
from insureflow.outcomes.store import OutcomeStore
from insureflow.rating.models import QuoteResult


class FeedbackEngine:
    """Compare AI predictions vs actual bind/loss outcomes for calibration."""

    def __init__(self, store: OutcomeStore | None = None) -> None:
        self.store = store or OutcomeStore()

    def record_prediction(
        self,
        bundle_id: str,
        memo: UnderwritingMemo,
        quote: QuoteResult,
        org_id: str = "default",
    ) -> PredictionRecord:
        record = PredictionRecord(
            prediction_id=f"pred-{uuid4().hex[:10]}",
            bundle_id=bundle_id,
            predicted_decision=memo.decision.value,
            predicted_premium=quote.adjusted_premium,
            predicted_loss_ratio=0.0,
        )
        self.store.save_prediction(record, org_id=org_id)
        return record

    def record_bind(
        self,
        bundle_id: str,
        org_id: str,
        policy_number: str,
        bound_premium: float,
        uw_decision: str,
        ai_decision: str,
        policy_admin_reference: str = "",
    ) -> BindOutcome:
        pred = self.store.get_prediction(bundle_id, org_id)
        outcome = BindOutcome(
            outcome_id=f"out-{uuid4().hex[:10]}",
            bundle_id=bundle_id,
            org_id=org_id,
            status=OutcomeStatus.BOUND,
            policy_number=policy_number,
            bound_premium=bound_premium,
            quoted_premium=pred.predicted_premium if pred else bound_premium,
            ai_decision=ai_decision,
            uw_decision=uw_decision,
            bound_by="",
            policy_admin_reference=policy_admin_reference,
        )
        self.store.save_outcome(outcome)

        if pred:
            pred.actual_decision = uw_decision
            pred.actual_premium = bound_premium
            self.store.save_prediction(pred, org_id=org_id)

        return outcome

    def record_loss_experience(
        self,
        policy_number: str,
        org_id: str,
        policy_year: int,
        earned_premium: float,
        incurred_losses: float,
        paid_losses: float,
        claim_count: int,
        bundle_id: str = "",
    ) -> LossExperience:
        loss_ratio = incurred_losses / earned_premium if earned_premium > 0 else 0.0
        exp = LossExperience(
            experience_id=f"exp-{uuid4().hex[:10]}",
            policy_number=policy_number,
            bundle_id=bundle_id,
            org_id=org_id,
            policy_year=policy_year,
            earned_premium=earned_premium,
            incurred_losses=incurred_losses,
            paid_losses=paid_losses,
            claim_count=claim_count,
            loss_ratio=round(loss_ratio, 4),
        )
        self.store.save_experience(exp)
        return exp

    def calibration_summary(self, org_id: str = "default") -> dict[str, Any]:
        experiences = self.store.list_experiences(org_id)
        if not experiences:
            return {"org_id": org_id, "sample_size": 0, "avg_loss_ratio": 0.0}

        avg_lr = sum(e.loss_ratio for e in experiences) / len(experiences)
        total_incurred = sum(e.incurred_losses for e in experiences)
        total_earned = sum(e.earned_premium for e in experiences)

        return {
            "org_id": org_id,
            "sample_size": len(experiences),
            "avg_loss_ratio": round(avg_lr, 4),
            "portfolio_loss_ratio": round(total_incurred / total_earned, 4) if total_earned else 0.0,
            "total_claims": sum(e.claim_count for e in experiences),
        }
