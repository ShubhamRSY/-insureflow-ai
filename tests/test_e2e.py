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

    # This suite runs with test_connectors=False / use_llm=False specifically so
    # it never depends on live external connectivity. GET /health independently
    # pings any CLUE/NCCI/CAT oracle whose API key happens to be set in the
    # ambient environment (e.g. a developer's local .env with dev keys pointing
    # at endpoints nobody is running right now) and reports "degraded" if one is
    # unreachable — correct behavior for the real endpoint, but it breaks this
    # test's own determinism goal unless those oracles are explicitly
    # unconfigured here too, the same way GUIDEWIRE is explicitly configured.
    for oracle in ("CLUE", "NCCI", "CAT", "A-PLUS"):
        monkeypatch.delenv(f"{oracle}_API_KEY", raising=False)
        monkeypatch.delenv(f"{oracle}_API_URL", raising=False)

    report = run_inprocess(test_connectors=False, use_llm=False, job_timeout=120)
    failures = [r for r in report["results"] if not r["passed"]]
    assert report["success"], f"E2E failures: {[f['name'] + ': ' + f['detail'] for f in failures]}"
