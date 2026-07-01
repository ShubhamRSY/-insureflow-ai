from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from insureflow.exceptions import InsureFlowError
from insureflow.pipeline import UnderwritingPipeline

# In-memory store for demo purposes.
# In production, this would be a database (e.g., PostgreSQL/Redis)
JOB_STORE: dict[str, dict[str, Any]] = {}

app = FastAPI(
    title="InsureFlow AI Underwriting Engine",
    description="Agentic pipeline for commercial underwriting data ingestion & reconciliation",
    version="1.0.0",
)

class SubmissionRequest(BaseModel):
    acord_xml: Optional[str] = None
    inspection_reports: Optional[list[str]] = None
    supplemental_docs: Optional[list[str]] = None
    bundle_id: Optional[str] = None


def _run_pipeline_task(job_id: str, request: SubmissionRequest) -> None:
    """Background task that executes the heavy LangGraph orchestration."""
    pipeline = UnderwritingPipeline()
    try:
        results = pipeline.run(
            acord_xml=request.acord_xml,
            inspection_reports=request.inspection_reports,
            supplemental_docs=request.supplemental_docs,
            bundle_id=request.bundle_id or job_id,
        )
        JOB_STORE[job_id] = {"status": "completed", "results": results}
    except InsureFlowError as e:
        JOB_STORE[job_id] = {"status": "failed", "error": str(e)}
    except Exception as e:
        JOB_STORE[job_id] = {"status": "failed", "error": f"Internal error: {e}"}


@app.post("/api/v1/submissions/reconcile", status_code=202)
def reconcile_submission(
    request: SubmissionRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """Accepts submission data and queues it for background reconciliation."""
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    JOB_STORE[job_id] = {"status": "processing"}

    background_tasks.add_task(_run_pipeline_task, job_id, request)

    return {"job_id": job_id, "status": "processing", "message": "Submission queued for processing."}


@app.get("/api/v1/submissions/jobs/{job_id}")
def get_job_status(job_id: str) -> dict[str, Any]:
    """Check the status and retrieve results of a queued submission."""
    if job_id not in JOB_STORE:
        raise HTTPException(status_code=404, detail="Job not found")
    return JOB_STORE[job_id]
