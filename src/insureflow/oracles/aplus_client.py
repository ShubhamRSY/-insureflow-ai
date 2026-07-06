from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from uuid import uuid4

from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.integrations.parsers import parse_aplus_response
from insureflow.oracles._live import build_oracle_http, resolve_integration_mode

logger = logging.getLogger(__name__)


class PropertyClaimType(str, Enum):
    FIRE = "fire"
    WIND = "wind"
    THEFT = "theft"
    WATER_DAMAGE = "water_damage"
    VANDALISM = "vandalism"
    HAIL = "hail"
    LIGHTNING = "lightning"
    OTHER = "other"


@dataclass
class APlusRecord:
    claim_id: str
    property_address: str
    date_of_loss: date
    claim_type: PropertyClaimType
    paid_amount: float
    current_status: str
    policy_type: str
    description: str = ""


@dataclass
class APlusResult:
    subject_name: str
    subject_address: str
    records: list[APlusRecord] = field(default_factory=list)
    total_claims_found: int = 0
    total_paid: float = 0.0
    has_repeated_property_claims: bool = False
    has_arson_or_fraud_flag: bool = False
    query_completed: bool = True
    error: str = ""

    @property
    def summary(self) -> str:
        if self.error:
            return f"A-PLUS query failed: {self.error}"
        parts = [f"A-PLUS returned {self.total_claims_found} property records for {self.subject_name}"]
        if self.has_repeated_property_claims:
            parts.append("Repeated property claims detected")
        if self.has_arson_or_fraud_flag:
            parts.append("Arson/fraud flag present")
        return " | ".join(parts)


class APlusClient:
    """Simulated A-PLUS (Automated Property Loss Underwriting System) client.

    In production this would integrate with the Verisk A-PLUS API.
    Returns deterministic mock property loss data matching the submission.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.verisk.com/aplus/v2",
        mode: str = "simulated",
        query_path: str = "/queries",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self.query_path = query_path
        self.http = build_oracle_http(api_key, base_url)
        self._enabled = True

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

    def query_by_property(
        self,
        legal_name: str,
        property_address: str = "",
        tax_id: str = "",
        years_back: int = 7,
    ) -> APlusResult:
        if not self._enabled:
            return APlusResult(
                subject_name=legal_name,
                subject_address=property_address,
                query_completed=False,
                error="A-PLUS API not configured",
            )

        resolved = self._resolved_mode()
        if resolved == "live":
            return self._call_live_api(legal_name, property_address, tax_id, years_back)
        if resolved == "misconfigured":
            return APlusResult(
                subject_name=legal_name,
                subject_address=property_address,
                query_completed=False,
                error="A-PLUS live mode requires APLUS_API_KEY or VERISK_API_KEY and APLUS_API_URL",
            )

        return self._simulated_query(legal_name, property_address, tax_id, years_back)

    def _call_live_api(self, legal_name: str, property_address: str, tax_id: str, years_back: int) -> APlusResult:
        try:
            resp = self.http.post(
                self.query_path,
                {
                    "legal_name": legal_name,
                    "property_address": property_address,
                    "tax_id": tax_id,
                    "years_back": years_back,
                },
            )
            if not resp.ok:
                return APlusResult(
                    subject_name=legal_name,
                    subject_address=property_address,
                    query_completed=False,
                    error=f"A-PLUS API HTTP {resp.status_code}",
                )
            parsed = parse_aplus_response(resp.json_dict())
            records: list[APlusRecord] = []
            for raw in parsed.get("records", []):
                claim_type_raw = str(raw.get("claim_type", "other")).lower()
                try:
                    claim_type = PropertyClaimType(claim_type_raw)
                except ValueError:
                    claim_type = PropertyClaimType.OTHER
                dol = raw.get("date_of_loss") or raw.get("loss_date")
                loss_date = date.fromisoformat(str(dol)[:10]) if dol else date.today()
                records.append(
                    APlusRecord(
                        claim_id=str(raw.get("claim_id", raw.get("id", ""))),
                        property_address=str(raw.get("property_address", property_address)),
                        date_of_loss=loss_date,
                        claim_type=claim_type,
                        paid_amount=float(raw.get("paid_amount", 0) or 0),
                        current_status=str(raw.get("current_status", raw.get("status", "closed"))),
                        policy_type=str(raw.get("policy_type", "")),
                        description=str(raw.get("description", "")),
                    )
                )
            return APlusResult(
                subject_name=legal_name,
                subject_address=property_address,
                records=records,
                total_claims_found=int(parsed.get("total_claims_found", len(records))),
                total_paid=float(parsed.get("total_paid", sum(r.paid_amount for r in records))),
                has_repeated_property_claims=bool(parsed.get("has_repeated_property_claims")),
                has_arson_or_fraud_flag=bool(parsed.get("has_arson_or_fraud_flag")),
            )
        except IntegrationHTTPError as exc:
            logger.exception("A-PLUS live query failed")
            return APlusResult(
                subject_name=legal_name,
                subject_address=property_address,
                query_completed=False,
                error=str(exc),
            )

    def _simulated_query(self, legal_name: str, property_address: str, tax_id: str, years_back: int) -> APlusResult:
        today = date.today()
        name_lower = (legal_name or "").lower()
        addr_lower = (property_address or "").lower()

        records: list[APlusRecord] = []

        if "pacific" in name_lower or "marine" in name_lower:
            records.append(
                APlusRecord(
                    claim_id=f"APLUS-{uuid4().hex[:8].upper()}",
                    property_address=property_address or "123 Harbor Blvd",
                    date_of_loss=today - timedelta(days=365 * 3),
                    claim_type=PropertyClaimType.WATER_DAMAGE,
                    paid_amount=28_000.0,
                    current_status="closed",
                    policy_type="CPP",
                    description="Pipe burst in warehouse — water damage to inventory",
                )
            )

        if "veririsk" in name_lower or "construction" in name_lower:
            records.append(
                APlusRecord(
                    claim_id=f"APLUS-{uuid4().hex[:8].upper()}",
                    property_address=property_address or "456 Industrial Dr",
                    date_of_loss=today - timedelta(days=90),
                    claim_type=PropertyClaimType.FIRE,
                    paid_amount=320_000.0,
                    current_status="open",
                    policy_type="CPP",
                    description="Electrical fire in workshop — building and contents damaged",
                )
            )
            records.append(
                APlusRecord(
                    claim_id=f"APLUS-{uuid4().hex[:8].upper()}",
                    property_address=property_address or "456 Industrial Dr",
                    date_of_loss=today - timedelta(days=365 * 2),
                    claim_type=PropertyClaimType.THEFT,
                    paid_amount=12_000.0,
                    current_status="closed",
                    policy_type="CPP",
                    description="Tools and equipment stolen from job site",
                )
            )

        if "northwind" in name_lower:
            records.append(
                APlusRecord(
                    claim_id=f"APLUS-{uuid4().hex[:8].upper()}",
                    property_address=property_address or "789 Main St",
                    date_of_loss=today - timedelta(days=365 * 5),
                    claim_type=PropertyClaimType.HAIL,
                    paid_amount=18_500.0,
                    current_status="closed",
                    policy_type="CPP",
                    description="Hail damage to roof — replaced",
                )
            )

        if "coastal" in addr_lower or "beach" in addr_lower:
            records.append(
                APlusRecord(
                    claim_id=f"APLUS-{uuid4().hex[:8].upper()}",
                    property_address=property_address,
                    date_of_loss=today - timedelta(days=365),
                    claim_type=PropertyClaimType.WIND,
                    paid_amount=95_000.0,
                    current_status="closed",
                    policy_type="CPP",
                    description="Wind damage from tropical storm — roof and awning",
                )
            )

        total_paid = sum(r.paid_amount for r in records)
        return APlusResult(
            subject_name=legal_name,
            subject_address=property_address,
            records=records,
            total_claims_found=len(records),
            total_paid=total_paid,
            has_repeated_property_claims=len(records) >= 2,
            has_arson_or_fraud_flag="arson" in str(records).lower() or "fraud" in str(records).lower(),
        )
