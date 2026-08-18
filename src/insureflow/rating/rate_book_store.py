"""Filed rate book store with full audit trail.

Every rate, loss cost, and LCM comes from a filed rate book — never from AI.
This module makes the source of every number explicit and auditable.

    RATE_BOOK_PATH  override default carrier book location
    RATE_BOOK_AUDIT  enable audit trail logging (default: on)

Architecture:
    Filed rates (rate book) → Rating engine → QuoteResult
    AI suggestions (ML)    → UW memo only  → schedule_mod % (advisory)

The AI never generates a premium. It only suggests a schedule modifier.
The premium always comes from the filed rate book.
"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_TESTING = os.environ.get("INSUREFLOW_AUTH_TESTING") == "1"
_AUDIT_ENABLED = os.getenv("RATE_BOOK_AUDIT", "1").strip().lower() not in {"0", "false", "off", "no"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RateSource(BaseModel):
    """Where a specific rate came from — the full citation chain."""

    rate_type: str  # "loss_cost", "lcm", "base_rate", "manual_rate", "minimum_premium"
    value: float
    source_file: str = ""  # e.g. "carrier_book.json", "ncci_manual_2026.json"
    filing_id: str = ""  # e.g. "SERFF-T12345"
    effective_date: str = ""  # e.g. "2026-01-01"
    carrier: str = ""  # e.g. "Travelers"
    state: str = ""  # e.g. "CT"
    line_of_business: str = ""  # e.g. "commercial_property"
    product_id: str = ""  # e.g. "cpp_property"
    version: str = ""  # e.g. "2026-Q3"
    notes: str = ""


class RateAuditEntry(BaseModel):
    """One audit trail entry — tracks every rate lookup."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    bundle_id: str = ""
    state_code: str = ""
    line_of_business: str = ""
    product_id: str = ""
    exposure: float = 0.0
    exposure_basis: str = ""
    # The filed rate values used
    loss_cost: float = 0.0
    lcm: float = 1.0
    state_relativity: float = 1.0
    base_premium: float = 0.0
    adjusted_premium: float = 0.0
    # Source citations
    rate_sources: list[RateSource] = Field(default_factory=list)
    # AI modification (advisory only)
    ai_suggested_mod_pct: float = 0.0
    ai_mod_applied: bool = False
    final_premium: float = 0.0
    # Metadata
    rate_book_id: str = ""
    rate_book_version: str = ""
    rate_book_posture: str = ""  # "carrier_imported", "pilot", "demo"
    is_filed_rate: bool = True  # True = rate came from filed book, False = AI-generated (should never happen for binding)


class RateAuditTrail(BaseModel):
    """Complete audit trail for a submission's rating."""

    bundle_id: str
    entries: list[RateAuditEntry] = Field(default_factory=list)
    total_filed_premium: float = 0.0
    total_adjusted_premium: float = 0.0
    has_filed_rate_book: bool = False
    rate_book_posture: str = ""
    summary: str = ""


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


def _audit_dir() -> Path:
    if _TESTING:
        return Path(tempfile.gettempdir()) / "insureflow_test" / "rate_audit"
    return Path.cwd() / ".insureflow" / "rate_audit"


class RateBookAuditStore:
    """File-backed rate audit trail storage."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._dir = _audit_dir()
        self._dir.mkdir(parents=True, exist_ok=True)

    def record(self, entry: RateAuditEntry) -> None:
        if not _AUDIT_ENABLED:
            return
        with self._lock:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            audit_file = self._dir / f"{date_str}.jsonl"
            try:
                with open(audit_file, "a", encoding="utf-8") as f:
                    f.write(entry.model_dump_json() + "\n")
            except OSError as exc:
                logger.warning("Rate audit write failed: %s", exc)

    def get_trail(self, bundle_id: str) -> list[RateAuditEntry]:
        entries: list[RateAuditEntry] = []
        with self._lock:
            for audit_file in sorted(self._dir.glob("*.jsonl"), reverse=True):
                try:
                    with open(audit_file, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            entry = RateAuditEntry.model_validate_json(line)
                            if entry.bundle_id == bundle_id:
                                entries.append(entry)
                except Exception:
                    continue
                if entries:
                    break
        return entries

    def get_entries_by_state(self, state_code: str, limit: int = 50) -> list[RateAuditEntry]:
        entries: list[RateAuditEntry] = []
        with self._lock:
            for audit_file in sorted(self._dir.glob("*.jsonl"), reverse=True):
                try:
                    with open(audit_file, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            entry = RateAuditEntry.model_validate_json(line)
                            if entry.state_code == state_code.upper():
                                entries.append(entry)
                                if len(entries) >= limit:
                                    return entries
                except Exception:
                    continue
        return entries


# ---------------------------------------------------------------------------
# Rate Book Source Resolver
# ---------------------------------------------------------------------------

_audit_store: RateBookAuditStore | None = None


def get_audit_store() -> RateBookAuditStore:
    global _audit_store
    if _audit_store is None:
        _audit_store = RateBookAuditStore()
    return _audit_store


class RateBookResolver:
    """Resolves rates from filed rate books with full audit trail.

    Every rate lookup returns a RateSource citation.
    The audit trail records every rate used in a quote.
    """

    def __init__(self) -> None:
        self._store = get_audit_store()

    def get_rate_sources(
        self,
        product_id: str,
        state_code: str,
    ) -> list[RateSource]:
        """Get all filed rate sources for a product in a state.

        Returns RateSource objects with full citation chain.
        """
        from insureflow.rating.leaf_filings import get_leaf_filing, load_carrier_book

        book = load_carrier_book()
        filing = get_leaf_filing(product_id)
        if not filing:
            return []

        sources: list[RateSource] = []
        carrier = book.get("carrier", "")
        version = book.get("version", "")
        effective = book.get("effective_date", "")

        # Loss cost
        if "loss_cost" in filing:
            sources.append(
                RateSource(
                    rate_type="loss_cost",
                    value=float(filing["loss_cost"]),
                    source_file=book.get("_loaded_from", ""),
                    filing_id=filing.get("filing_id", ""),
                    effective_date=effective,
                    carrier=carrier,
                    state=state_code,
                    line_of_business=product_id,
                    product_id=product_id,
                    version=version,
                    notes=f"Filed loss cost for {product_id} in {state_code}",
                )
            )

        # LCM (Loss Cost Multiplier)
        if "lcm" in filing:
            sources.append(
                RateSource(
                    rate_type="lcm",
                    value=float(filing["lcm"]),
                    source_file=book.get("_loaded_from", ""),
                    filing_id=filing.get("filing_id", ""),
                    effective_date=effective,
                    carrier=carrier,
                    state=state_code,
                    line_of_business=product_id,
                    product_id=product_id,
                    version=version,
                    notes=f"Filed LCM for {product_id}",
                )
            )

        # State relativity
        state_rels = filing.get("state_relativities", {})
        if state_code in state_rels:
            sources.append(
                RateSource(
                    rate_type="state_relativity",
                    value=float(state_rels[state_code]),
                    source_file=book.get("_loaded_from", ""),
                    filing_id=filing.get("filing_id", ""),
                    effective_date=effective,
                    carrier=carrier,
                    state=state_code,
                    line_of_business=product_id,
                    product_id=product_id,
                    version=version,
                    notes=f"Filed state relativity for {state_code}",
                )
            )

        # Minimum premium
        if "minimum_premium" in filing:
            sources.append(
                RateSource(
                    rate_type="minimum_premium",
                    value=float(filing["minimum_premium"]),
                    source_file=book.get("_loaded_from", ""),
                    filing_id=filing.get("filing_id", ""),
                    effective_date=effective,
                    carrier=carrier,
                    state=state_code,
                    line_of_business=product_id,
                    product_id=product_id,
                    version=version,
                    notes="Filed minimum premium",
                )
            )

        return sources

    def record_quote(
        self,
        bundle_id: str,
        state_code: str,
        line_of_business: str,
        product_id: str,
        exposure: float,
        exposure_basis: str,
        loss_cost: float,
        lcm: float,
        state_relativity: float,
        base_premium: float,
        adjusted_premium: float,
        rate_sources: list[RateSource],
        ai_suggested_mod_pct: float = 0.0,
        ai_mod_applied: bool = False,
        final_premium: float = 0.0,
    ) -> RateAuditEntry:
        """Record a complete rate audit entry for a quote."""
        from insureflow.rating.leaf_filings import load_carrier_book

        book = load_carrier_book()

        entry = RateAuditEntry(
            bundle_id=bundle_id,
            state_code=state_code,
            line_of_business=line_of_business,
            product_id=product_id,
            exposure=exposure,
            exposure_basis=exposure_basis,
            loss_cost=loss_cost,
            lcm=lcm,
            state_relativity=state_relativity,
            base_premium=base_premium,
            adjusted_premium=adjusted_premium,
            rate_sources=rate_sources,
            ai_suggested_mod_pct=ai_suggested_mod_pct,
            ai_mod_applied=ai_mod_applied,
            final_premium=final_premium,
            rate_book_id=book.get("book_id", ""),
            rate_book_version=book.get("version", ""),
            rate_book_posture=book.get("posture", ""),
            isFiledRate=True,
        )

        self._store.record(entry)
        return entry

    def get_trail(self, bundle_id: str) -> RateAuditTrail:
        """Get complete audit trail for a submission."""
        entries = self._store.get_trail(bundle_id)
        if not entries:
            return RateAuditTrail(bundle_id=bundle_id, summary="No rating audit entries found")

        total_filed = sum(e.base_premium for e in entries)
        total_adjusted = sum(e.adjusted_premium for e in entries)
        has_book = any(e.rate_book_posture in ("carrier_imported", "serff", "filed", "production") for e in entries)
        posture = entries[0].rate_book_posture if entries else ""

        return RateAuditTrail(
            bundle_id=bundle_id,
            entries=entries,
            total_filed_premium=round(total_filed, 2),
            total_adjusted_premium=round(total_adjusted, 2),
            has_filed_rate_book=has_book,
            rate_book_posture=posture,
            summary=(f"{len(entries)} rate component(s), filed premium ${total_filed:,.2f}, adjusted ${total_adjusted:,.2f}, book: {posture}"),
        )

    def has_filed_rate_book(self) -> bool:
        """Check if a production/carrier-imported rate book is loaded."""
        from insureflow.rating.leaf_filings import load_carrier_book

        book = load_carrier_book()
        posture = book.get("posture", "")
        return posture in ("carrier_imported", "serff", "filed", "production")

    def get_rate_book_info(self) -> dict[str, Any]:
        """Get current rate book metadata."""
        from insureflow.rating.leaf_filings import load_carrier_book

        book = load_carrier_book()
        filings = book.get("filings", {})
        return {
            "book_id": book.get("book_id", ""),
            "carrier": book.get("carrier", ""),
            "version": book.get("version", ""),
            "effective_date": book.get("effective_date", ""),
            "posture": book.get("posture", ""),
            "is_production": book.get("posture", "") in ("carrier_imported", "serff", "filed", "production"),
            "products_covered": list(filings.keys()),
            "total_products": len(filings),
            "source_path": book.get("_loaded_from", ""),
        }
