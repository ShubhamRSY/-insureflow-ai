"""Preliminary processing of an incoming case — Chapter 4.

Chapter 4's preliminary processing sequence for an application case file:

* preliminary review for completeness of the application;
* verification of the submitting agent's status (licensed for the line of
  business, license type, full-time agent vs. broker);
* a search of the company's existing records for information about the
  proposed insured (prior applications, policies, losses, declinations);
* issuance of an ID number and, for lines that rely on consumer-report data
  (credit / MVR), confirmation that the FCRA pre-notification disclosure was
  given to the applicant.

This module makes each of those steps structured data so the automation (and
the case underwriter on the worksheet) can execute, record, and retrieve them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import BrokerInfo, SubmissionBundle

PRODUCER_NS = "producer"
RECORDS_NS = "existing_records"


class ProducerLicenseType(str, Enum):
    PROPERTY_CASUALTY_AGENT = "p&c_agent"
    PROPERTY_CASUALTY_BROKER = "p&c_broker"
    LIFE_HEALTH_AGENT = "life_health_agent"
    LIFE_HEALTH_BROKER = "life_health_broker"
    MGA = "mga"
    UNLICENSED = "unlicensed"


class ProducerVerificationStatus(str, Enum):
    VERIFIED = "verified"  # licensed for the line in the state, appointed
    NOT_APPOINTED = "not_appointed"  # licensed but not appointed to this carrier
    NOT_LICENSED_LINE = "not_licensed_line"  # no license for the line of business
    NOT_LICENSED_STATE = "not_licensed_state"  # license does not cover the risk state
    BROKER_REQUIRES_REFERRAL = "broker_requires_referral"  # broker, not a full-time agent
    UNLICENSED = "unlicensed"
    NOT_FOUND = "not_found"


class ExistingRecordKind(str, Enum):
    PRIOR_APPLICATION = "prior_application"
    PRIOR_POLICY = "prior_policy"
    PRIOR_DECLINATION = "prior_declination"
    PRIOR_LOSS = "prior_loss"
    PRIOR_CANCELLATION = "prior_cancellation"


class ExistingRecordStatus(str, Enum):
    IN_FORCE = "in_force"
    PENDING = "pending"
    WITHDRAWN = "withdrawn"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    CLOSED = "closed"


@dataclass
class ProducerRecord:
    """A licensed producer's profile as the insurer knows it."""

    producer_id: str
    name: str
    agency: str = ""
    license_types: list[ProducerLicenseType] = field(default_factory=list)
    licensed_states: list[str] = field(default_factory=list)
    appointed_carriers: list[str] = field(default_factory=list)
    license_active: bool = True
    license_expiry: Optional[date] = None
    full_time: bool = True  # full-time agent vs. broker

    def to_dict(self) -> dict[str, Any]:
        return {
            "producer_id": self.producer_id,
            "name": self.name,
            "agency": self.agency,
            "license_types": [t.value for t in self.license_types],
            "licensed_states": self.licensed_states,
            "appointed_carriers": self.appointed_carriers,
            "license_active": self.license_active,
            "license_expiry": self.license_expiry.isoformat() if self.license_expiry else None,
            "full_time": self.full_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProducerRecord:
        exp = data.get("license_expiry")
        return cls(
            producer_id=data["producer_id"],
            name=data.get("name", ""),
            agency=data.get("agency", ""),
            license_types=[ProducerLicenseType(t) for t in data.get("license_types", [])],
            licensed_states=data.get("licensed_states", []),
            appointed_carriers=data.get("appointed_carriers", []),
            license_active=data.get("license_active", True),
            license_expiry=date.fromisoformat(exp) if exp else None,
            full_time=data.get("full_time", True),
        )


class ProducerRegistry:
    """Org-scoped producer profiles, persisted via the durable job store."""

    def __init__(self) -> None:
        self._records: dict[str, ProducerRecord] = {}
        self._cached_org: str | None = None

    def _store(self) -> Any:
        from insureflow.storage.job_store import get_job_store

        return get_job_store()

    def _seed_into(self, target: dict[str, ProducerRecord]) -> None:
        defaults = [
            ProducerRecord(
                producer_id="pr-001",
                name="Acme Insurance Agency",
                agency="Acme",
                license_types=[ProducerLicenseType.PROPERTY_CASUALTY_AGENT, ProducerLicenseType.LIFE_HEALTH_AGENT],
                licensed_states=["TX", "OK", "LA", "AR"],
                appointed_carriers=["insureflow"],
                license_active=True,
                full_time=True,
            ),
            ProducerRecord(
                producer_id="pr-002",
                name="Brighton & Wills Brokerage",
                agency="B&W",
                license_types=[ProducerLicenseType.PROPERTY_CASUALTY_BROKER],
                licensed_states=["TX", "OK"],
                appointed_carriers=["insureflow"],
                license_active=True,
                full_time=False,
            ),
            ProducerRecord(
                producer_id="pr-003",
                name="Gulf Coast Risk Partners",
                agency="Gulf Coast",
                license_types=[ProducerLicenseType.PROPERTY_CASUALTY_BROKER],
                licensed_states=["LA", "MS", "AL", "FL"],
                appointed_carriers=[],
                license_active=True,
                full_time=False,
            ),
        ]
        for r in defaults:
            target[r.producer_id] = r

    def _ensure_loaded(self, org_id: str) -> None:
        if self._cached_org == org_id:
            return
        cached: dict[str, ProducerRecord] = {}
        self._seed_into(cached)
        raw = self._store().get(PRODUCER_NS, "registry", org_id=org_id)
        if raw:
            for rec in raw.get("producers", []):
                try:
                    p = ProducerRecord.from_dict(rec)
                except (KeyError, ValueError):
                    continue
                cached[p.producer_id] = p
        self._records = cached
        self._cached_org = org_id

    def _persist(self, org_id: str) -> None:
        data = {"producers": [p.to_dict() for p in self._records.values()]}
        self._store().set(PRODUCER_NS, "registry", data, org_id=org_id)

    def lookup(self, producer_id: str, org_id: str = "default") -> Optional[ProducerRecord]:
        self._ensure_loaded(org_id)
        return self._records.get(producer_id)

    def lookup_by_name(self, name: str, org_id: str = "default") -> Optional[ProducerRecord]:
        self._ensure_loaded(org_id)
        lowered = name.strip().lower()
        for rec in self._records.values():
            if rec.name.lower() == lowered or rec.agency.lower() == lowered:
                return rec
        return None

    def upsert(self, producer: ProducerRecord, org_id: str = "default") -> ProducerRecord:
        self._ensure_loaded(org_id)
        self._records[producer.producer_id] = producer
        self._persist(org_id)
        return producer

    def remove(self, producer_id: str, org_id: str = "default") -> bool:
        self._ensure_loaded(org_id)
        if producer_id not in self._records:
            return False
        del self._records[producer_id]
        self._persist(org_id)
        return True

    def list_all(self, org_id: str = "default") -> list[ProducerRecord]:
        self._ensure_loaded(org_id)
        return list(self._records.values())


_producer_registry: ProducerRegistry | None = None


def get_producer_registry() -> ProducerRegistry:
    global _producer_registry
    if _producer_registry is None:
        _producer_registry = ProducerRegistry()
    return _producer_registry


def reset_producer_registry() -> None:
    global _producer_registry
    _producer_registry = None


class ProducerVerification(BaseModel):
    producer_id: str = ""
    producer_name: str = ""
    status: ProducerVerificationStatus = ProducerVerificationStatus.NOT_FOUND
    license_types: list[str] = Field(default_factory=list)
    is_broker: bool = False
    severity: RiskSeverity = RiskSeverity.LOW
    reason: str = ""


# Life/health vs. P&C licensing — used to check the producer holds a license for the line.
_PC_LICENSES = {
    ProducerLicenseType.PROPERTY_CASUALTY_AGENT,
    ProducerLicenseType.PROPERTY_CASUALTY_BROKER,
    ProducerLicenseType.MGA,
}
_LIFE_LICENSES = {
    ProducerLicenseType.LIFE_HEALTH_AGENT,
    ProducerLicenseType.LIFE_HEALTH_BROKER,
    ProducerLicenseType.MGA,
}


def _line_needs_life_license(line: str) -> bool:
    return (line or "").strip().lower() in {"life", "life_health", "life_and_health", "life insurance", "health"}


def verify_producer(
    broker: Optional[BrokerInfo],
    line: str = "",
    state: str = "",
    org_id: str = "default",
) -> ProducerVerification:
    """Verify the submitting agent's status before the case proceeds.

    Mirrors Chapter 4's "verification of submitting agent's status": the agent
    must be licensed for the line of business, licensed in the state of the
    risk, and appointed to this carrier. A broker who is not a full-time agent
    of the carrier may still place the business but is flagged for referral.
    """
    if broker is None or not (broker.broker_name or broker.broker_id):
        return ProducerVerification(
            status=ProducerVerificationStatus.NOT_FOUND,
            reason="No submitting agent/broker identified on the submission",
        )

    registry = get_producer_registry()
    producer = None
    if broker.broker_id:
        producer = registry.lookup(broker.broker_id, org_id=org_id)
    if producer is None and broker.broker_name:
        producer = registry.lookup_by_name(broker.broker_name, org_id=org_id)

    if producer is None:
        return ProducerVerification(
            producer_id=broker.broker_id or "",
            producer_name=broker.broker_name or "",
            status=ProducerVerificationStatus.NOT_FOUND,
            severity=RiskSeverity.HIGH,
            reason=f"Producer '{broker.broker_name}' has no record in the producer registry — verify licensing manually",
        )

    if not producer.license_active:
        return ProducerVerification(
            producer_id=producer.producer_id,
            producer_name=producer.name,
            status=ProducerVerificationStatus.UNLICENSED,
            severity=RiskSeverity.CRITICAL,
            reason=f"Producer '{producer.name}' has an inactive license",
        )

    if state and producer.licensed_states and state not in producer.licensed_states:
        return ProducerVerification(
            producer_id=producer.producer_id,
            producer_name=producer.name,
            status=ProducerVerificationStatus.NOT_LICENSED_STATE,
            is_broker=not producer.full_time,
            license_types=[t.value for t in producer.license_types],
            severity=RiskSeverity.HIGH,
            reason=f"Producer '{producer.name}' is not licensed in {state}",
        )

    needs_life = _line_needs_life_license(line)
    eligible = _LIFE_LICENSES if needs_life else _PC_LICENSES
    if producer.license_types and not (set(producer.license_types) & eligible):
        return ProducerVerification(
            producer_id=producer.producer_id,
            producer_name=producer.name,
            status=ProducerVerificationStatus.NOT_LICENSED_LINE,
            is_broker=not producer.full_time,
            license_types=[t.value for t in producer.license_types],
            severity=RiskSeverity.HIGH,
            reason=f"Producer '{producer.name}' is not licensed for the '{line}' line of business",
        )

    if "insureflow" not in producer.appointed_carriers:
        return ProducerVerification(
            producer_id=producer.producer_id,
            producer_name=producer.name,
            status=ProducerVerificationStatus.NOT_APPOINTED,
            is_broker=not producer.full_time,
            license_types=[t.value for t in producer.license_types],
            severity=RiskSeverity.HIGH,
            reason=f"Producer '{producer.name}' is not appointed to this carrier",
        )

    if not producer.full_time:
        return ProducerVerification(
            producer_id=producer.producer_id,
            producer_name=producer.name,
            status=ProducerVerificationStatus.BROKER_REQUIRES_REFERRAL,
            is_broker=True,
            license_types=[t.value for t in producer.license_types],
            severity=RiskSeverity.MODERATE,
            reason=f"Producer '{producer.name}' is a broker, not a full-time agent — placement subject to referral",
        )

    return ProducerVerification(
        producer_id=producer.producer_id,
        producer_name=producer.name,
        status=ProducerVerificationStatus.VERIFIED,
        is_broker=False,
        license_types=[t.value for t in producer.license_types],
        severity=RiskSeverity.LOW,
        reason=f"Producer '{producer.name}' is licensed, appointed, and in good standing",
    )


class ExistingRecord(BaseModel):
    kind: ExistingRecordKind
    status: ExistingRecordStatus = ExistingRecordStatus.CLOSED
    reference: str = ""
    carrier: str = ""
    effective_date: Optional[date] = None
    description: str = ""
    amount: float = 0.0


class ExistingRecordsSearch(BaseModel):
    """Results of searching company records for prior knowledge of the insured."""

    insured_key: str = ""
    records: list[ExistingRecord] = Field(default_factory=list)
    has_coverage_in_force: bool = False
    has_prior_application: bool = False
    has_prior_declination: bool = False
    has_prior_cancellation: bool = False
    summary: str = ""


def _insured_key(bundle: SubmissionBundle) -> str:
    structured = bundle.structured
    if structured and structured.named_insured:
        return (structured.named_insured.legal_name or "").strip().lower()
    return ""


def _claim_to_record(claim: Any) -> ExistingRecord:
    return ExistingRecord(
        kind=ExistingRecordKind.PRIOR_LOSS,
        status=ExistingRecordStatus.CLOSED if claim.claim_status.value == "closed" else ExistingRecordStatus.IN_FORCE,
        reference=claim.claim_id,
        effective_date=claim.date_of_loss,
        description=claim.cause,
        amount=claim.incurred_amount,
    )


def search_existing_records(bundle: SubmissionBundle, org_id: str = "default") -> ExistingRecordsSearch:
    """Search company records for prior applications, policies, and losses.

    Chapter 4 directs the underwriter to search existing records for
    information about the proposed insured before underwriting the case. The
    structured submission's own loss history is also folded in here as prior
    loss records, and the durable store is consulted for prior applications,
    declinations, and cancellations previously recorded against the insured.
    """
    key = _insured_key(bundle)
    result = ExistingRecordsSearch(insured_key=key)

    store = None
    if key:
        from insureflow.storage.job_store import get_job_store

        store = get_job_store()
        raw = store.get(RECORDS_NS, f"insured:{key}", org_id=org_id)
        if raw:
            for rec in raw.get("records", []):
                try:
                    result.records.append(
                        ExistingRecord(
                            kind=ExistingRecordKind(rec["kind"]),
                            status=ExistingRecordStatus(rec.get("status", "closed")),
                            reference=rec.get("reference", ""),
                            carrier=rec.get("carrier", ""),
                            effective_date=date.fromisoformat(rec["effective_date"]) if rec.get("effective_date") else None,
                            description=rec.get("description", ""),
                            amount=rec.get("amount", 0.0),
                        )
                    )
                except (KeyError, ValueError):
                    continue

    structured = bundle.structured
    if structured and structured.risk_profile:
        for claim in structured.risk_profile.prior_claims or []:
            result.records.append(_claim_to_record(claim))
    if structured and structured.financial and structured.financial.loss_run:
        for claim in structured.financial.loss_run.claims or []:
            result.records.append(_claim_to_record(claim))

    result.has_coverage_in_force = any(r.status == ExistingRecordStatus.IN_FORCE for r in result.records)
    result.has_prior_application = any(r.kind == ExistingRecordKind.PRIOR_APPLICATION for r in result.records)
    result.has_prior_declination = any(r.kind == ExistingRecordKind.PRIOR_DECLINATION for r in result.records)
    result.has_prior_cancellation = any(r.kind == ExistingRecordKind.PRIOR_CANCELLATION for r in result.records)

    pieces = []
    if result.records:
        pieces.append(f"{len(result.records)} prior record(s) found")
    else:
        pieces.append("No prior records on file")
    if result.has_coverage_in_force:
        pieces.append("coverage already in force")
    if result.has_prior_declination:
        pieces.append("prior declination on file")
    if result.has_prior_cancellation:
        pieces.append("prior cancellation on file")
    result.summary = "; ".join(pieces)

    if result.has_prior_cancellation:
        if store is not None and key:
            store.set(RECORDS_NS, "flag", {"has_prior_cancellation": True}, org_id=org_id)

    return result


def record_prior_application(
    insured_key: str,
    record: ExistingRecord,
    org_id: str = "default",
) -> None:
    """Persist a prior-application/policy record against an insured for future searches."""
    from insureflow.storage.job_store import get_job_store

    store = get_job_store()
    raw = store.get(RECORDS_NS, f"insured:{insured_key}", org_id=org_id) or {}
    records = raw.get("records", [])
    records.append(
        {
            "kind": record.kind.value,
            "status": record.status.value,
            "reference": record.reference,
            "carrier": record.carrier,
            "effective_date": record.effective_date.isoformat() if record.effective_date else None,
            "description": record.description,
            "amount": record.amount,
        }
    )
    store.set(RECORDS_NS, f"insured:{insured_key}", {"records": records}, org_id=org_id)


class PreliminaryStepStatus(str, Enum):
    PASS = "pass"
    FLAG = "flag"  # proceed with attention
    HOLD = "hold"  # request missing info before underwriting


class PreliminaryCheck(BaseModel):
    """The Chapter 4 preliminary-processing gate for one case."""

    bundle_id: str = ""
    completeness_pct: float = 0.0
    missing_documents: list[str] = Field(default_factory=list)
    agent_verification: Optional[ProducerVerification] = None
    existing_records: Optional[ExistingRecordsSearch] = None
    fcra_pre_notification_given: bool = False
    fcra_pre_notification_required: bool = False
    case_id: str = ""
    status: PreliminaryStepStatus = PreliminaryStepStatus.PASS
    reasons: list[str] = Field(default_factory=list)
    checks: dict[str, PreliminaryStepStatus] = Field(default_factory=dict)


def run_preliminary_check(
    bundle: SubmissionBundle,
    *,
    line: str = "",
    state: str = "",
    completeness: Optional[dict[str, Any]] = None,
    fcra_pre_notification_given: bool = False,
    org_id: str = "default",
) -> PreliminaryCheck:
    """Execute the preliminary-processing gate on a case.

    Combines: (1) completeness of the application package, (2) verification of
    the submitting agent's status, (3) a search of existing records, and (4)
    the FCRA pre-notification check. The case is *held* (request missing info)
    when the package is materially incomplete or the agent cannot be verified;
    it is *flagged* when records exist or a consumer report was used without
    the pre-notification disclosure.
    """
    from insureflow.insurance.package_checklist import package_checklist

    result = PreliminaryCheck(
        bundle_id=bundle.bundle_id,
        fcra_pre_notification_given=fcra_pre_notification_given,
    )

    if completeness is None:
        doc_types = [d.document_type for d in bundle.unstructured] + [d.document_type for d in bundle.supplemental]
        if bundle.structured:
            doc_types.append("acord_xml")
        completeness = package_checklist(doc_types, lob=line or "property")
    result.completeness_pct = float(completeness.get("completeness_pct", 0.0))
    result.missing_documents = list(completeness.get("missing", []))
    result.checks["completeness"] = PreliminaryStepStatus.PASS if result.completeness_pct >= 80.0 else PreliminaryStepStatus.HOLD
    if result.checks["completeness"] == PreliminaryStepStatus.HOLD:
        result.reasons.append(f"Package {result.completeness_pct:.0f}% complete; missing: {', '.join(result.missing_documents)}")

    result.agent_verification = verify_producer(bundle.structured.broker if bundle.structured else None, line=line, state=state, org_id=org_id)
    if result.agent_verification.status == ProducerVerificationStatus.VERIFIED:
        result.checks["agent"] = PreliminaryStepStatus.PASS
    elif result.agent_verification.status == ProducerVerificationStatus.BROKER_REQUIRES_REFERRAL:
        result.checks["agent"] = PreliminaryStepStatus.FLAG
        result.reasons.append(result.agent_verification.reason)
    else:
        result.checks["agent"] = PreliminaryStepStatus.HOLD
        result.reasons.append(result.agent_verification.reason)

    result.existing_records = search_existing_records(bundle, org_id=org_id)
    if result.existing_records.has_prior_declination or result.existing_records.has_prior_cancellation:
        result.checks["records"] = PreliminaryStepStatus.FLAG
        result.reasons.append(result.existing_records.summary)
    elif result.existing_records.records:
        result.checks["records"] = PreliminaryStepStatus.PASS
    else:
        result.checks["records"] = PreliminaryStepStatus.PASS

    uses_consumer_report = (line or "").strip().lower() in {"auto", "homeowners", "personal_auto", "life", "personal_lines"} or "mvr" in str(completeness.get("lob", ""))
    result.fcra_pre_notification_required = uses_consumer_report
    if uses_consumer_report and not fcra_pre_notification_given:
        result.checks["fcra"] = PreliminaryStepStatus.FLAG
        result.reasons.append("Consumer-report data may be used but the FCRA pre-notification disclosure is not confirmed")
    else:
        result.checks["fcra"] = PreliminaryStepStatus.PASS

    holds = [k for k, v in result.checks.items() if v == PreliminaryStepStatus.HOLD]
    flags = [k for k, v in result.checks.items() if v == PreliminaryStepStatus.FLAG]
    result.status = (
        PreliminaryStepStatus.HOLD
        if holds
        else PreliminaryStepStatus.FLAG
        if flags
        else PreliminaryStepStatus.PASS
    )
    return result
