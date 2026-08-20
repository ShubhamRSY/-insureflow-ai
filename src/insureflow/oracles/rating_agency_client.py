from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.integrations.parsers import parse_rating_agency_response
from insureflow.oracles._live import build_oracle_http, resolve_integration_mode

logger = logging.getLogger(__name__)

# Long-term issuer rating scale (investment vs speculative grade break).
SPECULATIVE_BREAK = "BB+"


@dataclass
class CreditRatingResult:
    """Issuer credit rating from a rating agency (Moody's / S&P style)."""

    subject_name: str
    tax_id: str
    issuer_rating: str = ""  # e.g. AAA, AA+, AA, ..., BBB-, BB+, ..., D
    outlook: str = "stable"  # positive | stable | negative | developing
    watch: str = ""  # "on-watch" | ""
    rating_date: date = field(default_factory=date.today)
    agency: str = "rating_agency"
    not_rated: bool = False
    query_completed: bool = True
    error: str = ""
    synthetic: bool = False
    mode: str = ""

    @property
    def is_investment_grade(self) -> bool:
        if self.not_rated or not self.issuer_rating:
            return False
        grade_rank = {
            "AAA": 22,
            "AA+": 21,
            "AA": 20,
            "AA-": 19,
            "A+": 18,
            "A": 17,
            "A-": 16,
            "BBB+": 15,
            "BBB": 14,
            "BBB-": 13,
            "BB+": 12,
            "BB": 11,
            "BB-": 10,
            "B+": 9,
            "B": 8,
            "B-": 7,
            "CCC+": 6,
            "CCC": 5,
            "CCC-": 4,
            "CC": 3,
            "C": 2,
            "D": 1,
        }
        rank = grade_rank.get(self.issuer_rating.upper(), 0)
        return rank >= 13

    @property
    def risk_band(self) -> str:
        if self.not_rated:
            return "moderate"
        if self.issuer_rating.upper() in {"D", "CC", "C"}:
            return "critical"
        if self.outlook == "negative" or self.issuer_rating.upper().startswith(("B", "CCC", "CC")):
            return "high" if not self.is_investment_grade else "moderate"
        if self.outlook == "developing":
            return "moderate"
        return "low"

    @property
    def summary(self) -> str:
        if self.error:
            return f"Rating agency query failed: {self.error}"
        if self.not_rated:
            return f"{self.subject_name}: Not rated by {self.agency}"
        parts = [f"{self.subject_name}: {self.issuer_rating} ({self.outlook})"]
        if self.watch:
            parts.append(self.watch)
        if self.synthetic:
            parts.append("SYNTHETIC/UNVERIFIED")
        return " | ".join(parts)


class CreditRatingAgencyClient:
    """Credit-rating-agency client (Moody's / S&P style).

    Makes real HTTP calls to the rating agency API.
    Set ORACLE_MODE=auto (default) and provide a real API key for live queries.
    Without a valid API key, queries return an error — never fake data.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.spglobal.com/ratings/v2",
        mode: str = "auto",
        query_path: str = "/entities",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self.query_path = query_path
        self.http = build_oracle_http(api_key, base_url)
        self._enabled = True

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

    def query_by_entity(self, legal_name: str, tax_id: str = "") -> CreditRatingResult:
        if not self._enabled:
            return CreditRatingResult(
                subject_name=legal_name,
                tax_id=tax_id,
                query_completed=False,
                error="Rating agency API not configured",
            )

        resolved = self._resolved_mode()
        if resolved == "misconfigured":
            return CreditRatingResult(
                subject_name=legal_name,
                tax_id=tax_id,
                query_completed=False,
                error="Rating agency requires RATING_AGENCY_API_KEY and RATING_AGENCY_API_URL to be configured",
            )

        return self._call_live_api(legal_name, tax_id)

    def _call_live_api(self, legal_name: str, tax_id: str) -> CreditRatingResult:
        try:
            resp = self.http.post(
                self.query_path,
                {"legal_name": legal_name, "tax_id": tax_id},
            )
            if not resp.ok:
                return CreditRatingResult(
                    subject_name=legal_name,
                    tax_id=tax_id,
                    query_completed=False,
                    error=f"Rating agency API HTTP {resp.status_code}",
                )
            parsed = parse_rating_agency_response(resp.json_dict())
            return CreditRatingResult(
                subject_name=legal_name,
                tax_id=tax_id,
                issuer_rating=str(parsed.get("issuer_rating", "")),
                outlook=str(parsed.get("outlook", "stable")),
                watch=str(parsed.get("watch", "")),
                agency=str(parsed.get("agency", "rating_agency")),
                not_rated=bool(parsed.get("not_rated", False)),
                synthetic=bool(parsed.get("synthetic", False)),
                mode=str(parsed.get("mode") or "live"),
            )
        except IntegrationHTTPError as exc:
            logger.exception("Rating agency live query failed")
            return CreditRatingResult(
                subject_name=legal_name,
                tax_id=tax_id,
                query_completed=False,
                error=str(exc),
            )
