"""API surface for fraud, marketplace, banking, AML, and NL workflow drafting."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from insureflow.auth import Role
from insureflow.auth.dependencies import require_role
from insureflow.auth.models import TokenData

router = APIRouter(dependencies=[Depends(require_role(Role.VIEWER))])


class DeviceAssessRequest(BaseModel):
    fingerprint: dict[str, Any] = Field(default_factory=dict)
    signals: dict[str, Any] = Field(default_factory=dict)


class SessionAssessRequest(BaseModel):
    session: dict[str, Any]


class GenAiAssessRequest(BaseModel):
    document: dict[str, Any]


class MarketplaceConnectRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)
    label: str = ""


class TransactionIn(BaseModel):
    txn_id: str = ""
    amount: float = 0.0
    posted_on: str = ""
    description: str = ""
    merchant: str = ""
    mcc: str = ""


class CategorizeRequest(BaseModel):
    transactions: list[TransactionIn]


class AchScheduleIn(BaseModel):
    name: str = "premium"
    cadence: str = "monthly"
    start_on: str
    amount: float = 0.0
    weekday: int | None = None
    count: int = 6


class BalancePredictRequest(BaseModel):
    transactions: list[TransactionIn]
    starting_balance: float = 0.0
    as_of: str | None = None
    horizon_days: int = 30
    upcoming_ach: list[AchScheduleIn] = Field(default_factory=list)


class AchDatesRequest(BaseModel):
    schedule: AchScheduleIn


class SanctionsScreenRequest(BaseModel):
    name: str
    entity_type: str = ""


class SarCreateRequest(BaseModel):
    subject_name: str
    filer_org: str = ""
    subject_tin: str = ""
    subject_type: str = "individual"
    activity_type: str = "fraud"
    amount: float = 0.0
    narrative: str = ""
    suspicious_period_start: str = ""
    suspicious_period_end: str = ""
    status: str = "draft"
    related_bundle_id: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class SarStatusRequest(BaseModel):
    status: str


class WorkflowDraftRequest(BaseModel):
    prompt: str
    title: str = ""


@router.post("/fraud/device/assess")
def fraud_assess_device(payload: DeviceAssessRequest) -> dict[str, Any]:
    from insureflow.fraud.device_intelligence import assess_device
    from insureflow.fraud.models import DeviceFingerprint, DeviceSignals

    fp = DeviceFingerprint(**payload.fingerprint)
    signals = DeviceSignals(**payload.signals)
    return assess_device(fp, signals).model_dump(mode="json")


@router.post("/fraud/session/assess")
def fraud_assess_session(payload: SessionAssessRequest) -> dict[str, Any]:
    from insureflow.fraud.behavioral_biometrics import assess_session
    from insureflow.fraud.models import BehavioralSession

    try:
        session = BehavioralSession(**payload.session)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid session: {exc}") from exc
    return assess_session(session).model_dump(mode="json")


@router.post("/fraud/genai/assess")
def fraud_assess_genai(payload: GenAiAssessRequest) -> dict[str, Any]:
    from insureflow.fraud.genai_defense import assess_document
    from insureflow.fraud.models import GenAiDocument

    try:
        doc = GenAiDocument(**payload.document)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid document: {exc}") from exc
    return assess_document(doc).model_dump(mode="json")


@router.get("/marketplace/sources")
def marketplace_sources(
    category: str | None = None,
    vertical: str | None = None,
    q: str | None = None,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.marketplace.catalog import MARKETPLACE_SOURCES
    from insureflow.marketplace.registry import catalog_with_connection_state

    items = catalog_with_connection_state(org_id=current.org_id or "default", category=category, vertical=vertical, q=q)
    return {"count": len(items), "total": len(MARKETPLACE_SOURCES), "sources": items}


@router.get("/marketplace/sources/{source_id}")
def marketplace_source_detail(source_id: str) -> dict[str, Any]:
    from insureflow.marketplace.catalog import get_source

    meta = get_source(source_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Unknown marketplace source: {source_id}")
    return meta


@router.get("/marketplace/connections")
def marketplace_connections(current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    from insureflow.marketplace.registry import list_connected_sources

    items = list_connected_sources(org_id=current.org_id or "default")
    return {"count": len(items), "connections": items}


@router.post("/marketplace/connect/{source_id}")
def marketplace_connect(
    source_id: str,
    payload: MarketplaceConnectRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.marketplace.registry import connect_source

    try:
        return connect_source(source_id, config=payload.config, label=payload.label, org_id=current.org_id or "default")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/marketplace/connect/{source_id}")
def marketplace_disconnect(source_id: str, current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    from insureflow.marketplace.registry import disconnect_source

    removed = disconnect_source(source_id, org_id=current.org_id or "default")
    if not removed:
        raise HTTPException(status_code=404, detail=f"No connection for {source_id}")
    return {"ok": True, "source_id": source_id}


@router.post("/banking/transactions/categorize")
def banking_categorize(payload: CategorizeRequest) -> dict[str, Any]:
    from insureflow.banking.engine import categorize_transactions
    from insureflow.banking.models import BankTransaction

    txns = [BankTransaction(**t.model_dump()) for t in payload.transactions]
    rows = categorize_transactions(txns)
    return {"count": len(rows), "transactions": [r.model_dump() for r in rows]}


@router.post("/banking/balance/predict")
def banking_predict(payload: BalancePredictRequest) -> dict[str, Any]:
    from insureflow.banking.engine import predict_balance
    from insureflow.banking.models import AchSchedule, BankTransaction

    txns = [BankTransaction(**t.model_dump()) for t in payload.transactions]
    ach = [AchSchedule(**s.model_dump()) for s in payload.upcoming_ach]
    forecast = predict_balance(
        txns,
        starting_balance=payload.starting_balance,
        as_of=payload.as_of,
        horizon_days=payload.horizon_days,
        upcoming_ach=ach,
    )
    return forecast.model_dump()


@router.post("/banking/ach/pull-dates")
def banking_ach_dates(payload: AchDatesRequest) -> dict[str, Any]:
    from insureflow.banking.engine import next_ach_pull_dates
    from insureflow.banking.models import AchSchedule

    dates = next_ach_pull_dates(AchSchedule(**payload.schedule.model_dump()))
    return {"count": len(dates), "dates": dates}


@router.post("/aml/sanctions/screen")
def aml_sanctions_screen(payload: SanctionsScreenRequest) -> dict[str, Any]:
    from insureflow.aml.sanctions import screen_name

    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    return screen_name(payload.name, entity_type=payload.entity_type).model_dump(mode="json")


@router.post("/aml/sar")
def aml_file_sar(payload: SarCreateRequest, current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    from insureflow.aml.sar import SarService

    try:
        filing = SarService().file(
            subject_name=payload.subject_name,
            org_id=current.org_id or "default",
            filer_org=payload.filer_org,
            subject_tin=payload.subject_tin,
            subject_type=payload.subject_type,
            activity_type=payload.activity_type,
            amount=payload.amount,
            narrative=payload.narrative,
            suspicious_period_start=payload.suspicious_period_start,
            suspicious_period_end=payload.suspicious_period_end,
            status=payload.status,
            related_bundle_id=payload.related_bundle_id,
            filed_by=current.username or "",
            extra=payload.extra,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return filing.model_dump(mode="json")


@router.get("/aml/sar")
def aml_list_sar(current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    from insureflow.aml.sar import SarService

    rows = SarService().list(org_id=current.org_id or "default")
    return {"count": len(rows), "filings": [r.model_dump(mode="json") for r in rows]}


@router.get("/aml/sar/{sar_id}")
def aml_get_sar(sar_id: str, current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    from insureflow.aml.sar import SarService

    rec = SarService().get(sar_id, org_id=current.org_id or "default")
    if rec is None:
        raise HTTPException(status_code=404, detail=f"SAR not found: {sar_id}")
    return rec.model_dump(mode="json")


@router.post("/aml/sar/{sar_id}/status")
def aml_sar_status(
    sar_id: str,
    payload: SarStatusRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.aml.sar import SarService

    try:
        rec = SarService().update_status(sar_id, payload.status, org_id=current.org_id or "default")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return rec.model_dump(mode="json")


@router.post("/workflow/draft")
def workflow_draft_nl(payload: WorkflowDraftRequest) -> dict[str, Any]:
    from insureflow.workflow.draft import draft_workflow

    try:
        draft = draft_workflow(payload.prompt, title=payload.title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return draft.model_dump()
