from __future__ import annotations

import asyncio
import json as _json
import logging
import os
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Optional

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
    require_staff_desk,
)
from insureflow.auth.jwt import create_access_token, hash_password, verify_password
from insureflow.auth.models import LoginRequest, Token, TokenData, User, UserCreateRequest
from insureflow.insurance.pipeline import InsurancePipeline
from insureflow.models.mortgage import ProductLine
from insureflow.pipeline import UnderwritingPipeline
from insureflow.security.posture import SecurityPosture, resolve_security_posture
from insureflow.storage.job_store import JobStore, get_job_store
from insureflow.underwriting.renewal import PremiumAuditEngine

try:
    from insureflow.config import bootstrap_security, maybe_enable_langsmith_tracing
    from insureflow.observability.cloudwatch import configure_cloudwatch_logging
    from insureflow.security.posture import resolve_security_posture as _resolve_boot_posture

    configure_cloudwatch_logging()
    maybe_enable_langsmith_tracing()
    _security_errors = bootstrap_security()
    if _security_errors:
        _boot_posture = _resolve_boot_posture()
        for _err in _security_errors:
            logging.getLogger(__name__).error("SECURITY: %s", _err)
        if _boot_posture.is_hardened:
            raise SystemExit("Refusing to start in BANK_MODE/production with security posture errors:\n- " + "\n- ".join(_security_errors))
except SystemExit:
    raise
except Exception as _sec_exc:
    from insureflow.security.posture import resolve_security_posture as _resolve_boot_posture

    logging.getLogger(__name__).error("Security bootstrap failed: %s", _sec_exc)
    if _resolve_boot_posture().is_hardened:
        raise SystemExit(f"Refusing to start: security bootstrap failed: {_sec_exc}") from _sec_exc
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
async def lifespan(_app: FastAPI) -> Any:
    logger.info("Rytera API started on port %s", os.getenv("PORT", "unknown"))
    yield


app = FastAPI(
    title="Rytera",
    description="AI underwriting platform API — Insurance, Mortgage & Lending",
    version="0.3.1",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

if integration_gateway_router is not None:
    app.include_router(integration_gateway_router, prefix="/integrations")

# api/main.py → package dir → insureflow/ → src/ → repo root
_PKG_ROOT = Path(__file__).resolve().parent.parent  # src/insureflow
STATIC_DIR = _PKG_ROOT / "static"
PROJECT_ROOT = _PKG_ROOT.parent.parent  # repo root
EXAMPLES_DIR = PROJECT_ROOT / "examples" / "insurance"
SIM_DOCS_DIR = PROJECT_ROOT / "simulated_documents"


# Demo packages for the "Connect & pull" source hub, per vertical. Mortgage and
# lending reuse the same enterprise connectors as insurance but pull from their
# own fixture directories instead of insurance example packages.
_VERTICAL_PACKAGES: dict[str, dict[str, dict[str, Any]]] = {
    "mortgage": {
        "johnson-residential": {
            "name": "Johnson Family (Residential)",
            "description": "Full residential loan package — income, credit, property, UW docs",
            "path": SIM_DOCS_DIR / "home_mortgage" / "johnson_marcus_imani",
        },
        "chen-residential": {
            "name": "Chen Family (Residential)",
            "description": "Residential package — income, assets, credit, property, UW docs",
            "path": SIM_DOCS_DIR / "home_mortgage" / "chen_david_karen",
        },
        "patel-residential": {
            "name": "Patel Home Loan (Residential)",
            "description": "Residential package — income, assets, credit, property, UW docs",
            "path": SIM_DOCS_DIR / "home_mortgage" / "patel_lisa",
        },
        "thompson-residential": {
            "name": "Thompson Family (Residential)",
            "description": "Residential package — underwriting file",
            "path": SIM_DOCS_DIR / "home_mortgage" / "thompson_john_sarah",
        },
        "wilson-residential": {
            "name": "Wilson Home Loan (Residential)",
            "description": "Residential package — income, credit, property, UW docs",
            "path": SIM_DOCS_DIR / "home_mortgage" / "wilson_james",
        },
        "rodriguez-residential": {
            "name": "Rodriguez Family (Residential)",
            "description": "Residential package — income, assets, credit, property, UW docs",
            "path": SIM_DOCS_DIR / "home_mortgage" / "rodriguez_maria",
        },
        "midwest-commercial": {
            "name": "Midwest Medical Plaza (Commercial)",
            "description": "Commercial CRE package — entity financials, leases, due diligence",
            "path": SIM_DOCS_DIR / "commercial_mortgage" / "midwest_medical_plaza",
        },
        "oak-street-commercial": {
            "name": "Oak Street Retail (Commercial)",
            "description": "Commercial CRE package — entity financials, debt, property performance",
            "path": SIM_DOCS_DIR / "commercial_mortgage" / "oak_street_retail",
        },
        "riverbend-commercial": {
            "name": "Riverbend Self Storage (Commercial)",
            "description": "Commercial CRE package — entity financials, due diligence",
            "path": SIM_DOCS_DIR / "commercial_mortgage" / "riverbend_self_storage",
        },
    },
    "lending": {
        "blue-harbor-bakery": {
            "name": "Blue Harbor Bakery LLC (SBA 7A)",
            "description": "Food manufacturer — application, P&L, balance sheet, bank, credit, tax",
            "path": SIM_DOCS_DIR / "lending" / "blue_harbor_bakery",
        },
        "keller-logistics": {
            "name": "Keller Logistics Group (Term Loan)",
            "description": "Trucking — application, P&L, balance sheet, bank, credit, tax",
            "path": SIM_DOCS_DIR / "lending" / "keller_logistics",
        },
    },
}


def _vertical_package_list(vertical: str) -> list[dict[str, object]]:
    return [
        {
            "id": pid,
            "name": meta["name"],
            "type": "library",
            "category": "Demo Packages",
            "description": meta["description"],
            "status": "ready",
            "file_count": 6,
        }
        for pid, meta in _VERTICAL_PACKAGES.get(vertical, {}).items()
    ]


def _load_vertical_package(vertical: str, package_id: str) -> list[dict[str, str]]:
    from insureflow.ingestion.insurance.sources import load_directory

    meta = _VERTICAL_PACKAGES.get(vertical, {}).get(package_id)
    if not meta:
        raise FileNotFoundError(f"Unknown {vertical} package: {package_id}")
    directory = meta["path"]
    if not directory.is_dir():
        raise FileNotFoundError(f"Fixture directory missing: {directory}")
    return load_directory(directory)


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
        "hardened": posture.is_hardened,
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
    # Admins can only create users in their own org
    org_id = current.org_id
    if new_user.role in (Role.ADMIN, Role.CUO) and new_user.role != current.role and current.role != Role.CUO:
        raise HTTPException(status_code=403, detail="Cannot create users with a higher role than your own")
    # Cap role: non-CUO admins cannot create CUO
    role = new_user.role
    if current.role != Role.CUO and role == Role.CUO:
        raise HTTPException(status_code=403, detail="Only CUO can create CUO users")
    store[new_user.username] = User(
        username=new_user.username,
        hashed_password=hash_password(new_user.password),
        role=role,
        full_name=new_user.full_name or new_user.username,
        org_id=org_id,
    )
    return {"message": f"User '{new_user.username}' created with role '{role.value}' in org '{org_id}'"}


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
    role = Role.VIEWER  # self-registration is always VIEWER; admin promotes later
    if username in store:
        raise HTTPException(status_code=409, detail="Username already exists")
    # Never trust client-supplied org_id — pin to default until an admin assigns.
    store[username] = User(
        username=username,
        hashed_password=hash_password(req.password),
        role=role,
        full_name=req.full_name or username,
        org_id="default",
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
    """OIDC callback — exchanges code, validates JWKS, issues local app JWT."""
    from insureflow.auth import Role
    from insureflow.auth.jwt import create_access_token
    from insureflow.auth.sso import exchange_code_for_claims, sso_status
    from insureflow.auth.store import get_user_store

    if not sso_status().get("enabled"):
        raise HTTPException(status_code=404, detail="SSO is not configured")
    code = str(payload.get("code") or "")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    claims = exchange_code_for_claims(code)

    if claims.get("status") != "validated" or not claims.get("email"):
        return {"claims": claims, "access_token": None, "error": claims.get("status", "unknown")}

    email = claims["email"]
    username = claims.get("sub", email.split("@")[0])
    name = claims.get("name", username)
    # Never trust client-supplied org_id from the SSO callback body.
    org_id = "default"

    store = get_user_store()
    user = store.get(username)
    if not user:
        from insureflow.auth.models import User

        user = User(
            username=username,
            email=email,
            full_name=name,
            role=Role.VIEWER,
            org_id=org_id,
        )
        store[username] = user
    # Existing users keep their assigned org — do not overwrite from client.
    token = create_access_token({"sub": username, "role": user.role.value, "org_id": user.org_id, "email": email})
    return {
        "claims": claims,
        "access_token": token,
        "token_type": "bearer",
        "user": {"username": username, "role": user.role.value, "email": email},
    }


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
                "description": "Line underwriter — implement UW process, coverage assist, producer/policyholder service",
                "desk": "line",
            },
            {
                "role": "staff_uw",
                "level": 2,
                "description": "Staff underwriter — market research, guides, rating plans, UW audits, training",
                "desk": "staff",
            },
            {
                "role": "licensed_uw",
                "level": 3,
                "description": "Licensed line UW — sign off decisions and bind; may join staff on large/unusual accounts",
                "desk": "line",
            },
            {
                "role": "admin",
                "level": 4,
                "description": "Manage users, delete jobs, configure webhooks — line + staff desks",
                "desk": "both",
            },
            {
                "role": "cuo",
                "level": 5,
                "description": "Chief underwriting officer — market cycles, policy, and system-wide parameters",
                "desk": "staff",
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
    raise HTTPException(status_code=404, detail="Dashboard not found")


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
    insurance_line: Optional[str] = None  # commercial_* | personal_homeowners | personal_auto | life
    use_llm: bool = True
    use_legacy_pipeline: bool = False
    use_celery: bool = False


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
    effective_date: str = ""  # coverage effective date (defaults to today)
    expiry_date: str = ""  # coverage expiry date (defaults to +1 year)
    certificate_holder: str = ""  # party named on the certificate of insurance


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
    unread_only: Optional[bool] = None
    bundle_id: Optional[str] = None  # accumulate into existing draft bundle


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.3.1"}


@app.get("/ops/snapshot")
def ops_snapshot(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Production ops snapshot — job counts, sandbox readiness, alerts for Railway dashboards."""
    from insureflow.observability.ops_snapshot import collect_ops_snapshot

    snap = collect_ops_snapshot(job_store)
    snap["org_id"] = current.org_id
    return snap


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
            "name": "Pacific Coast Distributors, Inc.",
            "description": "Commercial P&C — ACORD, loss run, SOV, inspection, broker API",
            "vertical": "insurance",
            "insurance_line": "commercial_property",
        },
        {
            "id": "northwind",
            "name": "Northwind Logistics LLC",
            "description": "Transportation & logistics — ACORD, loss run, SOV, inspection",
            "vertical": "insurance",
            "insurance_line": "commercial_property",
        },
        {
            "id": "maya-homeowners",
            "name": "Maya Chen (Homeowners)",
            "description": "Personal HO-3 — application, dwelling inspection, CLUE",
            "vertical": "insurance",
            "insurance_line": "personal_homeowners",
        },
        {
            "id": "jordan-auto",
            "name": "Jordan Blake (Personal Auto)",
            "description": "Personal auto — application, MVR, vehicle declarations",
            "vertical": "insurance",
            "insurance_line": "personal_auto",
        },
        {
            "id": "priya-life",
            "name": "Priya Nair (Term Life)",
            "description": "Term life — application, paramedical exam, beneficiary",
            "vertical": "insurance",
            "insurance_line": "life",
        },
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
            "id": "chen-residential",
            "name": "Chen Family (Residential)",
            "description": "Residential package — income, assets, credit, property, UW docs",
            "vertical": "mortgage",
            "product_line": "residential_mortgage",
            "directory": str(SIM_DOCS_DIR / "home_mortgage" / "chen_david_karen"),
        },
        {
            "id": "patel-residential",
            "name": "Patel Home Loan (Residential)",
            "description": "Residential package — income, assets, credit, property, UW docs",
            "vertical": "mortgage",
            "product_line": "residential_mortgage",
            "directory": str(SIM_DOCS_DIR / "home_mortgage" / "patel_lisa"),
        },
        {
            "id": "thompson-residential",
            "name": "Thompson Family (Residential)",
            "description": "Residential package — underwriting file",
            "vertical": "mortgage",
            "product_line": "residential_mortgage",
            "directory": str(SIM_DOCS_DIR / "home_mortgage" / "thompson_john_sarah"),
        },
        {
            "id": "wilson-residential",
            "name": "Wilson Home Loan (Residential)",
            "description": "Residential package — income, credit, property, UW docs",
            "vertical": "mortgage",
            "product_line": "residential_mortgage",
            "directory": str(SIM_DOCS_DIR / "home_mortgage" / "wilson_james"),
        },
        {
            "id": "rodriguez-residential",
            "name": "Rodriguez Family (Residential)",
            "description": "Residential package — income, assets, credit, property, UW docs",
            "vertical": "mortgage",
            "product_line": "residential_mortgage",
            "directory": str(SIM_DOCS_DIR / "home_mortgage" / "rodriguez_maria"),
        },
        {
            "id": "midwest-commercial",
            "name": "Midwest Medical Plaza (Commercial)",
            "description": "Commercial CRE package — entity financials, leases, due diligence",
            "vertical": "mortgage",
            "product_line": "commercial_mortgage",
            "directory": str(SIM_DOCS_DIR / "commercial_mortgage" / "midwest_medical_plaza"),
        },
        {
            "id": "oak-street-commercial",
            "name": "Oak Street Retail (Commercial)",
            "description": "Commercial CRE package — entity financials, debt, property performance",
            "vertical": "mortgage",
            "product_line": "commercial_mortgage",
            "directory": str(SIM_DOCS_DIR / "commercial_mortgage" / "oak_street_retail"),
        },
        {
            "id": "riverbend-commercial",
            "name": "Riverbend Self Storage (Commercial)",
            "description": "Commercial CRE package — entity financials, due diligence",
            "vertical": "mortgage",
            "product_line": "commercial_mortgage",
            "directory": str(SIM_DOCS_DIR / "commercial_mortgage" / "riverbend_self_storage"),
        },
    ]
    lending = [
        {
            "id": "blue-harbor-bakery",
            "name": "Blue Harbor Bakery LLC (SBA 7A)",
            "description": "Food manufacturer — application, P&L, balance sheet, bank, credit, tax",
            "vertical": "lending",
            "product_type": "sba_7a",
            "purpose": "working_capital",
            "directory": str(SIM_DOCS_DIR / "lending" / "blue_harbor_bakery"),
        },
        {
            "id": "keller-logistics",
            "name": "Keller Logistics Group (Term Loan)",
            "description": "Trucking — application, P&L, balance sheet, bank, credit, tax",
            "vertical": "lending",
            "product_type": "business_term_loan",
            "purpose": "equipment",
            "directory": str(SIM_DOCS_DIR / "lending" / "keller_logistics"),
        },
    ]
    return {"insurance": insurance, "mortgage": mortgage, "lending": lending}


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


def _load_docs_from_dir(subdir: str) -> list[InsuranceDocumentPayload]:
    root = EXAMPLES_DIR / subdir
    docs: list[InsuranceDocumentPayload] = []
    for path in sorted(root.glob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json", ".xml"}:
            docs.append(
                InsuranceDocumentPayload(
                    filename=path.name,
                    content=path.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            )
    return docs


def _load_maya_homeowners_submission() -> SubmissionRequest:
    return SubmissionRequest(
        documents=_load_docs_from_dir("personal_homeowners"),
        insurance_line="personal_homeowners",
        use_llm=True,
    )


def _load_jordan_auto_submission() -> SubmissionRequest:
    return SubmissionRequest(
        documents=_load_docs_from_dir("personal_auto"),
        insurance_line="personal_auto",
        use_llm=True,
    )


def _load_priya_life_submission() -> SubmissionRequest:
    return SubmissionRequest(
        documents=_load_docs_from_dir("life"),
        insurance_line="life",
        use_llm=True,
    )


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


def _load_northwind_submission() -> SubmissionRequest:
    acord = (EXAMPLES_DIR / "northwind_acord.xml").read_text(encoding="utf-8")
    loss_run = (EXAMPLES_DIR / "northwind_loss_run.md").read_text(encoding="utf-8")
    sov = (EXAMPLES_DIR / "northwind_sov.md").read_text(encoding="utf-8")
    inspection = (EXAMPLES_DIR / "northwind_inspection_report.md").read_text(encoding="utf-8")
    return SubmissionRequest(
        acord_xml=acord,
        loss_run=loss_run,
        schedule_of_values=sov,
        inspection_reports=[inspection],
        use_llm=True,
    )


@app.post("/api/demo/insurance/{preset_id}", status_code=202)
async def run_insurance_demo(
    preset_id: str,
    background_tasks: BackgroundTasks,
    current: TokenData | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    if _posture().is_hardened:
        raise HTTPException(status_code=403, detail="Demo presets are disabled in BANK_MODE/production")
    org_id = current.org_id if current and current.org_id else "demo"
    preset_map: dict[str, tuple[str, Callable[[], SubmissionRequest]]] = {
        "pacific-coast": ("pacific_coast_acord.xml", _load_pacific_coast_submission),
        "northwind": ("northwind_acord.xml", _load_northwind_submission),
        "maya-homeowners": ("personal_homeowners/homeowners_application.md", _load_maya_homeowners_submission),
        "jordan-auto": ("personal_auto/auto_application.md", _load_jordan_auto_submission),
        "priya-life": ("life/life_application.md", _load_priya_life_submission),
    }
    if preset_id not in preset_map:
        raise HTTPException(status_code=404, detail=f"Unknown insurance preset: {preset_id}")
    filename, loader = preset_map[preset_id]
    if not (EXAMPLES_DIR / filename).exists():
        raise HTTPException(status_code=503, detail="Example data not found on server")
    job_id = f"demo-{uuid.uuid4().hex[:12]}"
    req = loader()
    job_store.set(INSURANCE_NS, job_id, {"status": "processing", "demo": True}, org_id=org_id)

    from insureflow.tasks.dispatch import send_pipeline_task, should_use_celery

    celery_task_id: str | None = None
    if should_use_celery(False):
        try:
            celery_task_id = send_pipeline_task(job_id, req.model_dump(), org_id)
        except Exception as exc:
            logger.warning("Celery demo dispatch failed for job %s, falling back to in-process: %s", job_id, exc)
            celery_task_id = None
    if celery_task_id:
        job_store.set(
            INSURANCE_NS,
            job_id,
            {"status": "processing", "demo": True, "backend": "celery", "celery_task_id": celery_task_id},
            org_id=org_id,
        )
        return {"job_id": job_id, "status": "processing", "preset": preset_id, "org_id": org_id, "use_celery": True}

    background_tasks.add_task(_run_pipeline_task, job_id, req, org_id)
    return {"job_id": job_id, "status": "processing", "preset": preset_id, "org_id": org_id}


@app.get("/api/insurance/sources")
def list_insurance_sources(
    vertical: str = "insurance",
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.ingestion.insurance.sources import list_sources

    extra = _vertical_package_list(vertical) if vertical != "insurance" else None
    return {
        "sources": list_sources(
            EXAMPLES_DIR,
            extra_packages=extra,
            include_insurance_packages=vertical == "insurance",
        ),
        "hardened": _posture().is_hardened,
    }


@app.post("/api/insurance/sources/{source_id}/pull")
def pull_insurance_source(
    source_id: str,
    req: InsuranceSourcePullRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
    vertical: str = "insurance",
) -> dict[str, Any]:
    """Pull submission documents from a connected source (library, folder, or simulated cloud).

    If ``bundle_id`` is provided in the request, pulled documents are accumulated
    into that draft bundle instead of being returned as loose data.  This enables
    multi-source intake: pull from email → accumulate → pull from S3 → accumulate
    → run the pipeline with everything.
    """
    from insureflow.ingestion.insurance.sources import (
        DEMO_CONNECTORS,
        INSURANCE_PACKAGES,
        load_directory,
        load_package,
        simulated_connection_label,
    )

    def _accumulate(
        documents: list[dict[str, str]],
        source_id_val: str,
        connection_label: str,
    ) -> dict[str, Any] | None:
        """If bundle_id is set, push documents into the draft bundle."""
        if not req.bundle_id:
            return None
        from insureflow.storage.draft_bundle_store import get_draft_bundle_store

        store = get_draft_bundle_store()
        bundle = store.add_documents(
            req.bundle_id,
            documents,
            source_id=source_id_val,
            connection_label=connection_label,
            org_id=current.org_id,
        )
        if not bundle:
            return None
        return {
            "bundle_id": bundle["bundle_id"],
            "document_count": len(bundle.get("documents", [])),
            "added": len(documents),
        }

    def _register(label: str) -> None:
        """Persist the connection so the Integrations page reflects it."""
        from insureflow.integrations.connections import save_connection

        config_fields = DEMO_CONNECTORS.get(source_id, {}).get("config_fields") or []
        keys = [f["key"] for f in config_fields]
        if source_id == "server-folder":
            keys = ["path"]
        cfg = {k: getattr(req, k, None) for k in keys if getattr(req, k, None) is not None}
        save_connection(source_id, cfg, label, org_id=current.org_id)

    try:
        if source_id in INSURANCE_PACKAGES and vertical == "insurance":
            documents = load_package(EXAMPLES_DIR, source_id)
            meta = INSURANCE_PACKAGES[source_id]
            result: dict[str, Any] = {
                "source_id": source_id,
                "simulated": False,
                "connection_label": meta["name"],
                "package_id": source_id,
                "package_name": meta["name"],
                "documents": documents,
                "file_count": len(documents),
            }
            accum = _accumulate(documents, source_id, str(meta["name"]))
            if accum:
                result["accumulated"] = accum
            _register(str(meta["name"]))
            return result

        # Vertical library packages (mortgage / lending fixtures)
        if vertical != "insurance" and source_id in _VERTICAL_PACKAGES.get(vertical, {}):
            meta = _VERTICAL_PACKAGES[vertical][source_id]
            documents = _load_vertical_package(vertical, source_id)
            result = {
                "source_id": source_id,
                "simulated": False,
                "connection_label": meta["name"],
                "package_id": source_id,
                "package_name": meta["name"],
                "documents": documents,
                "file_count": len(documents),
            }
            accum = _accumulate(documents, source_id, str(meta["name"]))
            if accum:
                result["accumulated"] = accum
            _register(str(meta["name"]))
            return result

        # Real IMAP email connector — credentials from env vars (admin-configured)
        if source_id == "email-inbox":
            from insureflow.ingestion.insurance.email_connector import (
                ImapConnection,
                pull_email_submissions,
            )

            conn = ImapConnection()
            if conn.is_configured:
                pull_result = pull_email_submissions()
                label = f"Email › {conn.username}"
                result = {
                    "source_id": source_id,
                    "simulated": False,
                    "connection_label": label,
                    "emails": pull_result["emails"],
                    "documents": pull_result["documents"],
                    "file_count": pull_result["documents_found"],
                    "emails_found": pull_result["emails_found"],
                }
                accum = _accumulate(pull_result["documents"], source_id, label)
                if accum:
                    result["accumulated"] = accum
                _register(label)
                return result

            raise HTTPException(
                status_code=503,
                detail="Email integration not configured. Admin must set IMAP_HOST, IMAP_USERNAME, IMAP_PASSWORD.",
            )

        if source_id in DEMO_CONNECTORS:
            if _posture().is_hardened:
                raise HTTPException(
                    status_code=403,
                    detail="Demo connectors are disabled in BANK_MODE/production",
                )
            # Require at least one config field to be filled
            connector = DEMO_CONNECTORS[source_id]
            config_keys = [f["key"] for f in (connector.get("config_fields") or [])]
            has_config = any(getattr(req, k, None) for k in config_keys)
            if config_keys and not has_config:
                raise HTTPException(
                    status_code=400,
                    detail=f"Please configure the {connector['name']} connection fields above.",
                )
            package_id = req.package_id
            if vertical == "insurance":
                package_id = package_id or "pacific-coast"
                documents = load_package(EXAMPLES_DIR, package_id)
                meta = INSURANCE_PACKAGES[package_id]
            else:
                vertical_packages = _VERTICAL_PACKAGES.get(vertical, {})
                package_id = package_id or next(iter(vertical_packages), None)
                if not package_id or package_id not in vertical_packages:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Please choose a {vertical} demo package to pull through this connector.",
                    )
                documents = _load_vertical_package(vertical, package_id)
                meta = {"name": vertical_packages[package_id]["name"]}
            label = simulated_connection_label(source_id, req)
            result = {
                "source_id": source_id,
                "simulated": True,
                "connection_label": label,
                "package_id": package_id,
                "package_name": meta["name"],
                "documents": documents,
                "file_count": len(documents),
            }
            accum = _accumulate(documents, source_id, label)
            if accum:
                result["accumulated"] = accum
            _register(label)
            return result

        if source_id == "server-folder":
            raw = req.path or "examples"
            root = PROJECT_ROOT.resolve()
            directory = Path(raw)
            if not directory.is_absolute():
                directory = root / raw
            try:
                directory = directory.resolve()
            except OSError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid path: {exc}") from exc
            if not directory.is_relative_to(root):
                raise HTTPException(status_code=400, detail="Path must be under project root")
            documents = load_directory(directory)
            label = str(directory)
            result = {
                "source_id": source_id,
                "simulated": False,
                "connection_label": label,
                "documents": documents,
                "file_count": len(documents),
            }
            accum = _accumulate(documents, source_id, label)
            if accum:
                result["accumulated"] = accum
            _register(label)
            return result

        if source_id == "s3-bucket":
            from insureflow.ingestion.insurance.s3_connector import pull_s3_submissions, s3_configured

            if not s3_configured(req.bucket):
                raise HTTPException(
                    status_code=400,
                    detail="S3 not configured — set bucket on request or S3_SUBMISSIONS_BUCKET / AWS credentials",
                )
            try:
                pull = pull_s3_submissions(bucket=req.bucket, prefix=req.prefix or "")
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"S3 pull failed: {exc}") from exc
            label = f"s3://{pull['bucket']}/{pull.get('prefix') or ''}"
            result = {
                "source_id": source_id,
                "simulated": False,
                "connection_label": label,
                "documents": pull["documents"],
                "file_count": pull["documents_found"],
                "objects_considered": pull.get("objects_considered", 0),
            }
            accum = _accumulate(pull["documents"], source_id, label)
            if accum:
                result["accumulated"] = accum
            _register(label)
            return result

        raise HTTPException(status_code=404, detail=f"Unknown source: {source_id}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class EmailFilterRequest(BaseModel):
    email_ids: list[str]


@app.post("/api/insurance/sources/email-inbox/filter")
def filter_email_documents(
    req: EmailFilterRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Filter email documents by selected email IDs.

    The frontend stores the full email list after pull, then calls this
    endpoint with the IDs the user selected to get only those documents.
    """
    from insureflow.ingestion.insurance.email_connector import (
        ImapConnection,
        pull_email_submissions,
    )

    imap_conn = ImapConnection()
    if not imap_conn.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Email integration not configured",
        )

    result = pull_email_submissions()
    emails = result.get("emails", [])
    selected = {eid for eid in req.email_ids}

    filtered_docs: list[dict[str, str]] = []
    for email_entry in emails:
        if email_entry["id"] in selected:
            filtered_docs.extend(email_entry.get("documents", []))

    return {
        "documents": filtered_docs,
        "file_count": len(filtered_docs),
        "emails_selected": len(selected),
    }


# ── Draft Bundle Endpoints (multi-source intake) ─────────────────────


class DraftBundleCreateRequest(BaseModel):
    name: str = ""


class DraftBundleAddDocsRequest(BaseModel):
    documents: list[InsuranceDocumentPayload]
    source_id: str = ""
    connection_label: str = ""


@app.get("/pipeline/bundles")
def list_draft_bundles(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.storage.draft_bundle_store import get_draft_bundle_store

    store = get_draft_bundle_store()
    bundles = store.list_all(org_id=current.org_id)
    # Return summaries without document content (large payloads)
    summaries = []
    for b in bundles:
        summaries.append(
            {
                "bundle_id": b["bundle_id"],
                "name": b.get("name", ""),
                "status": b.get("status", ""),
                "document_count": len(b.get("documents", [])),
                "sources": list({d.get("source_id", "") for d in b.get("documents", []) if d.get("source_id")}),
                "created_at": b.get("created_at", ""),
                "updated_at": b.get("updated_at", ""),
            }
        )
    return {"bundles": summaries}


@app.post("/pipeline/bundles", status_code=201)
def create_draft_bundle(
    req: DraftBundleCreateRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.storage.draft_bundle_store import get_draft_bundle_store

    store = get_draft_bundle_store()
    bundle = store.create(org_id=current.org_id, name=req.name)
    return {
        "bundle_id": bundle["bundle_id"],
        "name": bundle["name"],
        "status": bundle["status"],
        "document_count": 0,
    }


@app.get("/pipeline/bundles/{bundle_id}")
def get_draft_bundle(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.storage.draft_bundle_store import get_draft_bundle_store

    store = get_draft_bundle_store()
    bundle = store.get(bundle_id, org_id=current.org_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Draft bundle not found")
    # Return without document content for the list view
    return {
        "bundle_id": bundle["bundle_id"],
        "name": bundle.get("name", ""),
        "status": bundle.get("status", ""),
        "documents": [
            {
                "doc_id": d["doc_id"],
                "filename": d["filename"],
                "source_id": d.get("source_id", ""),
                "connection_label": d.get("connection_label", ""),
                "added_at": d.get("added_at", ""),
            }
            for d in bundle.get("documents", [])
        ],
        "document_count": len(bundle.get("documents", [])),
        "created_at": bundle.get("created_at", ""),
        "updated_at": bundle.get("updated_at", ""),
    }


@app.post("/pipeline/bundles/{bundle_id}/documents")
def add_documents_to_draft(
    bundle_id: str,
    req: DraftBundleAddDocsRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.storage.draft_bundle_store import get_draft_bundle_store

    store = get_draft_bundle_store()
    docs = [{"filename": d.filename, "content": d.content, "encoding": d.encoding} for d in req.documents]
    bundle = store.add_documents(
        bundle_id,
        docs,
        source_id=req.source_id,
        connection_label=req.connection_label,
        org_id=current.org_id,
    )
    if not bundle:
        raise HTTPException(status_code=404, detail="Draft bundle not found")
    return {
        "bundle_id": bundle["bundle_id"],
        "document_count": len(bundle.get("documents", [])),
        "added": len(docs),
    }


@app.delete("/pipeline/bundles/{bundle_id}/documents/{doc_id}")
def remove_document_from_draft(
    bundle_id: str,
    doc_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.storage.draft_bundle_store import get_draft_bundle_store

    store = get_draft_bundle_store()
    bundle = store.remove_document(bundle_id, doc_id, org_id=current.org_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Draft bundle not found")
    return {
        "bundle_id": bundle["bundle_id"],
        "document_count": len(bundle.get("documents", [])),
    }


@app.delete("/pipeline/bundles/{bundle_id}")
def delete_draft_bundle(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, str]:
    from insureflow.storage.draft_bundle_store import get_draft_bundle_store

    store = get_draft_bundle_store()
    deleted = store.delete(bundle_id, org_id=current.org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft bundle not found")
    return {"detail": "deleted"}


@app.post("/pipeline/bundles/{bundle_id}/run", status_code=202)
def run_draft_bundle(
    bundle_id: str,
    background_tasks: BackgroundTasks,
    current: TokenData = Depends(require_role(Role.VIEWER)),
    use_llm: bool = True,
    vertical: str = "insurance",
) -> dict[str, Any]:
    """Execute the pipeline using all accumulated documents in a draft bundle.

    ``vertical`` routes the accumulated bundle into the matching pipeline:
    insurance (async job), mortgage (async job), or lending (inline result).
    """
    from insureflow.storage.draft_bundle_store import DRAFT_NS, get_draft_bundle_store

    store = get_draft_bundle_store()
    docs = store.to_pipeline_documents(bundle_id, org_id=current.org_id)
    if not docs:
        raise HTTPException(status_code=400, detail="Draft bundle has no documents")

    bundle = store.get(bundle_id, org_id=current.org_id)

    if vertical == "mortgage":
        job_id = f"mort-{uuid.uuid4().hex[:12]}"
        job_store.set(MORTGAGE_NS, job_id, {"status": "processing"}, org_id=current.org_id)
        mortgage_req = MortgageSubmissionRequest(
            documents=[MortgageDocumentPayload(**d) for d in docs],
            use_llm=use_llm,
            bundle_id=job_id,
        )
        background_tasks.add_task(_run_mortgage_task, job_id, mortgage_req, current.org_id)
        if bundle:
            bundle["status"] = "submitted"
            bundle["submitted_job_id"] = job_id
            store._store.set(DRAFT_NS, bundle_id, bundle, org_id=current.org_id)
        return {"job_id": job_id, "status": "processing", "bundle_id": bundle_id, "vertical": "mortgage"}

    if vertical == "lending":
        result = run_lending_pipeline(
            LendingSubmissionRequest(
                documents=[InsuranceDocumentPayload(**d) for d in docs],
                require_documents=True,
            ),
            current=current,
        )
        if bundle:
            bundle["status"] = "submitted"
            store._store.set(DRAFT_NS, bundle_id, bundle, org_id=current.org_id)
        return {"bundle_id": bundle_id, "vertical": "lending", **result}

    job_id = f"job-{uuid.uuid4().hex[:12]}"
    job_store.set(INSURANCE_NS, job_id, {"status": "processing"}, org_id=current.org_id)

    req = SubmissionRequest(documents=[InsuranceDocumentPayload(**d) for d in docs], use_llm=use_llm)
    background_tasks.add_task(_run_pipeline_task, job_id, req, current.org_id)

    # Mark draft as submitted
    if bundle:
        bundle["status"] = "submitted"
        bundle["submitted_job_id"] = job_id
        store._store.set(DRAFT_NS, bundle_id, bundle, org_id=current.org_id)

    return {"job_id": job_id, "status": "processing", "bundle_id": bundle_id}


@app.post("/api/demo/mortgage/{preset_id}", status_code=202)
async def run_mortgage_demo(
    preset_id: str,
    background_tasks: BackgroundTasks,
    current: TokenData | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    if _posture().is_hardened:
        raise HTTPException(status_code=403, detail="Demo presets are disabled in BANK_MODE/production")
    org_id = current.org_id if current and current.org_id else "demo"
    presets = {
        "johnson-residential": (
            SIM_DOCS_DIR / "home_mortgage" / "johnson_marcus_imani",
            "residential_mortgage",
        ),
        "chen-residential": (
            SIM_DOCS_DIR / "home_mortgage" / "chen_david_karen",
            "residential_mortgage",
        ),
        "patel-residential": (
            SIM_DOCS_DIR / "home_mortgage" / "patel_lisa",
            "residential_mortgage",
        ),
        "thompson-residential": (
            SIM_DOCS_DIR / "home_mortgage" / "thompson_john_sarah",
            "residential_mortgage",
        ),
        "wilson-residential": (
            SIM_DOCS_DIR / "home_mortgage" / "wilson_james",
            "residential_mortgage",
        ),
        "rodriguez-residential": (
            SIM_DOCS_DIR / "home_mortgage" / "rodriguez_maria",
            "residential_mortgage",
        ),
        "midwest-commercial": (
            SIM_DOCS_DIR / "commercial_mortgage" / "midwest_medical_plaza",
            "commercial_mortgage",
        ),
        "oak-street-commercial": (
            SIM_DOCS_DIR / "commercial_mortgage" / "oak_street_retail",
            "commercial_mortgage",
        ),
        "riverbend-commercial": (
            SIM_DOCS_DIR / "commercial_mortgage" / "riverbend_self_storage",
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


@app.post("/api/demo/lending/{preset_id}", status_code=200)
def run_lending_demo(
    preset_id: str,
    current: TokenData | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """One-click lending sample data — full document package to underwritten decision."""
    if _posture().is_hardened:
        raise HTTPException(status_code=403, detail="Demo presets are disabled in BANK_MODE/production")
    org_id = current.org_id if current and current.org_id else "demo"
    presets: dict[str, dict[str, Any]] = {
        "blue-harbor-bakery": {
            "directory": SIM_DOCS_DIR / "lending" / "blue_harbor_bakery",
            "product_type": "sba_7a",
            "purpose": "working_capital",
            "business_name": "Blue Harbor Bakery LLC",
            "industry": "Food Manufacturing",
        },
        "keller-logistics": {
            "directory": SIM_DOCS_DIR / "lending" / "keller_logistics",
            "product_type": "business_term_loan",
            "purpose": "equipment",
            "business_name": "Keller Logistics Group Inc.",
            "industry": "Freight Trucking",
        },
    }
    if preset_id not in presets:
        raise HTTPException(status_code=404, detail=f"Unknown lending preset: {preset_id}")
    cfg = presets[preset_id]
    directory = cfg["directory"]
    if not directory.is_dir():
        raise HTTPException(status_code=503, detail=f"Fixture directory missing: {directory}")

    from insureflow.ingestion.lending import (
        application_from_documents,
        load_lending_documents_from_directory,
    )
    from insureflow.lending import LendingPipeline
    from insureflow.lending.models import LoanProductType, LoanPurpose

    product_map: dict[str, LoanProductType] = {
        "business_term_loan": LoanProductType.BUSINESS_TERM_LOAN,
        "business_loc": LoanProductType.BUSINESS_LINE_OF_CREDIT,
        "cre": LoanProductType.COMMERCIAL_REAL_ESTATE,
        "construction": LoanProductType.CONSTRUCTION_LOAN,
        "sba_7a": LoanProductType.SBA_7A,
        "sba_504": LoanProductType.SBA_504,
        "equipment": LoanProductType.EQUIPMENT_FINANCING,
        "invoice": LoanProductType.INVOICE_FINANCING,
    }
    purpose_map: dict[str, LoanPurpose] = {
        "working_capital": LoanPurpose.WORKING_CAPITAL,
        "equipment": LoanPurpose.EQUIPMENT_PURCHASE,
        "refinance": LoanPurpose.DEBT_REFINANCE,
        "real_estate": LoanPurpose.REAL_ESTATE_PURCHASE,
        "construction": LoanPurpose.CONSTRUCTION,
        "expansion": LoanPurpose.BUSINESS_EXPANSION,
        "inventory": LoanPurpose.INVENTORY_FINANCING,
        "acquisition": LoanPurpose.ACQUISITION,
    }
    pt = product_map.get(cfg["product_type"], LoanProductType.BUSINESS_TERM_LOAN)
    purpose = purpose_map.get(cfg["purpose"], LoanPurpose.OTHER)
    is_business = pt.value.startswith(("business_", "commercial_", "construction_", "sba_", "equipment_", "invoice_"))

    docs = load_lending_documents_from_directory(directory)
    if not docs:
        raise HTTPException(status_code=503, detail=f"No readable documents in {directory}")
    application = application_from_documents(
        docs,
        product_type=pt,
        purpose=purpose,
        is_business=is_business,
        overrides={
            "business_name": cfg.get("business_name", ""),
            "industry": cfg.get("industry", ""),
        },
    )
    doc_payloads = [{"filename": d.filename, "content": d.content, "document_type": d.document_type.value} for d in docs]
    result = LendingPipeline().run(
        application,
        documents=doc_payloads,
        require_documents=True,
        pipeline_run_id=f"demo-lend-{uuid.uuid4().hex[:12]}",
    )
    return {
        **result.model_dump(mode="json"),
        "vertical": "lending",
        "preset": preset_id,
        "org_id": org_id,
        "documents_ingested": len(doc_payloads),
    }


@app.get("/", response_model=None)
async def root(request: Request) -> FileResponse | JSONResponse:
    """Serve the marketing landing by default; JSON only when explicitly requested."""
    accept = (request.headers.get("accept") or "*/*").lower()
    wants_json_only = "application/json" in accept and "text/html" not in accept
    landing = STATIC_DIR / "landing" / "index.html"
    if landing.exists() and not wants_json_only:
        return FileResponse(landing)
    return JSONResponse(
        {
            "service": "Rytera",
            "version": "0.3.1",
            "dashboard": "/dashboard",
            "diagnostics": "/system/diagnostics",
            "health": "/health",
            "integration_gateway": "/integrations",
            "landing": "/",
        }
    )


@app.get("/robots.txt", include_in_schema=False)
def robots_txt() -> FileResponse:
    path = STATIC_DIR / "landing" / "robots.txt"
    if not path.exists():
        raise HTTPException(status_code=404, detail="robots.txt not found")
    return FileResponse(path, media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml() -> FileResponse:
    path = STATIC_DIR / "landing" / "sitemap.xml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="sitemap.xml not found")
    return FileResponse(path, media_type="application/xml")


@app.get("/favicon.ico", include_in_schema=False)
def favicon_ico() -> FileResponse:
    path = STATIC_DIR / "landing" / "favicon.ico"
    if not path.exists():
        raise HTTPException(status_code=404, detail="favicon not found")
    return FileResponse(path, media_type="image/x-icon")


@app.get("/googlee8bd725babd1be66.html", include_in_schema=False)
def google_site_verification() -> FileResponse:
    path = STATIC_DIR / "landing" / "googlee8bd725babd1be66.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="verification file not found")
    return FileResponse(path, media_type="text/html")


@app.get("/google225357ae8c77ee88.html", include_in_schema=False)
def google_site_verification_two() -> FileResponse:
    path = STATIC_DIR / "landing" / "google225357ae8c77ee88.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="verification file not found")
    return FileResponse(path, media_type="text/html")


@app.get("/favicon.png", include_in_schema=False)
def favicon_png() -> FileResponse:
    path = STATIC_DIR / "landing" / "favicon.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="favicon not found")
    return FileResponse(path, media_type="image/png")


@app.get("/favicon.svg", include_in_schema=False)
def favicon_svg() -> FileResponse:
    path = STATIC_DIR / "landing" / "favicon.svg"
    if not path.exists():
        raise HTTPException(status_code=404, detail="favicon not found")
    return FileResponse(path, media_type="image/svg+xml")


@app.get("/apple-touch-icon.png", include_in_schema=False)
def apple_touch_icon() -> FileResponse:
    path = STATIC_DIR / "landing" / "apple-touch-icon.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="apple-touch-icon not found")
    return FileResponse(path, media_type="image/png")


@app.get("/og-image.png", include_in_schema=False)
def og_image() -> FileResponse:
    path = STATIC_DIR / "landing" / "og-image.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="og-image not found")
    return FileResponse(path, media_type="image/png")


@app.get("/icon-192.png", include_in_schema=False)
def icon_192() -> FileResponse:
    path = STATIC_DIR / "landing" / "icon-192.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="icon not found")
    return FileResponse(path, media_type="image/png")


@app.get("/icon-512.png", include_in_schema=False)
def icon_512() -> FileResponse:
    path = STATIC_DIR / "landing" / "icon-512.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="icon not found")
    return FileResponse(path, media_type="image/png")


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
                insurance_line=request.insurance_line,
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    from insureflow.tasks.dispatch import send_pipeline_task, should_use_celery

    use_celery = should_use_celery(req.use_celery)
    job_store.set(
        INSURANCE_NS,
        job_id,
        {"status": "processing", "backend": "celery" if use_celery else "background"},
        org_id=current.org_id,
    )
    celery_task_id: str | None = None
    if use_celery:
        try:
            celery_task_id = send_pipeline_task(job_id, req.model_dump(), current.org_id)
        except Exception as exc:
            logger.warning("Celery dispatch failed for job %s, falling back to in-process: %s", job_id, exc)
            celery_task_id = None
    if celery_task_id:
        job_store.set(
            INSURANCE_NS,
            job_id,
            {
                "status": "processing",
                "backend": "celery",
                "celery_task_id": celery_task_id,
            },
            org_id=current.org_id,
        )
        return {
            "job_id": job_id,
            "status": "processing",
            "org_id": current.org_id,
            "use_celery": True,
            "celery_task_id": celery_task_id,
        }

    background_tasks.add_task(_run_pipeline_task, job_id, req, current.org_id)
    return {"job_id": job_id, "status": "processing", "org_id": current.org_id, "use_celery": False}


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
def list_jobs(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, list[str]]:
    return {"jobs": job_store.list_ids(INSURANCE_NS, org_id=current.org_id)}


@app.delete("/pipeline/jobs/{job_id}", status_code=204)
def delete_job(
    job_id: str,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> None:
    if not job_store.delete(INSURANCE_NS, job_id, org_id=current.org_id):
        raise HTTPException(status_code=404, detail="Job not found")


@app.get("/pipeline/jobs/{job_id}/download")
def download_job(
    job_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    job = job_store.get(INSURANCE_NS, job_id, org_id=current.org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": job.get("status"), "results": job.get("results", {}), "error": job.get("error")}


@app.post("/pipeline/jobs/{job_id}/retry", status_code=202)
async def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Re-run a failed or completed insurance pipeline job."""
    org_id = current.org_id
    old_job = job_store.get(INSURANCE_NS, job_id, org_id=org_id)
    if not old_job:
        raise HTTPException(status_code=404, detail="Job not found")
    req = _load_pacific_coast_submission()
    new_id = f"retry-{uuid.uuid4().hex[:12]}"
    job_store.set(INSURANCE_NS, new_id, {"status": "processing", "retry_of": job_id}, org_id=org_id)

    from insureflow.tasks.dispatch import send_pipeline_task, should_use_celery

    celery_task_id: str | None = None
    if should_use_celery(False):
        try:
            celery_task_id = send_pipeline_task(new_id, req.model_dump(), org_id)
        except Exception as exc:
            logger.warning("Celery retry dispatch failed for job %s, falling back to in-process: %s", job_id, exc)
            celery_task_id = None
    if celery_task_id:
        job_store.set(
            INSURANCE_NS,
            new_id,
            {"status": "processing", "retry_of": job_id, "backend": "celery", "celery_task_id": celery_task_id},
            org_id=org_id,
        )
        return {"job_id": new_id, "status": "processing", "retry_of": job_id, "use_celery": True}

    background_tasks.add_task(_run_pipeline_task, new_id, req, org_id)
    return {"job_id": new_id, "status": "processing", "retry_of": job_id}


@app.delete("/pipeline/jobs/bulk", status_code=204)
def bulk_delete_jobs(
    job_ids: list[str],
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> None:
    for jid in job_ids:
        job_store.delete(INSURANCE_NS, jid, org_id=current.org_id)


def _resolve_job_any_vertical(job_id: str, org_id: str) -> tuple[dict[str, Any] | None, str]:
    """Find a job across insurance / mortgage / lending namespaces for the caller's org only.

    Returns ``(job, vertical)``; ``vertical`` is the namespace it lived in.
    """
    for ns in (INSURANCE_NS, MORTGAGE_NS, LENDING_NS):
        job = job_store.get(ns, job_id, org_id=org_id)
        if job:
            return job, ns
    return None, ""


@app.get("/pipeline/jobs/{job_id}/quote")
def get_job_quote(
    job_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> StreamingResponse:
    org_id = current.org_id
    job = job_store.get(INSURANCE_NS, job_id, org_id=org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    html = (job.get("results") or {}).get("quote_html", "")
    if not html:
        raise HTTPException(status_code=404, detail="Quote document not available")
    results = job.get("results") or {}
    insured = results.get("memo", {}).get("insured_name") or results.get("insured_name") or job_id
    safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in insured).strip().replace(" ", "_") or job_id
    try:
        from insureflow.rating.report_document import html_to_pdf

        pdf_bytes = html_to_pdf(html)
        is_pdf = pdf_bytes[:4] == b"%PDF"
        media_type = "application/pdf" if is_pdf else "text/html"
        ext = "pdf" if is_pdf else "html"
    except Exception as exc:
        logger.error("Quote PDF generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Quote PDF generation failed: {exc}")
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="Rytera_Quote_{safe_name}.{ext}"'},
    )


@app.get("/pipeline/jobs/{job_id}/report")
def get_job_report(
    job_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> StreamingResponse:
    org_id = current.org_id
    job, vertical = _resolve_job_any_vertical(job_id, org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    results = job.get("results") or {}
    if not results:
        raise HTTPException(status_code=404, detail="Pipeline results not available for this job")
    borrower = results.get("memo", {}).get("insured_name") or results.get("insured_name") or results.get("borrower") or (results.get("memo") or {}).get("borrower_name") or job_id
    safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in borrower).strip().replace(" ", "_") or job_id
    try:
        from insureflow.rating.report_document import (
            generate_lending_report_html,
            generate_mortgage_report_html,
            generate_report_html,
            html_to_pdf,
        )

        if vertical == "mortgage":
            html = generate_mortgage_report_html(results, job_id)
        elif vertical == "lending":
            html = generate_lending_report_html(results, job_id)
        else:
            html = generate_report_html(results, job_id)
        pdf_bytes = html_to_pdf(html)
        is_pdf = pdf_bytes[:4] == b"%PDF"
        media_type = "application/pdf" if is_pdf else "text/html"
        ext = "pdf" if is_pdf else "html"
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}")
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="Rytera_Report_{safe_name}.{ext}"'},
    )


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
@limiter.limit("20/minute")
def licensed_uw_sign_off(
    bundle_id: str,
    req: SignOffRequest,
    request: Request,
    current: TokenData = Depends(require_role(Role.LICENSED_UW)),
) -> dict[str, Any]:
    from insureflow.workflow.models import SignOffAction
    from insureflow.workflow.service import WorkflowService

    try:
        action = SignOffAction(req.action.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {req.action}")

    svc = WorkflowService()
    try:
        record = svc.sign_off(
            bundle_id,
            current.org_id,
            action,
            signed_by=current.username or "",
            license_number=req.license_number,
            notes=req.notes,
            override_reason=req.override_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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

    # ── Step 5a: communicate the decision to the producer (good or bad) ──
    try:
        from insureflow.audit.store import AuditStore
        from insureflow.insurance.notifications import ProducerNotificationService

        summary = AuditStore().load_json(bundle_id, "pipeline_summary.json", org_id=current.org_id) or {}
        ProducerNotificationService().notify_decision(
            bundle_id,
            current.org_id,
            decision=record.final_decision or record.ai_decision,
            action=action.value,
            signed_by=current.username or "",
            reason=req.notes or req.override_reason or "",
            producer_name=str(summary.get("broker_name") or ""),
        )
    except Exception as exc:
        logger.warning("Producer decision notification failed for %s: %s", bundle_id, exc)

    return record.model_dump()


@app.post("/pipeline/workflow/{bundle_id}/bind")
@limiter.limit("10/minute")
def bind_policy(
    bundle_id: str,
    req: BindRequest,
    request: Request,
    current: TokenData = Depends(require_role(Role.LICENSED_UW)),
) -> dict[str, Any]:
    from insureflow.audit.store import AuditStore
    from insureflow.outcomes.feedback import FeedbackEngine
    from insureflow.rating.engine import InsuranceRatingEngine
    from insureflow.underwriting.authority import get_authority_matrix
    from insureflow.workflow.service import WorkflowService

    wf = WorkflowService()
    record = wf.store.get(bundle_id, current.org_id)
    if not record or record.state.value != "approved":
        raise HTTPException(status_code=400, detail="Policy must be UW-approved before bind")

    from insureflow.pilot.sandbox_readiness import is_shadow_mode

    if is_shadow_mode():
        raise HTTPException(
            status_code=403,
            detail=("Pilot shadow mode is active — bind is disabled. Configure live Guidewire credentials and set PILOT_SHADOW_MODE=false to enable bind."),
        )

    store = AuditStore()
    summary = store.load_json(bundle_id, "pipeline_summary.json", org_id=current.org_id) or {}
    quote = summary.get("quote", {}) or {}
    quote_ref = quote.get("policy_admin_reference", "")
    if not quote.get("eligible", True):
        raise HTTPException(status_code=400, detail="Quote is not eligible for bind")
    if not quote_ref:
        raise HTTPException(status_code=400, detail="Missing policy admin quote reference — cannot bind")

    checkpoints = summary.get("human_checkpoints") or []
    open_checkpoints = [c for c in checkpoints if str(c.get("status", "pending")).lower() not in {"approved", "cleared", "waived"}]
    if open_checkpoints:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Cannot bind while human checkpoints remain open",
                "open_checkpoints": open_checkpoints,
            },
        )

    open_conditions = list(summary.get("open_conditions") or [])
    if open_conditions:
        raise HTTPException(
            status_code=400,
            detail={"message": "Cannot bind with outstanding subjectivities/conditions", "open_conditions": open_conditions},
        )

    # Authority premium must come from the system quote — never trust client under-reporting.
    quote_premium = float(quote.get("adjusted_premium") or quote.get("base_premium") or 0.0)
    if req.bound_premium is not None and quote_premium > 0 and float(req.bound_premium) + 1.0 < quote_premium * 0.9:
        raise HTTPException(
            status_code=400,
            detail="bound_premium cannot be materially below the quoted premium",
        )
    premium = max(float(req.bound_premium or 0.0), quote_premium)
    tiv = float(summary.get("tiv") or quote.get("tiv") or 0.0)

    from insureflow.underwriting.authority import AuthorityVerdict
    from insureflow.underwriting.cosign import cosign_allows_bind

    verdict, authority_reason = get_authority_matrix().evaluate_binding_authority(
        username=current.username or "",
        premium=premium,
        tiv=tiv,
        state=str(summary.get("primary_state") or ""),
        org_id=current.org_id,
    )
    if verdict == AuthorityVerdict.DENIED:
        raise HTTPException(status_code=403, detail=authority_reason)

    if verdict == AuthorityVerdict.NEEDS_CO_SIGN:
        ok, cosign_reason = cosign_allows_bind(record.metadata, current.username or "")
        if not ok:
            # Create / refresh pending co-sign and block bind
            record = wf.request_cosign(
                bundle_id,
                current.org_id,
                requested_by=current.username or "",
                premium=premium,
                tiv=tiv,
                reason=authority_reason,
            )
            raise HTTPException(
                status_code=409,
                detail={
                    "message": authority_reason,
                    "co_sign_required": True,
                    "co_sign": record.metadata.get("co_sign"),
                    "hint": cosign_reason,
                },
            )

    rating = InsuranceRatingEngine()
    bind_result = rating.bind(bundle_id, quote_ref, current.username or "")
    if bind_result.get("success") is False or bind_result.get("status") == "failed":
        raise HTTPException(
            status_code=502,
            detail=bind_result.get("error") or "Policy bind failed on policy-admin system",
        )

    policy_number = req.policy_number or bind_result.get("policy_number", "")
    bound_premium = req.bound_premium or quote.get("adjusted_premium", 0.0)

    try:
        wf.mark_bound(bundle_id, current.org_id, policy_number, binder_username=current.username or "")
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    # Record in portfolio only after successful bind
    try:
        from insureflow.portfolio.store import PortfolioPolicy, get_portfolio_store

        get_portfolio_store().add_policy(
            PortfolioPolicy(
                policy_id=f"pol-{policy_number or bundle_id}",
                bundle_id=bundle_id,
                org_id=current.org_id,
                insured_name=str(summary.get("insured_name") or ""),
                producer_name=str(summary.get("broker_name") or ""),
                premium=float(bound_premium or 0.0),
                tiv=tiv,
                state=str(summary.get("primary_state") or ""),
            )
        )
    except Exception as exc:
        logger.warning("Portfolio bind recording failed: %s", exc)

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

    # ── Step 5b: issue binder / policy worksheet / certificate of insurance ──
    try:
        from insureflow.issuance.service import IssuanceService

        issuance = IssuanceService().issue(
            bundle_id,
            current.org_id,
            policy_number=policy_number,
            bound_by=current.username or "",
            premium=float(bound_premium or 0),
            effective_date=req.effective_date,
            expiry_date=req.expiry_date,
            certificate_holder=req.certificate_holder,
            policy_admin_reference=quote_ref,
        )
    except Exception as exc:
        logger.warning("Issuance package generation failed for %s: %s", bundle_id, exc)
        issuance = None

    # ── Step 6: begin ongoing policy monitoring on the in-force policy ──
    try:
        from insureflow.monitoring.engine import MonitoringEngine

        policy_id = f"pol-{policy_number or bundle_id}"
        MonitoringEngine().seed_from_issuance(
            bundle_id,
            current.org_id,
            policy_id=policy_id,
            policy_number=policy_number,
            insured_name=str(summary.get("insured_name") or ""),
            line_of_business=str(summary.get("insurance_line") or ""),
            premium=float(bound_premium or 0),
            tiv=tiv,
            effective_date=issuance.effective_date if issuance else (req.effective_date or ""),
            expiry_date=issuance.expiry_date if issuance else (req.expiry_date or ""),
        )
    except Exception as exc:
        logger.warning("Policy monitoring seeding failed for %s: %s", bundle_id, exc)

    # ── Step 5a: notify the producer that coverage is in force ──
    try:
        from insureflow.insurance.notifications import ProducerNotificationService

        ProducerNotificationService().notify_bound(
            bundle_id,
            current.org_id,
            policy_number=policy_number,
            bound_by=current.username or "",
            premium=float(bound_premium or 0),
            producer_name=str(summary.get("broker_name") or ""),
        )
    except Exception as exc:
        logger.warning("Producer bind notification failed for %s: %s", bundle_id, exc)

    return {
        "bind": bind_result,
        "workflow": record.model_dump(),
        "outcome": outcome.model_dump(),
        "issuance": issuance.model_dump(mode="json") if issuance else None,
        "monitoring_policy_id": f"pol-{policy_number or bundle_id}",
    }


class CoSignResolveRequest(BaseModel):
    approve: bool = True
    notes: str = ""


@app.post("/pipeline/workflow/{bundle_id}/co-sign")
@limiter.limit("20/minute")
def resolve_workflow_cosign(
    bundle_id: str,
    req: CoSignResolveRequest,
    request: Request,
    current: TokenData = Depends(require_role(Role.LICENSED_UW)),
) -> dict[str, Any]:
    """Approve or reject a pending co-sign request (must be higher tier than requester)."""
    from insureflow.workflow.service import WorkflowService

    wf = WorkflowService()
    try:
        record = wf.resolve_cosign_request(
            bundle_id,
            current.org_id,
            signer_username=current.username or "",
            approve=req.approve,
            notes=req.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"workflow": record.model_dump(mode="json"), "co_sign": record.metadata.get("co_sign")}


@app.get("/pipeline/workflow/{bundle_id}/co-sign")
def get_workflow_cosign(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.workflow.service import WorkflowService

    record = WorkflowService().store.get(bundle_id, current.org_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"bundle_id": bundle_id, "state": record.state.value, "co_sign": record.metadata.get("co_sign")}


# ── Issuance: binder / policy worksheet / certificate of insurance (Step 5b) ──


@app.get("/pipeline/issuance")
def list_all_issuance(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """List every issued coverage package for the current org."""
    from insureflow.issuance.service import IssuanceService

    return {"records": [r.model_dump(mode="json") for r in IssuanceService().list_records(current.org_id)]}


@app.get("/pipeline/issuance/{bundle_id}")
def list_issuance_documents(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """List issued coverage documents for a bound policy."""
    from insureflow.issuance.service import IssuanceService

    svc = IssuanceService()
    record = svc.load_record(bundle_id, current.org_id)
    if not record:
        raise HTTPException(status_code=404, detail="No issuance package for this bundle — has it been bound?")
    return record.model_dump(mode="json")


@app.get("/pipeline/issuance/{bundle_id}/{doc_type}")
def download_issuance_document(
    bundle_id: str,
    doc_type: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> StreamingResponse:
    """Download an issued document (binder | policy_worksheet | certificate) as PDF/HTML."""
    from insureflow.issuance.service import IssuanceService

    result = IssuanceService().get_document_html(bundle_id, current.org_id, doc_type)
    if not result:
        raise HTTPException(status_code=404, detail=f"No issued {doc_type!r} document available")
    doc, _ = result
    try:
        from insureflow.rating.report_document import html_to_pdf

        pdf_bytes = html_to_pdf(doc.html)
        is_pdf = pdf_bytes[:4] == b"%PDF"
        media_type = "application/pdf" if is_pdf else "text/html"
        ext = "pdf" if is_pdf else "html"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Issuance document rendering failed: {exc}") from exc
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename.rsplit(".", 1)[0]}.{ext}"'},
    )


# ── Producer decision notifications (Step 5a) ──


@app.get("/pipeline/notifications")
def list_all_producer_notifications(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Every UW→producer decision communication logged for the current org."""
    from insureflow.insurance.notifications import ProducerNotificationStore

    return {"notifications": ProducerNotificationStore().list_all(current.org_id)}


@app.get("/pipeline/notifications/{bundle_id}")
def list_producer_notifications(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.insurance.notifications import ProducerNotificationStore

    return {
        "bundle_id": bundle_id,
        "notifications": ProducerNotificationStore().list_notifications(bundle_id, current.org_id),
    }


class AcknowledgeNotificationRequest(BaseModel):
    acknowledged_by: str = "broker"


@app.post("/pipeline/notifications/{bundle_id}/acknowledge", status_code=200)
def acknowledge_producer_notification(
    bundle_id: str,
    notification_id: str,
    req: AcknowledgeNotificationRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Record broker acknowledgement of a communicated underwriting decision."""
    from insureflow.insurance.notifications import ProducerNotificationStore

    try:
        notification = ProducerNotificationStore().mark_acknowledged(bundle_id, current.org_id, notification_id, acknowledged_by=req.acknowledged_by)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return notification


# ── Ongoing policy monitoring (Step 6) ──


class AddMonitoringItemRequest(BaseModel):
    title: str
    description: str = ""
    severity: str = "moderate"  # low | moderate | high | critical
    source: str = "manual"  # uw_memo | loss_development | expiry | renewal | manual
    due_by: str = ""
    bundle_id: str = ""


class ResolveMonitoringItemRequest(BaseModel):
    status: str = "cleared"  # cleared | waived
    resolved_by: str = ""
    note: str = ""


class RecordLossDevelopmentRequest(BaseModel):
    policy_year: int = 0
    earned_premium: float = 0.0
    incurred_losses: float = 0.0
    paid_losses: float = 0.0
    claim_count: int = 0
    recorded_by: str = "system"


@app.get("/monitoring/policies")
def list_monitoring_policies(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.monitoring.engine import MonitoringEngine

    return {"policies": MonitoringEngine().list_monitoring(current.org_id)}


@app.get("/monitoring/alerts")
def list_monitoring_alerts(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.monitoring.engine import MonitoringEngine

    return {"alerts": MonitoringEngine().list_open_alerts(current.org_id)}


@app.post("/monitoring/evaluate")
def evaluate_monitoring(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Re-evaluate all monitored policies for overdue items / renewal windows."""
    from insureflow.monitoring.engine import MonitoringEngine

    engine = MonitoringEngine()
    records = engine.evaluate_all(current.org_id)
    return {"policies": [r.to_summary_dict() for r in records], "alerts": engine.list_open_alerts(current.org_id)}


@app.get("/monitoring/policies/{policy_id}")
def get_monitoring_policy(
    policy_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.monitoring.engine import MonitoringEngine

    try:
        record = MonitoringEngine().store.get(policy_id, current.org_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not record:
        raise HTTPException(status_code=404, detail=f"No monitoring record for policy {policy_id}")
    return record.model_dump(mode="json")


@app.post("/monitoring/policies/{policy_id}/items", status_code=201)
def add_monitoring_item(
    policy_id: str,
    req: AddMonitoringItemRequest,
    current: TokenData = Depends(require_role(Role.LICENSED_UW)),
) -> dict[str, Any]:
    from insureflow.monitoring.engine import MonitoringEngine

    try:
        record = MonitoringEngine().add_item(
            policy_id,
            current.org_id,
            title=req.title,
            description=req.description,
            severity=req.severity,
            source=req.source,
            due_by=req.due_by,
            bundle_id=req.bundle_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@app.post("/monitoring/policies/{policy_id}/items/{item_id}/resolve", status_code=200)
def resolve_monitoring_item(
    policy_id: str,
    item_id: str,
    req: ResolveMonitoringItemRequest,
    current: TokenData = Depends(require_role(Role.LICENSED_UW)),
) -> dict[str, Any]:
    from insureflow.monitoring.engine import MonitoringEngine

    try:
        record = MonitoringEngine().resolve_item(
            policy_id,
            current.org_id,
            item_id,
            status=req.status,
            resolved_by=req.resolved_by or current.username or "",
            note=req.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@app.post("/monitoring/policies/{policy_id}/loss-development", status_code=201)
def record_monitoring_loss_development(
    policy_id: str,
    req: RecordLossDevelopmentRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Record realized loss experience and re-flag the monitored policy."""
    from insureflow.monitoring.engine import MonitoringEngine

    try:
        record = MonitoringEngine().record_loss_development(
            policy_id,
            current.org_id,
            policy_year=req.policy_year,
            earned_premium=req.earned_premium,
            incurred_losses=req.incurred_losses,
            paid_losses=req.paid_losses,
            claim_count=req.claim_count,
            recorded_by=req.recorded_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@app.post("/pipeline/outcomes/loss-experience", status_code=201)
def record_loss_experience(
    req: LossExperienceRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
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
    from evaluations.benchmark import seed_demo_benchmark

    seed_demo_benchmark(store)
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
                "desk": getattr(a, "desk", "line") or "line",
                "license_number": a.license_number,
                "binding_authority": {
                    "max_premium": a.binding_authority.max_premium,
                    "max_tiv": a.binding_authority.max_tiv,
                    "requires_co_sign": a.binding_authority.requires_co_sign,
                    "co_sign_threshold_premium": a.binding_authority.co_sign_threshold_premium,
                    "max_aggregate_exposure": a.binding_authority.max_aggregate_exposure,
                },
            }
            for a in matrix.list_all(org_id=current.org_id)
        ]
    }


class AuthorityRecordRequest(BaseModel):
    username: str
    display_name: str
    tier: str  # junior | senior | cuo | mga
    desk: str = "line"  # line | staff | both
    license_number: str = ""
    max_premium: float = 0.0
    max_tiv: float = 0.0
    max_aggregate_exposure: float = 0.0
    requires_co_sign: bool = False
    co_sign_threshold_premium: float = 0.0


def _build_authority_record(req: AuthorityRecordRequest) -> Any:
    from insureflow.underwriting.authority import (
        AuthorityTier,
        BindingAuthority,
        UnderwriterAuthority,
    )

    tier_value = req.tier.strip().lower()
    try:
        tier = AuthorityTier(tier_value)
    except ValueError:
        valid = ", ".join(t.value for t in AuthorityTier)
        raise HTTPException(status_code=400, detail=f"Invalid tier '{req.tier}'. Valid: {valid}")
    desk = (req.desk or "line").strip().lower()
    if desk not in ("line", "staff", "both"):
        raise HTTPException(status_code=400, detail="desk must be line, staff, or both")
    username = req.username.strip()
    if not username or not req.display_name.strip():
        raise HTTPException(status_code=400, detail="Username and display name are required")
    return UnderwriterAuthority(
        username=username,
        display_name=req.display_name.strip(),
        tier=tier,
        desk=desk,
        license_number=req.license_number.strip(),
        binding_authority=BindingAuthority(
            max_premium=req.max_premium,
            max_tiv=req.max_tiv,
            max_aggregate_exposure=req.max_aggregate_exposure,
            requires_co_sign=req.requires_co_sign,
            co_sign_threshold_premium=req.co_sign_threshold_premium,
        ),
    )


@app.post("/underwriting/authority", status_code=201)
def upsert_underwriting_authority(
    req: AuthorityRecordRequest,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Create or update an authority record (admin RBAC only)."""
    from insureflow.underwriting.authority import get_authority_matrix

    record = _build_authority_record(req)
    get_authority_matrix().upsert(record, org_id=current.org_id)
    return {
        "username": record.username,
        "tier": record.tier.value,
        "binding_authority": {
            "max_premium": record.binding_authority.max_premium,
            "max_tiv": record.binding_authority.max_tiv,
            "requires_co_sign": record.binding_authority.requires_co_sign,
            "co_sign_threshold_premium": record.binding_authority.co_sign_threshold_premium,
            "max_aggregate_exposure": record.binding_authority.max_aggregate_exposure,
        },
    }


@app.put("/underwriting/authority/{username}")
def update_underwriting_authority(
    username: str,
    req: AuthorityRecordRequest,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Update an existing authority record (admin RBAC only)."""
    from insureflow.underwriting.authority import get_authority_matrix

    matrix = get_authority_matrix()
    if matrix.get_authority(username, org_id=current.org_id) is None:
        raise HTTPException(status_code=404, detail=f"No authority record for '{username}'")
    record = _build_authority_record(req)
    matrix.upsert(record, org_id=current.org_id)
    return {
        "username": record.username,
        "tier": record.tier.value,
        "binding_authority": {
            "max_premium": record.binding_authority.max_premium,
            "max_tiv": record.binding_authority.max_tiv,
            "requires_co_sign": record.binding_authority.requires_co_sign,
            "co_sign_threshold_premium": record.binding_authority.co_sign_threshold_premium,
            "max_aggregate_exposure": record.binding_authority.max_aggregate_exposure,
        },
    }


@app.delete("/underwriting/authority/{username}", status_code=204)
def delete_underwriting_authority(
    username: str,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> None:
    """Delete an authority record (admin RBAC only)."""
    from insureflow.underwriting.authority import get_authority_matrix

    if not get_authority_matrix().remove(username, org_id=current.org_id):
        raise HTTPException(status_code=404, detail=f"No authority record for '{username}'")


# ── Line & Staff underwriter desks ───────────────────────────────


@app.get("/underwriting/desks")
def get_underwriting_desks(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Describe line vs staff underwriter desks and map the caller's role."""
    from insureflow.underwriting.roles import capabilities_overview, desk_for_role

    overview = capabilities_overview()
    desk = desk_for_role(current.role)
    return {
        **overview,
        "current_user": {
            "username": current.username,
            "role": current.role.value if current.role else None,
            "desk": desk.value,
        },
    }


class CoverageAssistRequest(BaseModel):
    applicant: str = ""
    occupancy: str = ""
    operations_description: str = ""
    requested_coverages: list[str] = []
    complex_submission: bool = False


@app.post("/underwriting/line/coverage-assist")
def line_coverage_assist(
    req: CoverageAssistRequest,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Line UW: recommend broaden / narrow / manuscript coverage actions."""
    from insureflow.underwriting.line_desk import assist_coverage

    return assist_coverage(
        applicant=req.applicant,
        occupancy=req.occupancy,
        operations_description=req.operations_description,
        requested_coverages=req.requested_coverages,
        complex_submission=req.complex_submission,
    ).to_dict()


class ServiceTicketRequest(BaseModel):
    request_type: str
    subject: str
    detail: str = ""
    requester: str = "producer"  # producer | policyholder | internal
    requester_name: str = ""
    policy_number: str = ""
    submission_id: str = ""


@app.get("/underwriting/line/service")
def list_line_service_tickets(
    status_filter: str = "",
    requester: str = "",
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Line UW: list producer / policyholder service tickets."""
    from insureflow.underwriting.line_desk import get_line_service_desk

    tickets = get_line_service_desk().list_tickets(
        org_id=current.org_id,
        status=status_filter or None,
        requester=requester or None,
    )
    return {"tickets": tickets, "count": len(tickets)}


@app.post("/underwriting/line/service", status_code=201)
def create_line_service_ticket(
    req: ServiceTicketRequest,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Line UW: open a producer or policyholder service ticket."""
    from insureflow.underwriting.line_desk import get_line_service_desk

    try:
        return get_line_service_desk().create_ticket(
            request_type=req.request_type,
            subject=req.subject,
            detail=req.detail,
            requester=req.requester,
            requester_name=req.requester_name,
            policy_number=req.policy_number,
            submission_id=req.submission_id,
            created_by=current.username or "",
            org_id=current.org_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class ServiceTicketUpdateRequest(BaseModel):
    status: str = ""
    resolution_notes: str = ""


@app.patch("/underwriting/line/service/{ticket_id}")
def update_line_service_ticket(
    ticket_id: str,
    req: ServiceTicketUpdateRequest,
    current: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    """Line UW: update service ticket status / resolution."""
    from insureflow.underwriting.line_desk import get_line_service_desk

    try:
        return get_line_service_desk().update_ticket(
            ticket_id,
            status=req.status or None,
            resolution_notes=req.resolution_notes if req.resolution_notes else None,
            org_id=current.org_id,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/underwriting/staff")
def staff_underwriting_overview(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Staff UW home-office workspace overview."""
    from insureflow.underwriting.staff_desk import get_staff_desk

    return get_staff_desk().overview(org_id=current.org_id)


@app.get("/underwriting/staff/{section}")
def staff_list_section(
    section: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """List a staff UW section (market_research, guides, audits, …)."""
    from insureflow.underwriting.staff_desk import get_staff_desk

    try:
        items = get_staff_desk().list_section(section, org_id=current.org_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=("Unknown section. Use: market_research, coverage_development, rating_reviews, guides, audits, training, policy_statements"),
        ) from None
    return {"section": section, "items": items, "count": len(items)}


class MarketResearchRequest(BaseModel):
    title: str
    topic: str = "other"
    summary: str
    recommendation: str = ""


@app.post("/underwriting/staff/market-research", status_code=201)
def staff_add_market_research(
    req: MarketResearchRequest,
    current: TokenData = Depends(require_staff_desk()),
) -> dict[str, Any]:
    from insureflow.underwriting.staff_desk import get_staff_desk

    return get_staff_desk().add_market_research(
        title=req.title,
        topic=req.topic,
        summary=req.summary,
        recommendation=req.recommendation,
        author=current.username or "",
        org_id=current.org_id,
    )


class CoverageDevelopmentRequest(BaseModel):
    title: str
    change_type: str = "form_mod"
    description: str


@app.post("/underwriting/staff/coverage-development", status_code=201)
def staff_add_coverage_development(
    req: CoverageDevelopmentRequest,
    current: TokenData = Depends(require_staff_desk()),
) -> dict[str, Any]:
    from insureflow.underwriting.staff_desk import get_staff_desk

    return get_staff_desk().add_coverage_development(
        title=req.title,
        change_type=req.change_type,
        description=req.description,
        author=current.username or "",
        org_id=current.org_id,
    )


class ExperienceEvalRequest(BaseModel):
    line_of_business: str = "commercial_property"
    class_of_business: str = ""
    territory: str = ""
    earned_premium: float = 0.0
    incurred_losses: float = 0.0
    industry_loss_ratio: float = 0.65


@app.post("/underwriting/staff/experience")
def staff_evaluate_experience(
    req: ExperienceEvalRequest,
    current: TokenData = Depends(require_staff_desk()),
) -> dict[str, Any]:
    from insureflow.underwriting.staff_desk import evaluate_experience

    return evaluate_experience(
        line_of_business=req.line_of_business,
        class_of_business=req.class_of_business,
        territory=req.territory,
        earned_premium=req.earned_premium,
        incurred_losses=req.incurred_losses,
        industry_loss_ratio=req.industry_loss_ratio,
    )


class RatingReviewRequest(BaseModel):
    line_of_business: str
    advisory_org: str = "ISO"
    summary: str
    loss_cost_change_pct: float = 0.0
    expense_load_pct: float = 0.0
    profit_load_pct: float = 0.0
    action: str = "monitor"


@app.post("/underwriting/staff/rating-plans", status_code=201)
def staff_add_rating_review(
    req: RatingReviewRequest,
    current: TokenData = Depends(require_staff_desk()),
) -> dict[str, Any]:
    from insureflow.underwriting.staff_desk import get_staff_desk

    return get_staff_desk().add_rating_review(
        line_of_business=req.line_of_business,
        advisory_org=req.advisory_org,
        summary=req.summary,
        loss_cost_change_pct=req.loss_cost_change_pct,
        expense_load_pct=req.expense_load_pct,
        profit_load_pct=req.profit_load_pct,
        action=req.action,
        author=current.username or "",
        org_id=current.org_id,
    )


class GuideRequest(BaseModel):
    title: str
    line_of_business: str
    body: str
    status: str = "draft"
    version: str = "1.0"
    guide_id: str = ""


@app.post("/underwriting/staff/guides", status_code=201)
def staff_upsert_guide(
    req: GuideRequest,
    current: TokenData = Depends(require_staff_desk()),
) -> dict[str, Any]:
    from insureflow.underwriting.staff_desk import get_staff_desk

    return get_staff_desk().upsert_guide(
        title=req.title,
        line_of_business=req.line_of_business,
        body=req.body,
        status=req.status,
        version=req.version,
        author=current.username or "",
        guide_id=req.guide_id or None,
        org_id=current.org_id,
    )


class PolicyStatementRequest(BaseModel):
    title: str
    body: str


@app.post("/underwriting/staff/policy", status_code=201)
def staff_add_policy(
    req: PolicyStatementRequest,
    current: TokenData = Depends(require_staff_desk()),
) -> dict[str, Any]:
    from insureflow.underwriting.staff_desk import get_staff_desk

    return get_staff_desk().add_policy_statement(
        title=req.title,
        body=req.body,
        author=current.username or "",
        org_id=current.org_id,
    )


class StaffAuditRequest(BaseModel):
    office: str
    scope: str = ""
    files_reviewed: int = 0
    findings: list[dict[str, Any]] = []


@app.post("/underwriting/staff/audits", status_code=201)
def staff_conduct_audit(
    req: StaffAuditRequest,
    current: TokenData = Depends(require_staff_desk()),
) -> dict[str, Any]:
    from insureflow.underwriting.staff_desk import get_staff_desk

    return get_staff_desk().conduct_audit(
        office=req.office,
        auditor=current.username or "staff",
        scope=req.scope,
        files_reviewed=req.files_reviewed,
        findings=req.findings,
        org_id=current.org_id,
    )


class TrainingRequest(BaseModel):
    title: str
    topic: str = "technical_insurance"
    audience: str = "line_uw"
    outline: str


@app.post("/underwriting/staff/training", status_code=201)
def staff_add_training(
    req: TrainingRequest,
    current: TokenData = Depends(require_staff_desk()),
) -> dict[str, Any]:
    from insureflow.underwriting.staff_desk import get_staff_desk

    return get_staff_desk().add_training(
        title=req.title,
        topic=req.topic,
        audience=req.audience,
        outline=req.outline,
        author=current.username or "",
        org_id=current.org_id,
    )


@app.post("/pipeline/renewal/{bundle_id}")
def analyze_renewal(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Audits with material adjustments needing UW review."""
    engine = _get_audit_engine()
    audits = engine.audits_needing_renewal_review(org_id=current.org_id)
    return {"audits": [a.__dict__ for a in audits], "total": len(audits)}


@app.get("/pipeline/documents/{bundle_id}/missing")
def get_missing_documents(
    bundle_id: str,
    current: TokenData | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Get list of missing documents for a submission."""
    org_id = current.org_id if current and current.org_id else "demo"

    from insureflow.agents.triage_agent import DocumentChecklist, TriageAgent

    checklist: DocumentChecklist | None = None
    line_hint = ""

    from insureflow.audit.store import AuditStore

    store = AuditStore()
    bundle_data = store.load_json(bundle_id, "submission_bundle.json", org_id=org_id)

    if not bundle_data:
        bundle_data = store.load_json(bundle_id, "submission_bundle.json")

    job_data = job_store.get(INSURANCE_NS, bundle_id, org_id=org_id) or job_store.get(INSURANCE_NS, bundle_id) or {}
    results = (job_data or {}).get("results") or {}
    line_hint = str(results.get("insurance_line") or results.get("product_line") or "")
    cached = results.get("document_checklist")
    if isinstance(cached, dict) and (cached.get("missing_documents") is not None or cached.get("lob")):
        return {
            "bundle_id": bundle_id,
            "lob": cached.get("lob") or line_hint or "property",
            "completeness_pct": cached.get("completeness_pct", 0),
            "missing_documents": cached.get("missing_documents") or [],
            "present_documents": cached.get("present_documents") or [],
            "can_request_from_broker": bool(cached.get("missing_documents")),
        }

    if bundle_data:
        from insureflow.models.submissions import SubmissionBundle

        try:
            bundle = SubmissionBundle(**bundle_data)
            result = TriageAgent().score_submission(bundle, insurance_line=line_hint or None)
            checklist = result.document_checklist
        except Exception:
            logger.warning("Triage agent scoring failed for bundle %s, falling back to job data", bundle_id, exc_info=True)

    if checklist is None:
        doc_count = results.get("document_count", 0)
        if doc_count:
            checklist = DocumentChecklist(
                acord_form=doc_count >= 1,
                loss_run=doc_count >= 2,
                financials=doc_count >= 3,
                schedule_of_values=doc_count >= 4,
                inspection_report=doc_count >= 5,
            )
        else:
            checklist = DocumentChecklist()

    summary = (
        checklist.to_summary_dict()
        if hasattr(checklist, "to_summary_dict")
        else {
            "completeness_pct": checklist.completeness_pct,
            "missing_documents": checklist.missing,
            "present_documents": list(getattr(checklist, "present", []) or []),
            "lob": getattr(checklist, "lob", "property"),
        }
    )
    missing = summary.get("missing_documents")
    missing_list: list[Any] = missing if isinstance(missing, list) else []
    return {
        "bundle_id": bundle_id,
        **summary,
        "can_request_from_broker": len(missing_list) > 0,
    }


@app.post("/pipeline/documents/{bundle_id}/request")
def request_broker_documents(
    bundle_id: str,
    body: dict[str, Any],
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Request missing documents from broker (persisted pending → broker respond loop)."""
    from insureflow.enterprise.ecosystem import get_ecosystem_service

    docs = body.get("documents") or body.get("missing_documents") or []
    notes = str(body.get("notes") or "")
    if not docs:
        missing = get_missing_documents(bundle_id, current)
        docs = missing.get("missing_documents", [])
    result = get_ecosystem_service().request_broker_documents(bundle_id, current.org_id, docs, notes=notes)
    return result


@app.get("/pipeline/jobs/{bundle_id}/info-requests")
def list_info_requests(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.insurance.collaboration import get_collaboration_store

    items = get_collaboration_store().list_info_requests(bundle_id, current.org_id)
    return {
        "bundle_id": bundle_id,
        "requests": items,
        "pending_count": sum(1 for r in items if r.get("status") == "pending"),
    }


@app.get("/pipeline/jobs/{bundle_id}/relationship-notes")
def list_relationship_notes(
    bundle_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.insurance.collaboration import get_collaboration_store

    return {"bundle_id": bundle_id, "notes": get_collaboration_store().list_notes(bundle_id, current.org_id)}


@app.post("/pipeline/jobs/{bundle_id}/relationship-notes", status_code=201)
def add_relationship_note(
    bundle_id: str,
    body: dict[str, Any],
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.insurance.collaboration import get_collaboration_store

    note = get_collaboration_store().add_note(
        bundle_id,
        current.org_id,
        str(body.get("text") or ""),
        author=str(body.get("author") or current.username or "underwriter"),
        role=str(body.get("role") or "uw"),
    )
    return note


@app.get("/pipeline/jobs/{bundle_id}/package-checklist")
def insurance_package_checklist(
    bundle_id: str,
    lob: str = "",
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """LOB-aware completeness checklist for the submission package."""
    from insureflow.audit.store import AuditStore
    from insureflow.insurance.package_checklist import detect_lob, package_checklist

    store = AuditStore()
    summary = store.load_json(bundle_id, "underwriting_memo.json", org_id=current.org_id) or {}
    bundle = store.load_json(bundle_id, "submission_bundle.json", org_id=current.org_id) or {}
    types: list[str] = []
    for doc in bundle.get("unstructured") or bundle.get("documents") or []:
        if isinstance(doc, dict):
            t = doc.get("document_type") or doc.get("doc_type") or ""
            if t:
                types.append(str(t))
    job = job_store.get(INSURANCE_NS, bundle_id, org_id=current.org_id) or {}
    results = job.get("results") or {}
    type_counts = results.get("document_types") or {}
    if isinstance(type_counts, dict):
        types.extend(list(type_counts.keys()))
    line_hint = str(results.get("insurance_line") or results.get("product_line") or summary.get("product_line") or (results.get("quote_full") or {}).get("line") or "")
    text_blob = " ".join(types) + " " + line_hint
    # Prefer job LOB / explicit query; map personal_* aliases to catalog keys.
    from insureflow.agents.triage_agent import _line_to_lob

    if lob in ("property", "do", "homeowners", "auto", "life"):
        resolved = lob
    elif lob:
        resolved = _line_to_lob(lob)
    else:
        resolved = _line_to_lob(line_hint) if line_hint else detect_lob(text_blob, line_hint)
    # Prefer cached pipeline checklist when LOB matches (0–1 completeness from triage)
    cached = results.get("document_checklist")
    if isinstance(cached, dict) and cached.get("lob") == resolved:
        return {
            "bundle_id": bundle_id,
            "lob": resolved,
            "present": cached.get("present_documents") or cached.get("present") or [],
            "missing": cached.get("missing_documents") or cached.get("missing") or [],
            "completeness_pct": round(float(cached.get("completeness_pct") or 0) * 100, 1) if float(cached.get("completeness_pct") or 0) <= 1 else float(cached.get("completeness_pct") or 0),
            "can_request_from_broker": bool(cached.get("missing_documents") or cached.get("missing")),
        }
    checklist = package_checklist(types, lob=resolved)
    return {"bundle_id": bundle_id, **checklist}


@app.post("/pipeline/vision/analyze")
async def analyze_property_photos_endpoint(
    request: Request,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Upload and analyze property photos — quality scoring, damage detection, satellite imagery."""
    from insureflow.ml.vision.pipeline import PropertyPhotoAnalyzer

    body = await request.json()
    photos = body.get("photos", [])
    if not photos:
        raise HTTPException(status_code=400, detail="No photos provided")

    latitude = body.get("latitude")
    longitude = body.get("longitude")
    address = body.get("address", "")
    bundle_id = body.get("bundle_id", f"vision-{uuid.uuid4().hex[:12]}")

    analyzer = PropertyPhotoAnalyzer()
    profile = analyzer.analyze_photos(
        photos,
        latitude=latitude,
        longitude=longitude,
        address=address,
        bundle_id=bundle_id,
    )
    return profile.to_dict()


@app.get("/pipeline/vision/status")
def vision_status() -> dict[str, Any]:
    """Check which vision providers are configured."""
    import os

    return {
        "vision_llm": bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")),
        "satellite_imagery": bool(os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("NEARMAP_API_KEY")),
        "satellite_geocoding": True,
        "satellite_note": "Nominatim + Overpass free fallback always available. Add GOOGLE_MAPS_API_KEY for satellite imagery.",
        "vision_model": os.getenv("VISION_MODEL", "gpt-4o"),
    }


class ZtaRouteRequest(BaseModel):
    task: str
    text: Optional[str] = None
    regex_field_count: int = 0
    expected_fields: int = 0
    doc_type: str = ""
    conflict_count: int = 0
    critical_conflict_count: int = 0
    required_features_present: bool = True
    missing_required: list[str] = []
    photo_count: int = 0


@app.get("/api/zta/status")
def zta_status() -> dict[str, Any]:
    """Zero Token Architecture process-wide stats and config."""
    from insureflow.zta.config import ZtaConfig
    from insureflow.zta.report import get_zta_stats

    config = ZtaConfig()
    stats = get_zta_stats()
    stats["config"] = config.to_dict()
    stats["policy"] = "Use AI only when you must. Everything else, solve deterministically."
    return stats


@app.post("/api/zta/route")
def zta_route(payload: ZtaRouteRequest) -> dict[str, Any]:
    """Ask the ZTA router how a single pipeline task would be resolved."""
    from insureflow.zta.config import ZtaConfig
    from insureflow.zta.models import RouteContext, ZtaTask
    from insureflow.zta.report import ZtaReporter
    from insureflow.zta.router import ZeroTokenRouter

    try:
        task = ZtaTask(payload.task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown task: {payload.task}") from exc

    router = ZeroTokenRouter(config=ZtaConfig())
    reporter = ZtaReporter(router)
    result = reporter.route(
        task,
        RouteContext(
            text=payload.text,
            regex_field_count=payload.regex_field_count,
            expected_fields=payload.expected_fields,
            doc_type=payload.doc_type,
            conflict_count=payload.conflict_count,
            critical_conflict_count=payload.critical_conflict_count,
            required_features_present=payload.required_features_present,
            missing_required=list(payload.missing_required),
            photo_count=payload.photo_count,
        ),
    )
    report = reporter.report()
    return {"route": result.to_dict(), "zta_report": report}


@app.get("/pilot/sandbox-status")
def pilot_sandbox_status(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Integration readiness for carrier/MGA pilots (sandbox vs live)."""
    from insureflow.pilot.sandbox_readiness import assess_sandbox_readiness

    report = assess_sandbox_readiness(ping=True)
    report["org_id"] = current.org_id
    return report


@app.get("/pilot/packages")
def list_pilot_packages(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.pilot.package_loader import discover_pilot_packages

    packages = discover_pilot_packages()
    return {
        "count": len(packages),
        "packages": [
            {
                "partner": p.partner,
                "submission_id": p.submission_id,
                "path": str(p.path),
                "insured_name": p.insured_name,
                "has_acord": bool(p.acord_xml),
                "has_loss_run": bool(p.loss_run),
                "has_sov": bool(p.schedule_of_values),
                "inspection_count": len(p.inspection_reports),
                "meta": p.meta,
            }
            for p in packages
        ],
    }


class PilotRunRequest(BaseModel):
    partner: str
    submission_id: str
    use_llm: bool = False


@app.post("/pilot/packages/run", status_code=202)
async def run_pilot_package_api(
    req: PilotRunRequest,
    background_tasks: BackgroundTasks,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.pilot.package_loader import discover_pilot_packages
    from insureflow.pilot.pii_gate import scan_pilot_package

    match = next(
        (p for p in discover_pilot_packages() if p.partner == req.partner and p.submission_id == req.submission_id),
        None,
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Pilot package not found — drop files under pilot_packages/")

    scan = scan_pilot_package(match)
    if not scan["ok_to_run"]:
        raise HTTPException(status_code=400, detail={"message": scan["message"], "pii": scan})

    job_id = f"pilot-{uuid.uuid4().hex[:12]}"
    job_store.set(INSURANCE_NS, job_id, {"status": "processing", "pilot": True}, org_id=current.org_id)

    def _task() -> None:
        from insureflow.pilot.package_loader import run_pilot_package

        try:
            result = run_pilot_package(match, org_id=current.org_id, use_llm=req.use_llm)
            job_store.set(INSURANCE_NS, job_id, {"status": "completed", **result}, org_id=current.org_id)
        except Exception as exc:
            logger.exception("Pilot package run failed")
            job_store.set(
                INSURANCE_NS,
                job_id,
                {"status": "failed", "error": str(exc)},
                org_id=current.org_id,
            )

    background_tasks.add_task(_task)
    return {
        "job_id": job_id,
        "status": "processing",
        "partner": req.partner,
        "submission_id": req.submission_id,
        "pii": scan,
    }


@app.get("/pilot/packages/{partner}/{submission_id}/pii")
def scan_pilot_pii(
    partner: str,
    submission_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.pilot.package_loader import discover_pilot_packages
    from insureflow.pilot.pii_gate import scan_pilot_package

    match = next(
        (p for p in discover_pilot_packages() if p.partner == partner and p.submission_id == submission_id),
        None,
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Pilot package not found")
    return scan_pilot_package(match)


class PilotRedactRequest(BaseModel):
    partner: str
    submission_id: str
    inplace: bool = False


@app.post("/pilot/packages/redact")
def redact_pilot_package_api(
    req: PilotRedactRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Auto-redact blocking PII in a pilot package (copy or inplace)."""
    from insureflow.pilot.auto_redact import redact_pilot_package
    from insureflow.pilot.package_loader import discover_pilot_packages

    match = next(
        (p for p in discover_pilot_packages() if p.partner == req.partner and p.submission_id == req.submission_id),
        None,
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Pilot package not found")
    return redact_pilot_package(match, inplace=req.inplace)


class PilotEmailIngestRequest(BaseModel):
    partner: str = "email"
    limit: int = 10
    unread_only: bool = True
    auto_redact: bool = True


@app.post("/pilot/ingest/email")
def ingest_pilot_email_api(
    req: PilotEmailIngestRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Pull IMAP attachments into pilot_packages/ and optionally auto-redact."""
    from insureflow.pilot.email_intake import ingest_imap_to_pilot

    result = ingest_imap_to_pilot(
        partner=req.partner,
        unread_only=req.unread_only,
        limit=max(1, min(req.limit, 50)),
        auto_redact=req.auto_redact,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "IMAP ingest failed")
    return result


@app.post("/pilot/calibrate")
def calibrate_pilot_batch(
    current: TokenData = Depends(require_role(Role.VIEWER)),
    use_llm: bool = False,
) -> dict[str, Any]:
    from insureflow.pilot.calibration import run_batch_calibration
    from insureflow.pilot.package_loader import discover_pilot_packages

    packages = discover_pilot_packages()
    if not packages:
        raise HTTPException(status_code=404, detail="No pilot packages found — run: python cli.py pilot seed")
    return run_batch_calibration(packages, org_id=current.org_id, use_llm=use_llm)


@app.get("/pilot/calibration")
def get_pilot_calibration(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.pilot.calibration import PilotCalibrationStore

    return PilotCalibrationStore().summarize()


@app.post("/pilot/seed")
def seed_pilot_packages_api(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.pilot.package_loader import export_scenario_as_pilot_package
    from insureflow.testing.realworld_scenarios import build_all_scenarios

    if _posture().is_hardened:
        raise HTTPException(status_code=403, detail="Demo seed disabled in BANK_MODE/production")
    dest_root = PROJECT_ROOT / "pilot_packages" / "demo"
    dest_root.mkdir(parents=True, exist_ok=True)
    exported = []
    for scenario in build_all_scenarios():
        out = export_scenario_as_pilot_package(scenario.id, dest_root / scenario.id)
        exported.append(str(out))
    return {"seeded": len(exported), "paths": exported}


@app.post("/pilot/calibration/human")
def record_pilot_human_decision(
    body: dict[str, Any],
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Record licensed-UW decision vs AI for override-rate tracking."""
    from insureflow.pilot.calibration import PilotCalibrationStore, PilotRunRecord

    ai = str(body.get("ai_decision") or "").lower()
    human = str(body.get("human_decision") or "").lower()
    if not ai or not human:
        raise HTTPException(status_code=400, detail="ai_decision and human_decision required")
    expected = body.get("expected_decision")
    row = PilotRunRecord(
        partner=str(body.get("partner") or "manual"),
        submission_id=str(body.get("submission_id") or body.get("bundle_id") or "unknown"),
        bundle_id=str(body.get("bundle_id") or ""),
        ai_decision=ai,
        expected_decision=str(expected).lower() if expected else None,
        human_decision=human,
        decision_match=(ai == str(expected).lower()) if expected else None,
        override=human != ai,
        notes=str(body.get("notes") or f"recorded_by={current.username}"),
    )
    store = PilotCalibrationStore()
    store.record(row)
    return {"recorded": True, "override": row.override, "summary": store.summarize()}


@app.get("/pipeline/ecosystem/status")
def ecosystem_status(
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.integrations.health import IntegrationHealthService
    from insureflow.pilot.sandbox_readiness import assess_sandbox_readiness, is_shadow_mode

    status = IntegrationHealthService().check_all(current.org_id)
    readiness = assess_sandbox_readiness(ping=False)
    status["pilot"] = {
        "overall": readiness["overall"],
        "shadow_mode": is_shadow_mode(),
        "required_ready": readiness["required_ready"],
        "required_total": readiness["required_total"],
    }
    return status


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
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    from insureflow.enterprise.ecosystem import get_ecosystem_service

    notes = (body or {}).get("notes", "")
    return get_ecosystem_service().loss_control_dispatch(bundle_id, current.org_id, notes)


@app.post("/pipeline/checkpoints/{bundle_id}/{checkpoint_id}")
def resolve_checkpoint(
    bundle_id: str,
    checkpoint_id: str,
    body: dict[str, Any],
    current: TokenData = Depends(require_role(Role.LICENSED_UW)),
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
    from insureflow.rating.models import PERSONAL_LINES, InsuranceLine
    from insureflow.rating.personal.manuals import auto_manual, homeowners_manual, life_manual, life_medical_guide

    filings = []
    for loader, line_id in (
        (homeowners_manual, "personal_homeowners"),
        (auto_manual, "personal_auto"),
        (life_manual, "life"),
    ):
        try:
            m = loader()
            filings.append(
                {
                    "line": line_id,
                    "filing_id": m.get("filing_id"),
                    "product": m.get("product"),
                    "serff_tracking": m.get("serff_tracking"),
                    "effective_date": m.get("effective_date"),
                    "expiration_date": m.get("expiration_date"),
                    "carrier": m.get("carrier"),
                }
            )
        except Exception:
            continue
    try:
        med = life_medical_guide()
        filings.append(
            {
                "line": "life_medical",
                "filing_id": med.get("guide_id"),
                "product": med.get("product"),
                "serff_tracking": med.get("serff_tracking"),
                "effective_date": med.get("effective_date"),
                "version": med.get("version"),
            }
        )
    except Exception:
        pass

    return {
        "lines": [
            {
                "id": line.value,
                "base_rate_per_100": ISO_LOSS_COSTS.get(line, 0.0),
                "personal": line in PERSONAL_LINES,
            }
            for line in InsuranceLine
        ],
        "filings": filings,
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
    # Raw application intake (parity with mortgage/insurance)
    documents: Optional[list[InsuranceDocumentPayload]] = None
    directory: Optional[str] = None
    require_documents: bool = False


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

    def on_progress(data: dict[str, Any]) -> None:
        job_store.set(
            MORTGAGE_NS,
            job_id,
            {"status": "processing", "progress": data},
            org_id=org_id,
        )

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
                progress_callback=on_progress,
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
                progress_callback=on_progress,
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
        docs = [{"filename": d.filename, "content": d.content, "encoding": d.encoding} for d in request.documents]
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    job_id = req.bundle_id or f"mortgage-job-{uuid.uuid4().hex[:12]}"
    job_store.set(MORTGAGE_NS, job_id, {"status": "processing"}, org_id=current.org_id)

    from insureflow.tasks.dispatch import should_use_celery

    use_celery = should_use_celery(req.use_celery)
    if use_celery:
        background_tasks.add_task(_dispatch_mortgage_celery, job_id, req, current.org_id)
    else:
        background_tasks.add_task(_run_mortgage_task, job_id, req, current.org_id)

    return {
        "job_id": job_id,
        "status": "processing",
        "org_id": current.org_id,
        "per_borrower": req.per_borrower,
        "use_llm": req.use_llm,
        "use_celery": use_celery,
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
def list_webhooks(current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
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
    from insureflow.insurance.collaboration import get_collaboration_store
    from insureflow.webhooks.dispatcher import webhook_dispatcher

    share = webhook_dispatcher.get_broker_share(token)
    if not share:
        raise HTTPException(status_code=404, detail="Invalid or expired broker status link")

    job = job_store.get(INSURANCE_NS, share.bundle_id, org_id=share.org_id)
    if not job:
        job = job_store.get(MORTGAGE_NS, share.bundle_id, org_id=share.org_id)

    status = (job or {}).get("status", "unknown")
    results = (job or {}).get("results") or {}
    collab = get_collaboration_store()
    info_requests = collab.list_info_requests(share.bundle_id, share.org_id)
    pending = [r for r in info_requests if r.get("status") == "pending"]

    return {
        "bundle_id": share.bundle_id,
        "status": status,
        "broker_name": share.broker_name,
        "vertical": "insurance" if job_store.get(INSURANCE_NS, share.bundle_id, org_id=share.org_id) else "mortgage",
        "decision": results.get("ai_decision") or ((results.get("memo") or {}).get("decision") if isinstance(results, dict) else None),
        "workflow_state": results.get("workflow_state", ""),
        "estimated_completion": None,
        "last_updated": (job or {}).get("updated_at", ""),
        "info_requests": info_requests,
        "pending_info_requests": pending,
        "awaiting_broker_info": len(pending) > 0,
    }


@app.post("/broker/status/{token}/respond")
def broker_respond_info_request(
    token: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Broker responds to a pending info request via share token (no login)."""
    from insureflow.insurance.collaboration import get_collaboration_store
    from insureflow.webhooks.dispatcher import webhook_dispatcher

    share = webhook_dispatcher.get_broker_share(token)
    if not share:
        raise HTTPException(status_code=404, detail="Invalid or expired broker status link")

    request_id = str(body.get("request_id") or "")
    note = str(body.get("response_note") or body.get("notes") or "")
    mark_all = bool(body.get("mark_all_pending"))
    try:
        updated = get_collaboration_store().respond_info_request(
            share.bundle_id,
            share.org_id,
            request_id,
            response_note=note,
            responded_by=str(body.get("responded_by") or share.broker_name or "broker"),
            mark_all_pending=mark_all or not request_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    get_collaboration_store().add_note(
        share.bundle_id,
        share.org_id,
        note or f"Broker fulfilled info request {updated.get('request_id')}",
        author=str(body.get("responded_by") or share.broker_name or "broker"),
        role="broker",
    )
    return {"status": "fulfilled", "request": updated}


class BrokerShareRequest(BaseModel):
    broker_name: str = ""
    broker_email: str = ""


@app.post("/pipeline/jobs/{bundle_id}/broker-share")
def create_broker_share(
    bundle_id: str,
    req: BrokerShareRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
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
    """List source connectors (Connect & pull hubs) plus core system adapters.

    ``adapters`` reflects the same connectors available in the insurance /
    mortgage / lending "Connect & pull" hubs, annotated with the live
    connected state from the persisted connections registry.
    """
    from insureflow.ingestion.insurance.sources import list_sources
    from insureflow.integration.britecore_adapter import BriteCoreAdapter
    from insureflow.integration.guidewire_adapter import GuidewireAdapter
    from insureflow.integrations.connections import list_connections

    conns = list_connections(current.org_id)
    adapters: list[dict[str, Any]] = []
    for s in list_sources(EXAMPLES_DIR):
        if s["type"] == "library":
            continue  # demo packages are sample data, not adapters
        source_id = str(s["id"])
        entry = conns.get(source_id)
        adapters.append(
            {
                "id": source_id,
                "name": s["name"],
                "type": s["type"],
                "category": s["category"],
                "description": s["description"],
                "config_fields": s.get("config_fields", []),
                "connected": source_id in conns,
                "connection_label": (entry or {}).get("label"),
                "status": "connected" if source_id in conns else "ready",
            }
        )

    britecore = BriteCoreAdapter(api_key=os.getenv("BRITECORE_API_KEY", ""))
    guidewire = GuidewireAdapter(api_key=os.getenv("GUIDEWIRE_API_KEY", ""))

    return {
        "adapters": adapters,
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
        ],
    }


class ConnectionRequest(BaseModel):
    config: dict[str, Any] = {}
    vertical: str = "insurance"


@app.post("/api/connections/{source_id}")
def connect_source(
    source_id: str,
    req: ConnectionRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Validate a source connector config and register the connection.

    Uses the same pull path as the Connect & pull hubs (without accumulating
    into a bundle), so any connector that works there connects here too.
    """
    pull_req = InsuranceSourcePullRequest(**req.config)
    result = pull_insurance_source(source_id, pull_req, current, vertical=req.vertical)
    return {
        "source_id": source_id,
        "connected": True,
        "connection_label": result.get("connection_label") or source_id,
        "file_count": result.get("file_count", 0),
        "simulated": result.get("simulated", False),
    }


@app.delete("/api/connections/{source_id}")
def disconnect_source(
    source_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, str]:
    from insureflow.integrations.connections import remove_connection

    remove_connection(source_id, org_id=current.org_id)
    return {"source_id": source_id, "connected": "false"}


class ConnectedPullRequest(BaseModel):
    bundle_id: Optional[str] = None
    vertical: str = "insurance"


@app.post("/api/connections/{source_id}/pull")
def pull_connected_source(
    source_id: str,
    req: ConnectedPullRequest,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Pull from an already-connected source using its stored config.

    Lets any vertical (e.g. Lending) pull from a connector the user connected
    in Integrations without re-entering credentials. Documents accumulate into
    ``bundle_id`` if provided.
    """
    from insureflow.integrations.connections import get_connection

    conn = get_connection(source_id, org_id=current.org_id)
    if not conn:
        raise HTTPException(
            status_code=404,
            detail=f"'{source_id}' is not connected — connect it from the Integrations page first",
        )
    cfg = conn.get("config") or {}
    allowed = set(InsuranceSourcePullRequest.model_fields)
    pull_req = InsuranceSourcePullRequest(
        **{k: v for k, v in cfg.items() if k in allowed and v is not None},
        bundle_id=req.bundle_id,
    )
    return pull_insurance_source(source_id, pull_req, current, vertical=req.vertical)


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
    funnel: bool = False
    skip_appetite_filter: bool = False
    skip_oracles: bool = False
    skip_portfolio: bool = False
    skip_reinsurance: bool = False
    skip_core_integration: bool = False
    create_broker_share: bool = False


@app.post("/pipeline/v2/run", status_code=202)
async def run_pipeline_v2(
    req: PipelineConfigRequest,
    background_tasks: BackgroundTasks,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Enhanced pipeline run with appetite filter, oracles, portfolio, and core integration."""
    if _posture().is_hardened and any(
        [
            req.skip_appetite_filter,
            req.skip_oracles,
            req.skip_portfolio,
            req.skip_reinsurance,
            req.skip_core_integration,
        ]
    ):
        raise HTTPException(
            status_code=403,
            detail="Pipeline skip flags are disabled in BANK_MODE/production",
        )
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
            funnel=request.funnel,
            skip_appetite_filter=request.skip_appetite_filter,
            skip_oracles=request.skip_oracles,
            skip_portfolio=request.skip_portfolio,
            skip_reinsurance=request.skip_reinsurance,
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


class DeepDiveRequest(BaseModel):
    """Select which deferred analyses to re-run for a completed submission."""

    include: list[str] = ["oracles", "portfolio", "selection_standards", "producer_experience", "adverse_selection", "reinsurance", "fraud_ml", "premium_ml", "churn_ml"]


@app.post("/pipeline/{bundle_id}/deep-dive")
def insurance_deep_dive(
    bundle_id: str,
    req: DeepDiveRequest | None = None,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Re-run funnel-deferred analyses (oracles, portfolio, reinsurance, ML) on a persisted submission."""
    from insureflow.insurance.pipeline import InsurancePipeline

    try:
        pipeline = InsurancePipeline(org_id=current.org_id, use_llm=False)
        return pipeline.deep_dive(bundle_id, org_id=current.org_id, include=(req.include if req else None))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Deep dive failed for %s", bundle_id)
        raise HTTPException(status_code=500, detail=f"Deep dive failed: {exc}") from exc


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
    current: TokenData = Depends(require_role(Role.VIEWER)),
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Run lending underwriting for a business or consumer loan application.

    Accepts structured fields and/or raw documents / a directory of applications.
    """
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

    doc_payloads: list[dict[str, Any]] = []
    loaded_docs = None
    app: Any
    try:
        if req.directory:
            from insureflow.ingestion.lending import (
                application_from_documents,
                load_lending_documents_from_directory,
            )

            loaded_docs = load_lending_documents_from_directory(req.directory)
            if not loaded_docs:
                raise HTTPException(status_code=400, detail=f"No readable documents in {req.directory}")
            doc_payloads = [{"filename": d.filename, "content": d.content, "document_type": d.document_type.value} for d in loaded_docs]
            overrides = {
                "amount": req.amount,
                "term_months": req.term_months,
                "business_name": req.business_name,
                "annual_revenue": req.revenue,
                "net_income": req.net_income,
                "ebitda": req.ebitda,
                "debt_service": req.debt_service,
                "total_assets": req.total_assets,
                "total_liabilities": req.total_liabilities,
                "annual_income": req.annual_income,
                "credit_score": req.credit_score,
                "years_in_business": req.years_in_business,
            }
            app = application_from_documents(
                loaded_docs,
                product_type=pt,
                purpose=purp,
                is_business=is_business,
                overrides=overrides,
            )
        elif req.documents:
            from insureflow.ingestion.lending import (
                application_from_documents,
                load_lending_documents_from_payloads,
            )

            payloads = [{"filename": d.filename, "content": d.content} for d in req.documents]
            loaded_docs = load_lending_documents_from_payloads(payloads)
            doc_payloads = payloads
            overrides = {
                "amount": req.amount,
                "term_months": req.term_months,
                "business_name": req.business_name,
                "annual_revenue": req.revenue,
                "net_income": req.net_income,
                "ebitda": req.ebitda,
                "debt_service": req.debt_service,
                "total_assets": req.total_assets,
                "total_liabilities": req.total_liabilities,
                "annual_income": req.annual_income,
                "credit_score": req.credit_score,
                "years_in_business": req.years_in_business,
            }
            app = application_from_documents(
                loaded_docs,
                product_type=pt,
                purpose=purp,
                is_business=is_business,
                overrides=overrides,
            )
        else:
            if is_business:
                from insureflow.lending.models import Collateral

                biz_fin = BusinessFinancialData(
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
                    financials=[biz_fin],
                    collateral=coll,
                )
            else:
                consumer_fin = ConsumerFinancialData(
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
                    financial_data=consumer_fin,
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Lending intake failed")
        raise HTTPException(status_code=400, detail=f"Lending document intake failed: {exc}") from exc

    pipeline = LendingPipeline()
    result = pipeline.run(
        app,
        documents=doc_payloads or None,
        require_documents=req.require_documents or bool(req.directory or req.documents),
    )
    timeline: list[Any] = []
    try:
        stored = job_store.get(LENDING_NS, app.application_id, org_id=current.org_id)
        if stored:
            timeline = list((stored.get("audit") or stored).get("timeline") or [])
    except Exception:
        timeline = []
    return {
        "result": result.model_dump(mode="json"),
        "application_id": app.application_id,
        "documents_ingested": len(doc_payloads),
        "extracted_from_docs": bool(loaded_docs),
        "timeline": timeline,
    }


@app.get("/lending/pipeline/result/{application_id}")
def get_lending_result(
    application_id: str,
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    import json

    # Prefer durable job store (survives restart)
    stored = job_store.get(LENDING_NS, application_id, org_id=current.org_id)
    if stored:
        return stored.get("audit") or stored

    audit_path = str(PROJECT_ROOT / "audit_logs" / "lending")
    if os.path.isdir(audit_path):
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
    current: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Pipeline run with enforced org isolation — jobs always scoped to caller's org."""
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    job_store.set(INSURANCE_NS, job_id, {"status": "processing"}, org_id=current.org_id)
    from insureflow.tasks.dispatch import send_pipeline_task, should_use_celery

    if should_use_celery(False):
        try:
            celery_task_id = send_pipeline_task(job_id, req.model_dump(), current.org_id)
        except Exception as exc:
            logger.warning("Celery dispatch failed for job %s, falling back to in-process: %s", job_id, exc)
            celery_task_id = None
    else:
        celery_task_id = None
    if celery_task_id:
        job_store.set(
            INSURANCE_NS,
            job_id,
            {"status": "processing", "backend": "celery", "celery_task_id": celery_task_id},
            org_id=current.org_id,
        )
    else:
        background_tasks.add_task(_run_pipeline_task, job_id, req, current.org_id)
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
@limiter.limit("20/minute")
def sign_off_v2(
    bundle_id: str,
    req: dict[str, Any],
    request: Request,
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
    try:
        result = svc.sign_off(
            bundle_id=bundle_id,
            org_id=current.org_id,
            action=action,
            signed_by=current.username or "",
            license_number=req.get("license_number", ""),
            notes=req.get("notes", ""),
            override_reason=req.get("override_reason", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _notify_job_subscribers(bundle_id, {"type": "workflow_update", "state": result.state.value})
    return result.model_dump(mode="json")


# ── ML Predictive Analytics Endpoints ──────────────────────────


@app.get("/ml/status")
def ml_status(current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    """ML module status — all models, versions, and metrics."""
    from insureflow.ml.training import get_training_status

    return get_training_status()


@app.post("/ml/train")
def ml_train_all(
    allow_synthetic: bool = False,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Train or retrain all ML models from ml_data/*.csv (synthetic off by default)."""
    from insureflow.ml.seed_datasets import ensure_training_csvs
    from insureflow.ml.training import get_training_status, train_all_models

    if not allow_synthetic:
        ensure_training_csvs()
    results = train_all_models(force=True, allow_synthetic=allow_synthetic)
    status = get_training_status()
    return {
        "trained": len(results),
        "results": [r.model_dump() for r in results],
        "datasets": status.get("datasets"),
        "history_tail": (status.get("history") or [])[-len(results) :],
        "allow_synthetic": allow_synthetic,
    }


@app.post("/ml/export-training")
def ml_export_training(
    model_type: str = "loss_prediction",
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Build ml_data/*.csv from persisted insurance/lending audit outcomes."""
    from insureflow.ml.export_training import export_from_audit_logs

    return export_from_audit_logs(model_type=model_type)


@app.post("/ml/train/{model_type}")
def ml_train_single(
    model_type: str,
    allow_synthetic: bool = False,
    current: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Retrain a single ML model from CSV when present (synthetic off by default)."""
    from insureflow.ml.models import ModelType as ModelTypeEnum
    from insureflow.ml.seed_datasets import ensure_training_csvs
    from insureflow.ml.training import retrain_model

    try:
        mt = ModelTypeEnum(model_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid model type: {model_type}. Valid: {[e.value for e in ModelTypeEnum]}")

    if not allow_synthetic:
        ensure_training_csvs()
    try:
        result = retrain_model(mt, allow_synthetic=allow_synthetic)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=400, detail=f"Cannot train {model_type}")
    return result.model_dump()


@app.post("/ml/predict/loss")
def ml_predict_loss(features: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
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
def ml_predict_fraud(features: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
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
def ml_predict_premium(features: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
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
def ml_predict_churn(features: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
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


@app.post("/ml/predict/mortgage-default")
def ml_predict_mortgage_default(features: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    """Mortgage default risk — probability, delinquency band, risk factors."""
    from insureflow.ml.base import BaseMLModel
    from insureflow.ml.features import FeatureVector
    from insureflow.ml.models import ModelType
    from insureflow.ml.registry import get_ml_registry

    registry = get_ml_registry()
    model = registry.get(ModelType.MORTGAGE_DEFAULT_RISK)
    if model is None or not isinstance(model, BaseMLModel):
        raise HTTPException(status_code=503, detail="Mortgage default-risk model not available")
    fv = FeatureVector(**{k: v for k, v in features.items() if k in FeatureVector.model_fields})
    return model.predict(fv)


@app.post("/ml/predict/lending-default")
def ml_predict_lending_default(features: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    """Lending default risk — probability, risk level, recommended structure."""
    from insureflow.ml.base import BaseMLModel
    from insureflow.ml.features import FeatureVector
    from insureflow.ml.models import ModelType
    from insureflow.ml.registry import get_ml_registry

    registry = get_ml_registry()
    model = registry.get(ModelType.LENDING_DEFAULT_RISK)
    if model is None or not isinstance(model, BaseMLModel):
        raise HTTPException(status_code=503, detail="Lending default-risk model not available")
    fv = FeatureVector(**{k: v for k, v in features.items() if k in FeatureVector.model_fields})
    return model.predict(fv)


@app.post("/ml/predict/portfolio-risk")
def ml_portfolio_risk(portfolio: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
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
def ml_portfolio_stress(portfolio: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
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
def ml_score_broker(broker_data: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
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
def ml_score_submission(submission_data: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
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
def ml_list_models(current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
    """List all registered ML models with status and metrics."""
    from insureflow.ml.registry import get_ml_registry

    return {"models": get_ml_registry().get_status()}


@app.post("/ml/explain/{model_type}")
def ml_explain(model_type: str, features: dict[str, Any], current: TokenData = Depends(require_role(Role.VIEWER))) -> dict[str, Any]:
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
