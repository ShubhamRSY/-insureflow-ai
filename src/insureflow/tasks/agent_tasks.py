from __future__ import annotations

from typing import Any

from insureflow.tasks.celery_app import celery_app


@celery_app.task(  # type: ignore
    bind=True,
    name="insureflow.tasks.agent_tasks.run_agent",
    max_retries=3,
    default_retry_delay=10,
)
def run_agent(self: Any, agent_name: str, bundle_data: dict[str, Any]) -> dict[str, Any]:
    from insureflow.agents.compliance_agent import ComplianceAgent
    from insureflow.agents.fraud_detection_agent import FraudDetectionAgent
    from insureflow.agents.loss_run_analyst import LossRunAnalystAgent
    from insureflow.agents.risk_analyst import RiskAnalystAgent
    from insureflow.models.submissions import SubmissionBundle

    agent_map = {
        "RiskAnalystAgent": RiskAnalystAgent,
        "LossRunAnalystAgent": LossRunAnalystAgent,
        "ComplianceAgent": ComplianceAgent,
        "FraudDetectionAgent": FraudDetectionAgent,
    }

    agent_cls = agent_map.get(agent_name)
    if agent_cls is None:
        raise ValueError(f"Unknown agent: {agent_name}")

    bundle = SubmissionBundle(**bundle_data)
    agent = agent_cls()
    result = agent.run(bundle)

    return result.model_dump()  # type: ignore[no-any-return]


@celery_app.task(  # type: ignore
    bind=True,
    name="insureflow.tasks.agent_tasks.supervisor_consolidate",
    max_retries=2,
)
def supervisor_consolidate(
    self: Any,
    bundle_data: dict[str, Any],
    agent_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from insureflow.agents.supervisor import SupervisorAgent
    from insureflow.agents.uw_decision_agent import UWDecisionAgent
    from insureflow.models.agents import AgentResult
    from insureflow.models.submissions import SubmissionBundle

    bundle = SubmissionBundle(**bundle_data)
    supervisor = SupervisorAgent()

    parsed_results = [AgentResult(**r) for r in (agent_results or [])]
    agents_map = {r.agent_name: r for r in parsed_results}

    uw_agent = UWDecisionAgent()
    uw_result = uw_agent.run(bundle, agent_results=agents_map)
    parsed_results.append(uw_result)

    memo = supervisor.uw_decision.produce_underwriting_memo(bundle, parsed_results, uw_result)
    conflict_resolution = supervisor._resolve_conflicts(parsed_results)
    if conflict_resolution:
        memo.review_notes.extend(conflict_resolution)

    return memo.model_dump()
