"""Broker status shares must survive process/worker restarts via job_store."""

from __future__ import annotations

from pathlib import Path

from insureflow.webhooks.dispatcher import WebhookDispatcher


def test_broker_share_persists_across_dispatcher_instances(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("JOB_STORE_BACKEND", "file")
    monkeypatch.setenv("JOB_STORE_PATH", str(tmp_path / "jobs"))

    a = WebhookDispatcher()
    a._broker_shares.clear()
    token = a.create_broker_share(bundle_id="job-abc", org_id="org-1", broker_name="Acme Broker")
    assert token.startswith("brk-")
    assert a.get_broker_share(token) is not None

    # Simulate another worker: empty memory, same durable store
    b = WebhookDispatcher()
    b._broker_shares.clear()
    share = b.get_broker_share(token)
    assert share is not None
    assert share.bundle_id == "job-abc"
    assert share.org_id == "org-1"
    assert share.broker_name == "Acme Broker"
