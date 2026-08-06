"""Producer decision notification tests — Step 5a."""

from __future__ import annotations

import pytest

from insureflow.audit.store import AuditStore
from insureflow.insurance.notifications import (
    ProducerNotificationService,
    ProducerNotificationStore,
)


@pytest.fixture()
def store(tmp_path) -> ProducerNotificationStore:
    return ProducerNotificationStore(audit_store=AuditStore(base_path=tmp_path / "audit"))


class TestProducerNotificationStore:
    def test_notify_and_list(self, store: ProducerNotificationStore) -> None:
        n = store.notify(
            "ins-1",
            "default",
            kind="uw_decision",
            decision="decline",
            message="Submission ins-1 was declined.",
            producer_name="Acme Brokerage",
        )
        assert n["notification_id"].startswith("notif-")
        assert n["status"] == "sent"
        assert n["producer_name"] == "Acme Brokerage"

        items = store.list_notifications("ins-1", "default")
        assert len(items) == 1
        assert items[0]["decision"] == "decline"

    def test_mark_acknowledged(self, store: ProducerNotificationStore) -> None:
        n = store.notify("ins-1", "default", kind="bind", decision="bound", message="In force.")
        updated = store.mark_acknowledged("ins-1", "default", n["notification_id"], acknowledged_by="broker@acme")
        assert updated["status"] == "acknowledged"
        assert updated["acknowledged_by"] == "broker@acme"
        assert updated["acknowledged_at"]

    def test_acknowledge_unknown_raises(self, store: ProducerNotificationStore) -> None:
        with pytest.raises(ValueError, match="No notification matching"):
            store.mark_acknowledged("ins-1", "default", "notif-nope")

    def test_notifications_are_org_scoped(self, store: ProducerNotificationStore) -> None:
        store.notify("ins-1", "org-a", kind="uw_decision", decision="accept", message="ok")
        assert store.list_notifications("ins-1", "org-b") == []

    def test_list_all_spans_bundles_and_is_org_scoped(self, store: ProducerNotificationStore) -> None:
        store.notify("ins-1", "default", kind="uw_decision", decision="accept", message="first")
        store.notify("ins-2", "default", kind="bind", decision="bound", message="second")
        store.notify("ins-3", "org-x", kind="uw_decision", decision="decline", message="other org")
        all_items = store.list_all("default")
        assert len(all_items) == 2
        assert {n["bundle_id"] for n in all_items} == {"ins-1", "ins-2"}
        assert all_items[0]["created_at"] >= all_items[1]["created_at"]
        assert store.list_all("org-unknown") == []


class TestProducerNotificationService:
    def test_notify_decision_approve(self, tmp_path) -> None:
        svc = ProducerNotificationService(
            store=ProducerNotificationStore(audit_store=AuditStore(base_path=tmp_path / "audit"))
        )
        n = svc.notify_decision(
            "ins-1",
            "default",
            decision="accept",
            action="approve",
            signed_by="sfields",
            producer_name="Acme Brokerage",
        )
        assert n["kind"] == "uw_decision"
        assert "APPROVED" in n["message"]
        assert "sfields" in n["message"]

    def test_notify_decision_decline_carries_reason(self, tmp_path) -> None:
        svc = ProducerNotificationService(
            store=ProducerNotificationStore(audit_store=AuditStore(base_path=tmp_path / "audit"))
        )
        n = svc.notify_decision(
            "ins-1",
            "default",
            decision="decline",
            action="decline",
            signed_by="sfields",
            reason="Claim frequency 12/yr exceeds threshold",
            producer_name="Acme Brokerage",
        )
        assert "DECLINED" in n["message"]
        assert "Claim frequency 12/yr exceeds threshold" in n["message"]

    def test_notify_bound_includes_policy_number(self, tmp_path) -> None:
        svc = ProducerNotificationService(
            store=ProducerNotificationStore(audit_store=AuditStore(base_path=tmp_path / "audit"))
        )
        n = svc.notify_bound(
            "ins-1",
            "default",
            policy_number="POL-42",
            bound_by="sfields",
            premium=10_000.0,
            producer_name="Acme Brokerage",
        )
        assert n["kind"] == "bind"
        assert "POL-42" in n["message"]
        assert "$10,000.00" in n["message"]
