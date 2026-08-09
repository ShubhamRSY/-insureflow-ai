from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import uuid4

from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.integrations.parsers import parse_bureau_response
from insureflow.oracles._live import build_oracle_http, resolve_integration_mode

logger = logging.getLogger(__name__)


@dataclass
class TradeCreditRecord:
    """A single trade credit line / payment-history record from a commercial bureau."""

    trade_id: str
    creditor: str
    credit_limit: float
    highest_credit: float
    current_balance: float
    past_due_days: int
    payment_status: str  # current | past_due | delinquent | derogatory
    opened_at: date

    @property
    def is_derogatory(self) -> bool:
        return self.payment_status in {"past_due", "delinquent", "derogatory"}


@dataclass
class BureauResult:
    """Commercial credit bureau profile (D&B / Experian-style)."""

    subject_name: str
    tax_id: str
    paydex_score: int = 0  # 0 = no score, 1-100 payment index
    financial_strength_rating: str = ""  # e.g. 5A, 4A, 3A, 2A, 1A, ... (D&B style)
    failure_risk_score: float = 0.0  # probability of failure within 12 months (0-1)
    delinquency_score: float = 0.0  # probability of 90+ day delinquency (0-1)
    records: list[TradeCreditRecord] = field(default_factory=list)
    total_credit_limit: float = 0.0
    total_current_balance: float = 0.0
    number_of_derogatory_trades: int = 0
    has_bankruptcy_indicator: bool = False
    has_lien_indicator: bool = False
    has_judgment_indicator: bool = False
    query_completed: bool = True
    error: str = ""
    synthetic: bool = False
    mode: str = ""

    @property
    def risk_band(self) -> str:
        if self.has_bankruptcy_indicator or self.failure_risk_score >= 0.4 or self.paydex_score < 40:
            return "critical"
        if self.number_of_derogatory_trades >= 2 or self.failure_risk_score >= 0.25:
            return "high"
        if self.paydex_score < 70:
            return "moderate"
        return "low"

    @property
    def summary(self) -> str:
        if self.error:
            return f"Bureau query failed: {self.error}"
        parts = [
            f"{self.subject_name}: Paydex {self.paydex_score}",
            f"Financial strength {self.financial_strength_rating or 'NR'}",
            f"Failure risk {self.failure_risk_score:.0%}",
        ]
        if self.has_bankruptcy_indicator:
            parts.append("BANKRUPTCY INDICATOR")
        if self.number_of_derogatory_trades:
            parts.append(f"{self.number_of_derogatory_trades} derogatory trade(s)")
        if self.synthetic or self.mode in {"simulated", "gateway_synthetic"}:
            parts.append("SYNTHETIC/UNVERIFIED")
        return " | ".join(parts)


class CreditBureauClient:
    """Simulated commercial credit bureau client (D&B / Experian business credit).

    In production this would integrate with the Dun & Bradstreet or Experian
    commercial credit API. Set ORACLE_MODE=live and provide a real API key.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.dnb.com/businesscredit/v2",
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

    def query_by_tax_id(self, tax_id: str, legal_name: str = "") -> BureauResult:
        if not self._enabled:
            return BureauResult(
                subject_name=legal_name or tax_id,
                tax_id=tax_id,
                query_completed=False,
                error="Credit bureau API not configured",
            )

        resolved = self._resolved_mode()
        if resolved == "live":
            return self._call_live_api(tax_id, legal_name)
        if resolved == "misconfigured":
            return BureauResult(
                subject_name=legal_name or tax_id,
                tax_id=tax_id,
                query_completed=False,
                error="Credit bureau live mode requires BUREAU_API_KEY and BUREAU_API_URL",
            )

        return self._simulate(tax_id, legal_name)

    def _simulate(self, tax_id: str, legal_name: str) -> BureauResult:
        today = date.today()
        name_lower = (legal_name or "").lower()
        records: list[TradeCreditRecord] = []

        if "pacific" in name_lower or "marine" in name_lower:
            records = [
                TradeCreditRecord(
                    trade_id=f"TR-{uuid4().hex[:8].upper()}",
                    creditor="West Coast Freight Partners",
                    credit_limit=250_000.0,
                    highest_credit=240_000.0,
                    current_balance=120_000.0,
                    past_due_days=0,
                    payment_status="current",
                    opened_at=today - timedelta(days=365 * 3),
                ),
                TradeCreditRecord(
                    trade_id=f"TR-{uuid4().hex[:8].upper()}",
                    creditor="Refrigeration Supply Co",
                    credit_limit=95_000.0,
                    highest_credit=95_000.0,
                    current_balance=42_000.0,
                    past_due_days=0,
                    payment_status="current",
                    opened_at=today - timedelta(days=365 * 2),
                ),
                TradeCreditRecord(
                    trade_id=f"TR-{uuid4().hex[:8].upper()}",
                    creditor="Industrial Pallet Services",
                    credit_limit=60_000.0,
                    highest_credit=58_000.0,
                    current_balance=31_000.0,
                    past_due_days=35,
                    payment_status="past_due",
                    opened_at=today - timedelta(days=400),
                ),
            ]
            return BureauResult(
                subject_name=legal_name or tax_id,
                tax_id=tax_id,
                paydex_score=58,
                financial_strength_rating="3A",
                failure_risk_score=0.28,
                delinquency_score=0.31,
                records=records,
                total_credit_limit=sum(r.credit_limit for r in records),
                total_current_balance=sum(r.current_balance for r in records),
                number_of_derogatory_trades=sum(1 for r in records if r.is_derogatory),
                has_bankruptcy_indicator=False,
                has_lien_indicator=True,
                has_judgment_indicator=False,
                synthetic=True,
                mode="simulated",
            )

        if "veririsk" in name_lower or "construction" in name_lower:
            records = [
                TradeCreditRecord(
                    trade_id=f"TR-{uuid4().hex[:8].upper()}",
                    creditor="Cement Supply Co",
                    credit_limit=180_000.0,
                    highest_credit=175_000.0,
                    current_balance=160_000.0,
                    past_due_days=90,
                    payment_status="delinquent",
                    opened_at=today - timedelta(days=365),
                ),
                TradeCreditRecord(
                    trade_id=f"TR-{uuid4().hex[:8].upper()}",
                    creditor="Heavy Equipment Leasing",
                    credit_limit=420_000.0,
                    highest_credit=400_000.0,
                    current_balance=310_000.0,
                    past_due_days=120,
                    payment_status="derogatory",
                    opened_at=today - timedelta(days=365 * 2),
                ),
            ]
            return BureauResult(
                subject_name=legal_name or tax_id,
                tax_id=tax_id,
                paydex_score=35,
                financial_strength_rating="2A",
                failure_risk_score=0.46,
                delinquency_score=0.52,
                records=records,
                total_credit_limit=sum(r.credit_limit for r in records),
                total_current_balance=sum(r.current_balance for r in records),
                number_of_derogatory_trades=sum(1 for r in records if r.is_derogatory),
                has_bankruptcy_indicator=True,
                has_lien_indicator=True,
                has_judgment_indicator=True,
                synthetic=True,
                mode="simulated",
            )

        # Default healthy profile
        records = [
            TradeCreditRecord(
                trade_id=f"TR-{uuid4().hex[:8].upper()}",
                creditor="National Office Supplies",
                credit_limit=75_000.0,
                highest_credit=72_000.0,
                current_balance=18_000.0,
                past_due_days=0,
                payment_status="current",
                opened_at=today - timedelta(days=365 * 4),
            )
        ]
        return BureauResult(
            subject_name=legal_name or tax_id,
            tax_id=tax_id,
            paydex_score=82,
            financial_strength_rating="3A",
            failure_risk_score=0.09,
            delinquency_score=0.07,
            records=records,
            total_credit_limit=sum(r.credit_limit for r in records),
            total_current_balance=sum(r.current_balance for r in records),
            number_of_derogatory_trades=0,
            has_bankruptcy_indicator=False,
            has_lien_indicator=False,
            has_judgment_indicator=False,
            synthetic=True,
            mode="simulated",
        )

    def _call_live_api(self, tax_id: str, legal_name: str) -> BureauResult:
        try:
            resp = self.http.post(
                self.query_path,
                {"tax_id": tax_id, "legal_name": legal_name},
            )
            if not resp.ok:
                return BureauResult(
                    subject_name=legal_name or tax_id,
                    tax_id=tax_id,
                    query_completed=False,
                    error=f"Credit bureau API HTTP {resp.status_code}",
                )
            parsed = parse_bureau_response(resp.json_dict())
            records: list[TradeCreditRecord] = []
            for raw in parsed.get("records", []):
                opened = raw.get("opened_at") or raw.get("opened_date")
                if isinstance(opened, str):
                    try:
                        opened_date = date.fromisoformat(opened[:10])
                    except ValueError:
                        opened_date = date.today()
                else:
                    opened_date = date.today()
                records.append(
                    TradeCreditRecord(
                        trade_id=str(raw.get("trade_id", raw.get("id", ""))),
                        creditor=str(raw.get("creditor", "")),
                        credit_limit=float(raw.get("credit_limit", 0) or 0),
                        highest_credit=float(raw.get("highest_credit", 0) or 0),
                        current_balance=float(raw.get("current_balance", 0) or 0),
                        past_due_days=int(raw.get("past_due_days", 0) or 0),
                        payment_status=str(raw.get("payment_status", "current")),
                        opened_at=opened_date,
                    )
                )
            return BureauResult(
                subject_name=legal_name or tax_id,
                tax_id=tax_id,
                paydex_score=int(parsed.get("paydex_score", 0) or 0),
                financial_strength_rating=str(parsed.get("financial_strength_rating", "")),
                failure_risk_score=float(parsed.get("failure_risk_score", 0) or 0),
                delinquency_score=float(parsed.get("delinquency_score", 0) or 0),
                records=records,
                total_credit_limit=float(parsed.get("total_credit_limit", sum(r.credit_limit for r in records))),
                total_current_balance=float(parsed.get("total_current_balance", sum(r.current_balance for r in records))),
                number_of_derogatory_trades=int(parsed.get("number_of_derogatory_trades", sum(1 for r in records if r.is_derogatory))),
                has_bankruptcy_indicator=bool(parsed.get("has_bankruptcy_indicator")),
                has_lien_indicator=bool(parsed.get("has_lien_indicator")),
                has_judgment_indicator=bool(parsed.get("has_judgment_indicator")),
                synthetic=bool(parsed.get("synthetic", False)),
                mode=str(parsed.get("mode") or "live"),
            )
        except IntegrationHTTPError as exc:
            logger.exception("Credit bureau live query failed")
            return BureauResult(
                subject_name=legal_name or tax_id,
                tax_id=tax_id,
                query_completed=False,
                error=str(exc),
            )
