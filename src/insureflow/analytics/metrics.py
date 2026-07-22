"""Pipeline business metrics — fill rate, override rate, cycle time.

These answer the measurement problem: "It works" isn't a metric.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class FieldFillRecord(BaseModel):
    """Tracks whether a specific field was filled by the AI or left empty."""
    field_name: str
    filled: bool
    confidence: float = 0.0
    source: str = ""
    bundle_id: str = ""
    agent: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class OverrideRecord(BaseModel):
    """Tracks a human override of an AI decision."""
    bundle_id: str
    ai_decision: str
    human_decision: str
    is_override: bool
    override_type: str = ""  # "upgrade", "downgrade", "lateral"
    signed_by: str = ""
    override_reason: str = ""
    org_id: str = "default"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class CycleTimeRecord(BaseModel):
    """Tracks end-to-end pipeline cycle time with stage breakdowns."""
    bundle_id: str
    started_at: datetime
    completed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    total_ms: float = 0.0
    stage_durations: dict[str, float] = Field(default_factory=dict)
    org_id: str = "default"
    status: str = "completed"


# ---------------------------------------------------------------------------
# Fill Rate Tracker
# ---------------------------------------------------------------------------

# Critical fields that MUST be filled for a submission to be complete
CRITICAL_FIELDS = [
    "named_insured",
    "naics_code",
    "state",
    "tiv",
    "effective_date",
    "expiration_date",
    "coverage_type",
    "limit_amount",
    "deductible",
    "premium",
    "construction_type",
    "occupancy_type",
    "year_built",
    "total_claims",
    "total_incurred",
    "broker_name",
]


class FillRateTracker:
    """Tracks field fill rates across pipeline runs."""

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._records: list[FieldFillRecord] = []
        self._persist_path = persist_path or Path(os.getenv("FILL_RATE_PATH", "./audit_logs/metrics/fill_rate.jsonl"))

    def record_field(
        self,
        field_name: str,
        filled: bool,
        confidence: float = 0.0,
        source: str = "",
        bundle_id: str = "",
        agent: str = "",
    ) -> None:
        entry = FieldFillRecord(
            field_name=field_name,
            filled=filled,
            confidence=confidence,
            source=source,
            bundle_id=bundle_id,
            agent=agent,
        )
        with self._lock:
            self._records.append(entry)
            self._persist(entry)

    def record_bundle_fields(
        self,
        bundle_id: str,
        fields: dict[str, Any],
        agent: str = "",
    ) -> None:
        for field_name in CRITICAL_FIELDS:
            value = fields.get(field_name)
            filled = value is not None and str(value).strip() != ""
            self.record_field(
                field_name=field_name,
                filled=filled,
                bundle_id=bundle_id,
                agent=agent,
            )

    def get_fill_rate(self, field_name: Optional[str] = None) -> dict[str, Any]:
        with self._lock:
            records = list(self._records)

        if field_name:
            records = [r for r in records if r.field_name == field_name]

        if not records:
            return {"total": 0, "filled": 0, "empty": 0, "fill_rate": 0.0}

        filled = sum(1 for r in records if r.filled)
        return {
            "field": field_name or "all",
            "total": len(records),
            "filled": filled,
            "empty": len(records) - filled,
            "fill_rate": round(filled / len(records), 4),
        }

    def get_fill_rates_by_field(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            records = list(self._records)

        by_field: dict[str, list[FieldFillRecord]] = defaultdict(list)
        for r in records:
            by_field[r.field_name].append(r)

        result: dict[str, dict[str, Any]] = {}
        for field, field_records in by_field.items():
            filled = sum(1 for r in field_records if r.filled)
            result[field] = {
                "total": len(field_records),
                "filled": filled,
                "empty": len(field_records) - filled,
                "fill_rate": round(filled / len(field_records), 4),
            }
        return result

    def get_fill_rates_by_agent(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            records = list(self._records)

        by_agent: dict[str, list[FieldFillRecord]] = defaultdict(list)
        for r in records:
            agent = r.agent or "unknown"
            by_agent[agent].append(r)

        result: dict[str, dict[str, Any]] = {}
        for agent, agent_records in by_agent.items():
            filled = sum(1 for r in agent_records if r.filled)
            result[agent] = {
                "total": len(agent_records),
                "filled": filled,
                "empty": len(agent_records) - filled,
                "fill_rate": round(filled / len(agent_records), 4),
            }
        return result

    def get_empty_critical_fields(self) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._records)

        empty: dict[str, int] = defaultdict(int)
        total: dict[str, int] = defaultdict(int)
        for r in records:
            total[r.field_name] += 1
            if not r.filled:
                empty[r.field_name] += 1

        return [
            {"field": field, "empty_count": empty[field], "total_count": total[field], "empty_rate": round(empty[field] / total[field], 4)}
            for field in sorted(empty, key=lambda f: -empty[f])
            if empty[field] > 0
        ]

    def _persist(self, entry: FieldFillRecord) -> None:
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except OSError:
            logger.debug("Failed to persist fill rate record", exc_info=True)


# ---------------------------------------------------------------------------
# Override Rate Tracker
# ---------------------------------------------------------------------------

_DECISION_RANK = {"decline": 0, "refer": 1, "approve": 2}


class OverrideRateTracker:
    """Tracks how often humans override AI decisions."""

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._records: list[OverrideRecord] = []
        self._persist_path = persist_path or Path(os.getenv("OVERRIDE_RATE_PATH", "./audit_logs/metrics/override_rate.jsonl"))

    def record_sign_off(
        self,
        bundle_id: str,
        ai_decision: str,
        human_decision: str,
        signed_by: str = "",
        override_reason: str = "",
        org_id: str = "default",
    ) -> OverrideRecord:
        is_override = ai_decision.lower() != human_decision.lower()
        override_type = "none"
        if is_override:
            ai_rank = _DECISION_RANK.get(ai_decision.lower(), 1)
            human_rank = _DECISION_RANK.get(human_decision.lower(), 1)
            if human_rank > ai_rank:
                override_type = "upgrade"
            elif human_rank < ai_rank:
                override_type = "downgrade"
            else:
                override_type = "lateral"

        record = OverrideRecord(
            bundle_id=bundle_id,
            ai_decision=ai_decision,
            human_decision=human_decision,
            is_override=is_override,
            override_type=override_type,
            signed_by=signed_by,
            override_reason=override_reason,
            org_id=org_id,
        )
        with self._lock:
            self._records.append(record)
            self._persist(record)
        return record

    def get_override_rate(self) -> dict[str, Any]:
        with self._lock:
            records = list(self._records)

        if not records:
            return {"total": 0, "overrides": 0, "override_rate": 0.0}

        overrides = sum(1 for r in records if r.is_override)
        upgrades = sum(1 for r in records if r.override_type == "upgrade")
        downgrades = sum(1 for r in records if r.override_type == "downgrade")

        return {
            "total": len(records),
            "overrides": overrides,
            "agreements": len(records) - overrides,
            "override_rate": round(overrides / len(records), 4),
            "upgrade_count": upgrades,
            "downgrade_count": downgrades,
        }

    def get_override_rate_by_agent(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            records = list(self._records)

        by_signer: dict[str, list[OverrideRecord]] = defaultdict(list)
        for r in records:
            signer = r.signed_by or "unknown"
            by_signer[signer].append(r)

        result: dict[str, dict[str, Any]] = {}
        for signer, signer_records in by_signer.items():
            overrides = sum(1 for r in signer_records if r.is_override)
            result[signer] = {
                "total": len(signer_records),
                "overrides": overrides,
                "override_rate": round(overrides / len(signer_records), 4),
            }
        return result

    def get_common_override_reasons(self) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._records)

        reasons: dict[str, int] = defaultdict(int)
        for r in records:
            if r.is_override and r.override_reason:
                reasons[r.override_reason] += 1

        return [
            {"reason": reason, "count": count}
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1])
        ]

    def _persist(self, entry: OverrideRecord) -> None:
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except OSError:
            logger.debug("Failed to persist override rate record", exc_info=True)


# ---------------------------------------------------------------------------
# Cycle Time Tracker
# ---------------------------------------------------------------------------

_STAGE_ORDER = [
    "ingest",
    "classify",
    "parse",
    "merge",
    "extract",
    "provenance",
    "reconcile",
    "rag",
    "synthesize",
    "audit",
    "human_review",
    "sign_off",
    "bind",
]


class CycleTimeTracker:
    """Tracks end-to-end pipeline cycle time with stage breakdowns."""

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._active: dict[str, dict[str, Any]] = {}
        self._records: list[CycleTimeRecord] = []
        self._persist_path = persist_path or Path(os.getenv("CYCLE_TIME_PATH", "./audit_logs/metrics/cycle_time.jsonl"))

    def start_pipeline(self, bundle_id: str, org_id: str = "default") -> None:
        with self._lock:
            self._active[bundle_id] = {
                "started_at": time.monotonic(),
                "started_utc": datetime.now(tz=timezone.utc),
                "org_id": org_id,
                "stages": {},
                "current_stage": None,
                "stage_start": None,
            }

    def start_stage(self, bundle_id: str, stage: str) -> None:
        with self._lock:
            active = self._active.get(bundle_id)
            if active is None:
                return
            if active["current_stage"] is not None:
                self._finish_current_stage(bundle_id)
            active["current_stage"] = stage
            active["stage_start"] = time.monotonic()

    def finish_stage(self, bundle_id: str, stage: str) -> None:
        with self._lock:
            active = self._active.get(bundle_id)
            if active is None:
                return
            if active["current_stage"] == stage:
                self._finish_current_stage(bundle_id)

    def _finish_current_stage(self, bundle_id: str) -> None:
        active = self._active.get(bundle_id)
        if active is None or active["current_stage"] is None or active["stage_start"] is None:
            return
        duration = (time.monotonic() - active["stage_start"]) * 1000
        active["stages"][active["current_stage"]] = active["stages"].get(active["current_stage"], 0) + duration
        active["current_stage"] = None
        active["stage_start"] = None

    def finish_pipeline(self, bundle_id: str, status: str = "completed") -> Optional[CycleTimeRecord]:
        with self._lock:
            active = self._active.pop(bundle_id, None)
            if active is None:
                return None
            if active["current_stage"] is not None:
                self._finish_current_stage_in(active)

            total_ms = (time.monotonic() - active["started_at"]) * 1000
            record = CycleTimeRecord(
                bundle_id=bundle_id,
                started_at=active["started_utc"],
                total_ms=round(total_ms, 3),
                stage_durations={k: round(v, 3) for k, v in active["stages"].items()},
                org_id=active["org_id"],
                status=status,
            )
            self._records.append(record)
            self._persist(record)
            return record

    @staticmethod
    def _finish_current_stage_in(active: dict[str, Any]) -> None:
        if active["current_stage"] is not None and active["stage_start"] is not None:
            duration = (time.monotonic() - active["stage_start"]) * 1000
            active["stages"][active["current_stage"]] = active["stages"].get(active["current_stage"], 0) + duration

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            records = list(self._records)

        if not records:
            return {"total_runs": 0, "avg_cycle_ms": 0, "p95_cycle_ms": 0}

        durations = [r.total_ms for r in records]
        durations_sorted = sorted(durations)
        p95_idx = int(0.95 * (len(durations_sorted) - 1))

        stage_totals: dict[str, float] = defaultdict(float)
        stage_counts: dict[str, int] = defaultdict(int)
        for r in records:
            for stage, dur in r.stage_durations.items():
                stage_totals[stage] += dur
                stage_counts[stage] += 1

        stage_avg = {
            stage: round(stage_totals[stage] / stage_counts[stage], 3)
            for stage in stage_totals
        }

        return {
            "total_runs": len(records),
            "avg_cycle_ms": round(sum(durations) / len(durations), 3),
            "p50_cycle_ms": round(durations_sorted[len(durations_sorted) // 2], 3),
            "p95_cycle_ms": round(durations_sorted[p95_idx], 3),
            "min_cycle_ms": round(min(durations), 3),
            "max_cycle_ms": round(max(durations), 3),
            "avg_stage_durations": stage_avg,
            "completed": sum(1 for r in records if r.status == "completed"),
            "failed": sum(1 for r in records if r.status != "completed"),
        }

    def get_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return [r.model_dump() for r in self._records[-limit:]]

    def _persist(self, entry: CycleTimeRecord) -> None:
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except OSError:
            logger.debug("Failed to persist cycle time record", exc_info=True)


# ---------------------------------------------------------------------------
# Aggregate Metrics
# ---------------------------------------------------------------------------

class PipelineMetrics:
    """Unified access to all pipeline business metrics."""

    def __init__(self) -> None:
        self.fill_rate = FillRateTracker()
        self.override_rate = OverrideRateTracker()
        self.cycle_time = CycleTimeTracker()

    def get_all(self) -> dict[str, Any]:
        return {
            "fill_rate": self.fill_rate.get_fill_rate(),
            "fill_rates_by_field": self.fill_rate.get_fill_rates_by_field(),
            "override_rate": self.override_rate.get_override_rate(),
            "override_rate_by_agent": self.override_rate.get_override_rate_by_agent(),
            "cycle_time": self.cycle_time.get_stats(),
            "empty_critical_fields": self.fill_rate.get_empty_critical_fields(),
            "common_override_reasons": self.override_rate.get_common_override_reasons(),
        }


_metrics: Optional[PipelineMetrics] = None


def get_pipeline_metrics() -> PipelineMetrics:
    global _metrics
    if _metrics is None:
        _metrics = PipelineMetrics()
    return _metrics
