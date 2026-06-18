from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from insureflow.auth import Role
from insureflow.auth.dependencies import (
    get_current_user,
    get_user_store,
    require_role,
)
from insureflow.auth.jwt import create_access_token, hash_password, verify_password
from insureflow.auth.models import LoginRequest, Token, TokenData, User, UserCreateRequest
from insureflow.models.mortgage import ProductLine
from insureflow.insurance.pipeline import InsurancePipeline
from insureflow.pipeline import UnderwritingPipeline
from insureflow.storage.job_store import JobStore, get_job_store

logger = logging.getLogger(__name__)

INSURANCE_NS = "insurance"
MORTGAGE_NS = "mortgage"

job_store: JobStore = get_job_store()

app = FastAPI(
    title="InsureFlow AI",
    description="Autonomous underwriting pipeline API — Insurance & Mortgage",
    version="0.2.0",
)

STATIC_DIR = Path(__file__).parent / "static"


# ── Auth Endpoints ──────────────────────────────────────────────


@app.post("/auth/setup", status_code=201)
def setup_first_admin(admin: UserCreateRequest) -> dict[str, str]:
    store = get_user_store()
    if store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin already exists. Use /auth/login.",
        )
    store[admin.username] = User(
        username=admin.username,
        hashed_password=hash_password(admin.password),
        role=Role.ADMIN,
        full_name=admin.full_name or admin.username,
        org_id=admin.org_id,
    )
    return {"message": f"Admin '{admin.username}' created for org '{admin.org_id}'"}


@app.post("/auth/login")
def login(req: LoginRequest) -> Token:
    store = get_user_store()
    user = store.get(req.username)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    token = create_access_token(
        data={"sub": user.username, "role": user.role.value, "org_id": user.org_id}
    )
    return Token(access_token=token)


@app.post("/auth/users", status_code=201)
def create_user(
    new_user: UserCreateRequest,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, str]:
    store = get_user_store()
    if new_user.username in store:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    # Admins can only create users in their own org unless super-admin pattern
    org_id = new_user.org_id if new_user.org_id != "default" else current.org_id
    store[new_user.username] = User(
        username=new_user.username,
        hashed_password=hash_password(new_user.password),
        role=new_user.role,
        full_name=new_user.full_name or new_user.username,
        org_id=org_id,
    )
    return {"message": f"User '{new_user.username}' created with role '{new_user.role.value}' in org '{org_id}'"}


@app.get("/auth/me")
def get_me(current_user: TokenData = Depends(get_current_user)) -> dict[str, str]:
    return {
        "username": current_user.username,
        "role": current_user.role.value if current_user.role else "none",
        "org_id": current_user.org_id,
    }


# ── Dashboard ───────────────────────────────────────────────────


@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard.html")


# ── Insurance Pipeline ──────────────────────────────────────────


class InsuranceDocumentPayload(BaseModel):
    filename: str
    content: str
    encoding: str = "utf-8"  # or "base64" for PDF/image uploads


class SubmissionRequest(BaseModel):
    acord_xml: Optional[str] = None
    inspection_reports: Optional[list[str]] = None
    supplemental_docs: Optional[list[str]] = None
    json_payload: Optional[str] = None
    loss_run: Optional[str] = None
    schedule_of_values: Optional[str] = None
    documents: Optional[list[InsuranceDocumentPayload]] = None
    pdf_paths: Optional[list[str]] = None
    bundle_id: Optional[str] = None
    use_llm: bool = True
    use_legacy_pipeline: bool = False


class SignOffRequest(BaseModel):
    action: str  # approve | decline | refer | request_info
    license_number: str = ""
    notes: str = ""
    override_reason: str = ""


class BindRequest(BaseModel):
    policy_number: str = ""
    bound_premium: float = 0.0


class LossExperienceRequest(BaseModel):
    policy_number: str
    policy_year: int
    earned_premium: float
    incurred_losses: float
    paid_losses: float = 0.0
    claim_count: int = 0
    bundle_id: str = ""


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}


def _run_pipeline_task(job_id: str, request: SubmissionRequest, org_id: str) -> None:
    try:
        if request.use_legacy_pipeline:
            pipeline = UnderwritingPipeline()
            result = pipeline.run(
                acord_xml=request.acord_xml,
                inspection_reports=request.inspection_reports,
                supplemental_docs=request.supplemental_docs,
                bundle_id=request.bundle_id or job_id,
            )
        else:
            docs = [d.model_dump() for d in request.documents] if request.documents else None
            pipeline = InsurancePipeline(org_id=org_id, use_llm=request.use_llm)
            result = pipeline.run(
                acord_xml=request.acord_xml,
                inspection_reports=request.inspection_reports,
                supplemental_docs=request.supplemental_docs,
                json_payload=request.json_payload,
                loss_run=request.loss_run,
                schedule_of_values=request.schedule_of_values,
                documents=docs,
                pdf_paths=request.pdf_paths,
                bundle_id=request.bundle_id or job_id,
            )
        job_store.set(INSURANCE_NS, job_id, {"status": "completed", "results": result}, org_id=org_id)
    except Exception as exc:
        logger.exception("Pipeline run failed")
        job_store.set(INSURANCE_NS, job_id, {"status": "failed", "error": str(exc)}, org_id=org_id)


@app.post("/pipeline/run", status_code=202)
async def run_pipeline(
    req: SubmissionRequest,
    background_tasks: BackgroundTasks,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    job_store.set(INSURANCE_NS, job_id, {"status": "processing"}, org_id=current.org_id)
    background_tasks.add_task(_run_pipeline_task, job_id, req, current.org_id)
    return {"job_id": job_id, "status": "processing", "org_id": current.org_id}


@app.get("/pipeline/jobs/{job_id}")
def get_job_status(
    job_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    job = job_store.get(INSURANCE_NS, job_id, org_id=current.org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/pipeline/jobs")
def list_jobs(current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, list[str]]:
    return {"jobs": job_store.list_ids(INSURANCE_NS, org_id=current.org_id)}


@app.delete("/pipeline/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, current: TokenData = Depends(require_role(Role.ADMIN))) -> None:
    if not job_store.delete(INSURANCE_NS, job_id, org_id=current.org_id):
        raise HTTPException(status_code=404, detail="Job not found")


# ── Insurance: Audit, Sign-off, Rating, Outcomes ─────────────────


@app.get("/pipeline/audit/{bundle_id}")
def get_insurance_audit(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.audit.store import AuditStore

    store = AuditStore()
    return {
        "bundle_id": bundle_id,
        "org_id": current.org_id,
        "submission": store.load_json(bundle_id, "submission_bundle.json", org_id=current.org_id),
        "memo": store.load_json(bundle_id, "underwriting_memo.json", org_id=current.org_id),
        "audit_trail": store.load_json(bundle_id, "audit_trail.json", org_id=current.org_id),
        "provenance": store.load_json(bundle_id, "provenance_record.json", org_id=current.org_id),
        "reconciliation": store.load_json(bundle_id, "reconciliation.json", org_id=current.org_id),
        "summary": store.load_json(bundle_id, "pipeline_summary.json", org_id=current.org_id),
    }


@app.get("/pipeline/audit/{bundle_id}/package")
def export_regulatory_package(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    from insureflow.audit.package import RegulatoryPackageBuilder

    try:
        builder = RegulatoryPackageBuilder()
        return builder.build(bundle_id, org_id=current.org_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No audit bundle for {bundle_id}")


@app.get("/pipeline/workflow/pending")
def list_pending_reviews(current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    from insureflow.workflow.service import WorkflowService

    return {"org_id": current.org_id, "pending": WorkflowService().store.list_pending(current.org_id)}


@app.get("/pipeline/workflow/{bundle_id}")
def get_workflow_status(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.workflow.service import WorkflowService

    record = WorkflowService().store.get(bundle_id, current.org_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return record.model_dump()


@app.post("/pipeline/workflow/{bundle_id}/sign-off")
def licensed_uw_sign_off(
    bundle_id: str,
    req: SignOffRequest,
    current: TokenData = Depends(require_role(Role.LICENSED_UW)),
) -> dict[str, Any]:
    from insureflow.workflow.models import SignOffAction
    from insureflow.workflow.service import WorkflowService

    try:
        action = SignOffAction(req.action.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {req.action}")

    svc = WorkflowService()
    record = svc.sign_off(
        bundle_id,
        current.org_id,
        action,
        signed_by=current.username or "",
        license_number=req.license_number,
        notes=req.notes,
        override_reason=req.override_reason,
    )
    return record.model_dump()


@app.post("/pipeline/workflow/{bundle_id}/bind")
def bind_policy(
    bundle_id: str,
    req: BindRequest,
    current: TokenData = Depends(require_role(Role.LICENSED_UW)),
) -> dict[str, Any]:
    from insureflow.audit.store import AuditStore
    from insureflow.outcomes.feedback import FeedbackEngine
    from insureflow.rating.engine import InsuranceRatingEngine
    from insureflow.workflow.service import WorkflowService

    wf = WorkflowService()
    record = wf.store.get(bundle_id, current.org_id)
    if not record or record.state.value != "approved":
        raise HTTPException(status_code=400, detail="Policy must be UW-approved before bind")

    store = AuditStore()
    summary = store.load_json(bundle_id, "pipeline_summary.json", org_id=current.org_id) or {}
    quote_ref = summary.get("quote", {}).get("policy_admin_reference", "")

    rating = InsuranceRatingEngine()
    bind_result = rating.bind(bundle_id, quote_ref, current.username or "")

    policy_number = req.policy_number or bind_result.get("policy_number", "")
    bound_premium = req.bound_premium or summary.get("quote", {}).get("adjusted_premium", 0.0)

    wf.mark_bound(bundle_id, current.org_id, policy_number)

    feedback = FeedbackEngine()
    outcome = feedback.record_bind(
        bundle_id,
        current.org_id,
        policy_number,
        bound_premium,
        record.final_decision,
        record.ai_decision,
        quote_ref,
    )

    return {"bind": bind_result, "workflow": record.model_dump(), "outcome": outcome.model_dump()}


@app.post("/pipeline/outcomes/loss-experience", status_code=201)
def record_loss_experience(
    req: LossExperienceRequest,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    from insureflow.outcomes.feedback import FeedbackEngine

    exp = FeedbackEngine().record_loss_experience(
        policy_number=req.policy_number,
        org_id=current.org_id,
        policy_year=req.policy_year,
        earned_premium=req.earned_premium,
        incurred_losses=req.incurred_losses,
        paid_losses=req.paid_losses,
        claim_count=req.claim_count,
        bundle_id=req.bundle_id,
    )
    return exp.model_dump()


@app.get("/pipeline/outcomes/calibration")
def get_calibration_summary(current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    from insureflow.outcomes.feedback import FeedbackEngine

    return FeedbackEngine().calibration_summary(current.org_id)


@app.get("/pipeline/rating/products")
def list_insurance_products(_: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    from insureflow.rating.engine import InsuranceRatingEngine
    from insureflow.rating.models import InsuranceLine

    return {
        "lines": [
            {"id": line.value, "base_rate_per_100": InsuranceRatingEngine.BASE_RATES.get(line, 0.0)}
            for line in InsuranceLine
        ]
    }


# ── Mortgage Pipeline ───────────────────────────────────────────


class MortgageDocumentPayload(BaseModel):
    filename: str
    content: str
    encoding: str = "utf-8"  # or "base64" for PDF/image uploads


class MortgageSubmissionRequest(BaseModel):
    documents: Optional[list[MortgageDocumentPayload]] = None
    directory: Optional[str] = None
    bundle_id: Optional[str] = None
    borrower_id: Optional[str] = None
    product_line: Optional[str] = None
    loan_product: Optional[str] = None
    loan_amount: Optional[float] = None
    use_llm: bool = True
    per_borrower: bool = False
    use_celery: bool = False


class WebhookRegisterRequest(BaseModel):
    url: str
    events: list[str] = ["mortgage.completed", "mortgage.failed"]
    secret: str = ""


def _parse_product_line(value: str | None) -> ProductLine | None:
    if not value or value == "auto":
        return None
    mapping = {
        "residential": ProductLine.RESIDENTIAL_MORTGAGE,
        "residential_mortgage": ProductLine.RESIDENTIAL_MORTGAGE,
        "commercial": ProductLine.COMMERCIAL_MORTGAGE,
        "commercial_mortgage": ProductLine.COMMERCIAL_MORTGAGE,
    }
    pl = mapping.get(value.lower())
    if not pl:
        raise ValueError(f"Unknown product_line: {value}")
    return pl


def _run_mortgage_task(job_id: str, request: MortgageSubmissionRequest, org_id: str) -> None:
    from insureflow.models.mortgage import ProductLine
    from insureflow.mortgage.pipeline import MortgagePipeline
    from insureflow.mortgage.webhooks import webhook_dispatcher

    pipeline = MortgagePipeline(use_llm=request.use_llm, org_id=org_id)
    try:
        product_line = _parse_product_line(request.product_line)

        if request.per_borrower and request.directory:
            result = pipeline.run_per_borrower(request.directory, product_line=product_line)
        elif request.directory:
            result = pipeline.run_from_directory(
                request.directory,
                bundle_id=request.bundle_id or job_id,
                product_line=product_line,
                loan_product=request.loan_product,
                loan_amount=request.loan_amount,
            )
        elif request.documents:
            docs = [d.model_dump() for d in request.documents]
            result = pipeline.run_from_texts(
                docs,
                bundle_id=request.bundle_id or job_id,
                product_line=product_line or ProductLine.RESIDENTIAL_MORTGAGE,
                borrower_id=request.borrower_id,
                loan_product=request.loan_product,
                loan_amount=request.loan_amount,
            )
        else:
            job_store.set(MORTGAGE_NS, job_id, {
                "status": "failed",
                "error": "Provide documents or directory",
            }, org_id=org_id)
            webhook_dispatcher.dispatch("mortgage.failed", org_id, {"job_id": job_id, "error": "no input"})
            return

        job_store.set(MORTGAGE_NS, job_id, {"status": "completed", "results": result}, org_id=org_id)
    except Exception as exc:
        logger.exception("Mortgage pipeline run failed")
        job_store.set(MORTGAGE_NS, job_id, {"status": "failed", "error": str(exc)}, org_id=org_id)
        from insureflow.mortgage.webhooks import webhook_dispatcher
        webhook_dispatcher.dispatch("mortgage.failed", org_id, {"job_id": job_id, "error": str(exc)})


def _dispatch_mortgage_celery(job_id: str, request: MortgageSubmissionRequest, org_id: str) -> None:
    from insureflow.tasks.mortgage_tasks import (
        run_mortgage_directory,
        run_mortgage_per_borrower,
        run_mortgage_pipeline,
    )

    job_store.set(MORTGAGE_NS, job_id, {"status": "processing", "backend": "celery"}, org_id=org_id)

    if request.per_borrower and request.directory:
        task = run_mortgage_per_borrower.delay(
            request.directory,
            product_line=request.product_line,
            use_llm=request.use_llm,
        )
    elif request.directory:
        task = run_mortgage_directory.delay(
            request.directory,
            bundle_id=job_id,
            product_line=request.product_line,
            use_llm=request.use_llm,
        )
    elif request.documents:
        docs = [{"filename": d.filename, "content": d.content} for d in request.documents]
        task = run_mortgage_pipeline.delay(
            docs,
            bundle_id=job_id,
            product_line=request.product_line or "residential_mortgage",
            use_llm=request.use_llm,
            borrower_id=request.borrower_id,
        )
    else:
        job_store.set(MORTGAGE_NS, job_id, {"status": "failed", "error": "no input"}, org_id=org_id)
        return

    job_store.set(MORTGAGE_NS, job_id, {
        "status": "processing",
        "backend": "celery",
        "celery_task_id": task.id,
    }, org_id=org_id)


@app.post("/mortgage/pipeline/run", status_code=202)
async def run_mortgage_pipeline(
    req: MortgageSubmissionRequest,
    background_tasks: BackgroundTasks,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    job_id = req.bundle_id or f"mortgage-job-{uuid.uuid4().hex[:12]}"
    job_store.set(MORTGAGE_NS, job_id, {"status": "processing"}, org_id=current.org_id)

    if req.use_celery:
        background_tasks.add_task(_dispatch_mortgage_celery, job_id, req, current.org_id)
    else:
        background_tasks.add_task(_run_mortgage_task, job_id, req, current.org_id)

    return {
        "job_id": job_id,
        "status": "processing",
        "org_id": current.org_id,
        "per_borrower": req.per_borrower,
        "use_llm": req.use_llm,
        "use_celery": req.use_celery,
    }


@app.get("/mortgage/pipeline/jobs/{job_id}")
def get_mortgage_job_status(
    job_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    job = job_store.get(MORTGAGE_NS, job_id, org_id=current.org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Mortgage job not found")
    return job


@app.get("/mortgage/pipeline/jobs")
def list_mortgage_jobs(current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, list[str]]:
    return {"jobs": job_store.list_ids(MORTGAGE_NS, org_id=current.org_id), "org_id": current.org_id}


@app.get("/mortgage/audit/{bundle_id}")
def get_mortgage_audit_trail(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.audit.store import AuditStore

    store = AuditStore()
    trail = store.load_json(bundle_id, "audit_trail.json")
    memo = store.load_json(bundle_id, "mortgage_memo.json")
    bundle = store.load_json(bundle_id, "mortgage_bundle.json")
    summary = store.load_json(bundle_id, "pipeline_summary.json")
    if not trail and not memo:
        raise HTTPException(status_code=404, detail=f"No audit data for bundle: {bundle_id}")
    return {
        "bundle_id": bundle_id,
        "org_id": current.org_id,
        "audit_trail": trail,
        "memo": memo,
        "bundle_summary": bundle,
        "pipeline_summary": summary,
    }


@app.get("/mortgage/products")
def list_loan_products(_: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    from insureflow.mortgage.pricing import PRODUCT_CATALOG

    return {
        "products": [
            {
                "id": p.product.value,
                "min_credit_score": p.min_credit_score,
                "max_ltv": p.max_ltv,
                "max_dti": p.max_dti,
                "base_rate": p.base_rate,
                "rate_lock_days": p.rate_lock_days,
                "notes": p.notes,
            }
            for p in PRODUCT_CATALOG.values()
        ]
    }


# ── Webhooks ────────────────────────────────────────────────────


@app.post("/mortgage/webhooks", status_code=201)
def register_webhook(
    req: WebhookRegisterRequest,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    from insureflow.mortgage.webhooks import webhook_dispatcher

    sub = webhook_dispatcher.register(
        org_id=current.org_id,
        url=req.url,
        events=req.events,
        secret=req.secret,
    )
    return {
        "subscription_id": sub.subscription_id,
        "org_id": sub.org_id,
        "url": sub.url,
        "events": sub.events,
        "secret": sub.secret,
    }


@app.get("/mortgage/webhooks")
def list_webhooks(current: TokenData = Depends(require_role(Role.ADMIN))) -> dict[str, Any]:
    from insureflow.mortgage.webhooks import webhook_dispatcher

    subs = webhook_dispatcher.list_for_org(current.org_id)
    return {
        "org_id": current.org_id,
        "subscriptions": [
            {"subscription_id": s.subscription_id, "url": s.url, "events": s.events, "active": s.active}
            for s in subs
        ],
    }


@app.delete("/mortgage/webhooks/{subscription_id}", status_code=204)
def delete_webhook(
    subscription_id: str,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> None:
    from insureflow.mortgage.webhooks import webhook_dispatcher

    if not webhook_dispatcher.unregister(subscription_id, current.org_id):
        raise HTTPException(status_code=404, detail="Webhook not found")


@app.delete("/mortgage/pipeline/jobs/{job_id}", status_code=204)
def delete_mortgage_job(
    job_id: str,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> None:
    if not job_store.delete(MORTGAGE_NS, job_id, org_id=current.org_id):
        raise HTTPException(status_code=404, detail="Mortgage job not found")
