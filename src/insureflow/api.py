from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from insureflow.auth import Role
from insureflow.auth.dependencies import (
    clear_user_store,
    get_current_user,
    get_user_store,
    require_role,
)
from insureflow.auth.jwt import create_access_token, hash_password, verify_password
from insureflow.auth.models import LoginRequest, Token, TokenData, User, UserCreateRequest
from insureflow.models.mortgage import ProductLine
from insureflow.storage.job_store import JobStore, get_job_store
from insureflow.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

INSURANCE_NS = "insurance"
MORTGAGE_NS = "mortgage"
LENDING_NS = "lending"

job_store: JobStore = get_job_store()

limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])

app = FastAPI(
    title="InsureFlow AI",
    description="Autonomous underwriting pipeline API — Insurance & Mortgage",
    version="0.2.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

STATIC_DIR = Path(__file__).parent / "static"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SIM_DOCS_DIR = PROJECT_ROOT / "simulated_documents"


# ── Auth Endpoints ──────────────────────────────────────────────


@app.get("/auth/status")
def auth_status() -> dict[str, bool]:
    """Whether first-time admin setup is still required."""
    return {"setup_required": not bool(get_user_store())}


def _do_auth_reset() -> dict[str, str | int | bool]:
    removed = clear_user_store()
    return {
        "message": "All credentials cleared. Use First-time Setup to create a new admin.",
        "users_removed": removed,
        "setup_required": True,
        "clear_browser_session": True,
    }


_RESET_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Session cleared</title>
<style>body{font-family:system-ui;background:#0c0f17;color:#e2e8f0;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.box{text-align:center;padding:2rem;border:1px solid #334155;border-radius:12px;max-width:420px}
a{color:#7aa3f5}</style></head>
<body><div class="box"><h1>All sign-in data cleared</h1>
<p>Server accounts removed. Browser session wiped.</p>
<p><a href="/dashboard">Open dashboard → First-time Setup</a></p></div>
<script>
['insureflow_token','insureflow_user'].forEach(function(k){localStorage.removeItem(k);sessionStorage.removeItem(k);});
setTimeout(function(){window.location.href='/dashboard';},800);
</script></body></html>"""


@app.get("/auth/reset")
def reset_auth_get():
    """One-click wipe: server accounts + redirect to dashboard."""
    from fastapi.responses import HTMLResponse

    _do_auth_reset()
    return HTMLResponse(_RESET_HTML)


@app.post("/auth/reset")
def reset_auth_post() -> dict[str, str | int | bool]:
    """Clear all server accounts (JSON). Client should wipe localStorage too."""
    return _do_auth_reset()


@app.post("/auth/setup", status_code=201)
def setup_first_admin(admin: UserCreateRequest) -> dict[str, str]:
    store = get_user_store()
    if store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin already exists. Use /auth/login.",
        )
    username = admin.username.strip()
    if not username or not admin.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    store[username] = User(
        username=username,
        hashed_password=hash_password(admin.password),
        role=Role.ADMIN,
        full_name=(admin.full_name or username).strip(),
        org_id=(admin.org_id or "default").strip(),
    )
    return {"message": f"Admin '{username}' created for org '{admin.org_id}'"}


@app.post("/auth/login")
@limiter.limit("10/minute")
def login(req: LoginRequest, request: Request) -> Token:
    store = get_user_store()
    username = req.username.strip()
    user = store.get(username)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    token = create_access_token(data={"sub": user.username, "role": user.role.value, "org_id": user.org_id})
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


@app.post("/auth/register", status_code=201)
@limiter.limit("3/hour")
def register_user(req: UserCreateRequest, request: Request) -> dict[str, str]:
    """Self-register — limited to VIEWER or UNDERWRITER roles."""
    store = get_user_store()
    username = req.username.strip()
    if not username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    role = req.role if req.role in (Role.VIEWER, Role.UNDERWRITER) else Role.VIEWER
    if username in store:
        raise HTTPException(status_code=409, detail="Username already exists")
    store[username] = User(
        username=username,
        hashed_password=hash_password(req.password),
        role=role,
        full_name=req.full_name or username,
        org_id=req.org_id or "default",
    )
    return {"message": f"User '{username}' created with role '{role.value}'"}


@app.get("/auth/roles")
def get_role_hierarchy() -> dict[str, Any]:
    """List all roles with hierarchy levels and descriptions."""
    return {
        "roles": [
            {
                "role": "viewer",
                "level": 1,
                "description": "View dashboards, jobs, and audit results — read-only",
            },
            {
                "role": "underwriter",
                "level": 2,
                "description": "Run pipelines, create audits, pull data sources",
            },
            {
                "role": "licensed_uw",
                "level": 3,
                "description": "Sign off decisions and bind policies",
            },
            {
                "role": "admin",
                "level": 4,
                "description": "Manage users, delete jobs, configure webhooks",
            },
            {
                "role": "cuo",
                "level": 5,
                "description": "Set market cycles and system-wide parameters",
            },
        ]
    }


# ── Dashboard ───────────────────────────────────────────────────

_UI_ASSETS = STATIC_DIR / "ui" / "assets"
if _UI_ASSETS.is_dir():
    app.mount("/dashboard/assets", StaticFiles(directory=_UI_ASSETS), name="dashboard-assets")


@app.get("/dashboard")
@app.get("/dashboard/")
def dashboard_root() -> FileResponse:
    return _dashboard_index()


@app.get("/dashboard/{full_path:path}")
def dashboard_spa(full_path: str) -> FileResponse:
    if full_path.startswith("assets/"):
        raise HTTPException(status_code=404, detail="Asset not found")
    return _dashboard_index()


def _dashboard_index() -> FileResponse:
    ui_index = STATIC_DIR / "ui" / "index.html"
    if ui_index.exists():
        return FileResponse(ui_index)
    path = STATIC_DIR / "dashboard.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return FileResponse(path)


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
    override_reason_category: str = ""  # pricing | coverage | terms | appetite | ...
    uw_confidence: str = ""  # low | medium | high


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


class InsuranceSourcePullRequest(BaseModel):
    path: Optional[str] = None
    package_id: Optional[str] = None
    bucket: Optional[str] = None
    prefix: str = ""
    folder_id: Optional[str] = None
    site_url: Optional[str] = None
    mailbox: Optional[str] = None
    host: Optional[str] = None
    environment: Optional[str] = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}


@app.get("/system/diagnostics")
async def system_diagnostics() -> dict[str, Any]:
    """Public system health — shows what's configured without exposing secrets."""
    from insureflow.health.diagnostics import SystemDiagnostics

    return SystemDiagnostics(project_root=PROJECT_ROOT).run_all()


@app.get("/api/demo/presets")
async def demo_presets() -> dict[str, Any]:
    """Available one-click demo submissions for the dashboard."""
    insurance = [
        {
            "id": "pacific-coast",
            "name": "Pacific Coast Marine",
            "description": "Commercial P&C — ACORD, loss run, SOV, inspection, broker API",
            "vertical": "insurance",
        }
    ]
    mortgage = [
        {
            "id": "johnson-residential",
            "name": "Johnson Family (Residential)",
            "description": "Full residential loan package — income, credit, property, UW docs",
            "vertical": "mortgage",
            "product_line": "residential_mortgage",
            "directory": str(SIM_DOCS_DIR / "home_mortgage" / "johnson_marcus_imani"),
        },
        {
            "id": "midwest-commercial",
            "name": "Midwest Medical Plaza (Commercial)",
            "description": "Commercial CRE package — entity financials, leases, due diligence",
            "vertical": "mortgage",
            "product_line": "commercial_mortgage",
            "directory": str(SIM_DOCS_DIR / "commercial_mortgage" / "midwest_medical_plaza"),
        },
    ]
    return {"insurance": insurance, "mortgage": mortgage}


@app.get("/api/dashboard/overview")
def dashboard_overview(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Aggregated job counts and recent activity for the dashboard home."""
    from insureflow.workflow.service import WorkflowService

    org_id = current.org_id

    def _recent_jobs(namespace: str, limit: int = 12) -> list[dict[str, Any]]:
        ids = job_store.list_ids(namespace, org_id=org_id)
        rows: list[dict[str, Any]] = []
        for job_id in reversed(ids[-limit:]):
            job = job_store.get(namespace, job_id, org_id=org_id) or {}
            row: dict[str, Any] = {
                "job_id": job_id,
                "status": job.get("status", "unknown"),
                "vertical": "insurance" if namespace == INSURANCE_NS else "mortgage",
            }
            results = job.get("results") or {}
            if isinstance(results, dict):
                if namespace == INSURANCE_NS:
                    memo = results.get("memo") or {}
                    row["decision"] = results.get("ai_decision") or (memo.get("decision") if isinstance(memo, dict) else None)
                    row["bundle_id"] = results.get("bundle_id")
                    row["insured_name"] = results.get("insured_name") or (memo.get("insured_name") if isinstance(memo, dict) else None)
                else:
                    summary = results.get("summary") or results.get("pipeline_summary") or results
                    if isinstance(summary, dict):
                        row["decision"] = summary.get("decision") or summary.get("recommendation")
                    row["bundle_id"] = results.get("bundle_id") or (summary.get("bundle_id") if isinstance(summary, dict) else None)
            rows.append(row)
        return rows

    ins_ids = job_store.list_ids(INSURANCE_NS, org_id=org_id)
    mort_ids = job_store.list_ids(MORTGAGE_NS, org_id=org_id)
    pending = WorkflowService().store.list_pending(org_id)

    def _count_status(namespace: str, ids: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {"processing": 0, "completed": 0, "failed": 0}
        for job_id in ids:
            job = job_store.get(namespace, job_id, org_id=org_id) or {}
            st = job.get("status", "unknown")
            counts[st] = counts.get(st, 0) + 1
        return counts

    ins_counts = _count_status(INSURANCE_NS, ins_ids)
    mort_counts = _count_status(MORTGAGE_NS, mort_ids)

    return {
        "org_id": org_id,
        "username": current.username,
        "role": current.role.value if current.role else "none",
        "insurance": {"total": len(ins_ids), **ins_counts},
        "mortgage": {"total": len(mort_ids), **mort_counts},
        "pending_reviews": len(pending),
        "recent_jobs": _recent_jobs(INSURANCE_NS) + _recent_jobs(MORTGAGE_NS),
        "pending": pending,
    }


def _load_pacific_coast_submission() -> SubmissionRequest:
    acord = (EXAMPLES_DIR / "pacific_coast_acord.xml").read_text(encoding="utf-8")
    loss_run = (EXAMPLES_DIR / "pacific_coast_loss_run.md").read_text(encoding="utf-8")
    sov = (EXAMPLES_DIR / "pacific_coast_sov.md").read_text(encoding="utf-8")
    inspection = (EXAMPLES_DIR / "pacific_coast_inspection_report.md").read_text(encoding="utf-8")
    broker = (EXAMPLES_DIR / "pacific_coast_broker_api.json").read_text(encoding="utf-8")
    return SubmissionRequest(
        acord_xml=acord,
        loss_run=loss_run,
        schedule_of_values=sov,
        inspection_reports=[inspection],
        json_payload=broker,
        use_llm=True,
    )


@app.post("/api/demo/insurance/{preset_id}", status_code=202)
async def run_insurance_demo(
    preset_id: str,
    background_tasks: BackgroundTasks,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    if preset_id != "pacific-coast":
        raise HTTPException(status_code=404, detail=f"Unknown insurance preset: {preset_id}")
    if not (EXAMPLES_DIR / "pacific_coast_acord.xml").exists():
        raise HTTPException(status_code=503, detail="Example data not found on server")
    job_id = f"demo-{uuid.uuid4().hex[:12]}"
    req = _load_pacific_coast_submission()
    job_store.set(INSURANCE_NS, job_id, {"status": "processing", "demo": True}, org_id=current.org_id)
    celery_app.send_task(
        "insureflow.tasks.pipeline_tasks.run_pipeline",
        args=[job_id, req.model_dump(), current.org_id],
        queue="pipeline",
    )
    return {"job_id": job_id, "status": "processing", "preset": preset_id, "org_id": current.org_id}


@app.get("/api/insurance/sources")
def list_insurance_sources() -> dict[str, Any]:
    from insureflow.ingestion.insurance.sources import list_sources

    return {"sources": list_sources(EXAMPLES_DIR)}


@app.post("/api/insurance/sources/{source_id}/pull")
def pull_insurance_source(
    source_id: str,
    req: InsuranceSourcePullRequest,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Pull submission documents from a connected source (library, folder, or simulated cloud)."""
    from insureflow.ingestion.insurance.sources import (
        DEMO_CONNECTORS,
        INSURANCE_PACKAGES,
        load_directory,
        load_package,
        simulated_connection_label,
    )

    try:
        if source_id in INSURANCE_PACKAGES:
            documents = load_package(EXAMPLES_DIR, source_id)
            meta = INSURANCE_PACKAGES[source_id]
            return {
                "source_id": source_id,
                "simulated": False,
                "connection_label": meta["name"],
                "package_id": source_id,
                "package_name": meta["name"],
                "documents": documents,
                "file_count": len(documents),
            }

        if source_id in DEMO_CONNECTORS:
            package_id = req.package_id or "pacific-coast"
            documents = load_package(EXAMPLES_DIR, package_id)
            meta = INSURANCE_PACKAGES[package_id]
            return {
                "source_id": source_id,
                "simulated": True,
                "connection_label": simulated_connection_label(source_id, req),
                "package_id": package_id,
                "package_name": meta["name"],
                "documents": documents,
                "file_count": len(documents),
            }

        if source_id == "server-folder":
            raw = req.path or "examples"
            directory = Path(raw)
            if not directory.is_absolute():
                directory = (PROJECT_ROOT / raw).resolve()
            if not str(directory).startswith(str(PROJECT_ROOT.resolve())):
                raise HTTPException(status_code=400, detail="Path must be under project root")
            documents = load_directory(directory)
            return {
                "source_id": source_id,
                "simulated": False,
                "connection_label": str(directory),
                "documents": documents,
                "file_count": len(documents),
            }

        raise HTTPException(status_code=404, detail=f"Unknown source: {source_id}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/demo/mortgage/{preset_id}", status_code=202)
async def run_mortgage_demo(
    preset_id: str,
    background_tasks: BackgroundTasks,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    presets = {
        "johnson-residential": (
            SIM_DOCS_DIR / "home_mortgage" / "johnson_marcus_imani",
            "residential_mortgage",
        ),
        "midwest-commercial": (
            SIM_DOCS_DIR / "commercial_mortgage" / "midwest_medical_plaza",
            "commercial_mortgage",
        ),
    }
    if preset_id not in presets:
        raise HTTPException(status_code=404, detail=f"Unknown mortgage preset: {preset_id}")
    directory, product_line = presets[preset_id]
    if not directory.is_dir():
        raise HTTPException(status_code=503, detail=f"Fixture directory missing: {directory}")
    job_id = f"demo-mort-{uuid.uuid4().hex[:12]}"
    req = MortgageSubmissionRequest(
        directory=str(directory),
        product_line=product_line,
        use_llm=True,
        bundle_id=job_id,
    )
    job_store.set(MORTGAGE_NS, job_id, {"status": "processing", "demo": True}, org_id=current.org_id)
    background_tasks.add_task(_run_mortgage_task, job_id, req, current.org_id)
    return {"job_id": job_id, "status": "processing", "preset": preset_id, "org_id": current.org_id}


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "InsureFlow AI",
        "version": "0.2.0",
        "dashboard": "/dashboard",
        "diagnostics": "/system/diagnostics",
        "health": "/health",
    }


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
@limiter.limit("10/minute")
async def run_pipeline(
    req: SubmissionRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    job_store.set(INSURANCE_NS, job_id, {"status": "processing"}, org_id=current.org_id)
    celery_app.send_task(
        "insureflow.tasks.pipeline_tasks.run_pipeline",
        args=[job_id, req.model_dump(), current.org_id],
        queue="pipeline",
    )
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


@app.get("/pipeline/jobs/{job_id}/quote")
def get_job_quote(
    job_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> HTMLResponse:
    job = job_store.get(INSURANCE_NS, job_id, org_id=current.org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    html = job.get("quote_html", "")
    if not html:
        raise HTTPException(status_code=404, detail="Quote document not available")
    return HTMLResponse(content=html, status_code=200)


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

    return {
        "org_id": current.org_id,
        "pending": WorkflowService().store.list_pending(current.org_id),
    }


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

    # Capture structured override analytics when UW decision differs from AI
    if req.override_reason and record.ai_decision and record.final_decision:
        from uuid import uuid4

        from insureflow.outcomes.analytics import get_analytics_engine
        from insureflow.outcomes.override import (
            OverrideDetail,
            OverrideReasonCategory,
        )

        try:
            category = OverrideReasonCategory(req.override_reason_category.lower())
        except (ValueError, AttributeError):
            from insureflow.outcomes.override import OverrideReasonCategory

            category = OverrideReasonCategory.OTHER

        ai_decision = record.ai_decision
        uw_decision = record.final_decision
        decision_changed = ai_decision != uw_decision

        detail = OverrideDetail(
            override_id=f"ovr-{uuid4().hex[:10]}",
            sign_off_id=record.sign_offs[-1].sign_off_id if record.sign_offs else "",
            bundle_id=bundle_id,
            org_id=current.org_id,
            ai_decision=ai_decision,
            uw_decision=uw_decision,
            decision_changed=decision_changed,
            reason_category=category,
            reason_freeform=req.override_reason,
            uw_confidence=req.uw_confidence,
        )
        get_analytics_engine().record_override(detail)

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

    record = wf.store.get(bundle_id, current.org_id) or record

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
def get_calibration_summary(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.outcomes.feedback import FeedbackEngine

    return FeedbackEngine().calibration_summary(current.org_id)


@app.get("/analytics/overrides")
def list_override_analytics(
    limit: int = 100,
    offset: int = 0,
    reason_category: str = "",
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.outcomes.analytics import get_analytics_engine
    from insureflow.outcomes.override import OverrideAnalyticsQuery, OverrideReasonCategory

    query = OverrideAnalyticsQuery(
        org_id=current.org_id,
        limit=limit,
        offset=offset,
        reason_category=OverrideReasonCategory(reason_category) if reason_category else None,
    )
    engine = get_analytics_engine()
    return {
        "summary": engine.generate_summary(current.org_id).model_dump(),
        "overrides": [o.model_dump() for o in engine.query_overrides(query)],
    }


@app.get("/analytics/overrides/patterns")
def list_override_patterns(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.outcomes.analytics import get_analytics_engine

    engine = get_analytics_engine()
    return {
        "patterns": [p.model_dump() for p in engine.get_patterns()],
    }


# ── Underwriting Workspace Endpoints ──────────────────────────────


@app.get("/pipeline/queue")
def get_submission_queue(
    priority: str = "",
    limit: int = 50,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Get the prioritized submission queue — sorted by triage score."""
    from insureflow.agents.triage_agent import SubmissionPriority, get_triage_agent

    ta = get_triage_agent()
    pri = SubmissionPriority(priority) if priority else None
    return {
        "queue": [{k: v for k, v in r.__dict__.items() if not k.startswith("_")} for r in ta.get_queue(pri, limit)],
        "statistics": ta.get_statistics(),
    }


@app.get("/pipeline/cope/{bundle_id}")
def get_cope_analysis(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Run COPE risk analysis on a submission bundle."""
    from insureflow.underwriting.cope import COPERatingEngine
    from insureflow.workflow.service import WorkflowService

    svc = WorkflowService()
    record = svc.store.get(bundle_id, current.org_id)
    if not record:
        raise HTTPException(status_code=404, detail="Submission not found")

    from insureflow.audit.store import AuditStore

    store = AuditStore()
    bundle = store.load_json(bundle_id, "submission_bundle.json", org_id=current.org_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle data not found")

    from insureflow.models.submissions import SubmissionBundle

    cope = COPERatingEngine()
    result = cope.analyze(SubmissionBundle(**bundle))
    return {
        "cope_score": result.score.__dict__,
        "construction": {
            "class": result.construction_class.value if result.construction_class else None,
            "raw": result.construction_raw,
            "mod_pct": result.score.construction_mod_pct,
            "detail": result.construction_detail,
        },
        "occupancy": {
            "class": result.occupancy_class.value if result.occupancy_class else None,
            "raw": result.occupancy_raw,
            "mod_pct": result.score.occupancy_mod_pct,
            "detail": result.occupancy_detail,
        },
        "protection": {
            "class": result.protection_class,
            "mod_pct": result.score.protection_mod_pct,
            "detail": result.protection_detail,
        },
        "exposure": {
            "types": [e.value for e in result.exposure_types],
            "mod_pct": result.score.exposure_mod_pct,
            "detail": result.exposure_detail,
        },
    }


@app.get("/underwriting/market")
def get_market_cycle_status(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Get current market phase and its impact on pricing/appetite."""
    from insureflow.underwriting.market import get_market_cycle

    return get_market_cycle().market_adjustment_narrative()


@app.post("/underwriting/market/set")
def set_market_cycle(
    phase: str,
    current: TokenData = Depends(require_role(Role.CUO)),
) -> dict[str, Any]:
    """Set market phase (hard/soft) — CUO-level access only."""
    from insureflow.underwriting.market import MarketCycle, MarketPhase, get_market_cycle

    try:
        mp = MarketPhase(phase.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phase: {phase} (use: hard, soft, transitioning_hard, transitioning_soft)",
        )

    cycles = {
        MarketPhase.HARD: MarketCycle(
            phase=MarketPhase.HARD,
            property_rate_mod=1.25,
            liability_rate_mod=1.15,
            workers_comp_rate_mod=0.95,
            auto_rate_mod=1.30,
            appetite_tightness=1.4,
            reinsurance_cost_mod=1.20,
            industry_loss_ratio=0.73,
            capacity_available=False,
            nuclear_verdict_trend="rising",
            description="Hard market: Rates rising, capacity tightening. Nuclear verdicts driving increases.",
        ),
        MarketPhase.SOFT: MarketCycle(
            phase=MarketPhase.SOFT,
            property_rate_mod=0.92,
            liability_rate_mod=0.95,
            workers_comp_rate_mod=0.90,
            auto_rate_mod=0.96,
            appetite_tightness=0.80,
            reinsurance_cost_mod=0.90,
            industry_loss_ratio=0.55,
            capacity_available=True,
            nuclear_verdict_trend="stable",
            description="Soft market: Rates declining 4-8%. Capacity abundant. Competition increasing.",
        ),
        MarketPhase.TRANSITIONING_HARD: MarketCycle(
            phase=MarketPhase.TRANSITIONING_HARD,
            property_rate_mod=1.10,
            liability_rate_mod=1.05,
            workers_comp_rate_mod=0.92,
            auto_rate_mod=1.15,
            appetite_tightness=1.15,
            reinsurance_cost_mod=1.08,
            industry_loss_ratio=0.65,
            capacity_available=True,
            nuclear_verdict_trend="stable",
            description="Transitioning from hard to soft: Rates still elevated but capacity returning.",
        ),
    }

    mc = get_market_cycle()
    mc.set_cycle(cycles.get(mp, cycles[MarketPhase.SOFT]))
    return mc.market_adjustment_narrative()


@app.get("/underwriting/authority")
def list_underwriting_authorities(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """List all underwriter authority levels and binding limits."""
    from insureflow.underwriting.authority import get_authority_matrix

    matrix = get_authority_matrix()
    return {
        "authorities": [
            {
                "username": a.username,
                "display_name": a.display_name,
                "tier": a.tier.value,
                "license_number": a.license_number,
                "binding_authority": {
                    "max_premium": a.binding_authority.max_premium,
                    "max_tiv": a.binding_authority.max_tiv,
                    "requires_co_sign": a.binding_authority.requires_co_sign,
                    "co_sign_threshold_premium": a.binding_authority.co_sign_threshold_premium,
                    "max_aggregate_exposure": a.binding_authority.max_aggregate_exposure,
                },
            }
            for a in matrix.list_all()
        ]
    }


@app.post("/pipeline/renewal/{bundle_id}")
def analyze_renewal(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Run renewal analysis on an existing policy."""
    from insureflow.underwriting.renewal import RenewalEngine
    from insureflow.workflow.service import WorkflowService

    record = WorkflowService().store.get(bundle_id, current.org_id)
    if not record:
        raise HTTPException(status_code=404, detail="Submission not found")

    engine = RenewalEngine()
    from datetime import date, timedelta

    rec = engine.analyze_renewal(
        bundle_id=bundle_id,
        insured_name="",  # Would come from bundle
        current_premium=0.0,
        loss_ratio=0.0,
        expiry_date=date.today() + timedelta(days=90),
    )
    return rec.__dict__


# ── Premium Audit Endpoints ────────────────────────────────────


_audit_engine: Optional[PremiumAuditEngine] = None


def _get_audit_engine() -> PremiumAuditEngine:
    global _audit_engine
    if _audit_engine is None:
        from insureflow.underwriting.renewal import PremiumAuditEngine

        _audit_engine = PremiumAuditEngine()
    return _audit_engine


@app.post("/pipeline/audits/{bundle_id}/create")
def create_premium_audit(
    bundle_id: str,
    estimated_premium: float,
    policy_period_start: Optional[str] = None,
    policy_period_end: Optional[str] = None,
    policy_number: str = "",
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Create a premium audit for end-of-year reconciliation."""
    engine = _get_audit_engine()
    from datetime import date

    p_start = date.fromisoformat(policy_period_start) if policy_period_start else None
    p_end = date.fromisoformat(policy_period_end) if policy_period_end else None
    audit = engine.create_audit(
        bundle_id=bundle_id,
        estimated_premium=estimated_premium,
        policy_period_start=p_start,
        policy_period_end=p_end,
        policy_number=policy_number,
        org_id=current.org_id,
    )
    return audit.__dict__


@app.post("/pipeline/audits/{audit_id}/adjustment")
def add_audit_adjustment(
    audit_id: str,
    adjustment_type: str,
    description: str,
    amount: float,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Add an adjustment to a premium audit."""
    from insureflow.underwriting.renewal import AuditAdjustmentType

    engine = _get_audit_engine()
    try:
        adj_type = AuditAdjustmentType(adjustment_type)
        audit = engine.add_adjustment(audit_id, adj_type, description, amount)
    except KeyError:
        raise HTTPException(status_code=404, detail="Audit not found")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid adjustment type: {adjustment_type}")
    return audit.__dict__


@app.post("/pipeline/audits/{audit_id}/complete")
def complete_premium_audit(
    audit_id: str,
    actual_premium: float,
    audited_exposure: str = "",
    notes: str = "",
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Complete a premium audit with actual figures."""
    engine = _get_audit_engine()
    try:
        audit = engine.complete_audit(
            audit_id,
            actual_premium,
            audited_exposure=audited_exposure,
            notes=notes,
            reconciled_by=current.username,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit.__dict__


@app.get("/pipeline/audits")
def list_premium_audits(
    status: Optional[str] = None,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """List premium audits with optional status filter."""
    from insureflow.underwriting.renewal import AuditStatus

    engine = _get_audit_engine()
    audit_status = AuditStatus(status) if status else None
    audits = engine.list_audits(org_id=current.org_id, status=audit_status)
    return {"audits": [a.__dict__ for a in audits], "total": len(audits)}


@app.get("/pipeline/audits/material-adjustments")
def material_audit_adjustments(
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Audits with material adjustments needing UW review."""
    engine = _get_audit_engine()
    audits = engine.audits_needing_renewal_review(org_id=current.org_id)
    return {"audits": [a.__dict__ for a in audits], "total": len(audits)}


@app.get("/pipeline/documents/{bundle_id}/missing")
def get_missing_documents(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Get list of missing documents for a submission."""
    from insureflow.workflow.service import WorkflowService

    record = WorkflowService().store.get(bundle_id, current.org_id)
    if not record:
        raise HTTPException(status_code=404, detail="Submission not found")

    from insureflow.audit.store import AuditStore

    store = AuditStore()
    bundle_data = store.load_json(bundle_id, "submission_bundle.json", org_id=current.org_id)

    if not bundle_data:
        from insureflow.agents.triage_agent import DocumentChecklist

        checklist = DocumentChecklist()
    else:
        from insureflow.models.submissions import SubmissionBundle

        bundle = SubmissionBundle(**bundle_data)
        from insureflow.agents.triage_agent import get_triage_agent

        result = get_triage_agent().score_submission(bundle)
        checklist = result.document_checklist

    return {
        "bundle_id": bundle_id,
        "completeness_pct": checklist.completeness_pct,
        "missing_documents": checklist.missing,
    }


@app.get("/pipeline/rating/products")
def list_insurance_products(_: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    from insureflow.rating.engine import ISO_LOSS_COSTS
    from insureflow.rating.models import InsuranceLine

    return {
        "lines": [
            {
                "id": line.value,
                "base_rate_per_100": ISO_LOSS_COSTS.get(line, 0.0),
            }
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


class LendingSubmissionRequest(BaseModel):
    product_type: str = "business_term_loan"
    amount: float = 100000.0
    term_months: int = 12
    purpose: str = "other"
    business_name: str = ""
    industry: str = ""
    revenue: float = 0.0
    net_income: float = 0.0
    ebitda: float = 0.0
    debt_service: float = 0.0
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    current_assets: float = 0.0
    current_liabilities: float = 0.0
    collateral_value: float = 0.0
    years_in_business: float = 0.0
    credit_score: int = 0
    annual_income: float = 0.0
    monthly_debt: float = 0.0
    employment_years: float = 0.0
    bankruptcies: int = 0
    foreclosures: int = 0


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
            job_store.set(
                MORTGAGE_NS,
                job_id,
                {
                    "status": "failed",
                    "error": "Provide documents or directory",
                },
                org_id=org_id,
            )
            webhook_dispatcher.dispatch("mortgage.failed", org_id, {"job_id": job_id, "error": "no input"})
            return

        job_store.set(MORTGAGE_NS, job_id, {"status": "completed", "results": result}, org_id=org_id)
    except Exception as exc:
        logger.exception("Mortgage pipeline run failed")
        job_store.set(MORTGAGE_NS, job_id, {"status": "failed", "error": str(exc)}, org_id=org_id)
        from insureflow.mortgage.webhooks import webhook_dispatcher

        webhook_dispatcher.dispatch("mortgage.failed", org_id, {"job_id": job_id, "error": str(exc)})


def _finalize_celery_mortgage_job(job_id: str, org_id: str, job: dict[str, Any]) -> dict[str, Any]:
    """Promote finished Celery task state into job_store (lazy sync on poll)."""
    if job.get("status") != "processing" or job.get("backend") != "celery":
        return job
    task_id = job.get("celery_task_id")
    if not task_id:
        return job

    from celery.result import AsyncResult

    from insureflow.mortgage.webhooks import webhook_dispatcher
    from insureflow.tasks.celery_app import celery_app

    async_result = AsyncResult(task_id, app=celery_app)
    if not async_result.ready():
        return job

    if async_result.successful():
        result = async_result.result
        updated: dict[str, Any] = {
            "status": "completed",
            "results": result,
            "backend": "celery",
            "celery_task_id": task_id,
        }
        job_store.set(MORTGAGE_NS, job_id, updated, org_id=org_id)
        webhook_dispatcher.dispatch("mortgage.completed", org_id, {"job_id": job_id, "results": result})
        return updated

    error = str(async_result.result) if async_result.failed() else "Celery task failed"
    updated = {
        "status": "failed",
        "error": error,
        "backend": "celery",
        "celery_task_id": task_id,
    }
    job_store.set(MORTGAGE_NS, job_id, updated, org_id=org_id)
    webhook_dispatcher.dispatch("mortgage.failed", org_id, {"job_id": job_id, "error": error})
    return updated


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
            bundle_id=request.bundle_id or job_id,
            product_line=request.product_line,
            use_llm=request.use_llm,
            job_id=job_id,
            org_id=org_id,
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

    job_store.set(
        MORTGAGE_NS,
        job_id,
        {
            "status": "processing",
            "backend": "celery",
            "celery_task_id": task.id,
        },
        org_id=org_id,
    )


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
    return _finalize_celery_mortgage_job(job_id, current.org_id, job)


@app.get("/mortgage/pipeline/jobs")
def list_mortgage_jobs(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, list[str]]:
    return {"jobs": job_store.list_ids(MORTGAGE_NS, org_id=current.org_id)}


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
            {
                "subscription_id": s.subscription_id,
                "url": s.url,
                "events": s.events,
                "active": s.active,
            }
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


# ── Broker / Agent Real-Time Visibility ──────────────────────────


@app.get("/broker/status/{token}")
def broker_submission_status(
    token: str,
) -> dict[str, Any]:
    """Public (no-auth) endpoint for brokers to check submission status via share token."""
    from insureflow.webhooks.dispatcher import webhook_dispatcher

    share = webhook_dispatcher.get_broker_share(token)
    if not share:
        raise HTTPException(status_code=404, detail="Invalid or expired broker status link")

    job = job_store.get(INSURANCE_NS, share.bundle_id, org_id=share.org_id)
    if not job:
        job = job_store.get(MORTGAGE_NS, share.bundle_id, org_id=share.org_id)

    status = (job or {}).get("status", "unknown")
    results = (job or {}).get("results") or {}

    return {
        "bundle_id": share.bundle_id,
        "status": status,
        "broker_name": share.broker_name,
        "vertical": "insurance" if job_store.get(INSURANCE_NS, share.bundle_id, org_id=share.org_id) else "mortgage",
        "decision": results.get("ai_decision") or ((results.get("memo") or {}).get("decision") if isinstance(results, dict) else None),
        "workflow_state": results.get("workflow_state", ""),
        "estimated_completion": None,
        "last_updated": (job or {}).get("updated_at", ""),
    }


class BrokerShareRequest(BaseModel):
    broker_name: str = ""
    broker_email: str = ""


@app.post("/pipeline/jobs/{bundle_id}/broker-share")
def create_broker_share(
    bundle_id: str,
    req: BrokerShareRequest,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, str]:
    """Generate a shareable broker status link for this bundle."""
    from insureflow.webhooks.dispatcher import webhook_dispatcher

    token = webhook_dispatcher.create_broker_share(
        bundle_id=bundle_id,
        org_id=current.org_id,
        broker_name=req.broker_name,
        broker_email=req.broker_email,
    )
    return {
        "token": token,
        "bundle_id": bundle_id,
        "status_url": f"/broker/status/{token}",
    }


# ── Unified Webhook Management (Insurance + Mortgage) ────────────


class InsuranceWebhookRegisterRequest(BaseModel):
    url: str
    events: list[str] = ["insurance.completed", "insurance.failed"]
    secret: str = ""
    label: str = ""


@app.post("/webhooks/insurance", status_code=201)
def register_insurance_webhook(
    req: InsuranceWebhookRegisterRequest,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    from insureflow.webhooks.dispatcher import webhook_dispatcher

    sub = webhook_dispatcher.register(
        org_id=current.org_id,
        url=req.url,
        events=req.events or ["insurance.completed", "insurance.failed"],
        secret=req.secret,
        label=req.label,
    )
    return {
        "subscription_id": sub.subscription_id,
        "org_id": sub.org_id,
        "url": sub.url,
        "events": sub.events,
        "label": sub.label,
    }


@app.get("/webhooks/insurance")
def list_insurance_webhooks(
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    from insureflow.webhooks.dispatcher import webhook_dispatcher

    subs = webhook_dispatcher.list_for_org(current.org_id)
    insurance_subs = [s for s in subs if any("insurance" in e for e in s.events)]
    return {
        "org_id": current.org_id,
        "subscriptions": [
            {
                "subscription_id": s.subscription_id,
                "url": s.url,
                "events": s.events,
                "active": s.active,
                "label": s.label,
            }
            for s in insurance_subs
        ],
    }


@app.delete("/webhooks/{subscription_id}", status_code=204)
def delete_any_webhook(
    subscription_id: str,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> None:
    from insureflow.webhooks.dispatcher import webhook_dispatcher

    if not webhook_dispatcher.unregister(subscription_id, current.org_id):
        raise HTTPException(status_code=404, detail="Webhook not found")


# ── Portfolio Concentration ──────────────────────────────────────


@app.get("/portfolio/summary")
def portfolio_summary(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """View the carrier's current portfolio composition for concentration analysis."""
    from insureflow.portfolio.store import get_portfolio_store

    store = get_portfolio_store()
    policies = store.list_policies(org_id=current.org_id)

    by_state: dict[str, dict[str, Any]] = {}
    by_naics2: dict[str, dict[str, Any]] = {}
    total_tiv = 0.0
    total_policies = len(policies)

    for p in policies:
        total_tiv += p.tiv
        state = p.geographic_region
        if state not in by_state:
            by_state[state] = {"count": 0, "tiv": 0.0, "policies": []}
        by_state[state]["count"] += 1
        by_state[state]["tiv"] += p.tiv
        by_state[state]["policies"].append(
            {
                "insured_name": p.insured_name,
                "tiv": p.tiv,
                "naics": p.naics_code,
            }
        )

        naics2 = p.industry_code
        if naics2 not in by_naics2:
            by_naics2[naics2] = {"count": 0, "tiv": 0.0, "policies": []}
        by_naics2[naics2]["count"] += 1
        by_naics2[naics2]["tiv"] += p.tiv
        by_naics2[naics2]["policies"].append(
            {
                "insured_name": p.insured_name,
                "tiv": p.tiv,
                "state": p.state,
            }
        )

    return {
        "org_id": current.org_id,
        "total_policies": total_policies,
        "total_tiv": total_tiv,
        "by_state": {
            state: {
                "count": info["count"],
                "tiv": info["tiv"],
                "pct": round(info["tiv"] / total_tiv * 100, 1) if total_tiv else 0,
            }
            for state, info in sorted(by_state.items(), key=lambda x: -x[1]["tiv"])
        },
        "by_industry": {
            naics: {
                "count": info["count"],
                "tiv": info["tiv"],
                "pct": round(info["tiv"] / total_tiv * 100, 1) if total_tiv else 0,
            }
            for naics, info in sorted(by_naics2.items(), key=lambda x: -x[1]["tiv"])
        },
        "concentration_warnings": [f"{state}: {info['tiv'] / total_tiv * 100:.0f}% of portfolio TIV" for state, info in by_state.items() if total_tiv > 0 and info["tiv"] / total_tiv > 0.30],
    }


# ── Core System Integration Status ────────────────────────────────


@app.get("/integration/status")
def integration_status(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Check which core systems are configured and their connectivity."""
    from insureflow.integration.britecore_adapter import BriteCoreAdapter
    from insureflow.integration.guidewire_adapter import GuidewireAdapter

    britecore = BriteCoreAdapter(api_key=os.getenv("BRITECORE_API_KEY", ""))
    guidewire = GuidewireAdapter(api_key=os.getenv("GUIDEWIRE_API_KEY", ""))

    return {
        "systems": [
            {
                "name": britecore.get_system_name(),
                "configured": bool(os.getenv("BRITECORE_API_KEY")),
                "mode": "simulated" if not os.getenv("BRITECORE_API_KEY") else "live",
                "healthy": True,
            },
            {
                "name": guidewire.get_system_name(),
                "configured": bool(os.getenv("GUIDEWIRE_API_KEY")),
                "mode": "simulated" if not os.getenv("GUIDEWIRE_API_KEY") else "live",
                "healthy": True,
            },
        ]
    }


# ── Pipeline Configuration (enhanced with new features) ──────────


class PipelineConfigRequest(BaseModel):
    """Extended submission request with new pipeline feature toggles."""

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
    skip_appetite_filter: bool = False
    skip_oracles: bool = False
    skip_portfolio: bool = False
    skip_core_integration: bool = False
    create_broker_share: bool = False


@app.post("/pipeline/v2/run", status_code=202)
async def run_pipeline_v2(
    req: PipelineConfigRequest,
    background_tasks: BackgroundTasks,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Enhanced pipeline run with appetite filter, oracles, portfolio, and core integration."""
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    job_store.set(
        INSURANCE_NS,
        job_id,
        {"status": "processing", "pipeline_version": "v2"},
        org_id=current.org_id,
    )
    background_tasks.add_task(_run_pipeline_v2_task, job_id, req, current.org_id)
    return {
        "job_id": job_id,
        "status": "processing",
        "pipeline_version": "v2",
        "org_id": current.org_id,
    }


def _run_pipeline_v2_task(job_id: str, request: PipelineConfigRequest, org_id: str) -> None:
    try:
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
            skip_appetite_filter=request.skip_appetite_filter,
            skip_oracles=request.skip_oracles,
            skip_portfolio=request.skip_portfolio,
            skip_core_integration=request.skip_core_integration,
        )

        if request.create_broker_share and result.get("bundle_id"):
            from insureflow.webhooks.dispatcher import webhook_dispatcher

            token = webhook_dispatcher.create_broker_share(
                bundle_id=result["bundle_id"],
                org_id=org_id,
                broker_name=result.get("broker_name", ""),
            )
            result["broker_status_token"] = token
            result["broker_status_url"] = f"/broker/status/{token}"

        job_store.set(INSURANCE_NS, job_id, {"status": "completed", "results": result}, org_id=org_id)
    except Exception as exc:
        logger.exception("Pipeline v2 run failed")
        job_store.set(INSURANCE_NS, job_id, {"status": "failed", "error": str(exc)}, org_id=org_id)


# ── Registry API (Model Versioning & Compliance Review) ────────────────


@app.get("/registry/versions")
def list_registry_versions(
    component: str = "",
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.registry import ComponentType, RegistryService

    reg = RegistryService()
    if component:
        try:
            ct = ComponentType(component)
            entries = reg.list_versions(ct)
        except ValueError:
            return {"error": f"Invalid component type: {component}"}
    else:
        entries = []
        for ct in ComponentType:
            entries.extend(reg.list_versions(ct))

    return {
        "total": len(entries),
        "entries": [e.model_dump(mode="json") for e in entries],
    }


@app.get("/registry/versions/{entry_id}")
def get_registry_version(
    entry_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    entry = reg.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Version entry not found")
    return entry.model_dump(mode="json")


@app.post("/registry/versions", status_code=201)
def create_registry_version(
    component: str,
    key: str = "",
    version: str = "1.0.0",
    description: str = "",
    change_notes: str = "",
    creator: str = "api",
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    from insureflow.registry import ComponentType, RegistryService
    from insureflow.registry.models import (
        AgentLogicVersion,
        ComplianceRuleVersion,
        LLMConfigVersion,
        PromptVersion,
    )

    reg = RegistryService()
    ct = ComponentType(component)

    if ct == ComponentType.PROMPT:
        from insureflow.agents.prompts import SYSTEM_PROMPTS

        prompt_text = SYSTEM_PROMPTS.get(key, "")
        if not prompt_text:
            raise HTTPException(status_code=400, detail=f"Unknown prompt key: {key}")
        entry = PromptVersion(
            component_type=ct,
            version_label=version,
            created_by=creator,
            description=description,
            change_notes=change_notes,
            prompt_key=key,
            prompt_text=prompt_text,
        )
    elif ct == ComponentType.LLM_CONFIG:
        entry = LLMConfigVersion(
            component_type=ct,
            version_label=version,
            created_by=creator,
            description=description,
            change_notes=change_notes,
            model_tier=key,
        )
    elif ct == ComponentType.COMPLIANCE_RULE:
        from insureflow.mortgage.compliance import BANK_RULES

        rules = {}
        for rule in BANK_RULES:
            rules[rule.rule_id] = {
                "name": rule.name,
                "severity": rule.severity,
                "product_lines": [p.value for p in rule.product_lines],
            }
        entry = ComplianceRuleVersion(
            component_type=ct,
            version_label=version,
            created_by=creator,
            description=description,
            change_notes=change_notes,
            rules_snapshot=rules,
        )
    elif ct == ComponentType.AGENT_LOGIC:
        entry = AgentLogicVersion(
            component_type=ct,
            version_label=version,
            created_by=creator,
            description=description,
            change_notes=change_notes,
            agent_type=key,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported component: {component}")

    result = reg.create(entry)
    return result.model_dump(mode="json")


@app.post("/registry/versions/{entry_id}/submit")
def submit_registry_version(
    entry_id: str,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    entry = reg.submit_for_review(entry_id)
    if not entry:
        raise HTTPException(status_code=400, detail="Cannot submit — not found or not DRAFT")
    return {"status": "submitted", "entry": entry.model_dump(mode="json")}


class ReviewRequest(BaseModel):
    reviewer: str = "api-user"
    comment: str = ""


@app.post("/registry/versions/{entry_id}/approve")
def approve_registry_version(
    entry_id: str,
    req: ReviewRequest = ReviewRequest(),
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    entry = reg.approve(entry_id, reviewer=req.reviewer, comment=req.comment)
    if not entry:
        raise HTTPException(status_code=400, detail="Cannot approve — not found or not in REVIEW")
    return {"status": "approved", "entry": entry.model_dump(mode="json")}


@app.post("/registry/versions/{entry_id}/reject")
def reject_registry_version(
    entry_id: str,
    req: ReviewRequest = ReviewRequest(),
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    entry = reg.reject(entry_id, reviewer=req.reviewer, comment=req.comment)
    if not entry:
        raise HTTPException(status_code=400, detail="Cannot reject — not found or not in REVIEW")
    return {"status": "rejected", "entry": entry.model_dump(mode="json")}


@app.get("/registry/diff")
def diff_registry_versions(
    id_a: str,
    id_b: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    diff = reg.compute_diff(id_a, id_b)
    if "error" in diff:
        raise HTTPException(status_code=404, detail=diff["error"])
    return diff


@app.get("/registry/context")
def registry_version_context(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    return reg.version_context()


@app.post("/registry/snapshot", status_code=201)
def take_registry_snapshot(
    bundle_id: str = "",
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    snapshot = reg.take_snapshot(bundle_id=bundle_id)
    return snapshot.model_dump(mode="json")


@app.get("/registry/snapshots")
def list_registry_snapshots(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    snapshots = reg.list_snapshots()
    return {
        "total": len(snapshots),
        "snapshots": [s.model_dump(mode="json") for s in snapshots],
    }


@app.post("/registry/bootstrap", status_code=201)
def bootstrap_registry(
    creator: str = "api",
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    from insureflow.registry import RegistryService

    reg = RegistryService()
    entries = reg.bootstrap(created_by=creator)
    return {
        "message": f"Bootstrapped {len(entries)} approved versions",
        "total": len(entries),
        "entries": [e.model_dump(mode="json") for e in entries],
    }


# ── Document Analytics API ───────────────────────────────────────────────


@app.get("/analytics/documents")
def document_analytics(
    vertical: str = "",
    distribution: bool = False,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.analytics.documents import DocumentAnalyticsEngine

    engine = DocumentAnalyticsEngine()
    if distribution:
        return {"distribution": engine.distribution(vertical=vertical)}
    return engine.summary(vertical=vertical)


# ── Lending API ──────────────────────────────────────────────────────────


@app.post("/lending/pipeline/run", status_code=200)
def run_lending_pipeline(
    req: LendingSubmissionRequest,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Run lending underwriting for a business or consumer loan application."""
    from insureflow.lending import LendingPipeline
    from insureflow.lending.models import (
        BusinessFinancialData,
        BusinessLoanApplication,
        ConsumerFinancialData,
        ConsumerLoanApplication,
        LoanProductType,
        LoanPurpose,
    )

    product_map: dict[str, LoanProductType] = {
        "business_term_loan": LoanProductType.BUSINESS_TERM_LOAN,
        "business_loc": LoanProductType.BUSINESS_LINE_OF_CREDIT,
        "cre": LoanProductType.COMMERCIAL_REAL_ESTATE,
        "construction": LoanProductType.CONSTRUCTION_LOAN,
        "sba_7a": LoanProductType.SBA_7A,
        "sba_504": LoanProductType.SBA_504,
        "equipment": LoanProductType.EQUIPMENT_FINANCING,
        "invoice": LoanProductType.INVOICE_FINANCING,
        "personal_term": LoanProductType.PERSONAL_TERM_LOAN,
        "personal_loc": LoanProductType.PERSONAL_LINE_OF_CREDIT,
        "auto": LoanProductType.AUTO_LOAN,
        "boat": LoanProductType.BOAT_LOAN,
        "heloc": LoanProductType.HOME_EQUITY_LINE,
        "secured": LoanProductType.SECURED_PERSONAL,
        "unsecured": LoanProductType.UNSECURED_PERSONAL,
    }
    purpose_map: dict[str, LoanPurpose] = {
        "working_capital": LoanPurpose.WORKING_CAPITAL,
        "refinance": LoanPurpose.DEBT_REFINANCE,
        "equipment": LoanPurpose.EQUIPMENT_PURCHASE,
        "real_estate": LoanPurpose.REAL_ESTATE_PURCHASE,
        "construction": LoanPurpose.CONSTRUCTION,
        "expansion": LoanPurpose.BUSINESS_EXPANSION,
        "inventory": LoanPurpose.INVENTORY_FINANCING,
        "acquisition": LoanPurpose.ACQUISITION,
        "auto": LoanPurpose.AUTO_PURCHASE,
        "boat": LoanPurpose.BOAT_PURCHASE,
        "home_improvement": LoanPurpose.HOME_IMPROVEMENT,
        "debt_consolidation": LoanPurpose.DEBT_CONSOLIDATION,
        "education": LoanPurpose.EDUCATION,
        "medical": LoanPurpose.MEDICAL,
        "other": LoanPurpose.OTHER,
    }

    pt = product_map.get(req.product_type)
    if pt is None:
        raise HTTPException(status_code=400, detail=f"Unknown product: {req.product_type}")

    purp = purpose_map.get(req.purpose, LoanPurpose.OTHER)
    is_business = pt.value.startswith(("business_", "commercial_", "construction_", "sba_", "equipment_", "invoice_"))

    if is_business:
        from insureflow.lending.models import Collateral

        fin = BusinessFinancialData(
            annual_revenue=req.revenue,
            net_income=req.net_income,
            ebitda=req.ebitda,
            debt_service=req.debt_service,
            total_assets=req.total_assets,
            total_liabilities=req.total_liabilities,
            current_assets=req.current_assets,
            current_liabilities=req.current_liabilities,
        )
        coll = [Collateral(estimated_value=req.collateral_value)] if req.collateral_value > 0 else []
        app = BusinessLoanApplication(
            business_name=req.business_name or "Unnamed Business",
            industry=req.industry,
            years_in_business=req.years_in_business,
            product_type=pt,
            loan_purpose=purp,
            requested_amount=req.amount,
            requested_term_months=req.term_months,
            financials=[fin],
            collateral=coll,
        )
    else:
        fin = ConsumerFinancialData(
            annual_income=req.annual_income,
            total_monthly_debt=req.monthly_debt,
            credit_score=req.credit_score,
            employment_years=req.employment_years,
            bankruptcies_last_7_years=req.bankruptcies,
            foreclosures_last_7_years=req.foreclosures,
        )
        app = ConsumerLoanApplication(
            product_type=pt,
            loan_purpose=purp,
            requested_amount=req.amount,
            requested_term_months=req.term_months,
            financial_data=fin,
        )

    pipeline = LendingPipeline()
    result = pipeline.run(app)
    return {"result": result.model_dump(mode="json"), "application_id": app.application_id}


@app.get("/lending/pipeline/result/{application_id}")
def get_lending_result(
    application_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    import json

    audit_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "..",
        "audit_logs",
        "lending",
    )
    for fname in os.listdir(audit_path):
        if application_id in fname:
            with open(os_mod.path.join(audit_path, fname)) as f:
                return json.load(f)
    raise HTTPException(status_code=404, detail=f"Lending result not found: {application_id}")


@app.get("/lending/products")
def list_lending_products(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, list[str]]:
    from insureflow.lending.models import LoanProductType

    return {"products": [p.value for p in LoanProductType]}
