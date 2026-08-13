"""AI natural-language workflow drafting.

Deterministic compiler first (ZTA): parse a UW desk instruction into a
structured step graph. Optionally enrich with an LLM when available — never
required. This does **not** mutate WorkflowService sign-off state.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from pydantic import BaseModel, Field

_STEP_SPLIT = re.compile(r"\s*(?:,|;|\n|then|and then|after that|->|→)\s*", re.IGNORECASE)
_IF = re.compile(
    r"\bif\s+(.+?)\s+then\s+(.+?)(?:\.|$)",
    re.IGNORECASE | re.DOTALL,
)
_WHEN = re.compile(r"\bwhen\s+(.+?)(?:,|\n|then|\.|$)", re.IGNORECASE)
_COMPARE = re.compile(
    r"\b(tiv|premium|limit|revenue|employees|loss[_\s-]?ratio|credit[_\s-]?score)\s*"
    r"(>=|<=|>|<|==|is at least|is over|exceeds|above|below|under)\s*"
    r"\$?([\d,.]+)(m|mm|k|b)?",
    re.IGNORECASE,
)

_ACTION_VERBS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(extract|parse|ingest)\b", re.I), "extract"),
    (re.compile(r"\b(run clue|clue|a-?plus|loss history)\b", re.I), "run_oracle"),
    (re.compile(r"\b(ncci|experience mod)\b", re.I), "run_oracle"),
    (re.compile(r"\b(screen|sanctions|ofac|kyc|aml)\b", re.I), "sanctions_screen"),
    (re.compile(r"\b(categorize|bank statement|cash[- ]flow|ach)\b", re.I), "banking_analyze"),
    (re.compile(r"\b(price|rate|quote)\b", re.I), "price"),
    (re.compile(r"\b(bind)\b", re.I), "bind"),
    (re.compile(r"\b(co-?sign|cosign)\b", re.I), "require_cosign"),
    (re.compile(r"\b(refer|escalate|send to uw|underwriter review)\b", re.I), "refer"),
    (re.compile(r"\b(decline|reject)\b", re.I), "decline"),
    (re.compile(r"\b(accept|approve)\b", re.I), "approve"),
    (re.compile(r"\b(notify|email|alert)\b", re.I), "notify"),
    (re.compile(r"\b(sar|file sar|suspicious activity)\b", re.I), "file_sar"),
    (re.compile(r"\b(fingerprint|device intelligence|spoof)\b", re.I), "device_assess"),
    (re.compile(r"\b(behavioral|keystroke|biometrics)\b", re.I), "session_assess"),
    (re.compile(r"\b(genai|ai generated|prompt injection)\b", re.I), "genai_assess"),
]


class DraftStep(BaseModel):
    step_id: str
    action: str
    title: str
    target: str = ""
    condition: str = ""
    on_true: str = ""
    on_false: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowDraft(BaseModel):
    draft_id: str
    title: str
    description: str
    source_prompt: str
    triggers: list[str] = Field(default_factory=list)
    steps: list[DraftStep] = Field(default_factory=list)
    compiled: dict[str, Any] = Field(default_factory=dict)
    engine: str = "deterministic_nl"


def _magnitude(num: str, suffix: str) -> float:
    value = float(num.replace(",", ""))
    s = suffix.lower()
    if s in {"m", "mm"}:
        return value * 1_000_000
    if s == "k":
        return value * 1_000
    if s == "b":
        return value * 1_000_000_000
    return value


def _op(raw: str) -> str:
    r = raw.lower().strip()
    if r in {">", "is over", "exceeds", "above"}:
        return ">"
    if r in {">=", "is at least"}:
        return ">="
    if r in {"<", "below", "under"}:
        return "<"
    if r == "<=":
        return "<="
    return "=="


def _detect_action(text: str) -> tuple[str, str]:
    for pattern, action in _ACTION_VERBS:
        if pattern.search(text):
            return action, text.strip().rstrip(".")
    cleaned = text.strip().rstrip(".")
    return "custom", cleaned or "step"


def _title_from_prompt(prompt: str) -> str:
    first = prompt.strip().split("\n", 1)[0].strip().rstrip(".")
    if len(first) > 80:
        first = first[:77] + "..."
    return first or "Untitled workflow"


class WorkflowDrafter:
    """Compile a natural-language UW instruction into a WorkflowDraft."""

    def draft(self, prompt: str, *, title: str = "") -> WorkflowDraft:
        text = (prompt or "").strip()
        if not text:
            raise ValueError("prompt is required")

        triggers = [m.group(1).strip().rstrip(".,") for m in _WHEN.finditer(text)]
        steps: list[DraftStep] = []

        for match in _IF.finditer(text):
            cond_raw = match.group(1).strip()
            then_raw = match.group(2).strip()
            action, title_txt = _detect_action(then_raw)
            cmp_m = _COMPARE.search(cond_raw)
            condition = cond_raw
            meta: dict[str, Any] = {}
            if cmp_m:
                field, op_raw, num, suffix = cmp_m.group(1), cmp_m.group(2), cmp_m.group(3), cmp_m.group(4) or ""
                field_key = re.sub(r"[\s-]+", "_", field.lower())
                condition = f"{field_key} {_op(op_raw)} {_magnitude(num, suffix):.0f}"
                meta = {"field": field_key, "op": _op(op_raw), "value": _magnitude(num, suffix)}
            sid = f"s{len(steps) + 1}"
            steps.append(
                DraftStep(
                    step_id=sid,
                    action=action,
                    title=title_txt[:120],
                    condition=condition,
                    metadata=meta,
                )
            )

        # Sequential imperative clauses that aren't already captured as then-clauses.
        then_blobs = {m.group(2).strip().lower() for m in _IF.finditer(text)}
        remainder = _IF.sub(" ", text)
        remainder = _WHEN.sub(" ", remainder)
        for chunk in _STEP_SPLIT.split(remainder):
            chunk = chunk.strip(" .,-")
            if len(chunk) < 4:
                continue
            if chunk.lower() in then_blobs:
                continue
            if chunk.lower().startswith("if "):
                continue
            action, title_txt = _detect_action(chunk)
            if action == "custom" and not re.search(r"\b(extract|run|screen|price|quote|bind|refer|notify|file|assess)\b", chunk, re.I):
                continue
            sid = f"s{len(steps) + 1}"
            steps.append(DraftStep(step_id=sid, action=action, title=title_txt[:120], target=chunk[:160]))

        if not steps:
            steps.append(
                DraftStep(
                    step_id="s1",
                    action="custom",
                    title=text[:120],
                    target=text[:200],
                )
            )

        for i, step in enumerate(steps[:-1]):
            if not step.on_true:
                step.on_true = steps[i + 1].step_id

        compiled = {
            "entry": steps[0].step_id,
            "steps": [s.model_dump() for s in steps],
            "triggers": triggers,
        }
        return WorkflowDraft(
            draft_id=f"WD-{uuid.uuid4().hex[:10].upper()}",
            title=title or _title_from_prompt(text),
            description=text[:400],
            source_prompt=text,
            triggers=triggers,
            steps=steps,
            compiled=compiled,
        )


def draft_workflow(prompt: str, *, title: str = "") -> WorkflowDraft:
    return WorkflowDrafter().draft(prompt, title=title)
