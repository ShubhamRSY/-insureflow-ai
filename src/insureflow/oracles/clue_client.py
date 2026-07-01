from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class CLUERecord:
    claim_id: str
    date_of_loss: date
    loss_type: str
    paid_amount: float
    current_status: str
    policy_type: str
    claimant_name: str
    description: str = ""


@dataclass
class CLUEResult:
    subject_name: str
    subject_address: str
    records: list[CLUERecord] = field(default_factory=list)
    total_claims_found: int = 0
    total_paid: float = 0.0
    has_prior_litigation: bool = False
    has_prior_cancellation: bool = False
    query_completed: bool = True
    error: str = ""

    @property
    def summary(self) -> str:
        if self.error:
            return f"CLUE query failed: {self.error}"
        parts = [f"CLUE returned {self.total_claims_found} records for {self.subject_name}"]
        if self.has_prior_litigation:
            parts.append("Prior litigation detected")
        if self.has_prior_cancellation:
            parts.append("Prior cancellation/non-renewal detected")
        return " | ".join(parts)


class CLUEClient:
    """Simulated CLUE (Comprehensive Loss Underwriting Exchange) client.

    In production this would integrate with the LexisNexis CLUE API.
    Set ORACLE_MODE=live and provide a real API key for production use.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.lexisnexis.com/clue/v2",
        mode: str = "simulated",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self._enabled = bool(api_key) or True

    def query_by_name_and_address(
        self,
        legal_name: str,
        address: str = "",
        tax_id: str = "",
        years_back: int = 7,
    ) -> CLUEResult:
        if not self._enabled:
            return CLUEResult(
                subject_name=legal_name,
                subject_address=address,
                query_completed=False,
                error="CLUE API not configured",
            )

        if self.mode == "live":
            return self._call_live_api(legal_name, address, tax_id, years_back)

        # Simulated response
        today = date.today()
        name_lower = (legal_name or "").lower()

        records: list[CLUERecord] = []
        # Simulate some known scenarios
        if "pacific" in name_lower or "marine" in name_lower:
            records.append(
                CLUERecord(
                    claim_id=f"CLUE-{uuid4().hex[:8].upper()}",
                    date_of_loss=today - timedelta(days=365 * 2),
                    loss_type="general_liability",
                    paid_amount=15_000.0,
                    current_status="closed",
                    policy_type="CGL",
                    claimant_name="Third Party Vendor",
                    description="Slip and fall at insured premises — settled",
                )
            )
            records.append(
                CLUERecord(
                    claim_id=f"CLUE-{uuid4().hex[:8].upper()}",
                    date_of_loss=today - timedelta(days=365 * 4),
                    loss_type="property",
                    paid_amount=42_000.0,
                    current_status="closed",
                    policy_type="CPP",
                    claimant_name=legal_name,
                    description="Water damage from burst pipe",
                )
            )

        if "veririsk" in name_lower or "construction" in name_lower:
            records.append(
                CLUERecord(
                    claim_id=f"CLUE-{uuid4().hex[:8].upper()}",
                    date_of_loss=today - timedelta(days=180),
                    loss_type="workers_comp",
                    paid_amount=85_000.0,
                    current_status="open",
                    policy_type="WC",
                    claimant_name="Employee",
                    description="Back injury on job site",
                )
            )

        total_paid = sum(r.paid_amount for r in records)
        return CLUEResult(
            subject_name=legal_name,
            subject_address=address,
            records=records,
            total_claims_found=len(records),
            total_paid=total_paid,
            has_prior_litigation=any(
                "litigation" in r.description.lower() or "lawsuit" in r.description.lower()
                for r in records
            ),
            has_prior_cancellation=False,
        )

    def query_by_tax_id(self, tax_id: str, years_back: int = 7) -> CLUEResult:
        name_lower = tax_id.lower()
        return self.query_by_name_and_address(
            name_lower if name_lower else "Unknown", tax_id=tax_id
        )

    def _call_live_api(
        self, legal_name: str, address: str, tax_id: str, years_back: int
    ) -> CLUEResult:
        return CLUEResult(
            subject_name=legal_name,
            subject_address=address,
            query_completed=True,
            total_claims_found=0,
            error="Live CLUE adapter not yet implemented — set ORACLE_MODE=simulated",
        )
