"""SAR filing service — FinCEN-style suspicious activity report drafts.

Persists via JobStore (same pattern as workflow + connections). Does not
transmit to FinCEN BSA E-Filing; that is a live connector (`ofac-sdn` /
marketplace) once the org is enrolled.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from insureflow.aml.models import SarFiling
from insureflow.storage.job_store import JobStore, get_job_store

SAR_NS = "aml_sar"

_VALID_ACTIVITY = {
    "structuring",
    "fraud",
    "money_laundering",
    "terrorist_financing",
    "cyber",
    "other",
    "sanctions_evasion",
    "identity_theft",
}
_VALID_STATUS = {"draft", "filed", "acknowledged"}


class SarService:
    def __init__(self, store: JobStore | None = None) -> None:
        self.store = store or get_job_store()

    def file(
        self,
        *,
        subject_name: str,
        org_id: str = "default",
        filer_org: str = "",
        subject_tin: str = "",
        subject_type: str = "individual",
        activity_type: str = "fraud",
        amount: float = 0.0,
        narrative: str = "",
        suspicious_period_start: str = "",
        suspicious_period_end: str = "",
        status: str = "draft",
        related_bundle_id: str = "",
        filed_by: str = "",
        extra: dict[str, Any] | None = None,
        sar_id: str | None = None,
    ) -> SarFiling:
        if not subject_name.strip():
            raise ValueError("subject_name is required")
        activity = activity_type if activity_type in _VALID_ACTIVITY else "other"
        st = status if status in _VALID_STATUS else "draft"
        now = datetime.now(tz=timezone.utc)
        filing = SarFiling(
            sar_id=sar_id or f"SAR-{uuid.uuid4().hex[:10].upper()}",
            org_id=org_id,
            filer_org=filer_org or org_id,
            subject_name=subject_name.strip(),
            subject_tin=subject_tin,
            subject_type=subject_type if subject_type in {"individual", "business"} else "individual",
            activity_type=activity,
            amount=float(amount or 0.0),
            narrative=narrative,
            suspicious_period_start=suspicious_period_start,
            suspicious_period_end=suspicious_period_end,
            status=st,
            related_bundle_id=related_bundle_id,
            filed_by=filed_by,
            extra=extra or {},
            created_at=now,
            updated_at=now,
        )
        self.store.set(SAR_NS, filing.sar_id, filing.model_dump(mode="json"), org_id=org_id)
        return filing

    def get(self, sar_id: str, *, org_id: str = "default") -> SarFiling | None:
        raw = self.store.get(SAR_NS, sar_id, org_id=org_id)
        if not raw:
            return None
        return SarFiling.model_validate(raw)

    def list(self, *, org_id: str = "default") -> list[SarFiling]:
        out: list[SarFiling] = []
        for sid in self.store.list_ids(SAR_NS, org_id=org_id):
            rec = self.get(sid, org_id=org_id)
            if rec:
                out.append(rec)
        out.sort(key=lambda s: s.created_at, reverse=True)
        return out

    def update_status(self, sar_id: str, status: str, *, org_id: str = "default") -> SarFiling:
        rec = self.get(sar_id, org_id=org_id)
        if rec is None:
            raise ValueError(f"SAR not found: {sar_id}")
        if status not in _VALID_STATUS:
            raise ValueError(f"Invalid SAR status: {status}")
        rec.status = status
        rec.updated_at = datetime.now(tz=timezone.utc)
        self.store.set(SAR_NS, rec.sar_id, rec.model_dump(mode="json"), org_id=org_id)
        return rec


_default: SarService | None = None


def _svc() -> SarService:
    global _default
    if _default is None:
        _default = SarService()
    return _default


def file_sar(**kwargs: Any) -> SarFiling:
    return _svc().file(**kwargs)


def get_sar(sar_id: str, *, org_id: str = "default") -> SarFiling | None:
    return _svc().get(sar_id, org_id=org_id)


def list_sars(*, org_id: str = "default") -> list[SarFiling]:
    return _svc().list(org_id=org_id)
