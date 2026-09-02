from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional, cast

from insureflow.agents.base import BaseAgent
from insureflow.agents.prompts import SYSTEM_PROMPTS
from insureflow.agents.react_tools import ToolRegistry
from insureflow.llm.client import LLMClient
from insureflow.models.agents import AgentResult, AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.verification.circuit_breaker import get_circuit_breaker

logger = logging.getLogger(__name__)


def _llm_circuit_key(llm: LLMClient) -> str:
    return f"{llm.provider}/{llm.model or ''}"


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
        self.bundle = bundle

        self._insurance_line = kwargs.get("insurance_line")
        self._org_id = kwargs.get("org_id")
        self._reflect_enabled = kwargs.get("reflect", False)
        self._reflection_note = ""
        self._tools_registry = ToolRegistry(bundle, insurance_line=self._insurance_line, org_id=self._org_id)

        circuit_key = _llm_circuit_key(self.llm)
        breaker = get_circuit_breaker(
            name=f"llm:{circuit_key}",
            failure_threshold=3,
            recovery_timeout=60.0,
        )
        if self.llm.api_key and breaker.is_available:
            try:
                self._react_loop(bundle, **kwargs)
                breaker.record_success()
                if self._reflect_enabled and self._findings:
                    self._reflect()
            except Exception as e:
                breaker.record_failure()
                state = breaker.state
                logger.warning(
                    "ReAct LLM call failed (breaker=%s, state=%s): %s — falling back to deterministic",
                    circuit_key,
                    state.value,
                    e,
                )
                self._errors.append(f"ReAct loop error: {type(e).__name__}: {e}")
                self._findings = []
                self._analyze(bundle, **kwargs)
        else:
            if self.llm.api_key:
                logger.info("LLM circuit breaker OPEN for %s — using deterministic analysis", circuit_key)
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
        from insureflow.rating.models import is_non_property_line

        base_prompt = SYSTEM_PROMPTS.get(self.prompt_key, "")
        tools_desc = self._tools_registry.tool_descriptions() if self._tools_registry else ""
        insured = self.tools.get_named_insured(bundle)
        insurance_line = getattr(self, "_insurance_line", None)

        line_context = f"This submission's line of business is: {insurance_line}.\n" if insurance_line else ""
        scope_warning = (
            "This line has no physical insured locations, coverage limits/deductibles/"
            "sublimits, or P&C-style claims loss-run history — those concepts do not "
            "apply here. Never report a finding about missing/absent locations, "
            "coverages, coverage limits, loss runs, claims history, or schedule of "
            "values for this submission; only the tools relevant to this line are "
            "available to you below.\n"
            if is_non_property_line(insurance_line)
            else ""
        )

        return (
            f"You are {self.agent_name} analyzing a submission for {insured}.\n\n"
            f"{line_context}{scope_warning}\n"
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

    def _try_parse_json(self, raw: str) -> dict[str, Any] | None:
        """The actual parse attempt, with no fallback shape — returns None on
        total failure so callers can tell "the model said findings: []"
        apart from "this didn't parse at all", which _parse_llm_output's own
        fallback (below) would otherwise make indistinguishable.
        """
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

        return None

    def _parse_llm_output(self, raw: str) -> dict[str, Any]:
        parsed = self._try_parse_json(raw)
        if parsed is not None:
            return parsed
        return {"action": "final_answer", "findings": [], "summary": "Could not parse LLM output"}

    def _call_tool(self, name: str, inp: dict[str, Any]) -> Any:
        if not self._tools_registry:
            return {"error": "No tool registry"}
        result = self._tools_registry.call(name, **inp)
        return result

    # Keyword guard applied only when insurance_line is a NON_PROPERTY_LINE —
    # a last-resort, generation-time reject for an LLM finding that names a
    # P&C-only concept despite the prompt/tool scoping above. This runs
    # before the finding is ever constructed or enters memo.key_findings, so
    # it's still "the source," not a downstream display filter.
    _PROPERTY_ONLY_FINDING_KEYWORDS = (
        "insured location",
        "no location",
        "missing location",
        "coverage schedule",
        "coverage limit",
        "missing coverage",
        "no coverage",
        "loss run",
        "schedule of values",
        "statement of values",
    )

    def _process_final_answer(self, parsed: dict[str, Any]) -> None:
        findings_data = parsed.get("findings", [])
        for finding in self._build_findings(findings_data):
            self._add_finding(finding)

    def _build_findings(self, findings_data: Any) -> list[Finding]:
        """Convert raw LLM finding dicts into Finding objects, applying the
        same non-property-line keyword guard _process_final_answer always
        has. Shared with _reflect() so a revised finding list goes through
        the identical filtering the original draft did.
        """
        from insureflow.rating.models import is_non_property_line

        if not isinstance(findings_data, list):
            return []

        line_restricted = is_non_property_line(getattr(self, "_insurance_line", None))
        sev_map = {
            "low": RiskSeverity.LOW,
            "moderate": RiskSeverity.MODERATE,
            "high": RiskSeverity.HIGH,
            "critical": RiskSeverity.CRITICAL,
        }
        built: list[Finding] = []
        for fd in findings_data:
            if line_restricted:
                blob = f"{fd.get('title', '')} {fd.get('description', '')}".lower()
                if any(kw in blob for kw in self._PROPERTY_ONLY_FINDING_KEYWORDS):
                    logger.warning(
                        "%s: dropped LLM finding referencing a P&C-only concept on a non-property line: %r",
                        self.agent_name,
                        fd.get("title"),
                    )
                    continue
            built.append(
                Finding(
                    title=fd.get("title", "Untitled"),
                    description=fd.get("description", ""),
                    severity=sev_map.get(fd.get("severity", ""), RiskSeverity.MODERATE),
                    category=fd.get("category", "general"),
                    evidence=fd.get("evidence", []),
                )
            )
        return built

    def _reflect(self) -> None:
        """One bounded self-review pass: the agent critiques its own draft
        findings against its own stated rules (the same SYSTEM_PROMPTS
        persona it was given) and may revise, drop, or add findings —
        before this result is ever returned to the supervisor.

        Never loops (a single critique-and-revise call, not another
        multi-step react loop) and never destructive: any failure to call
        the LLM, or a response that doesn't parse into a usable findings
        list, leaves the original draft findings completely untouched.
        Opt-in only (ReActAgent.run(..., reflect=True)) — off by default,
        so no existing caller's behavior changes.
        """
        system_prompt = SYSTEM_PROMPTS.get(self.prompt_key, "")
        draft = [{"title": f.title, "description": f.description, "severity": f.severity.value, "category": f.category, "evidence": f.evidence} for f in self._findings]
        critique_prompt = (
            f"{system_prompt}\n\n"
            "You previously produced the draft findings below during your analysis of this submission. "
            "Review them critically against your own rules above: is every finding actually supported by "
            "data you gathered, not inferred or guessed? Is each severity justified by the evidence? Are "
            "there duplicate or contradictory findings?\n\n"
            f"Your draft findings:\n{json.dumps(draft, default=str)}\n\n"
            'Respond in JSON: {"findings": [...], "summary": "..."}. Return the SAME findings unchanged '
            "if they are already correct — only change what genuinely needs fixing (revise wording, drop "
            "an unsupported finding, adjust a severity, or add one you missed).\n"
            "Do not add markdown formatting. Return ONLY valid JSON."
        )

        try:
            raw = self.llm.complete("You are an AI assistant that critically reviews its own prior work for accuracy before finalizing it.", critique_prompt)
        except Exception:
            logger.debug("%s: reflection pass failed — keeping original draft findings", self.agent_name, exc_info=True)
            return

        # A genuine "findings: []" (the model deliberately clearing the
        # draft) must be trusted; a response that didn't parse at all must
        # not be silently treated the same way — hence _try_parse_json, not
        # _parse_llm_output's own final_answer/empty-findings fallback.
        parsed = self._try_parse_json(raw)
        if parsed is None:
            logger.debug("%s: reflection response could not be parsed — keeping original draft findings", self.agent_name)
            return

        revised_data = parsed.get("findings")
        if not isinstance(revised_data, list):
            logger.debug("%s: reflection returned no usable findings list — keeping original draft", self.agent_name)
            return

        original_signature = {(f.title, f.severity.value, f.description) for f in self._findings}
        revised_findings = self._build_findings(revised_data)
        self._findings = []
        for finding in revised_findings:
            self._add_finding(finding)
        revised_signature = {(f.title, f.severity.value, f.description) for f in self._findings}
        if revised_signature != original_signature:
            self._reflection_note = f"Reflection revised the draft findings ({len(original_signature)} -> {len(revised_signature)})"

    def _build_summary(self) -> str:
        base = super()._build_summary()
        if getattr(self, "_reflection_note", ""):
            return f"{base} ({self._reflection_note})"
        return base

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        pass
