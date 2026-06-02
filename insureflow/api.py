from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from insureflow.pipeline import UnderwritingPipeline

logger = logging.getLogger(__name__)

# In-memory store for demo purposes. 
# In production, this would be a database (e.g., PostgreSQL/Redis)
JOB_STORE: dict[str, dict[str, Any]] = {}

app = FastAPI(
    title="InsureFlow AI",
    description="Autonomous underwriting pipeline API",
    version="0.1.0",
)


class SubmissionRequest(BaseModel):
    acord_xml: Optional[str] = None
    inspection_reports: Optional[list[str]] = None
    supplemental_docs: Optional[list[str]] = None
    bundle_id: Optional[str] = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _run_pipeline_task(job_id: str, request: SubmissionRequest) -> None:
    """Background task that executes the heavy LangGraph orchestration."""
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
    req: SubmissionRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    JOB_STORE[job_id] = {"status": "processing"}
    background_tasks.add_task(_run_pipeline_task, job_id, req)
    return {"job_id": job_id, "status": "processing", "message": "Submission queued for processing."}


@app.get("/pipeline/jobs/{job_id}")
def get_job_status(job_id: str) -> dict[str, Any]:
    if job_id not in JOB_STORE:
        raise HTTPException(status_code=404, detail="Job not found")
    return JOB_STORE[job_id]
