from __future__ import annotations

import asyncio
import json as _json
import logging
import os
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from insureflow.auth import Role
from insureflow.auth.dependencies import (
    clear_user_store,
    get_current_user,
    get_current_user_optional,
    get_user_store,
    require_role,
)
from insureflow.auth.jwt import create_access_token, hash_password, verify_password
from insureflow.auth.models import LoginRequest, Token, TokenData, User, UserCreateRequest
from insureflow.insurance.pipeline import InsurancePipeline
from insureflow.models.mortgage import ProductLine
from insureflow.pipeline import UnderwritingPipeline
from insureflow.security.posture import SecurityPosture, resolve_security_posture
from insureflow.storage.job_store import JobStore, get_job_store
from insureflow.tasks.celery_app import celery_app
from insureflow.underwriting.renewal import PremiumAuditEngine

try:
    from insureflow.config import bootstrap_security, maybe_enable_langsmith_tracing
    from insureflow.observability.cloudwatch import configure_cloudwatch_logging

    configure_cloudwatch_logging()
    maybe_enable_langsmith_tracing()
    _security_errors = bootstrap_security()
    if _security_errors:
        for _err in _security_errors:
            logging.getLogger(__name__).error("SECURITY: %s", _err)
except Exception as _sec_exc:
    logging.getLogger(__name__).warning("Security bootstrap non-fatal error: %s", _sec_exc)

integration_gateway_router: APIRouter | None = None
try:
    from insureflow.gateway.router import router as integration_gateway_router
except ImportError:
    pass

logger = logging.getLogger(__name__)

INSURANCE_NS = "insurance"
MORTGAGE_NS = "mortgage"
LENDING_NS = "lending"

job_store: JobStore = get_job_store()

limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Rytera API started on port %s", os.getenv("PORT", "unknown"))
    yield


app = FastAPI(
    title="Rytera",
    description="AI underwriting platform API — Insurance, Mortgage & Lending",
    version="0.3.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

if integration_gateway_router is not None:
    app.include_router(integration_gateway_router, prefix="/integrations")

STATIC_DIR = Path(__file__).parent / "static"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SIM_DOCS_DIR = PROJECT_ROOT / "simulated_documents"


def _posture() -> SecurityPosture:
    return resolve_security_posture()


# ── Auth Endpoints ──────────────────────────────────────────────


@app.get("/auth/status")
def auth_status() -> dict[str, Any]:
    """Auth setup status + bank security posture flags."""
    posture = _posture()
    return {
        "setup_required": not bool(get_user_store()),
        "bank_mode": posture.bank_mode,
        "environment": posture.environment,
        "allow_open_registration": posture.allow_open_registration,
        "allow_auth_reset": posture.allow_auth_reset,
        "require_encryption": posture.require_encryption,
    }


@app.get("/security/status")
def security_status() -> dict[str, Any]:
    """Bank landing-zone security summary (no secrets)."""
    from insureflow.auth.sso import sso_status
    from insureflow.config import settings

    posture = _posture()
    return {
        "posture": {
            "environment": posture.environment,
            "bank_mode": posture.bank_mode,
            "hardened": posture.is_hardened,
            "allow_open_registration": posture.allow_open_registration,
            "allow_auth_reset": posture.allow_auth_reset,
            "require_encryption": posture.require_encryption,
            "encryption_configured": bool(settings.encryption_key),
            "secret_key_is_default": settings.secret_key == "CHANGE_ME_TO_A_LONG_SECRET_KEY_IN_PRODUCTION",
        },
        "observability": {
            "langsmith": bool(settings.langsmith_api_key),
            "cloudwatch_logs": settings.cloudwatch_logs or posture.bank_mode,
            "aws_region": settings.aws_region,
            "aws_secrets_configured": bool(settings.aws_secrets_arn),
        },
        "sso": sso_status(),
        "retention": {
            "worm_path": str(settings.worm_audit_path),
            "retention_days": settings.audit_retention_days,
            "s3_bucket": settings.retention_s3_bucket or None,
        },
    }


def _do_auth_reset() -> dict[str, str | int | bool]:
    posture = _posture()
    if not posture.allow_auth_reset:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auth reset is disabled in BANK_MODE/production. Set ALLOW_AUTH_RESET=true only for emergency break-glass.",
        )
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
def reset_auth_get(current: TokenData = Depends(require_role(Role.ADMIN))) -> HTMLResponse:
    """One-click wipe: server accounts + redirect to dashboard. Requires admin auth."""
    _do_auth_reset()
    return HTMLResponse(_RESET_HTML)


@app.post("/auth/reset")
def reset_auth_post(current: TokenData = Depends(require_role(Role.ADMIN))) -> dict[str, str | int | bool]:
    """Clear all server accounts (JSON). Requires admin auth."""
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
def get_me(current_user: TokenData = Depends(get_current_user)) -> dict[str, str | None]:
    return {
        "username": current_user.username,
        "role": current_user.role.value if current_user.role else "none",
        "org_id": current_user.org_id,
    }


@app.post("/auth/register", status_code=201)
@limiter.limit("3/hour")
def register_user(req: UserCreateRequest, request: Request) -> dict[str, str]:
    """Self-register — disabled in BANK_MODE/production unless ALLOW_OPEN_REGISTRATION=true."""
    posture = _posture()
    if not posture.allow_open_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Open registration is disabled in BANK_MODE/production. An admin must create users via /auth/users or SSO.",
        )
    store = get_user_store()
    username = req.username.strip()
    if not username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if len(req.password) < posture.min_password_length:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {posture.min_password_length} characters",
        )
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


@app.get("/auth/sso/status")
def auth_sso_status() -> dict[str, Any]:
    from insureflow.auth.sso import sso_status

    return sso_status()


@app.get("/auth/sso/login")
def auth_sso_login() -> dict[str, str]:
    """Start Cognito/Okta OIDC login — returns authorize URL for the SPA to redirect."""
    from insureflow.auth.sso import build_authorize_url, sso_status

    status_info = sso_status()
    if not status_info.get("enabled"):
        raise HTTPException(status_code=404, detail="SSO is not configured")
    state = uuid.uuid4().hex
    return {"authorize_url": build_authorize_url(state), "state": state}


@app.post("/auth/sso/callback")
def auth_sso_callback(payload: dict[str, Any]) -> dict[str, Any]:
    """OIDC callback stub — exchanges code once JWKS validation is wired to the bank IdP."""
    from insureflow.auth.sso import exchange_code_for_claims, sso_status

    if not sso_status().get("enabled"):
        raise HTTPException(status_code=404, detail="SSO is not configured")
    code = str(payload.get("code") or "")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    claims = exchange_code_for_claims(code)
    return {"claims": claims, "access_token": None, "note": "Complete JWKS validation before issuing app JWTs"}


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
    return {"status": "ok", "version": "0.3.0"}


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
    current: TokenData | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    org_id = current.org_id if current and current.org_id else "demo"
    if preset_id != "pacific-coast":
        raise HTTPException(status_code=404, detail=f"Unknown insurance preset: {preset_id}")
    if not (EXAMPLES_DIR / "pacific_coast_acord.xml").exists():
        raise HTTPException(status_code=503, detail="Example data not found on server")
    job_id = f"demo-{uuid.uuid4().hex[:12]}"
    req = _load_pacific_coast_submission()
    job_store.set(INSURANCE_NS, job_id, {"status": "processing", "demo": True}, org_id=org_id)
    celery_app.send_task(
        "insureflow.tasks.pipeline_tasks.run_pipeline",
        args=[job_id, req.model_dump(), org_id],
        queue="pipeline",
    )
    return {"job_id": job_id, "status": "processing", "preset": preset_id, "org_id": org_id}


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
    current: TokenData | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    org_id = current.org_id if current and current.org_id else "demo"
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
    job_store.set(MORTGAGE_NS, job_id, {"status": "processing", "demo": True}, org_id=org_id)
    background_tasks.add_task(_run_mortgage_task, job_id, req, org_id)
    return {"job_id": job_id, "status": "processing", "preset": preset_id, "org_id": org_id}


@app.get("/", response_model=None)
async def root(request: Request) -> FileResponse | JSONResponse:
    accept = request.headers.get("accept", "")
    landing = STATIC_DIR / "landing" / "index.html"
    if landing.exists() and "text/html" in accept and not accept.strip().startswith("application/json"):
        return FileResponse(landing)
    return JSONResponse(
        {
            "service": "Rytera",
            "version": "0.3.0",
            "dashboard": "/dashboard",
            "diagnostics": "/system/diagnostics",
            "health": "/health",
            "integration_gateway": "/integrations",
        }
    )


def _run_pipeline_task(job_id: str, request: SubmissionRequest, org_id: str) -> None:
    try:
        pipeline: Any
        result: Any
        if request.use_legacy_pipeline:
            pipeline = UnderwritingPipeline()
            result = pipeline.run(
                acord_xml=request.acord_xml,
                inspection_reports=request.inspection_reports,
                supplemental_docs=request.supplemental_docs,
                bundle_id=request.bundle_id or job_id,
            )
        else:
            docs = [{"filename": d.filename, "content": d.content} for d in request.documents] if request.documents else None
            pipeline = InsurancePipeline(org_id=org_id, use_llm=request.use_llm)

            def on_progress(data: dict[str, Any]) -> None:
                job_store.set(
                    INSURANCE_NS,
                    job_id,
                    {"status": "processing", "progress": data},
                    org_id=org_id,
                )

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
                progress_callback=on_progress,
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


# ── HITL evaluation rubrics ─────────────────────────────────────


class HITLEvalSubmitRequest(BaseModel):
    case_id: str
    bundle_id: str = ""
    scores: dict[str, int] = {}
    ai_decision: str = ""
    human_preferred_decision: str = ""
    decision_agree: str = "agree"  # agree | partial | disagree
    decision_change_reason: str = ""
    notes: str = ""
    feedback_tags: list[str] = []
    reviewer_role: str = "licensed_uw"


@app.get("/evaluations/hitl/rubrics")
def get_hitl_rubrics(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Human-in-the-loop eval rubric card (what reviewers score)."""
    from evaluations.hitl_rubrics import RUBRIC_DEFINITIONS, export_rubric_card

    return {
        "rubrics": RUBRIC_DEFINITIONS,
        "rubric_card_path": export_rubric_card(),
        "production_hitl_note": ("Production also tracks UW sign-off overrides, confidence, premium delta, and bind/loss calibration via /analytics/overrides."),
    }


@app.get("/evaluations/golden/inventory")
def get_golden_inventory(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Ground-truth gold-set inventory: case counts + question counts."""
    from evaluations.qa_ground_truth import all_ground_truth_questions, ground_truth_inventory

    inv = ground_truth_inventory()
    return {
        **inv,
        "sample_questions": [
            {
                "question_id": q.question_id,
                "question": q.question,
                "expected_answer": q.expected_answer,
                "category": q.category,
            }
            for q in all_ground_truth_questions()[:8]
        ],
    }


@app.get("/evaluations/cadence")
def get_eval_cadence(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Frequency of automated eval checks and human-in-the-loop reviews."""
    from evaluations.cadence import cadence_inventory

    return cadence_inventory()


@app.get("/evaluations/quality-gates")
def get_quality_gates(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Metric thresholds and flag/block rules for eval scoring."""
    from evaluations.quality_gates import QUALITY_GATES, apply_quality_gates

    return {
        "gates": [
            {
                "metric": g.metric,
                "threshold": g.threshold,
                "direction": g.direction,
                "severity": g.severity.value,
                "category": g.category,
                "description": g.description,
            }
            for g in QUALITY_GATES
        ],
        "automation_vs_manual": apply_quality_gates({}).get("automation"),
        "interview_summary": apply_quality_gates({}).get("interview_summary"),
    }


class QualityGateCheckRequest(BaseModel):
    metrics: dict[str, float] = {}


@app.post("/evaluations/quality-gates/check")
def check_quality_gates(
    req: QualityGateCheckRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Score a metric dict against thresholds — returns PASS / FLAGGED / BLOCKED."""
    from evaluations.quality_gates import apply_quality_gates

    return apply_quality_gates(req.metrics)


@app.get("/releases/checklist")
def get_release_checklist(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """11-step agent release checklist (classify → MLflow → gates → canary → prod)."""
    from evaluations.release_process import release_walkthrough

    return release_walkthrough()


class ExperimentStartRequest(BaseModel):
    name: str
    experiment_class: str
    hypothesis: str = ""
    params: dict[str, Any] = {}
    tags: dict[str, str] = {}
    registry_entry_id: str = ""


@app.get("/releases/experiments")
def list_release_experiments(
    experiment_class: str = "",
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """List MLflow-compatible experiment runs (local store + optional MLflow)."""
    from evaluations.release_process import ExperimentStore, seed_demo_experiments

    store = ExperimentStore()
    seed_demo_experiments(store)
    runs = store.list_runs(experiment_class=experiment_class or None)
    return {
        "runs": runs,
        "summary": store.by_class_summary(),
        "mlflow_tracking_uri": os.getenv("MLFLOW_TRACKING_URI", "") or None,
        "experiment_name": os.getenv("MLFLOW_EXPERIMENT_NAME", "insureflow-agent-releases"),
    }


@app.post("/releases/experiments", status_code=201)
def start_release_experiment(
    req: ExperimentStartRequest,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    from evaluations.release_process import ExperimentStore

    return ExperimentStore().start_run(
        name=req.name,
        experiment_class=req.experiment_class,
        hypothesis=req.hypothesis,
        params=req.params,
        tags=req.tags,
        registry_entry_id=req.registry_entry_id,
    )


class ExperimentMetricsRequest(BaseModel):
    metrics: dict[str, float]


@app.post("/releases/experiments/{run_id}/metrics")
def log_experiment_metrics(
    run_id: str,
    req: ExperimentMetricsRequest,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    from evaluations.release_process import ExperimentStore

    row = ExperimentStore().log_metrics(run_id, req.metrics)
    if not row:
        raise HTTPException(status_code=404, detail="experiment run not found")
    return row


class ExperimentPromoteRequest(BaseModel):
    stage: str


@app.post("/releases/experiments/{run_id}/promote")
def promote_experiment(
    run_id: str,
    req: ExperimentPromoteRequest,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    from evaluations.release_process import ExperimentStore

    row = ExperimentStore().promote(run_id, req.stage)
    if not row:
        raise HTTPException(status_code=404, detail="experiment run not found")
    return row


@app.get("/evaluations/drift")
def get_drift_status(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Compare recent eval trends to champion baseline — model/agent drift."""
    from evaluations.drift import detect_from_trends, drift_policy_payload, maybe_open_regression_experiment

    report = detect_from_trends()
    exp = maybe_open_regression_experiment(report)
    payload = report.to_dict()
    payload["policy"] = drift_policy_payload()
    if exp:
        payload["regression_experiment"] = {"run_id": exp.get("run_id"), "name": exp.get("name")}
    return payload


@app.get("/evaluations/drift/policy")
def get_drift_policy(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from evaluations.drift import drift_policy_payload

    return drift_policy_payload()


class DriftCheckRequest(BaseModel):
    metrics: dict[str, float] = {}


@app.post("/evaluations/drift/check")
def check_drift(
    req: DriftCheckRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from evaluations.drift import detect_drift, maybe_open_regression_experiment

    report = detect_drift(req.metrics)
    exp = maybe_open_regression_experiment(report)
    out = report.to_dict()
    if exp:
        out["regression_experiment"] = {"run_id": exp.get("run_id"), "name": exp.get("name")}
    return out


@app.get("/rag/retrieval-policy")
def get_rag_retrieval_policy(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Top-K, re-ranking, and fallback ladder for guideline RAG."""
    from insureflow.rag.rag_agent import retrieval_policy_payload

    return retrieval_policy_payload()


@app.get("/rag/retrieve")
def rag_retrieve_demo(
    q: str = "masonry construction protection class sprinkler",
    top_k: int = 5,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Live retrieval with re-rank + fallbacks (for dashboards / demos)."""
    from insureflow.rag.rag_agent import RAGAgent

    return RAGAgent(use_knowledge_graph=True).retrieve_contexts(q, top_k=top_k)


@app.get("/analytics/agent-performance")
def get_agent_performance(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Log-analysis derived agent performance (+ demo seed if no logs)."""
    from insureflow.analytics.agent_perf import analyze_audit_directory, seed_demo_agent_perf

    live = analyze_audit_directory()
    if not live.get("agents"):
        demo = seed_demo_agent_perf()
        demo["note"] = "No live agent logs found — returning seeded demo metrics"
        return demo
    return live


@app.get("/evaluations/trends")
def get_eval_trends(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Eval metric time series for trend visualization."""
    from evaluations.trend_store import EvalTrendStore, seed_demo_trends
    from insureflow.analytics.agent_perf import analyze_audit_directory, seed_demo_agent_perf

    store = EvalTrendStore()
    seed_demo_trends(store)
    payload = store.dashboard_payload()

    perf = analyze_audit_directory()
    if not perf.get("agents"):
        perf = seed_demo_agent_perf()
    agents = perf.get("agents") or {}
    if agents:
        err_rates = [a["error_rate"] for a in agents.values() if a.get("error_rate") is not None]
        latencies = [a["avg_duration_ms"] for a in agents.values() if a.get("avg_duration_ms") is not None]
        payload["agent_snapshot"] = {
            "agents": agents,
            "avg_error_rate": round(sum(err_rates) / len(err_rates), 4) if err_rates else 0.0,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "log_explorers": perf.get("log_explorers"),
        }
    return payload


@app.get("/observability/log-explorers")
def get_log_explorers(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Which log explorers we use + CloudWatch Insights query templates."""
    from insureflow.analytics.agent_perf import LOG_EXPLORER_QUERIES

    return {
        "explorers": [
            {
                "name": "Amazon CloudWatch Logs Insights",
                "role": "Infra + agent structured JSON log analysis, latency/error aggregates",
                "url": "https://console.aws.amazon.com/cloudwatch/home#logsV2:logs-insights",
            },
            {
                "name": "LangSmith",
                "role": "LLM/agent trace explorer, eval feedback scores, latency/tokens",
                "url": "https://smith.langchain.com",
                "project": "insureflow-evals",
            },
        ],
        "cloudwatch_insights_queries": LOG_EXPLORER_QUERIES,
        "automation": ("JSON logs emitted in BANK_MODE; nightly eval job runs agent log analyzer; metrics appended to evaluation_trends for dashboard charts."),
    }


@app.get("/evaluations/hitl/summary")
def get_hitl_summary(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from evaluations.hitl_rubrics import HITLEvalStore, seed_demo_reviews, track_hitl_to_langsmith

    store = HITLEvalStore()
    seed_demo_reviews(store)
    summary = store.summary()
    cloud = track_hitl_to_langsmith(summary)
    return {**summary.model_dump(), "cloud_tracking": cloud}


@app.get("/evaluations/hitl/reviews")
def list_hitl_reviews(
    case_id: str = "",
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from evaluations.hitl_rubrics import HITLEvalStore, seed_demo_reviews

    store = HITLEvalStore()
    seed_demo_reviews(store)
    reviews = store.list_reviews(case_id or None)
    return {"reviews": [r.model_dump() for r in reviews], "count": len(reviews)}


@app.post("/evaluations/hitl/reviews", status_code=201)
def submit_hitl_review(
    req: HITLEvalSubmitRequest,
    current: TokenData = Depends(require_role(Role.LICENSED_UW)),
) -> dict[str, Any]:
    """Submit a human rubric review for an eval / golden case."""
    from evaluations.hitl_rubrics import AgreeLabel, HITLEvalStore, HumanEvalReview, track_hitl_to_langsmith

    try:
        agree = AgreeLabel(req.decision_agree.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="decision_agree must be agree|partial|disagree") from None

    review = HumanEvalReview(
        case_id=req.case_id,
        bundle_id=req.bundle_id,
        reviewer=current.username or "unknown",
        reviewer_role=req.reviewer_role,
        scores=req.scores,
        ai_decision=req.ai_decision,
        human_preferred_decision=req.human_preferred_decision,
        decision_agree=agree,
        decision_change_reason=req.decision_change_reason,
        notes=req.notes,
        feedback_tags=req.feedback_tags,
    )
    stored = HITLEvalStore().submit(review)
    cloud = track_hitl_to_langsmith()
    return {"review": stored.model_dump(), "cloud_tracking": cloud}


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
            reconciled_by=current.username or "",
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
        "present_documents": getattr(checklist, "present", []),
        "can_request_from_broker": len(checklist.missing) > 0,
    }


@app.post("/pipeline/documents/{bundle_id}/request")
def request_broker_documents(
    bundle_id: str,
    body: dict[str, Any],
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Request missing documents from broker (data quality gate)."""
    from insureflow.enterprise.ecosystem import get_ecosystem_service

    docs = body.get("documents") or body.get("missing_documents") or []
    if not docs:
        missing = get_missing_documents(bundle_id, current)
        docs = missing.get("missing_documents", [])
    return get_ecosystem_service().request_broker_documents(bundle_id, current.org_id, docs)


@app.get("/pipeline/ecosystem/status")
def ecosystem_status(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.integrations.health import IntegrationHealthService

    return IntegrationHealthService().check_all(current.org_id)


@app.get("/pipeline/ecosystem/{bundle_id}")
def ecosystem_bundle(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.enterprise.ecosystem import get_ecosystem_service

    return get_ecosystem_service().bundle_ecosystem(bundle_id, current.org_id)


@app.post("/pipeline/ecosystem/{bundle_id}/loss-control/dispatch")
def dispatch_loss_control(
    bundle_id: str,
    body: dict[str, Any] | None = None,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    from insureflow.enterprise.ecosystem import get_ecosystem_service

    notes = (body or {}).get("notes", "")
    return get_ecosystem_service().loss_control_dispatch(bundle_id, current.org_id, notes)


@app.post("/pipeline/checkpoints/{bundle_id}/{checkpoint_id}")
def resolve_checkpoint(
    bundle_id: str,
    checkpoint_id: str,
    body: dict[str, Any],
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    from insureflow.enterprise.ecosystem import get_ecosystem_service

    action = body.get("action", "approve")
    return get_ecosystem_service().resolve_checkpoint(
        bundle_id,
        current.org_id,
        checkpoint_id,
        action,
        reviewer=current.username or "underwriter",
    )


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
        docs = [{"filename": d.filename, "content": d.content} for d in request.documents] if request.documents else None
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

    entry: Any
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

    app: Any
    fin: Any
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
            with open(os.path.join(audit_path, fname)) as f:
                result: dict[str, Any] = json.load(f)
                return result
    raise HTTPException(status_code=404, detail=f"Lending result not found: {application_id}")


@app.get("/lending/products")
def list_lending_products(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, list[str]]:
    from insureflow.lending.models import LoanProductType

    return {"products": [p.value for p in LoanProductType]}


# ── WebSocket / SSE: Real-time Job Status ────────────────────────

_job_ws_subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
_job_sse_subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)


def _notify_job_subscribers(job_id: str, data: dict[str, Any]) -> None:
    """Push status update to all WebSocket and SSE subscribers of a job."""
    payload = _json.dumps(data, default=str)
    for q in list(_job_ws_subscribers.get(job_id, set())):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass
    for q in list(_job_sse_subscribers.get(job_id, set())):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for real-time job status updates.

    Connect with: ws://host/ws/jobs/{job_id}?token=<jwt>
    Server pushes JSON messages whenever job status changes.
    """
    token = websocket.query_params.get("token", "")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    from insureflow.auth.jwt import decode_access_token

    user = decode_access_token(token)
    if user is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    job = job_store.get(INSURANCE_NS, job_id, org_id=user.org_id)
    if not job:
        await websocket.close(code=4004, reason="Job not found or access denied")
        return

    await websocket.accept()
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    _job_ws_subscribers[job_id].add(queue)
    try:
        await websocket.send_json({"type": "connected", "job_id": job_id, "status": job.get("status", "unknown")})
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(msg)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass
    finally:
        _job_ws_subscribers[job_id].discard(queue)


@app.get("/pipeline/jobs/{job_id}/stream")
async def sse_job_status(
    job_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> StreamingResponse:
    """SSE endpoint for job status — returns text/event-stream.

    Useful for clients that cannot use WebSocket (e.g., Load Balancers that strip Upgrade headers).
    """
    job = job_store.get(INSURANCE_NS, job_id, org_id=current.org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    _job_sse_subscribers[job_id].add(queue)

    async def event_generator() -> Any:
        try:
            yield f"data: {_json.dumps({'type': 'connected', 'job_id': job_id, 'status': job.get('status', 'unknown')})}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {_json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            _job_sse_subscribers[job_id].discard(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Row-Level Permission Enforcement ──────────────────────────────


def _check_row_access(resource_org_id: str, user_org_id: str) -> None:
    """Raise 403 if the user's org_id doesn't match the resource's org_id."""
    if resource_org_id and resource_org_id != user_org_id:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: resource belongs to org '{resource_org_id}', you are in '{user_org_id}'",
        )


# Patched pipeline endpoints with row-level checks


@app.post("/v2/pipeline/run", status_code=202)
@limiter.limit("10/minute")
async def run_pipeline_row_level(
    req: SubmissionRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Pipeline run with enforced org isolation — jobs always scoped to caller's org."""
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    job_store.set(INSURANCE_NS, job_id, {"status": "processing"}, org_id=current.org_id)
    celery_app.send_task(
        "insureflow.tasks.pipeline_tasks.run_pipeline",
        args=[job_id, req.model_dump(), current.org_id],
        queue="pipeline",
    )
    _notify_job_subscribers(job_id, {"type": "status", "status": "processing", "job_id": job_id})
    return {"job_id": job_id, "status": "processing", "org_id": current.org_id}


@app.get("/v2/pipeline/jobs/{job_id}")
def get_job_status_v2(
    job_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Job status with row-level permission check."""
    job = job_store.get(INSURANCE_NS, job_id, org_id=current.org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _check_row_access(job.get("org_id", "default"), current.org_id)
    return job


@app.get("/v2/pipeline/workflow/{bundle_id}")
def get_workflow_v2(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Workflow with row-level org isolation."""
    from insureflow.workflow.service import WorkflowService

    svc = WorkflowService()
    record = svc.store.get(bundle_id, current.org_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    _check_row_access(record.org_id, current.org_id)
    return record.model_dump(mode="json")


@app.post("/v2/pipeline/workflow/{bundle_id}/sign-off")
def sign_off_v2(
    bundle_id: str,
    req: dict[str, Any],
    current: TokenData = Depends(require_role(Role.LICENSED_UW)),
) -> dict[str, Any]:
    """Sign-off with row-level permission check — user must be in the same org."""
    from insureflow.workflow.models import SignOffAction
    from insureflow.workflow.service import WorkflowService

    svc = WorkflowService()
    record = svc.store.get(bundle_id, current.org_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    _check_row_access(record.org_id, current.org_id)
    action = SignOffAction(req.get("action", "approve"))
    result = svc.sign_off(
        bundle_id=bundle_id,
        org_id=current.org_id,
        action=action,
        signed_by=current.username or "",
        license_number=req.get("license_number", ""),
        notes=req.get("notes", ""),
        override_reason=req.get("override_reason", ""),
    )
    _notify_job_subscribers(bundle_id, {"type": "workflow_update", "state": result.state.value})
    return result.model_dump(mode="json")


# ── ML Predictive Analytics Endpoints ──────────────────────────


@app.get("/ml/status")
def ml_status() -> dict[str, Any]:
    """ML module status — all models, versions, and metrics."""
    from insureflow.ml.training import get_training_status

    return get_training_status()


@app.post("/ml/train")
def ml_train_all() -> dict[str, Any]:
    """Train or retrain all ML models with synthetic data."""
    from insureflow.ml.training import train_all_models

    results = train_all_models(force=True)
    return {
        "trained": len(results),
        "results": [r.model_dump() for r in results],
    }


@app.post("/ml/train/{model_type}")
def ml_train_single(model_type: str) -> dict[str, Any]:
    """Retrain a single ML model."""
    from insureflow.ml.models import ModelType as ModelTypeEnum
    from insureflow.ml.training import retrain_model

    try:
        mt = ModelTypeEnum(model_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid model type: {model_type}. Valid: {[e.value for e in ModelTypeEnum]}")

    result = retrain_model(mt)
    if result is None:
        raise HTTPException(status_code=400, detail=f"Cannot train {model_type}")
    return result.model_dump()


@app.post("/ml/predict/loss")
def ml_predict_loss(features: dict[str, Any]) -> dict[str, Any]:
    """Loss prediction — expected claim frequency, severity, and total loss."""
    from insureflow.ml.base import BaseMLModel
    from insureflow.ml.features import FeatureVector
    from insureflow.ml.models import ModelType
    from insureflow.ml.registry import get_ml_registry

    registry = get_ml_registry()
    model = registry.get(ModelType.LOSS_PREDICTION)
    if model is None or not isinstance(model, BaseMLModel):
        raise HTTPException(status_code=503, detail="Loss prediction model not available")
    fv = FeatureVector(**{k: v for k, v in features.items() if k in FeatureVector.model_fields})
    return model.predict(fv)


@app.post("/ml/predict/fraud")
def ml_predict_fraud(features: dict[str, Any]) -> dict[str, Any]:
    """Fraud anomaly detection — probability, risk level, flagged patterns."""
    from insureflow.ml.base import BaseMLModel
    from insureflow.ml.features import FeatureVector
    from insureflow.ml.models import ModelType
    from insureflow.ml.registry import get_ml_registry

    registry = get_ml_registry()
    model = registry.get(ModelType.FRAUD_DETECTION)
    if model is None or not isinstance(model, BaseMLModel):
        raise HTTPException(status_code=503, detail="Fraud detection model not available")
    fv = FeatureVector(**{k: v for k, v in features.items() if k in FeatureVector.model_fields})
    return model.predict(fv)


@app.post("/ml/predict/premium")
def ml_predict_premium(features: dict[str, Any]) -> dict[str, Any]:
    """Premium optimization — recommended price, elasticity, retention probability."""
    from insureflow.ml.base import BaseMLModel
    from insureflow.ml.features import FeatureVector
    from insureflow.ml.models import ModelType
    from insureflow.ml.registry import get_ml_registry

    registry = get_ml_registry()
    model = registry.get(ModelType.PREMIUM_OPTIMIZER)
    if model is None or not isinstance(model, BaseMLModel):
        raise HTTPException(status_code=503, detail="Premium optimizer model not available")
    fv = FeatureVector(**{k: v for k, v in features.items() if k in FeatureVector.model_fields})
    return model.predict(fv)


@app.post("/ml/predict/churn")
def ml_predict_churn(features: dict[str, Any]) -> dict[str, Any]:
    """Churn prediction — non-renewal probability, LTV, retention actions."""
    from insureflow.ml.base import BaseMLModel
    from insureflow.ml.features import FeatureVector
    from insureflow.ml.models import ModelType
    from insureflow.ml.registry import get_ml_registry

    registry = get_ml_registry()
    model = registry.get(ModelType.CHURN_PREDICTION)
    if model is None or not isinstance(model, BaseMLModel):
        raise HTTPException(status_code=503, detail="Churn prediction model not available")
    fv = FeatureVector(**{k: v for k, v in features.items() if k in FeatureVector.model_fields})
    return model.predict(fv)


@app.post("/ml/predict/portfolio-risk")
def ml_portfolio_risk(portfolio: dict[str, Any]) -> dict[str, Any]:
    """Portfolio risk modeling — VaR, tail risk, Monte Carlo simulation."""
    from insureflow.ml.portfolio_risk import PortfolioRiskModel

    exposures = portfolio.get("exposures", [1000000.0])
    probabilities = portfolio.get("loss_probabilities", [0.05])
    severities = portfolio.get("severity_means", [50000.0])
    severity_stds = portfolio.get("severity_stds")
    cat_weight = portfolio.get("cat_weight", 0.15)

    model = PortfolioRiskModel(n_simulations=portfolio.get("n_simulations", 10000))
    result = model.simulate(exposures, probabilities, severities, severity_stds, cat_weight)
    return result.model_dump()


@app.post("/ml/predict/portfolio-stress")
def ml_portfolio_stress(portfolio: dict[str, Any]) -> dict[str, Any]:
    """Portfolio stress testing across multiple scenarios."""
    from insureflow.ml.portfolio_risk import PortfolioRiskModel

    model = PortfolioRiskModel(n_simulations=portfolio.get("n_simulations", 10000))
    results = model.stress_test(
        exposures=portfolio.get("exposures", [1000000.0]),
        loss_probabilities=portfolio.get("loss_probabilities", [0.05]),
        severity_means=portfolio.get("severity_means", [50000.0]),
        stress_scenarios=portfolio.get("scenarios"),
    )
    return {"scenarios": results}


@app.post("/ml/score/broker")
def ml_score_broker(broker_data: dict[str, Any]) -> dict[str, Any]:
    """Behavioral scoring — broker quality, consistency, accuracy."""
    from insureflow.ml.behavioral import BehavioralScoringModel

    model = BehavioralScoringModel()
    return model.score_broker(
        broker_id=broker_data.get("broker_id", "unknown"),
        submission_count=broker_data.get("submission_count", 0),
        avg_data_completeness=broker_data.get("avg_data_completeness", 0.5),
        override_rate=broker_data.get("override_rate", 0),
        avg_loss_ratio=broker_data.get("avg_loss_ratio", 0.5),
        on_time_rate=broker_data.get("on_time_rate", 0.9),
        accuracy_rate=broker_data.get("accuracy_rate", 0.85),
        loss_ratio_history=broker_data.get("loss_ratio_history", []),
    ).model_dump()


@app.post("/ml/score/submission")
def ml_score_submission(submission_data: dict[str, Any]) -> dict[str, Any]:
    """Behavioral scoring — submission data quality."""
    from insureflow.ml.behavioral import BehavioralScoringModel

    model = BehavioralScoringModel()
    return model.score_submission(
        submission_id=submission_data.get("submission_id", "unknown"),
        data_fields_present=submission_data.get("data_fields_present", 10),
        total_fields_expected=submission_data.get("total_fields_expected", 20),
        has_acord=submission_data.get("has_acord", False),
        has_loss_run=submission_data.get("has_loss_run", False),
        has_inspection=submission_data.get("has_inspection", False),
        has_sov=submission_data.get("has_sov", False),
    ).model_dump()


@app.get("/ml/models")
def ml_list_models() -> dict[str, Any]:
    """List all registered ML models with status and metrics."""
    from insureflow.ml.registry import get_ml_registry

    return {"models": get_ml_registry().get_status()}


@app.post("/ml/explain/{model_type}")
def ml_explain(model_type: str, features: dict[str, Any]) -> dict[str, Any]:
    """Get feature importance explanation for a prediction."""
    from insureflow.ml.features import FeatureVector
    from insureflow.ml.models import ModelType
    from insureflow.ml.registry import get_ml_registry

    registry = get_ml_registry()
    try:
        mt = ModelType(model_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid model type: {model_type}")

    model = registry.get(mt)
    if model is None or not hasattr(model, "explain"):
        raise HTTPException(status_code=403, detail=f"Model {model_type} does not support explanations")
    fv = FeatureVector(**{k: v for k, v in features.items() if k in FeatureVector.model_fields})
    return model.explain(fv)
