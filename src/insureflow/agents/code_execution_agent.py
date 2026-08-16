"""Programmatic-generative hybrid execution (technique #6).

For documents a generic parser can't handle (odd embedded tables, zip-of-mixed-
files), the agent writes a small Python script to parse the artifact, runs it in
an isolated subprocess, checks the output, and — if the result doesn't align —
feeds the traceback back to the model to fix its own code, up to ``max_attempts``.

Trust boundary: the generated code executes locally, so this is OFF by default
and must be explicitly enabled with ``ALLOW_CODE_EXECUTION=true``. The script
runs in a scratch directory with a sanitized environment (secrets/proxies
stripped), a timeout, and a static deny-list scan for network/system escape.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DENIED_PATTERNS = (
    re.compile(r"\bos\.system\b"),
    re.compile(r"\bsubprocess\b"),
    re.compile(r"\b__import__\b"),
    re.compile(r"\bimportlib\b"),
    re.compile(r"\bsocket\b"),
    re.compile(r"\brequests\b"),
    re.compile(r"\burlopen\b"),
    re.compile(r"\bftp\b"),
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"\bos\.remove\b|\bos\.unlink\b"),
)

_GENERATE_PROMPT = (
    "You generate Python to parse messy document artifacts for insurance "
    "underwriting. Write a single self-contained Python script that reads the "
    "input file at sys.argv[1] and prints a JSON object of extracted fields "
    "to stdout. The keys must be snake_case field names and values strings. "
    "Handle the file robustly (wrong encoding, embedded tables, header rows). "
    "Do not use network access, subprocess, or eval. Print only the JSON.\n"
    "INSTRUCTIONS: {instructions}\n"
    "FILENAME: {filename}\n"
    "PREVIEW:\n{preview}\n"
    "PREVIOUS ERROR (fix this):\n{error}"
)


@dataclass
class CodeExecResult:
    fields: dict[str, str] = field(default_factory=dict)
    script: str = ""
    attempts: int = 0
    error: str = ""


def code_exec_enabled() -> bool:
    return os.getenv("ALLOW_CODE_EXECUTION", "").strip().lower() in {"1", "true", "yes", "on"}


def _sanitized_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if any(marker in upper for marker in ("KEY", "SECRET", "TOKEN", "PASSWORD", "PROXY", "AWS_", "GCP_", "AZURE_")):
            continue
        env[key] = value
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _scan_script(script: str) -> str | None:
    for pattern in _DENIED_PATTERNS:
        if pattern.search(script):
            return f"generated script uses forbidden construct {pattern.pattern}"
    return None


def _execute_script(script: str, input_path: str, cwd: str, timeout: int) -> tuple[str, str, int]:
    script_path = Path(cwd) / "agent_code.py"
    script_path.write_text(script, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(script_path), input_path],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_sanitized_env(),
    )
    return proc.stdout, proc.stderr, proc.returncode


def _parse_output(stdout: str) -> dict[str, str] | None:
    cleaned = stdout.strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    return {str(k): str(v) for k, v in parsed.items() if v is not None}


class CodeExecutionAgent:
    def __init__(self, llm: Any = None, max_attempts: int = 3, timeout: int = 30) -> None:
        self.llm = llm
        self.max_attempts = max_attempts
        self.timeout = timeout

    def parse_document(self, file_bytes: bytes, filename: str, instructions: str = "") -> CodeExecResult | None:
        if not code_exec_enabled():
            return None
        if self.llm is None or not getattr(self.llm, "api_key", None):
            return CodeExecResult(error="code execution enabled but no LLM available")
        preview = file_bytes[:4000].decode("utf-8", errors="replace")
        error_hint = "none"
        for attempt in range(1, self.max_attempts + 1):
            script = self._generate_script(filename, preview, instructions, error_hint)
            if not script:
                return CodeExecResult(attempts=attempt, error="LLM produced no script")
            blocked = _scan_script(script)
            if blocked:
                error_hint = blocked
                continue
            with tempfile.TemporaryDirectory() as cwd:
                input_path = str(Path(cwd) / filename)
                Path(input_path).write_bytes(file_bytes)
                try:
                    stdout, stderr, code = _execute_script(script, input_path, cwd, self.timeout)
                except subprocess.TimeoutExpired:
                    error_hint = "script timed out"
                    continue
                except Exception as exc:  # pragma: no cover - defensive
                    error_hint = str(exc)
                    continue
            fields = _parse_output(stdout)
            if fields:
                return CodeExecResult(fields=fields, script=script, attempts=attempt)
            error_hint = (stderr or stdout or "no JSON on stdout").strip()[:1500]
            logger.debug("code-exec attempt %d failed: %s", attempt, error_hint)
        return CodeExecResult(error=f"gave up after {self.max_attempts} attempts: {error_hint}", attempts=self.max_attempts)

    def _generate_script(self, filename: str, preview: str, instructions: str, error: str) -> str:
        prompt = _GENERATE_PROMPT.format(
            instructions=instructions or "Extract the underwriting-relevant fields.",
            filename=filename,
            preview=preview,
            error=error or "none",
        )
        try:
            raw = self.llm.complete(prompt)
        except Exception as exc:
            logger.warning("script generation failed: %s", exc)
            return ""
        script = raw.strip()
        if script.startswith("```python"):
            script = script[len("```python") :]
        elif script.startswith("```"):
            script = script[3:]
        if script.endswith("```"):
            script = script[:-3]
        return script.strip()
