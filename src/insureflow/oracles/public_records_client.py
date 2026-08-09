from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import uuid4

from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.integrations.parsers import parse_public_records_response
from insureflow.oracles._live import build_oracle_http, resolve_integration_mode

logger = logging.getLogger(__name__)


@dataclass
class PublicRecord:
    """A single public-record event (judgment, lien, UCC filing, bankruptcy)."""

    record_id: str
    record_type: str  # judgment | lien | ucc | bankruptcy | litigation
    jurisdiction: str
    amount: float = 0.0
    filed_at: date = field(default_factory=date.today)
    status: str = "open"  # open | discharged | satisfied | withdrawn
    plaintiff: str = ""
    defendant: str = ""
    description: str = ""

    @property
    def is_active(self) -> bool:
        return self.status in {"open", "pending"}


@dataclass
class PublicRecordsResult:
    """Public-record search profile: litigation history, UCC filings, liens, judgments."""

    subject_name: str
    tax_id: str
    records: list[PublicRecord] = field(default_factory=list)
    total_records_found: int = 0
    total_judgment_amount: float = 0.0
    has_bankruptcy: bool = False
    has_active_judgment: bool = False
    has_ucc_filing: bool = False
    has_active_lien: bool = False
    query_completed: bool = True
    error: str = ""
    synthetic: bool = False
    mode: str = ""

    @property
    def risk_band(self) -> str:
        if self.has_bankruptcy:
            return "critical"
        if self.has_active_judgment or self.has_active_lien or self.total_judgment_amount >= 100_000:
            return "high"
        if self.total_records_found:
            return "moderate"
        return "low"

    @property
    def summary(self) -> str:
        if self.error:
            return f"Public records query failed: {self.error}"
        parts = [f"{self.total_records_found} public record(s) for {self.subject_name}"]
        if self.has_bankruptcy:
            parts.append("BANKRUPTCY")
        if self.has_active_judgment:
            parts.append("ACTIVE JUDGMENT")
        if self.has_active_lien:
            parts.append("ACTIVE LIEN")
        if self.has_ucc_filing:
            parts.append("UCC filing")
        if self.synthetic or self.mode in {"simulated", "gateway_synthetic"}:
            parts.append("SYNTHETIC/UNVERIFIED")
        return " | ".join(parts)


class PublicRecordsClient:
    """Simulated public-record client (judgments, liens, UCC filings, bankruptcy).

    In production this would integrate with LexisNexis Public Records, Courthouse
    Direct, or a similar court/UCC database. Set ORACLE_MODE=live and provide a
    real API key.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.lexisnexis.com/publicrecords/v2",
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

    def query_by_entity(self, legal_name: str, tax_id: str = "", address: str = "") -> PublicRecordsResult:
        if not self._enabled:
            return PublicRecordsResult(
                subject_name=legal_name,
                tax_id=tax_id,
                query_completed=False,
                error="Public records API not configured",
            )

        resolved = self._resolved_mode()
        if resolved == "live":
            return self._call_live_api(legal_name, tax_id, address)
        if resolved == "misconfigured":
            return PublicRecordsResult(
                subject_name=legal_name,
                tax_id=tax_id,
                query_completed=False,
                error="Public records live mode requires PUBLIC_RECORDS_API_KEY and PUBLIC_RECORDS_API_URL",
            )

        return self._simulate(legal_name, tax_id, address)

    def _simulate(self, legal_name: str, tax_id: str, address: str) -> PublicRecordsResult:
        today = date.today()
        name_lower = (legal_name or "").lower()
        records: list[PublicRecord] = []

        if "veririsk" in name_lower or "construction" in name_lower:
            records = [
                PublicRecord(
                    record_id=f"JUD-{uuid4().hex[:8].upper()}",
                    record_type="judgment",
                    jurisdiction="CA Superior Court, Alameda",
                    amount=125_000.0,
                    filed_at=today - timedelta(days=180),
                    status="open",
                    plaintiff="Subcontractor Trust",
                    defendant=legal_name,
                    description="Unpaid subcontractor judgment",
                ),
                PublicRecord(
                    record_id=f"UCC-{uuid4().hex[:8].upper()}",
                    record_type="ucc",
                    jurisdiction="California SOS",
                    amount=420_000.0,
                    filed_at=today - timedelta(days=120),
                    status="open",
                    description="Security interest — heavy equipment financing",
                ),
                PublicRecord(
                    record_id=f"LIE-{uuid4().hex[:8].upper()}",
                    record_type="lien",
                    jurisdiction="Internal Revenue Service",
                    amount=88_000.0,
                    filed_at=today - timedelta(days=90),
                    status="open",
                    description="Federal tax lien",
                ),
            ]
            return PublicRecordsResult(
                subject_name=legal_name,
                tax_id=tax_id,
                records=records,
                total_records_found=len(records),
                total_judgment_amount=125_000.0,
                has_bankruptcy=True,
                has_active_judgment=True,
                has_ucc_filing=True,
                has_active_lien=True,
                synthetic=True,
                mode="simulated",
            )

        if "pacific" in name_lower or "marine" in name_lower:
            records = [
                PublicRecord(
                    record_id=f"UCC-{uuid4().hex[:8].upper()}",
                    record_type="ucc",
                    jurisdiction="California SOS",
                    amount=310_000.0,
                    filed_at=today - timedelta(days=60),
                    status="open",
                    description="Security interest — fleet financing",
                )
            ]
            return PublicRecordsResult(
                subject_name=legal_name,
                tax_id=tax_id,
                records=records,
                total_records_found=len(records),
                total_judgment_amount=0.0,
                has_bankruptcy=False,
                has_active_judgment=False,
                has_ucc_filing=True,
                has_active_lien=False,
                synthetic=True,
                mode="simulated",
            )

        return PublicRecordsResult(
            subject_name=legal_name,
            tax_id=tax_id,
            records=[],
            total_records_found=0,
            total_judgment_amount=0.0,
            has_bankruptcy=False,
            has_active_judgment=False,
            has_ucc_filing=False,
            has_active_lien=False,
            synthetic=True,
            mode="simulated",
        )

    def _call_live_api(self, legal_name: str, tax_id: str, address: str) -> PublicRecordsResult:
        try:
            resp = self.http.post(
                self.query_path,
                {"legal_name": legal_name, "tax_id": tax_id, "address": address},
            )
            if not resp.ok:
                return PublicRecordsResult(
                    subject_name=legal_name,
                    tax_id=tax_id,
                    query_completed=False,
                    error=f"Public records API HTTP {resp.status_code}",
                )
            parsed = parse_public_records_response(resp.json_dict())
            records: list[PublicRecord] = []
            for raw in parsed.get("records", []):
                filed = raw.get("filed_at") or raw.get("filed_date")
                if isinstance(filed, str):
                    try:
                        filed_date = date.fromisoformat(filed[:10])
                    except ValueError:
                        filed_date = date.today()
                else:
                    filed_date = date.today()
                records.append(
                    PublicRecord(
                        record_id=str(raw.get("record_id", raw.get("id", ""))),
                        record_type=str(raw.get("record_type", "other")),
                        jurisdiction=str(raw.get("jurisdiction", "")),
                        amount=float(raw.get("amount", 0) or 0),
                        filed_at=filed_date,
                        status=str(raw.get("status", "open")),
                        plaintiff=str(raw.get("plaintiff", "")),
                        defendant=str(raw.get("defendant", legal_name)),
                        description=str(raw.get("description", "")),
                    )
                )
            return PublicRecordsResult(
                subject_name=legal_name,
                tax_id=tax_id,
                records=records,
                total_records_found=int(parsed.get("total_records_found", len(records))),
                total_judgment_amount=float(parsed.get("total_judgment_amount", 0) or 0),
                has_bankruptcy=bool(parsed.get("has_bankruptcy")),
                has_active_judgment=bool(parsed.get("has_active_judgment")),
                has_ucc_filing=bool(parsed.get("has_ucc_filing")),
                has_active_lien=bool(parsed.get("has_active_lien")),
                synthetic=bool(parsed.get("synthetic", False)),
                mode=str(parsed.get("mode") or "live"),
            )
        except IntegrationHTTPError as exc:
            logger.exception("Public records live query failed")
            return PublicRecordsResult(
                subject_name=legal_name,
                tax_id=tax_id,
                query_completed=False,
                error=str(exc),
            )
