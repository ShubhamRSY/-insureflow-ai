"""Producer decision notifications — Step 5a of the underwriting process.

Contact the producer (and others involved) with the decision, good or
bad. If the decision is to accept the submission with modifications, the
reasons must be clearly communicated and the applicant must agree to the
modifications. If the submission is rejected, a clear and logical reason
must be communicated.

This store keeps a durable, auditable log of every decision communicated
to the producer and tracks acknowledgement back from the broker.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from insureflow.audit.store import AuditStore


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class ProducerNotificationStore:
    """Persist UW→producer decision communications on the audit bundle."""

    FILE = "producer_notifications.json"

    def __init__(self, audit_store: AuditStore | None = None) -> None:
        self.audit = audit_store or AuditStore()

    def _load(self, bundle_id: str, org_id: str) -> list[dict[str, Any]]:
        raw = self.audit.load_json(bundle_id, self.FILE, org_id=org_id)
        if isinstance(raw, dict):
            items = raw.get("items")
            return list(items) if isinstance(items, list) else []
        if isinstance(raw, list):
            return list(raw)
        return []

    def _save(self, bundle_id: str, org_id: str, items: list[dict[str, Any]]) -> None:
        self.audit.save_json(bundle_id, self.FILE, {"items": items}, org_id=org_id)

    def notify(
        self,
        bundle_id: str,
        org_id: str,
        *,
        kind: str,
        decision: str,
        message: str,
        producer_name: str = "",
        channel: str = "log",
    ) -> dict[str, Any]:
        """Record a decision communication sent to the producer."""
        items = self._load(bundle_id, org_id)
        notification = {
            "notification_id": f"notif-{uuid4().hex[:10]}",
            "bundle_id": bundle_id,
            "org_id": org_id,
            "kind": kind,
            "decision": decision,
            "message": message[:2000],
            "producer_name": producer_name,
            "channel": channel,
            "status": "sent",
            "created_at": _now(),
            "acknowledged_by": "",
            "acknowledged_at": "",
            "read_at": "",
        }
        items.append(notification)
        self._save(bundle_id, org_id, items)
        return notification

    def list_notifications(self, bundle_id: str, org_id: str) -> list[dict[str, Any]]:
        items = self._load(bundle_id, org_id)
        return sorted(items, key=lambda n: n.get("created_at", ""), reverse=True)

    def list_all(self, org_id: str) -> list[dict[str, Any]]:
        """Every decision communication logged for an org, newest first."""
        base = self.audit.base_path / org_id
        if not base.is_dir():
            return []
        items: list[dict[str, Any]] = []
        for bundle_dir in sorted(base.iterdir()):
            if not bundle_dir.is_dir():
                continue
            raw = self.audit.load_json(bundle_dir.name, self.FILE, org_id=org_id)
            if isinstance(raw, dict):
                chunk = raw.get("items")
            elif isinstance(raw, list):
                chunk = raw
            else:
                continue
            for item in chunk or []:
                if isinstance(item, dict):
                    item["bundle_id"] = item.get("bundle_id") or bundle_dir.name
                    items.append(item)
        items.sort(key=lambda n: n.get("created_at", ""), reverse=True)
        return items

    def mark_acknowledged(
        self,
        bundle_id: str,
        org_id: str,
        notification_id: str,
        acknowledged_by: str = "broker",
    ) -> dict[str, Any]:
        items = self._load(bundle_id, org_id)
        for item in items:
            if item.get("notification_id") == notification_id:
                item["status"] = "acknowledged"
                item["acknowledged_by"] = acknowledged_by or "broker"
                item["acknowledged_at"] = _now()
                self._save(bundle_id, org_id, items)
                return item
        raise ValueError(f"No notification matching {notification_id}")

    def mark_read(self, bundle_id: str, org_id: str, notification_id: str) -> dict[str, Any]:
        items = self._load(bundle_id, org_id)
        for item in items:
            if item.get("notification_id") == notification_id:
                item["read_at"] = item.get("read_at") or _now()
                self._save(bundle_id, org_id, items)
                return item
        raise ValueError(f"No notification matching {notification_id}")


class ProducerNotificationService:
    """Decision-communication logic wired into sign-off and bind."""

    def __init__(self, store: ProducerNotificationStore | None = None) -> None:
        self.store = store or ProducerNotificationStore()

    def notify_decision(
        self,
        bundle_id: str,
        org_id: str,
        *,
        decision: str,
        action: str,
        signed_by: str,
        reason: str = "",
        producer_name: str = "",
    ) -> dict[str, Any]:
        """Send the sign-off outcome to the producer (good or bad)."""
        decision_label = decision.upper()
        message_parts: list[str] = []
        if action == "approve":
            message_parts.append(f"Your submission {bundle_id} has been APPROVED by underwriter {signed_by}. Coverage may now be bound.")
        elif action == "decline":
            message_parts.append(f"Your submission {bundle_id} was DECLINED ({decision_label}).")
        elif action == "request_info":
            message_parts.append(f"Additional underwriting information is required for {bundle_id} to proceed.")
        elif action == "refer":
            message_parts.append(f"Submission {bundle_id} was referred for senior underwriting review.")
        else:
            message_parts.append(f"Decision on submission {bundle_id}: {decision_label}.")
        if reason:
            message_parts.append(f"Reason: {reason}")
        message = " ".join(message_parts)

        return self.store.notify(
            bundle_id,
            org_id,
            kind="uw_decision",
            decision=decision,
            message=message,
            producer_name=producer_name,
            channel="log",
        )

    def notify_bound(
        self,
        bundle_id: str,
        org_id: str,
        *,
        policy_number: str,
        bound_by: str,
        premium: float,
        producer_name: str = "",
    ) -> dict[str, Any]:
        message = (
            f"Coverage for submission {bundle_id} is now in force. Policy number {policy_number} bound by {bound_by} "
            f"at ${float(premium or 0):,.2f} annual premium. Binder and certificate of insurance are available."
        )
        return self.store.notify(
            bundle_id,
            org_id,
            kind="bind",
            decision="bound",
            message=message,
            producer_name=producer_name,
            channel="log",
        )


def get_producer_notification_service() -> ProducerNotificationService:
    return ProducerNotificationService()
