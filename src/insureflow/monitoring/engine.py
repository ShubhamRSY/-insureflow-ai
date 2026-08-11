"""Monitoring engine — monitors in-force policies between bind and renewal.

Implements Step 6 of the underwriting process. A policy created at bind
time starts monitoring: moderate/low UW-memo findings that did not block
binding are carried forward as monitoring items, loss development is
tracked against earned premium, and alerts are raised when loss ratios
deteriorate, monitoring items go overdue, or the policy approaches
renewal / expiry.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from insureflow.audit.store import AuditStore
from insureflow.monitoring.models import LossDevelopmentEntry, MonitoringAlert, MonitoringItem, MonitoringItemStatus, MonitoringSeverity, MonitoringSource, PolicyMonitoringRecord, PolicyStatus
from insureflow.monitoring.store import MonitoringStore


class MonitoringEngine:
    """Create, update, and evaluate policy monitoring records."""

    LOSS_RATIO_WATCH = 0.70
    LOSS_RATIO_CRITICAL = 0.90
    OVERDUE_DAYS = 90
    RENEWAL_WINDOW_DAYS = 120

    def __init__(self, store: MonitoringStore | None = None, audit_store: AuditStore | None = None) -> None:
        self.store = store or MonitoringStore()
        self.audit = audit_store or AuditStore()

    def seed_from_issuance(
        self,
        bundle_id: str,
        org_id: str,
        *,
        policy_id: str,
        policy_number: str,
        insured_name: str = "",
        line_of_business: str = "",
        premium: float = 0.0,
        tiv: float = 0.0,
        effective_date: str = "",
        expiry_date: str = "",
    ) -> PolicyMonitoringRecord:
        """Create a monitoring record from a bound policy and carry memo items forward."""
        memo = self.audit.load_json(bundle_id, "underwriting_memo.json", org_id=org_id) or {}
        summary = self.audit.load_json(bundle_id, "pipeline_summary.json", org_id=org_id) or {}
        quote = summary.get("quote") or {}

        items: list[MonitoringItem] = []
        for f in memo.get("key_findings") or []:
            if not isinstance(f, dict):
                continue
            severity = _severity_from_str(f.get("severity"))
            if severity not in (MonitoringSeverity.MODERATE, MonitoringSeverity.LOW):
                continue
            items.append(
                MonitoringItem(
                    item_id=f"mi-{uuid4().hex[:10]}",
                    policy_id=policy_id,
                    bundle_id=bundle_id,
                    org_id=org_id,
                    title=f.get("title") or "Monitoring item",
                    description=f.get("description") or "",
                    severity=severity,
                    source=MonitoringSource.UW_MEMO,
                    status=MonitoringItemStatus.MONITORING,
                    due_by=_default_due(severity),
                )
            )

        record = PolicyMonitoringRecord(
            policy_id=policy_id,
            bundle_id=bundle_id,
            org_id=org_id,
            policy_number=policy_number,
            insured_name=insured_name or summary.get("insured_name") or memo.get("insured_name") or "",
            line_of_business=line_of_business or summary.get("insurance_line") or "",
            premium=float(premium or quote.get("adjusted_premium") or 0),
            tiv=float(tiv or summary.get("tiv") or 0),
            effective_date=effective_date,
            expiry_date=expiry_date,
            items=items,
            status=PolicyStatus.MONITORED if items else PolicyStatus.ACTIVE,
        )
        self.store.save(record)
        return record

    def add_item(
        self,
        policy_id: str,
        org_id: str,
        *,
        title: str,
        description: str = "",
        severity: str = "moderate",
        source: str = "manual",
        due_by: str = "",
        bundle_id: str = "",
    ) -> PolicyMonitoringRecord:
        record = self._require(policy_id, org_id)
        record.items.append(
            MonitoringItem(
                item_id=f"mi-{uuid4().hex[:10]}",
                policy_id=policy_id,
                bundle_id=bundle_id or record.bundle_id,
                org_id=org_id,
                title=title,
                description=description,
                severity=_severity_from_str(severity),
                source=_source_from_str(source),
                status=MonitoringItemStatus.OPEN,
                due_by=due_by or _default_due(_severity_from_str(severity)),
            )
        )
        if record.status == PolicyStatus.ACTIVE:
            record.status = PolicyStatus.MONITORED
        self.store.save(record)
        return record

    def resolve_item(
        self,
        policy_id: str,
        org_id: str,
        item_id: str,
        *,
        status: str = "cleared",
        resolved_by: str = "",
        note: str = "",
    ) -> PolicyMonitoringRecord:
        record = self._require(policy_id, org_id)
        target_status = MonitoringItemStatus(status if status in (MonitoringItemStatus.CLEARED.value, MonitoringItemStatus.WAIVED.value) else MonitoringItemStatus.CLEARED.value)
        for item in record.items:
            if item.item_id == item_id:
                item.status = target_status
                item.resolved_at = datetime.now(tz=timezone.utc).isoformat()
                item.resolved_by = resolved_by or "underwriter"
                if note:
                    item.notes.append(note)
                break
        else:
            raise ValueError(f"No monitoring item matching {item_id}")
        self.store.save(record)
        return record

    def record_loss_development(
        self,
        policy_id: str,
        org_id: str,
        *,
        policy_year: int = 0,
        earned_premium: float = 0.0,
        incurred_losses: float = 0.0,
        paid_losses: float = 0.0,
        claim_count: int = 0,
        recorded_by: str = "system",
    ) -> PolicyMonitoringRecord:
        record = self._require(policy_id, org_id)
        loss_ratio = (incurred_losses / earned_premium) if earned_premium > 0 else 0.0
        record.loss_development.append(
            LossDevelopmentEntry(
                entry_id=f"ld-{uuid4().hex[:10]}",
                policy_id=policy_id,
                org_id=org_id,
                policy_year=policy_year or datetime.now(tz=timezone.utc).year,
                earned_premium=earned_premium,
                incurred_losses=incurred_losses,
                paid_losses=paid_losses,
                claim_count=claim_count,
                loss_ratio=round(loss_ratio, 4),
                recorded_by=recorded_by,
            )
        )

        if loss_ratio >= self.LOSS_RATIO_CRITICAL:
            record.status = PolicyStatus.WATCH
            record.alerts.append(
                MonitoringAlert(
                    alert_id=f"al-{uuid4().hex[:10]}",
                    policy_id=policy_id,
                    bundle_id=record.bundle_id,
                    org_id=org_id,
                    severity=MonitoringSeverity.CRITICAL,
                    title="Loss ratio critical — underwriting review required",
                    message=(
                        f"Policy {record.policy_number or policy_id} loss ratio is {loss_ratio:.0%} "
                        f"(threshold {self.LOSS_RATIO_CRITICAL:.0%}) with {claim_count} claim(s) in {policy_year or 'current'} year. "
                        "Review the account now; consider non-renewal at next anniversary."
                    ),
                )
            )
        elif loss_ratio >= self.LOSS_RATIO_WATCH:
            if record.status != PolicyStatus.WATCH:
                record.status = PolicyStatus.WATCH
            record.alerts.append(
                MonitoringAlert(
                    alert_id=f"al-{uuid4().hex[:10]}",
                    policy_id=policy_id,
                    bundle_id=record.bundle_id,
                    org_id=org_id,
                    severity=MonitoringSeverity.HIGH,
                    title="Loss ratio deteriorating",
                    message=(f"Policy {record.policy_number or policy_id} loss ratio is {loss_ratio:.0%} (watch threshold {self.LOSS_RATIO_WATCH:.0%}). Monitor account activity closely."),
                )
            )
        elif loss_ratio > 0.0 and record.status == PolicyStatus.WATCH:
            record.status = PolicyStatus.MONITORED

        self.store.save(record)
        return record

    def evaluate(self, policy_id: str, org_id: str = "default") -> PolicyMonitoringRecord:
        """Re-evaluate one policy: overdue items, upcoming renewal, alert resolution."""
        record = self._require(policy_id, org_id)
        today = date.today()

        for item in record.items:
            if item.status not in (MonitoringItemStatus.OPEN, MonitoringItemStatus.MONITORING):
                continue
            if not item.due_by:
                continue
            try:
                due = datetime.fromisoformat(item.due_by).date()
            except (ValueError, TypeError):
                continue
            if (today - due).days > self.OVERDUE_DAYS:
                record.alerts.append(
                    MonitoringAlert(
                        alert_id=f"al-{uuid4().hex[:10]}",
                        policy_id=policy_id,
                        bundle_id=record.bundle_id,
                        org_id=org_id,
                        severity=MonitoringSeverity.HIGH,
                        title="Monitoring item overdue",
                        message=f"Monitoring item '{item.title}' has been open since {item.due_by} ({(today - due).days} days overdue).",
                    )
                )

        if record.expiry_date and record.days_to_expiry >= 0 and record.days_to_expiry <= self.RENEWAL_WINDOW_DAYS:
            record.alerts.append(
                MonitoringAlert(
                    alert_id=f"al-{uuid4().hex[:10]}",
                    policy_id=policy_id,
                    bundle_id=record.bundle_id,
                    org_id=org_id,
                    severity=MonitoringSeverity.MODERATE,
                    title="Policy approaching renewal",
                    message=f"Policy expires in {record.days_to_expiry} day(s) on {record.expiry_date}. Start pre-renewal evaluation.",
                )
            )
            record.status = PolicyStatus.MONITORED

        for alert in record.alerts:
            if not alert.resolved and alert.severity == MonitoringSeverity.HIGH and record.latest_loss_ratio < self.LOSS_RATIO_WATCH:
                alert.resolved = True
                alert.resolved_at = datetime.now(tz=timezone.utc).isoformat()

        self.store.save(record)
        return record

    def evaluate_all(self, org_id: str = "default") -> list[PolicyMonitoringRecord]:
        records = self.store.list(org_id)
        for rec in records:
            try:
                self.evaluate(rec.policy_id, org_id)
            except ValueError:
                continue
        return self.store.list(org_id)

    def list_open_alerts(self, org_id: str = "default") -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for rec in self.store.list(org_id):
            for alert in rec.alerts:
                if not alert.resolved:
                    out.append(
                        {
                            "alert_id": alert.alert_id,
                            "policy_id": rec.policy_id,
                            "policy_number": rec.policy_number,
                            "insured_name": rec.insured_name,
                            "bundle_id": rec.bundle_id,
                            "severity": alert.severity.value,
                            "title": alert.title,
                            "message": alert.message,
                            "created_at": alert.created_at.isoformat(),
                        }
                    )
        return sorted(out, key=lambda a: a["created_at"], reverse=True)

    def list_monitoring(self, org_id: str = "default") -> list[dict[str, Any]]:
        return [r.to_summary_dict() for r in self.store.list(org_id)]

    def _require(self, policy_id: str, org_id: str) -> PolicyMonitoringRecord:
        record = self.store.get(policy_id, org_id)
        if record is None:
            raise ValueError(f"No policy monitoring record for {policy_id} (org={org_id})")
        return record


def _severity_from_str(value: Any) -> MonitoringSeverity:
    raw = str(value or "moderate").lower()
    for sev in MonitoringSeverity:
        if sev.value == raw or raw.startswith(sev.value[:2]):
            return sev
    return MonitoringSeverity.MODERATE


def _source_from_str(value: Any) -> MonitoringSource:
    raw = str(value or "manual").lower().replace(" ", "_")
    for src in MonitoringSource:
        if src.value == raw:
            return src
    return MonitoringSource.MANUAL


def _default_due(severity: MonitoringSeverity) -> str:
    now = datetime.now(tz=timezone.utc)
    days = {MonitoringSeverity.LOW: 365, MonitoringSeverity.MODERATE: 180, MonitoringSeverity.HIGH: 90, MonitoringSeverity.CRITICAL: 30}[severity]
    return (now + timedelta(days=days)).strftime("%Y-%m-%d")
