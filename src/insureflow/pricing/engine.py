"""Per-submission pricing and usage tracking engine.

Manages tiered pricing, API key authentication, usage tracking,
and rate limiting for self-serve MGA/broker customers.

Tiers:
    free    — $0, 50 submissions/mo, 1 user
    pro     — $999/mo + $1.99/submission, unlimited submissions, 5 users
    starter — $299/mo + $2.99/submission, 200 submissions/mo, 3 users
    enterprise — custom pricing, unlimited everything

Designed for: Small MGAs, binding authorities, independent brokers
Beating Sixfold/Cytora's $100K+/yr enterprise contracts.

    PRICING_STORAGE_BACKEND  "file" (default) or "postgres"
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from insureflow.storage.lock import FileLock, atomic_write

logger = logging.getLogger(__name__)

_TESTING = os.environ.get("INSUREFLOW_AUTH_TESTING") == "1"


# ---------------------------------------------------------------------------
# Pricing Tiers
# ---------------------------------------------------------------------------


class PricingTier(BaseModel):
    name: str
    monthly_base: float  # fixed monthly fee
    per_submission: float  # cost per submission
    monthly_included: int  # submissions included in base (overage charged per-submission)
    max_users: int  # max API keys / users
    max_submissions_per_day: int  # daily rate limit
    features: list[str] = Field(default_factory=list)


TIERS: dict[str, PricingTier] = {
    "free": PricingTier(
        name="free",
        monthly_base=0.0,
        per_submission=0.0,
        monthly_included=50,
        max_users=1,
        max_submissions_per_day=25,
        features=["basic_extraction", "risk_scoring", "state_rules"],
    ),
    "starter": PricingTier(
        name="starter",
        monthly_base=299.0,
        per_submission=2.99,
        monthly_included=200,
        max_users=3,
        max_submissions_per_day=100,
        features=[
            "basic_extraction",
            "risk_scoring",
            "state_rules",
            "health_compliance",
            "surplus_lines_compliance",
            "workers_comp_compliance",
            "regulatory_intelligence",
        ],
    ),
    "pro": PricingTier(
        name="pro",
        monthly_base=999.0,
        per_submission=1.99,
        monthly_included=1000,
        max_users=5,
        max_submissions_per_day=500,
        features=[
            "basic_extraction",
            "risk_scoring",
            "state_rules",
            "health_compliance",
            "surplus_lines_compliance",
            "workers_comp_compliance",
            "regulatory_intelligence",
            "adverse_selection",
            "moral_hazard",
            "fraud_detection",
            "reinsurance",
            "premium_optimization",
            "api_access",
            "webhook_support",
            "priority_support",
        ],
    ),
    "enterprise": PricingTier(
        name="enterprise",
        monthly_base=0.0,  # custom
        per_submission=0.0,  # custom
        monthly_included=-1,  # unlimited
        max_users=-1,  # unlimited
        max_submissions_per_day=-1,  # unlimited
        features=["everything"],
    ),
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class APIKey(BaseModel):
    key_id: str
    key_hash: str  # SHA-256 of the actual key
    org_id: str
    tier: str = "free"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    last_used_at: Optional[datetime] = None
    disabled: bool = False
    label: str = ""  # human-readable label


class UsageRecord(BaseModel):
    org_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    submission_id: str = ""
    line_of_business: str = ""
    state_code: str = ""
    tier: str = "free"
    billed: bool = False


class UsageSummary(BaseModel):
    org_id: str
    tier: str
    period: str  # "2026-08"
    submissions_used: int
    submissions_included: int
    submissions_overage: int
    overage_cost: float
    base_cost: float
    total_cost: float
    daily_used: int
    daily_limit: int
    rate_limited: bool


class BillingSummary(BaseModel):
    org_id: str
    tier: str
    current_period: str
    monthly_base: float
    per_submission_rate: float
    submissions_used: int
    submissions_included: int
    overage_submissions: int
    overage_cost: float
    total_billed: float
    next_billing_date: str
    api_keys_active: int


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def _storage_path() -> Path:
    if _TESTING:
        return Path(tempfile.gettempdir()) / "insureflow_test" / "pricing.json"
    return Path.cwd() / ".insureflow" / "pricing.json"


class PricingStore:
    """File-backed pricing store with optional Redis."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._path = _storage_path()
        self._data: dict[str, Any] = {
            "api_keys": {},  # key_hash -> APIKey dict
            "usage": {},  # org_id -> [UsageRecord dict]
            "subscriptions": {},  # org_id -> {tier, started_at}
        }
        self._load()

    def _load(self) -> None:
        with self._lock:
            if self._path.exists():
                try:
                    with FileLock(str(self._path) + ".lock"):
                        raw = self._path.read_text(encoding="utf-8")
                    loaded = json.loads(raw)
                    self._data.update(loaded)
                except (json.JSONDecodeError, OSError, ValueError):
                    pass

    def _save(self) -> None:
        with self._lock:
            try:
                payload = json.dumps(self._data, indent=2, default=str)
                with FileLock(str(self._path) + ".lock"):
                    atomic_write(self._path, payload)
            except OSError as exc:
                logger.warning("Pricing store save failed: %s", exc)

    # -- API Keys --

    def create_api_key(self, org_id: str, tier: str = "free", label: str = "") -> tuple[str, APIKey]:
        """Create a new API key. Returns (raw_key, APIKey)."""
        raw_key = f"ifly_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id = key_hash[:16]

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            org_id=org_id,
            tier=tier,
            label=label or f"key-{key_id[:8]}",
        )

        with self._lock:
            self._data["api_keys"][key_hash] = api_key.model_dump(mode="json")
            self._save()

        logger.info("Created API key %s for org %s (tier=%s)", key_id, org_id, tier)
        return raw_key, api_key

    def validate_api_key(self, raw_key: str) -> APIKey | None:
        """Validate an API key and return the key metadata."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        with self._lock:
            key_data = self._data["api_keys"].get(key_hash)
            if key_data is None:
                return None
            api_key = APIKey.model_validate(key_data)
            if api_key.disabled:
                return None
            # Update last_used_at
            api_key.last_used_at = datetime.now(tz=timezone.utc)
            self._data["api_keys"][key_hash] = api_key.model_dump(mode="json")
            self._save()
            return api_key

    def disable_api_key(self, key_hash: str) -> bool:
        with self._lock:
            key_data = self._data["api_keys"].get(key_hash)
            if key_data is None:
                return False
            key_data["disabled"] = True
            self._data["api_keys"][key_hash] = key_data
            self._save()
            return True

    def list_api_keys(self, org_id: str) -> list[APIKey]:
        with self._lock:
            keys = []
            for kd in self._data["api_keys"].values():
                if kd.get("org_id") == org_id:
                    keys.append(APIKey.model_validate(kd))
            return keys

    # -- Subscriptions --

    def set_subscription(self, org_id: str, tier: str) -> None:
        with self._lock:
            self._data.setdefault("subscriptions", {})[org_id] = {
                "tier": tier,
                "started_at": datetime.now(tz=timezone.utc).isoformat(),
            }
            self._save()

    def get_subscription(self, org_id: str) -> str:
        with self._lock:
            sub = self._data.get("subscriptions", {}).get(org_id)
            return sub.get("tier", "free") if sub else "free"

    # -- Usage Tracking --

    def record_submission(
        self,
        org_id: str,
        submission_id: str = "",
        line_of_business: str = "",
        state_code: str = "",
    ) -> UsageRecord:
        tier = self.get_subscription(org_id)
        record = UsageRecord(
            org_id=org_id,
            submission_id=submission_id,
            line_of_business=line_of_business,
            state_code=state_code,
            tier=tier,
        )

        with self._lock:
            self._data.setdefault("usage", {}).setdefault(org_id, [])
            self._data["usage"][org_id].append(record.model_dump(mode="json"))
            # Keep only last 90 days of records
            cutoff = datetime.now(tz=timezone.utc).timestamp() - (90 * 86400)
            self._data["usage"][org_id] = [r for r in self._data["usage"][org_id] if datetime.fromisoformat(r["timestamp"]).timestamp() > cutoff]
            self._save()

        return record

    def get_usage(self, org_id: str, period: str | None = None) -> list[UsageRecord]:
        """Get usage records for an org, optionally filtered by period (YYYY-MM)."""
        if period is None:
            now = datetime.now(tz=timezone.utc)
            period = f"{now.year}-{now.month:02d}"

        with self._lock:
            records = self._data.get("usage", {}).get(org_id, [])
            result = []
            for r in records:
                ts = r.get("timestamp", "")
                if ts.startswith(period):
                    result.append(UsageRecord.model_validate(r))
            return result

    def get_daily_usage(self, org_id: str) -> int:
        """Count submissions used today."""
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            records = self._data.get("usage", {}).get(org_id, [])
            return sum(1 for r in records if r.get("timestamp", "").startswith(today))


# ---------------------------------------------------------------------------
# Pricing Engine
# ---------------------------------------------------------------------------

_pricing_store: PricingStore | None = None


def get_pricing_store() -> PricingStore:
    global _pricing_store
    if _pricing_store is None:
        _pricing_store = PricingStore()
    return _pricing_store


class PricingEngine:
    """Calculate costs, check rate limits, manage API keys."""

    def __init__(self) -> None:
        self._store = get_pricing_store()

    def check_rate_limit(self, org_id: str) -> tuple[bool, str]:
        """Check if org has hit daily rate limit. Returns (allowed, reason)."""
        tier_name = self._store.get_subscription(org_id)
        tier = TIERS.get(tier_name, TIERS["free"])

        daily_used = self._store.get_daily_usage(org_id)

        if tier.max_submissions_per_day < 0:
            return True, "unlimited"

        if daily_used >= tier.max_submissions_per_day:
            return False, (f"Daily rate limit reached: {daily_used}/{tier.max_submissions_per_day} submissions today ({tier_name} tier). Upgrade for higher limits.")

        return True, f"{daily_used}/{tier.max_submissions_per_day} used today"

    def record_and_bill(
        self,
        org_id: str,
        submission_id: str = "",
        line_of_business: str = "",
        state_code: str = "",
    ) -> UsageSummary:
        """Record a submission and return current usage summary."""
        self._store.record_submission(org_id, submission_id, line_of_business, state_code)
        return self.get_usage_summary(org_id)

    def get_usage_summary(self, org_id: str, period: str | None = None) -> UsageSummary:
        """Get current period usage summary with cost calculation."""
        now = datetime.now(tz=timezone.utc)
        if period is None:
            period = f"{now.year}-{now.month:02d}"

        tier_name = self._store.get_subscription(org_id)
        tier = TIERS.get(tier_name, TIERS["free"])
        records = self._store.get_usage(org_id, period)
        used = len(records)
        included = tier.monthly_included if tier.monthly_included >= 0 else used
        overage = max(0, used - included)
        overage_cost = overage * tier.per_submission
        base_cost = tier.monthly_base
        daily_used = self._store.get_daily_usage(org_id)
        daily_limit = tier.max_submissions_per_day

        return UsageSummary(
            org_id=org_id,
            tier=tier_name,
            period=period,
            submissions_used=used,
            submissions_included=included,
            submissions_overage=overage,
            overage_cost=round(overage_cost, 2),
            base_cost=base_cost,
            total_cost=round(base_cost + overage_cost, 2),
            daily_used=daily_used,
            daily_limit=daily_limit,
            rate_limited=daily_limit > 0 and daily_used >= daily_limit,
        )

    def get_billing_summary(self, org_id: str) -> BillingSummary:
        """Full billing summary for the org."""
        now = datetime.now(tz=timezone.utc)
        period = f"{now.year}-{now.month:02d}"
        tier_name = self._store.get_subscription(org_id)
        tier = TIERS.get(tier_name, TIERS["free"])
        summary = self.get_usage_summary(org_id, period)
        keys = self._store.list_api_keys(org_id)

        # Next billing date: 1st of next month
        if now.month == 12:
            next_billing = f"{now.year + 1}-01-01"
        else:
            next_billing = f"{now.year}-{now.month + 1:02d}-01"

        return BillingSummary(
            org_id=org_id,
            tier=tier_name,
            current_period=period,
            monthly_base=tier.monthly_base,
            per_submission_rate=tier.per_submission,
            submissions_used=summary.submissions_used,
            submissions_included=summary.submissions_included,
            overage_submissions=summary.submissions_overage,
            overage_cost=summary.overage_cost,
            total_billed=summary.total_cost,
            next_billing_date=next_billing,
            api_keys_active=sum(1 for k in keys if not k.disabled),
        )

    def create_api_key(self, org_id: str, tier: str = "free", label: str = "") -> tuple[str, APIKey]:
        return self._store.create_api_key(org_id, tier, label)

    def validate_api_key(self, raw_key: str) -> APIKey | None:
        return self._store.validate_api_key(raw_key)

    def list_api_keys(self, org_id: str) -> list[APIKey]:
        return self._store.list_api_keys(org_id)

    def disable_api_key(self, key_hash: str) -> bool:
        return self._store.disable_api_key(key_hash)

    def upgrade_tier(self, org_id: str, new_tier: str) -> dict[str, Any]:
        """Upgrade an org's pricing tier."""
        if new_tier not in TIERS:
            return {"error": f"Invalid tier: {new_tier}. Valid tiers: {list(TIERS.keys())}"}

        old_tier = self._store.get_subscription(org_id)
        self._store.set_subscription(org_id, new_tier)

        return {
            "org_id": org_id,
            "previous_tier": old_tier,
            "new_tier": new_tier,
            "tier_details": TIERS[new_tier].model_dump(),
            "message": f"Upgraded from {old_tier} to {new_tier}",
        }

    def get_pricing_plans(self) -> dict[str, Any]:
        """Return all available pricing plans."""
        return {
            "plans": {
                name: {
                    "name": tier.name,
                    "monthly_base": tier.monthly_base,
                    "per_submission": tier.per_submission,
                    "monthly_included": tier.monthly_included,
                    "max_users": tier.max_users,
                    "max_submissions_per_day": tier.max_submissions_per_day,
                    "features": tier.features,
                }
                for name, tier in TIERS.items()
            },
            "currency": "USD",
            "billing_cycle": "monthly",
        }
