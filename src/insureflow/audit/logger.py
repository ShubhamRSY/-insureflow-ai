from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from insureflow.models.audit import AuditEntry, AuditTrail, EventSeverity, PipelineEvent

logger = logging.getLogger("insureflow.audit")


class AuditLogger:
    def __init__(self) -> None:
        self._trails: dict[str, AuditTrail] = {}

    def create_trail(self, bundle_id: str) -> AuditTrail:
        trail = AuditTrail(
            trail_id=f"trail-{uuid4().hex[:12]}",
            bundle_id=bundle_id,
        )
        self._trails[bundle_id] = trail
        return trail

    def get_trail(self, bundle_id: str) -> Optional[AuditTrail]:
        return self._trails.get(bundle_id)

    def log(
        self,
        bundle_id: str,
        event: PipelineEvent,
        agent_name: str = "",
        message: str = "",
        severity: EventSeverity = EventSeverity.INFO,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEntry:
        trail = self._trails.get(bundle_id)
        if trail is None:
            trail = self.create_trail(bundle_id)

        entry = AuditEntry(
            entry_id=f"entry-{uuid4().hex[:8]}",
            bundle_id=bundle_id,
            event=event,
            severity=severity,
            agent_name=agent_name,
            message=message,
            metadata=metadata or {},
        )

        trail.add_entry(entry)

        # Emit standard observability logs for infrastructure monitoring (e.g., Datadog)
        log_msg = f"[Bundle: {bundle_id}] {getattr(event, 'value', event)} - {message}"
        if severity in (EventSeverity.ERROR, EventSeverity.CRITICAL):
            logger.error(log_msg, extra={"agent": agent_name, "metadata": metadata})
        elif severity == EventSeverity.WARNING:
            logger.warning(log_msg, extra={"agent": agent_name, "metadata": metadata})
        else:
            logger.info(log_msg, extra={"agent": agent_name, "metadata": metadata})

        return entry

    def complete_trail(self, bundle_id: str) -> None:
        trail = self._trails.get(bundle_id)
        if trail:
            trail.completed_at = datetime.now(timezone.utc)

    def get_all_entries(self, bundle_id: str) -> list[AuditEntry]:
        trail = self._trails.get(bundle_id)
        if trail:
            return trail.entries
        return []

    def get_errors(self, bundle_id: str) -> list[AuditEntry]:
        return [e for e in self.get_all_entries(bundle_id) if e.severity in (EventSeverity.ERROR, EventSeverity.CRITICAL)]

    def cleanup_trail(self, bundle_id: str) -> None:
        """Removes the trail from memory to prevent memory leaks in long-running processes."""
        if bundle_id in self._trails:
            del self._trails[bundle_id]
