"""Pytest wrapper for E2E suite (in-process)."""

from __future__ import annotations

import pytest

from insureflow.e2e.runner import run_inprocess


@pytest.mark.e2e
def test_e2e_inprocess_fast(monkeypatch) -> None:
    # Bind requires ready mode + a policy-admin credential; the ISO adapter then
    # falls back to a simulated bind when the live endpoint is unreachable. This
    # makes the E2E bind flow deterministic in clean CI environments.
    monkeypatch.setenv("OPERATING_MODE", "ready")
    monkeypatch.setenv("PILOT_SHADOW_MODE", "false")
    monkeypatch.setenv("GUIDEWIRE_API_KEY", "ci-e2e-guidewire-key")
    monkeypatch.setenv("GUIDEWIRE_API_URL", "http://127.0.0.1:9/integrations/policy/guidewire/v1")

    report = run_inprocess(test_connectors=False, use_llm=False, job_timeout=120)
    failures = [r for r in report["results"] if not r["passed"]]
    assert report["success"], f"E2E failures: {[f['name'] + ': ' + f['detail'] for f in failures]}"
