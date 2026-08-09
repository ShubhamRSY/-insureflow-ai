from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import uuid4

from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.integrations.parsers import parse_osha_response
from insureflow.oracles._live import build_oracle_http, resolve_integration_mode

logger = logging.getLogger(__name__)


@dataclass
class OSHAViolation:
    """A single OSHA inspection violation."""

    violation_id: str
    inspection_number: str
    inspection_type: str  # complaint | programmed | accident | referral | follow-up
    violation_type: str  # serious | willful | repeat | other
    description: str = ""
    penalty: float = 0.0
    inspected_at: date = field(default_factory=date.today)
    closed: bool = False
    items: int = 0
    serious: bool = False

    @property
    def risk_weight(self) -> float:
        if self.violation_type == "willful":
            return 1.0
        if self.violation_type == "repeat":
            return 0.8
        if self.violation_type == "serious":
            return 0.6
        return 0.3


@dataclass
class OSHAInspectionResult:
    """OSHA inspection / violation history for a workplace."""

    subject_name: str
    tax_id: str
    violations: list[OSHAViolation] = field(default_factory=list)
    total_violations: int = 0
    total_penalty: float = 0.0
    has_willful_violation: bool = False
    has_repeat_violation: bool = False
    has_open_inspection: bool = False
    safety_rating: str = "not_scored"  # low | moderate | high | critical | not_scored
    query_completed: bool = True
    error: str = ""
    synthetic: bool = False
    mode: str = ""

    @property
    def summary(self) -> str:
        if self.error:
            return f"OSHA query failed: {self.error}"
        parts = [f"{self.total_violations} violation(s) for {self.subject_name}"]
        if self.total_penalty:
            parts.append(f"${self.total_penalty:,.0f} in penalties")
        if self.has_willful_violation:
            parts.append("WILLFUL")
        if self.has_repeat_violation:
            parts.append("REPEAT")
        if self.has_open_inspection:
            parts.append("OPEN INSPECTION")
        if self.synthetic or self.mode in {"simulated", "gateway_synthetic"}:
            parts.append("SYNTHETIC/UNVERIFIED")
        return " | ".join(parts)


class OSHAClient:
    """Simulated OSHA (Occupational Safety and Health Administration) client.

    In production this would call the OSHA Establishment Search / OnSite API.
    Set ORACLE_MODE=live and provide a real API key.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.osha.gov/inspections/v1",
        mode: str = "simulated",
        query_path: str = "/searches",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self.query_path = query_path
        self.http = build_oracle_http(api_key, base_url)
        self._enabled = True

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

    def query_by_entity(self, legal_name: str, tax_id: str = "", naics_code: str = "") -> OSHAInspectionResult:
        if not self._enabled:
            return OSHAInspectionResult(
                subject_name=legal_name,
                tax_id=tax_id,
                query_completed=False,
                error="OSHA API not configured",
            )

        resolved = self._resolved_mode()
        if resolved == "live":
            return self._call_live_api(legal_name, tax_id, naics_code)
        if resolved == "misconfigured":
            return OSHAInspectionResult(
                subject_name=legal_name,
                tax_id=tax_id,
                query_completed=False,
                error="OSHA live mode requires OSHA_API_KEY and OSHA_API_URL",
            )

        return self._simulate(legal_name, tax_id)

    def _simulate(self, legal_name: str, tax_id: str) -> OSHAInspectionResult:
        today = date.today()
        name_lower = (legal_name or "").lower()
        violations: list[OSHAViolation] = []

        if "veririsk" in name_lower or "construction" in name_lower:
            violations = [
                OSHAViolation(
                    violation_id=f"VIO-{uuid4().hex[:8].upper()}",
                    inspection_number=f"INSP-{uuid4().hex[:8].upper()}",
                    inspection_type="accident",
                    violation_type="willful",
                    description="Failure to provide fall protection on elevated work platform — fatality exposure",
                    penalty=72_000.0,
                    inspected_at=today - timedelta(days=210),
                    closed=False,
                    items=3,
                    serious=True,
                ),
                OSHAViolation(
                    violation_id=f"VIO-{uuid4().hex[:8].upper()}",
                    inspection_number=f"INSP-{uuid4().hex[:8].upper()}",
                    inspection_type="complaint",
                    violation_type="repeat",
                    description="Lockout/tagout procedures not followed on machinery",
                    penalty=24_000.0,
                    inspected_at=today - timedelta(days=90),
                    closed=False,
                    items=2,
                    serious=True,
                ),
                OSHAViolation(
                    violation_id=f"VIO-{uuid4().hex[:8].upper()}",
                    inspection_number=f"INSP-{uuid4().hex[:8].upper()}",
                    inspection_type="programmed",
                    violation_type="serious",
                    description="Inadequate hazard communication program",
                    penalty=9_000.0,
                    inspected_at=today - timedelta(days=400),
                    closed=True,
                    items=1,
                    serious=True,
                ),
            ]
            return OSHAInspectionResult(
                subject_name=legal_name,
                tax_id=tax_id,
                violations=violations,
                total_violations=len(violations),
                total_penalty=sum(v.penalty for v in violations),
                has_willful_violation=True,
                has_repeat_violation=True,
                has_open_inspection=True,
                safety_rating="critical",
                synthetic=True,
                mode="simulated",
            )

        if "pacific" in name_lower or "marine" in name_lower:
            violations = [
                OSHAViolation(
                    violation_id=f"VIO-{uuid4().hex[:8].upper()}",
                    inspection_number=f"INSP-{uuid4().hex[:8].upper()}",
                    inspection_type="complaint",
                    violation_type="serious",
                    description="Blocked exit route in cold-storage facility",
                    penalty=11_000.0,
                    inspected_at=today - timedelta(days=160),
                    closed=True,
                    items=1,
                    serious=True,
                )
            ]
            return OSHAInspectionResult(
                subject_name=legal_name,
                tax_id=tax_id,
                violations=violations,
                total_violations=len(violations),
                total_penalty=11_000.0,
                has_willful_violation=False,
                has_repeat_violation=False,
                has_open_inspection=False,
                safety_rating="moderate",
                synthetic=True,
                mode="simulated",
            )

        return OSHAInspectionResult(
            subject_name=legal_name,
            tax_id=tax_id,
            violations=[],
            total_violations=0,
            total_penalty=0.0,
            has_willful_violation=False,
            has_repeat_violation=False,
            has_open_inspection=False,
            safety_rating="low",
            synthetic=True,
            mode="simulated",
        )

    def _call_live_api(self, legal_name: str, tax_id: str, naics_code: str) -> OSHAInspectionResult:
        try:
            resp = self.http.post(
                self.query_path,
                {"legal_name": legal_name, "tax_id": tax_id, "naics_code": naics_code},
            )
            if not resp.ok:
                return OSHAInspectionResult(
                    subject_name=legal_name,
                    tax_id=tax_id,
                    query_completed=False,
                    error=f"OSHA API HTTP {resp.status_code}",
                )
            parsed = parse_osha_response(resp.json_dict())
            violations: list[OSHAViolation] = []
            for raw in parsed.get("violations", []):
                inspected = raw.get("inspected_at") or raw.get("inspection_date")
                if isinstance(inspected, str):
                    try:
                        inspected_date = date.fromisoformat(inspected[:10])
                    except ValueError:
                        inspected_date = date.today()
                else:
                    inspected_date = date.today()
                v_type = str(raw.get("violation_type", "other"))
                violations.append(
                    OSHAViolation(
                        violation_id=str(raw.get("violation_id", raw.get("id", ""))),
                        inspection_number=str(raw.get("inspection_number", "")),
                        inspection_type=str(raw.get("inspection_type", "programmed")),
                        violation_type=v_type,
                        description=str(raw.get("description", "")),
                        penalty=float(raw.get("penalty", 0) or 0),
                        inspected_at=inspected_date,
                        closed=bool(raw.get("closed", False)),
                        items=int(raw.get("items", 0) or 0),
                        serious=bool(raw.get("serious", False)) or v_type == "serious",
                    )
                )
            return OSHAInspectionResult(
                subject_name=legal_name,
                tax_id=tax_id,
                violations=violations,
                total_violations=int(parsed.get("total_violations", len(violations))),
                total_penalty=float(parsed.get("total_penalty", sum(v.penalty for v in violations)) or 0),
                has_willful_violation=bool(parsed.get("has_willful_violation")),
                has_repeat_violation=bool(parsed.get("has_repeat_violation")),
                has_open_inspection=bool(parsed.get("has_open_inspection")),
                safety_rating=str(parsed.get("safety_rating", "not_scored")),
                synthetic=bool(parsed.get("synthetic", False)),
                mode=str(parsed.get("mode") or "live"),
            )
        except IntegrationHTTPError as exc:
            logger.exception("OSHA live query failed")
            return OSHAInspectionResult(
                subject_name=legal_name,
                tax_id=tax_id,
                query_completed=False,
                error=str(exc),
            )
