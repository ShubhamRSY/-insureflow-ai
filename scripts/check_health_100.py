#!/usr/bin/env python3
"""Quick local health check without importing the full API stack."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insureflow.health.diagnostics import SystemDiagnostics  # noqa: E402

report = SystemDiagnostics(project_root=ROOT).run_all()
print(json.dumps({"overall": report["overall"], "summary": report["summary"], "llm_mode": report["llm_mode"]}, indent=2))
for c in report["checks"]:
    print(f"{c['status']:8} {c['component']:22} {c['message']}")
sys.exit(0 if report["overall"] == "healthy" and report["summary"]["ok"] == report["summary"]["total"] else 1)
