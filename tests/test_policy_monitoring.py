"""Ongoing policy monitoring tests — Step 6."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from insureflow.audit.store import AuditStore
from insureflow.monitoring.engine import MonitoringEngine
from insureflow.monitoring.models import MonitoringItemStatus, MonitoringSeverity, MonitoringSource, PolicyStatus
from insureflow.monitoring.store import MonitoringStore


@pytest.fixture()
def engine(tmp_path) -> MonitoringEngine:
    store = MonitoringStore(base_path=tmp_path / "monitoring")
    audit = AuditStore(base_path=tmp_path / "audit")
    return MonitoringEngine(store=store, audit_store=audit)


@pytest.fixture()
def seeded(engine: MonitoringEngine) -> str:
    """Seed a monitored policy with two UW-memo monitoring items."""
    audit = engine.audit
    audit.save_json(
        "ins-mon-1",
        "underwriting_memo.json",
        {
            "bundle_id": "ins-mon-1",
            "insured_name": "Bayfront Retail LLC",
            "key_findings": [
                {
                    "title": "Roof age not verified",
                    "description": "Verify roof age before renewal",
                    "severity": "moderate",
                    "category": "data_quality",
                },
                {
                    "title": "No security alarm monitored",
                    "description": "Install monitored alarm",
                    "severity": "low",
                    "category": "loss_control",
                },
                {
                    "title": "Critical claim frequency",
                    "description": "Blocking finding — should not be carried as monitoring item",
                    "severity": "critical",
                    "category": "frequency",
                },
            ],
        },
        org_id="default",
    )
    audit.save_json(
        "ins-mon-1",
        "pipeline_summary.json",
        {
            "bundle_id": "ins-mon-1",
            "insured_name": "Bayfront Retail LLC",
            "tiv": 4_500_000,
            "insurance_line": "commercial_property",
            "quote": {"adjusted_premium": 22_500.0},
        },
        org_id="default",
    )
    expiry = (datetime.now().date() + timedelta(days=30)).isoformat()
    record = engine.seed_from_issuance(
        "ins-mon-1",
        "default",
        policy_id="pol-mon-1",
        policy_number="POL-77",
        insured_name="Bayfront Retail LLC",
        line_of_business="commercial_property",
        premium=22_500.0,
        tiv=4_500_000,
        effective_date=(datetime.now().date() - timedelta(days=100)).isoformat(),
        expiry_date=expiry,
    )
    assert record.policy_id == "pol-mon-1"
    return record.policy_id


class TestMonitoringEngine:
    def test_seed_carries_only_low_moderate_memo_items(self, seeded: str, engine: MonitoringEngine) -> None:
        record = engine.store.get(seeded, "default")
        assert record is not None
        assert len(record.items) == 2
        assert all(i.source == MonitoringSource.UW_MEMO for i in record.items)
        assert all(i.severity in (MonitoringSeverity.MODERATE, MonitoringSeverity.LOW) for i in record.items)
        assert record.status == PolicyStatus.MONITORED
        assert record.open_item_count == 2

    def test_loss_development_watch_and_critical(self, seeded: str, engine: MonitoringEngine) -> None:
        record = engine.record_loss_development(
            seeded,
            "default",
            earned_premium=22_500.0,
            incurred_losses=18_000.0,
            claim_count=6,
        )
        assert record.latest_loss_ratio == pytest.approx(18_000 / 22_500, rel=1e-3)
        assert record.status == PolicyStatus.WATCH
        assert any(a.severity == MonitoringSeverity.HIGH for a in record.alerts)

        record = engine.record_loss_development(
            seeded,
            "default",
            earned_premium=22_500.0,
            incurred_losses=25_000.0,
            claim_count=9,
        )
        assert record.latest_loss_ratio > 0.90
        assert any(a.severity == MonitoringSeverity.CRITICAL for a in record.alerts)
        assert record.open_alert_count >= 2

    def test_add_and_resolve_item(self, seeded: str, engine: MonitoringEngine) -> None:
        record = engine.add_item(
            seeded,
            "default",
            title="Implement fire suppression upgrade",
            description="Install sprinklers by renewal",
            severity="high",
            source="loss_control",
        )
        assert record.open_item_count == 3

        item_id = record.items[-1].item_id
        record = engine.resolve_item(
            seeded,
            "default",
            item_id,
            status="cleared",
            resolved_by="sfields",
            note="Sprinkler inspection passed",
        )
        resolved = next(i for i in record.items if i.item_id == item_id)
        assert resolved.status == MonitoringItemStatus.CLEARED
        assert resolved.resolved_by == "sfields"
        assert "Sprinkler inspection passed" in resolved.notes

    def test_evaluate_flags_overdue_items_and_renewal(self, seeded: str, engine: MonitoringEngine) -> None:
        record = engine.store.get(seeded, "default")
        assert record is not None
        # Force an overdue due date
        record.items[0].due_by = (date.today() - timedelta(days=200)).isoformat()
        engine.store.save(record)

        record = engine.evaluate(seeded, "default")
        titles = [a.title for a in record.alerts]
        assert any("overdue" in t.lower() for t in titles)
        # 30-day expiry is inside the 120-day renewal window
        assert any("renewal" in t.lower() for t in titles)
        assert record.status == PolicyStatus.MONITORED

    def test_list_open_alerts_and_summary(self, seeded: str, engine: MonitoringEngine) -> None:
        engine.record_loss_development(seeded, "default", earned_premium=10_000, incurred_losses=8_000)
        engine.evaluate_all("default")
        alerts = engine.list_open_alerts("default")
        assert len(alerts) >= 1
        assert all(a["policy_id"] == seeded for a in alerts)

        rows = engine.list_monitoring("default")
        assert len(rows) == 1
        assert rows[0]["policy_number"] == "POL-77"
        assert rows[0]["open_item_count"] == 2

    def test_unknown_policy_raises(self, engine: MonitoringEngine) -> None:
        with pytest.raises(ValueError, match="No policy monitoring record"):
            engine.add_item("pol-nope", "default", title="x")
        with pytest.raises(ValueError, match="No policy monitoring record"):
            engine.evaluate("pol-nope", "default")
