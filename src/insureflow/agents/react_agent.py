from __future__ import annotations

import json
import time
from typing import Any, Optional, cast

from insureflow.agents.base import BaseAgent
from insureflow.agents.prompts import SYSTEM_PROMPTS
from insureflow.agents.react_tools import ToolRegistry
from insureflow.llm.client import LLMClient
from insureflow.models.agents import (
    AgentResult,
    AgentType,
    Finding,
    RiskSeverity,
)
from insureflow.models.submissions import SubmissionBundle


class ReActAgent(BaseAgent):
    agent_type: AgentType
    agent_name: str = "react_agent"
    prompt_key: str = ""

    def __init__(
        self,
        tools: Optional[ToolRegistry] = None,
        llm: Optional[LLMClient] = None,
        model_tier: str = "cheap",
    ) -> None:
        super().__init__()
        self._tools_registry: ToolRegistry | None = None
        self.llm = llm or LLMClient(model_tier=model_tier)
        self._model_tier = model_tier

    def run(self, bundle: SubmissionBundle, **kwargs: Any) -> AgentResult:
        start = time.time()
        self._findings = []
        self._errors = []

        self._tools_registry = ToolRegistry(bundle)

        if self.llm.api_key:
            try:
                self._react_loop(bundle, **kwargs)
            except Exception as e:
                self._errors.append(f"ReAct loop error: {type(e).__name__}: {e}")
                if not self._findings:
                    self._analyze(bundle, **kwargs)
        else:
            self._analyze(bundle, **kwargs)

        elapsed = (time.time() - start) * 1000
        severity = self.tools.assess_overall_severity(self._findings)
        return AgentResult(
            agent_type=self.agent_type,
            agent_name=self.agent_name,
            findings=self._findings,
            risk_score=self._calculate_risk_score(),
            risk_severity=severity,
            recommendation=self._build_recommendation(),
            summary=self._build_summary(),
            errors=self._errors,
            processing_time_ms=round(elapsed, 1),
            success=len(self._errors) == 0,
            data_sources_used=self._get_sources(bundle),
        )

    def _react_loop(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        system_prompt = self._build_react_prompt(bundle)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (f"Analyze the submission for {self.agent_name}. Think step by step and use tools to gather data. When you have enough information, produce your final findings."),
            },
        ]

        max_steps = 10
        for step in range(max_steps):
            raw = self.llm.complete(
                "You are an AI assistant that follows instructions precisely.",
                self._format_messages(messages),
            )

            parsed = self._parse_llm_output(raw)

            if parsed.get("action") == "final_answer":
                self._process_final_answer(parsed)
                return

            tool_name = parsed.get("action")
            tool_input = parsed.get("action_input", {})

            if not tool_name or tool_name == "none":
                self._process_final_answer(parsed)
                return

            observation = self._call_tool(tool_name, tool_input)
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": f"Observation: {json.dumps(observation, default=str)}",
                }
            )

        self._errors.append("ReAct loop reached max steps without final answer")

    def _build_react_prompt(self, bundle: SubmissionBundle) -> str:
        base_prompt = SYSTEM_PROMPTS.get(self.prompt_key, "")
        tools_desc = self._tools_registry.tool_descriptions() if self._tools_registry else ""
        insured = self.tools.get_named_insured(bundle)

        return (
            f"You are {self.agent_name} analyzing a submission for {insured}.\n\n"
            f"{base_prompt}\n\n"
            f"{tools_desc}\n\n"
            "You must respond in JSON format with exactly this structure:\n"
            '{"thought": "your reasoning here", "action": "tool_name", "action_input": {"param": "value"}}\n\n'
            "When you have enough information, respond with:\n"
            '{"thought": "I have enough information", "action": "final_answer", '
            '"findings": [...], "summary": "..."}\n\n'
            'Each finding: {"title": str, "description": str, '
            '"severity": "low|moderate|high|critical", '
            '"category": str, "evidence": [str]}\n'
            "Do not add markdown formatting. Return ONLY valid JSON."
        )

    def _format_messages(self, messages: list[dict[str, str]]) -> str:
        parts = []
        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            if len(content) > 12000:
                content = content[:12000] + "\n... [truncated]"
            parts.append(f"[{role}]\n{content}")
        return "\n\n".join(parts)

    def _parse_llm_output(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return cast(dict[str, Any], json.loads(cleaned))
        except json.JSONDecodeError:
            pass

        try:
            import re

            json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if json_match:
                return cast(dict[str, Any], json.loads(json_match.group()))
        except (json.JSONDecodeError, AttributeError):
            pass

        return {"action": "final_answer", "findings": [], "summary": "Could not parse LLM output"}

    def _call_tool(self, name: str, inp: dict[str, Any]) -> Any:
        if not self._tools_registry:
            return {"error": "No tool registry"}
        result = self._tools_registry.call(name, **inp)
        return result

    def _process_final_answer(self, parsed: dict[str, Any]) -> None:
        findings_data = parsed.get("findings", [])
        if not findings_data and parsed.get("action") == "final_answer":
            findings_data = parsed.get("findings", [])

        for fd in findings_data:
            sev_map = {
                "low": RiskSeverity.LOW,
                "moderate": RiskSeverity.MODERATE,
                "high": RiskSeverity.HIGH,
                "critical": RiskSeverity.CRITICAL,
            }
            self._add_finding(
                Finding(
                    title=fd.get("title", "Untitled"),
                    description=fd.get("description", ""),
                    severity=sev_map.get(fd.get("severity", ""), RiskSeverity.MODERATE),
                    category=fd.get("category", "general"),
                    evidence=fd.get("evidence", []),
                )
            )

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        pass
