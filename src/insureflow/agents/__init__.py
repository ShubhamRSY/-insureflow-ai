"""Underwriting agents. Heavy orchestrator imports stay lazy."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_MAP: dict[str, tuple[str, str]] = {
    "BaseAgent": ("insureflow.agents.base", "BaseAgent"),
    "ComplianceAgent": ("insureflow.agents.compliance_agent", "ComplianceAgent"),
    "ExtractionAgent": ("insureflow.agents.extraction_agent", "ExtractionAgent"),
    "FraudDetectionAgent": ("insureflow.agents.fraud_detection_agent", "FraudDetectionAgent"),
    "LossRunAnalystAgent": ("insureflow.agents.loss_run_analyst", "LossRunAnalystAgent"),
    "PipelineOrchestrator": ("insureflow.agents.orchestrator", "PipelineOrchestrator"),
    "RiskAnalystAgent": ("insureflow.agents.risk_analyst", "RiskAnalystAgent"),
    "SupervisorAgent": ("insureflow.agents.supervisor", "SupervisorAgent"),
    "SynthesisAgent": ("insureflow.agents.synthesis_agent", "SynthesisAgent"),
    "UWDecisionAgent": ("insureflow.agents.uw_decision_agent", "UWDecisionAgent"),
    "VerificationAgent": ("insureflow.agents.verification_agent", "VerificationAgent"),
    "ActuarialAgent": ("insureflow.agents.actuarial_agent", "ActuarialAgent"),
    "MibOrderAgent": ("insureflow.agents.mib_order_agent", "MibOrderAgent"),
    "ApsOrderAgent": ("insureflow.agents.aps_order_agent", "ApsOrderAgent"),
    "PolicyIssuanceAgent": ("insureflow.agents.policy_issuance_agent", "PolicyIssuanceAgent"),
    "RenewalTrackerAgent": ("insureflow.agents.renewal_tracker_agent", "RenewalTrackerAgent"),
    "BeneficiaryReviewAgent": ("insureflow.agents.beneficiary_review_agent", "BeneficiaryReviewAgent"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_MAP:
        mod_path, attr = _LAZY_MAP[name]
        return getattr(import_module(mod_path), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_LAZY_MAP)
