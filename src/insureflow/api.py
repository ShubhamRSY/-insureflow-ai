from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from insureflow.auth import Role, ROLE_HIERARCHY
from insureflow.auth.dependencies import (
    get_current_user,
    get_user_store,
    require_role,
)
from insureflow.auth.jwt import create_access_token, hash_password, verify_password
from insureflow.auth.models import LoginRequest, Token, TokenData, User, UserCreateRequest
from insureflow.pipeline import UnderwritingPipeline

logger = logging.getLogger(__name__)

JOB_STORE: dict[str, dict[str, Any]] = {}

app = FastAPI(
    title="InsureFlow AI",
    description="Autonomous underwriting pipeline API",
    version="0.1.0",
)


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
    )
    return {"message": f"Admin '{admin.username}' created"}


@app.post("/auth/login")
def login(req: LoginRequest) -> Token:
    store = get_user_store()
    user = store.get(req.username)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )
    token = create_access_token(
        data={"sub": user.username, "role": user.role.value}
    )
    return Token(access_token=token)


@app.post("/auth/users", status_code=201)
def create_user(
    new_user: UserCreateRequest,
    _: TokenData = Depends(require_role(Role.ADMIN)),
) -> dict[str, str]:
    store = get_user_store()
    if new_user.username in store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )
    store[new_user.username] = User(
        username=new_user.username,
        hashed_password=hash_password(new_user.password),
        role=new_user.role,
        full_name=new_user.full_name or new_user.username,
    )
    return {"message": f"User '{new_user.username}' created with role '{new_user.role.value}'"}


@app.get("/auth/me")
def get_me(current_user: TokenData = Depends(get_current_user)) -> dict[str, str]:
    return {"username": current_user.username, "role": current_user.role.value if current_user.role else "none"}


# ── Pipeline Endpoints ──────────────────────────────────────────


class SubmissionRequest(BaseModel):
    acord_xml: Optional[str] = None
    inspection_reports: Optional[list[str]] = None
    supplemental_docs: Optional[list[str]] = None
    bundle_id: Optional[str] = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _run_pipeline_task(job_id: str, request: SubmissionRequest) -> None:
    pipeline = UnderwritingPipeline()
    try:
        result = pipeline.run(
            acord_xml=request.acord_xml,
            inspection_reports=request.inspection_reports,
            supplemental_docs=request.supplemental_docs,
            bundle_id=request.bundle_id or job_id,
        )
        JOB_STORE[job_id] = {"status": "completed", "results": result}
    except Exception as exc:
        logger.exception("Pipeline run failed")
        JOB_STORE[job_id] = {"status": "failed", "error": str(exc)}


@app.post("/pipeline/run", status_code=202)
async def run_pipeline(
    req: SubmissionRequest,
    background_tasks: BackgroundTasks,
    _: TokenData = Depends(require_role(Role.UNDERWRITER)),
) -> dict[str, Any]:
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    JOB_STORE[job_id] = {"status": "processing"}
    background_tasks.add_task(_run_pipeline_task, job_id, req)
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Submission queued for processing.",
    }


@app.get("/pipeline/jobs/{job_id}")
def get_job_status(
    job_id: str,
    _: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    if job_id not in JOB_STORE:
        raise HTTPException(status_code=404, detail="Job not found")
    return JOB_STORE[job_id]


@app.get("/pipeline/jobs")
def list_jobs(
    _: TokenData = Depends(require_role(Role.VIEWER)),
) -> dict[str, list[str]]:
    return {"jobs": list(JOB_STORE.keys())}


@app.delete("/pipeline/jobs/{job_id}", status_code=204)
def delete_job(
    job_id: str,
    _: TokenData = Depends(require_role(Role.ADMIN)),
) -> None:
    if job_id not in JOB_STORE:
        raise HTTPException(status_code=404, detail="Job not found")
    del JOB_STORE[job_id]
