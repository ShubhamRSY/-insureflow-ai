"""Commercial plan gates: live oracles, customer rate book, live PAS bind.

Default is ``pilot`` so local/CI stays simulated. Desk+ fail closed on fake data.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

_PLAN_ALIASES = {
    "free": "pilot",
    "starter": "pilot",
    "explorer": "desk",
    "pro": "book",
    "professional": "book",
}


@dataclass(frozen=True)
class PlanEntitlements:
    plan_id: str
    allow_simulated_oracles: bool
    require_live_oracles: bool
    allow_demo_rate_book: bool
    require_carrier_book: bool
    allow_simulated_pas: bool
    require_live_pas: bool
    allow_bind: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "allow_simulated_oracles": self.allow_simulated_oracles,
            "require_live_oracles": self.require_live_oracles,
            "allow_demo_rate_book": self.allow_demo_rate_book,
            "require_carrier_book": self.require_carrier_book,
            "allow_simulated_pas": self.allow_simulated_pas,
            "require_live_pas": self.require_live_pas,
            "allow_bind": self.allow_bind,
        }


_PLANS: dict[str, PlanEntitlements] = {
    "pilot": PlanEntitlements(
        plan_id="pilot",
        allow_simulated_oracles=True,
        require_live_oracles=False,
        allow_demo_rate_book=True,
        require_carrier_book=False,
        allow_simulated_pas=True,
        require_live_pas=False,
        allow_bind=False,  # shadow / bind off
    ),
    "desk": PlanEntitlements(
        plan_id="desk",
        allow_simulated_oracles=False,
        require_live_oracles=True,
        allow_demo_rate_book=False,
        require_carrier_book=True,
        allow_simulated_pas=True,  # quote without PAS ok; live PAS required at bind
        require_live_pas=False,
        allow_bind=True,
    ),
    "book": PlanEntitlements(
        plan_id="book",
        allow_simulated_oracles=False,
        require_live_oracles=True,
        allow_demo_rate_book=False,
        require_carrier_book=True,
        allow_simulated_pas=False,
        require_live_pas=True,
        allow_bind=True,
    ),
    "enterprise": PlanEntitlements(
        plan_id="enterprise",
        allow_simulated_oracles=False,
        require_live_oracles=True,
        allow_demo_rate_book=False,
        require_carrier_book=True,
        allow_simulated_pas=False,
        require_live_pas=True,
        allow_bind=True,
    ),
}


def resolve_plan(plan_id: str | None = None) -> PlanEntitlements:
    raw = (plan_id or os.getenv("RYTERA_PLAN") or "pilot").strip().lower()
    raw = _PLAN_ALIASES.get(raw, raw)
    return _PLANS.get(raw, _PLANS["pilot"])


def current_plan() -> PlanEntitlements:
    return resolve_plan()


def is_customer_rate_book(status: dict[str, Any]) -> bool:
    """True when the loaded book is a carrier/SERFF import, not the InsureFlow pilot manual."""
    posture = str(status.get("posture") or "").strip().lower()
    book_id = str(status.get("book_id") or "").strip().lower()
    if posture in {"carrier_imported", "serff", "filed", "customer", "production"}:
        return True
    if "pilot" in posture or book_id.startswith("insureflow_pilot"):
        return False
    if status.get("filings") and os.getenv("CARRIER_BOOK_PATH", "").strip():
        path = os.getenv("CARRIER_BOOK_PATH", "").lower()
        if "carrier_book.json" in path and "live" not in path:
            return False
        return True
    return False


def live_pas_ready() -> bool:
    """True when Guidewire or BriteCore is live — bind will not force a re-key."""
    try:
        from insureflow.integrations.factory import build_policy_admin_service

        status = build_policy_admin_service().status()
    except Exception:
        return False
    for key in ("primary", "fallback"):
        st = status.get(key) or {}
        if str(st.get("mode") or "").lower() == "live" and st.get("configured"):
            return True
    return False
