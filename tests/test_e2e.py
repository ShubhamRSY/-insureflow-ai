"""Pytest wrapper for E2E suite (in-process)."""

from __future__ import annotations

import pytest

from insureflow.e2e.runner import run_inprocess


@pytest.mark.e2e
def test_e2e_inprocess_fast() -> None:
    report = run_inprocess(test_connectors=False, use_llm=False, job_timeout=120)
    failures = [r for r in report["results"] if not r["passed"]]
    assert report["success"], f"E2E failures: {[f['name'] + ': ' + f['detail'] for f in failures]}"
