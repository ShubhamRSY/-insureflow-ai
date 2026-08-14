"""Customer-owned decision memory — patterns, not people.

Lives on disk in *their* landing zone (same AUDIT_LOG_PATH as the rest of the
desk). Records are feature bands and outcomes only: line, NAICS, state, TIV
band, construction, decision. No named insured, no account numbers, no file
text. That is how a decision maker remembers “habitational wood-frame in CA
with three losses was referred last quarter” without becoming a data store.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from insureflow.redaction.redactor import PIIRedactor

logger = logging.getLogger(__name__)

_TIV_BANDS = (
    (0, 250_000, "0-250k"),
    (250_000, 1_000_000, "250k-1m"),
    (1_000_000, 5_000_000, "1m-5m"),
    (5_000_000, 25_000_000, "5m-25m"),
    (25_000_000, 100_000_000, "25m-100m"),
)


def tiv_band(tiv: float | None) -> str:
    value = float(tiv or 0)
    for low, high, label in _TIV_BANDS:
        if low <= value < high:
            return label
    return "100m+"


def loss_count_band(count: int | None) -> str:
    n = int(count or 0)
    if n <= 0:
        return "0"
    if n == 1:
        return "1"
    if n <= 3:
        return "2-3"
    if n <= 6:
        return "4-6"
    return "7+"


class DecisionMemoryRecord(BaseModel):
    """One remembered underwriting outcome — safe to keep after the file is gone."""

    org_id: str
    bundle_id: str
    line: str = ""
    decision: str = ""
    routing: str = ""
    naics: str = ""
    state: str = ""
    tiv_band: str = ""
    construction: str = ""
    occupancy: str = ""
    loss_count_band: str = ""
    reasons: list[str] = Field(default_factory=list)
    remembered_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def match_score(self, other: DecisionMemoryRecord) -> float:
        score = 0.0
        checks = 0
        for field in ("line", "naics", "state", "tiv_band", "construction", "occupancy"):
            mine = (getattr(self, field) or "").strip().lower()
            theirs = (getattr(other, field) or "").strip().lower()
            if not mine and not theirs:
                continue
            checks += 1
            if mine and theirs and mine == theirs:
                score += 1.0
            elif mine and theirs and (mine in theirs or theirs in mine):
                score += 0.5
        return score / max(checks, 1)


class DecisionMemoryStore:
    """JSONL memory under the customer's audit path — never a Rytera-hosted copy."""

    def __init__(self, persist_path: Path | None = None) -> None:
        default = Path(os.getenv("DECISION_MEMORY_PATH", "./audit_logs/decision_memory.jsonl"))
        self._path = persist_path or default
        self._lock = threading.Lock()
        self._redactor = PIIRedactor()

    def remember(self, record: DecisionMemoryRecord) -> DecisionMemoryRecord:
        clean = record.model_copy(
            update={
                "reasons": [self._redactor.redact(r, mask=False) for r in (record.reasons or []) if r][:8],
                "naics": (record.naics or "")[:12],
                "state": (record.state or "")[:2].upper(),
                "construction": self._redactor.redact(record.construction or "", mask=False)[:40],
                "occupancy": self._redactor.redact(record.occupancy or "", mask=False)[:40],
                "line": (record.line or "")[:64],
                "decision": (record.decision or "")[:32],
                "routing": (record.routing or "")[:32],
            }
        )
        with self._lock:
            existing = self._load_unlocked()
            key = (clean.org_id, clean.bundle_id)
            kept = [r for r in existing if (r.org_id, r.bundle_id) != key]
            kept.append(clean)
            self._write_unlocked(kept)
        return clean

    def remember_from_summary(self, summary: dict[str, Any], *, org_id: str = "default") -> DecisionMemoryRecord | None:
        """Build a memory row from a pipeline summary — drops insured/broker names."""
        if not summary:
            return None
        try:
            from insureflow.privacy.data_plane import retain_source_documents

            # Always remember the decision; never copy names even in lab mode.
            reasons = []
            for key in ("human_review_reasons", "conditions", "rationale"):
                val = summary.get(key)
                if isinstance(val, list):
                    reasons.extend(str(x) for x in val[:6])
                elif isinstance(val, str) and val:
                    reasons.append(val)
            rec = DecisionMemoryRecord(
                org_id=org_id or str(summary.get("org_id") or "default"),
                bundle_id=str(summary.get("bundle_id") or ""),
                line=str(summary.get("insurance_line") or summary.get("product_line") or ""),
                decision=str(summary.get("ai_decision") or summary.get("outcome") or ""),
                routing="referred" if summary.get("human_review_required") else str(summary.get("outcome") or ""),
                naics=str(summary.get("naics") or summary.get("naics_code") or ""),
                state=str(summary.get("primary_state") or summary.get("state") or ""),
                tiv_band=tiv_band(summary.get("tiv")),
                construction=str(summary.get("construction") or ""),
                occupancy=str(summary.get("occupancy") or ""),
                loss_count_band=loss_count_band(summary.get("loss_count") or summary.get("claim_count")),
                reasons=reasons,
            )
            stored = self.remember(rec)
            if not retain_source_documents():
                logger.info(
                    "Decision memory stored for org=%s line=%s band=%s (source docs not retained)",
                    stored.org_id,
                    stored.line,
                    stored.tiv_band,
                )
            return stored
        except Exception:
            logger.debug("Decision memory write skipped", exc_info=True)
            return None

    def get(self, org_id: str, bundle_id: str) -> DecisionMemoryRecord | None:
        for rec in self._iter_org(org_id):
            if rec.bundle_id == bundle_id:
                return rec
        return None

    def list_records(
        self,
        org_id: str,
        *,
        line: str = "",
        state: str = "",
        tiv_band: str = "",
        decision: str = "",
        q: str = "",
        limit: int = 100,
    ) -> list[DecisionMemoryRecord]:
        needle = (q or "").strip().lower()
        out: list[DecisionMemoryRecord] = []
        for rec in self._iter_org(org_id):
            if line and rec.line.lower() != line.strip().lower():
                continue
            if state and rec.state.upper() != state.strip().upper()[:2]:
                continue
            if tiv_band and rec.tiv_band != tiv_band:
                continue
            if decision and rec.decision.lower() != decision.strip().lower():
                continue
            if needle:
                blob = " ".join(
                    [
                        rec.bundle_id,
                        rec.line,
                        rec.state,
                        rec.tiv_band,
                        rec.decision,
                        rec.naics,
                        rec.construction,
                        rec.occupancy,
                        " ".join(rec.reasons),
                    ]
                ).lower()
                if needle not in blob:
                    continue
            out.append(rec)
        out.sort(key=lambda r: r.remembered_at, reverse=True)
        return out[: max(1, min(limit, 500))]

    def similar(
        self,
        probe: DecisionMemoryRecord,
        *,
        limit: int = 8,
        min_score: float = 0.4,
    ) -> list[tuple[DecisionMemoryRecord, float]]:
        hits: list[tuple[DecisionMemoryRecord, float]] = []
        for rec in self._iter_org(probe.org_id):
            if rec.bundle_id == probe.bundle_id:
                continue
            score = rec.match_score(probe)
            if score >= min_score:
                hits.append((rec, score))
        hits.sort(key=lambda x: -x[1])
        return hits[:limit]

    def similar_to_bundle(self, org_id: str, bundle_id: str, *, limit: int = 8) -> list[tuple[DecisionMemoryRecord, float]]:
        probe = self.get(org_id, bundle_id)
        if probe is None:
            return []
        return self.similar(probe, limit=limit)

    def _iter_org(self, org_id: str) -> list[DecisionMemoryRecord]:
        with self._lock:
            return [r for r in self._load_unlocked() if r.org_id == org_id]

    def _load_unlocked(self) -> list[DecisionMemoryRecord]:
        if not self._path.exists():
            return []
        out: list[DecisionMemoryRecord] = []
        try:
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    out.append(DecisionMemoryRecord.model_validate_json(line))
                except Exception:
                    continue
        except Exception:
            logger.debug("Decision memory read failed", exc_info=True)
        return out

    def _write_unlocked(self, records: list[DecisionMemoryRecord]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec.model_dump(mode="json"), default=str, ensure_ascii=False) + "\n")
        tmp.replace(self._path)


_store: DecisionMemoryStore | None = None
_store_lock = threading.Lock()


def get_decision_memory() -> DecisionMemoryStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = DecisionMemoryStore()
        return _store
