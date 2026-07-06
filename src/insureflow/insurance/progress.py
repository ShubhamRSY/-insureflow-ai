from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


class PipelineProgressTracker:
    """Tracks pipeline stage timing and emits live progress updates."""

    def __init__(self, on_update: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.stages: list[dict[str, Any]] = []
        self.on_update = on_update
        self._active_id: str | None = None
        self._index: dict[str, int] = {}

    def start(self, stage_id: str, label: str, detail: str = "") -> None:
        if self._active_id and self._active_id != stage_id:
            self.complete(self._active_id)
        now = datetime.now(tz=timezone.utc)
        self._active_id = stage_id
        stage = {
            "id": stage_id,
            "label": label,
            "status": "active",
            "detail": detail,
            "findings": 0,
            "started_at": now.isoformat(),
            "completed_at": None,
            "duration_ms": None,
        }
        self._index[stage_id] = len(self.stages)
        self.stages.append(stage)
        self._emit()

    def complete(
        self,
        stage_id: str,
        *,
        detail: str | None = None,
        findings: int = 0,
        status: str = "complete",
    ) -> None:
        idx = self._index.get(stage_id)
        if idx is None:
            return
        stage = self.stages[idx]
        now = datetime.now(tz=timezone.utc)
        started = datetime.fromisoformat(stage["started_at"])
        stage["status"] = status
        stage["completed_at"] = now.isoformat()
        stage["duration_ms"] = int((now - started).total_seconds() * 1000)
        if detail is not None:
            stage["detail"] = detail
        stage["findings"] = findings
        if self._active_id == stage_id:
            self._active_id = None
        self._emit()

    def skip(self, stage_id: str, label: str, reason: str = "") -> None:
        now = datetime.now(tz=timezone.utc)
        stage = {
            "id": stage_id,
            "label": label,
            "status": "skipped",
            "detail": reason or "Skipped",
            "findings": 0,
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_ms": 0,
        }
        self._index[stage_id] = len(self.stages)
        self.stages.append(stage)
        self._emit()

    def fail(self, stage_id: str, reason: str) -> None:
        self.complete(stage_id, detail=reason, status="failed")

    def finish(self) -> list[dict[str, Any]]:
        if self._active_id:
            self.complete(self._active_id)
        return self.stages

    def snapshot(self) -> dict[str, Any]:
        return {
            "pipeline_stages": list(self.stages),
            "current_stage": self._active_id,
        }

    def _emit(self) -> None:
        if self.on_update:
            self.on_update(self.snapshot())
