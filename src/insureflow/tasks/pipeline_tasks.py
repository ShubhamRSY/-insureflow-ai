from __future__ import annotations

import logging
from typing import Any

from insureflow.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

INSURANCE_NS = "insurance"


def _is_infrastructure_error(exc: Exception) -> bool:
    """Redis/broker connection problems are worth a retry; pipeline errors are not."""
    try:
        import redis.exceptions as rex

        return isinstance(exc, (rex.ConnectionError, rex.TimeoutError))
    except ImportError:  # pragma: no cover - redis is a core dependency
        return False


@celery_app.task(  # type: ignore
    bind=True,
    name="insureflow.tasks.pipeline_tasks.run_pipeline",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def run_pipeline(self: Any, job_id: str, request_data: dict[str, Any], org_id: str) -> dict[str, Any]:
    from insureflow.api.job_events import publish
    from insureflow.storage.job_store import get_job_store
    from insureflow.tasks.submission_runner import run_submission

    job_store = get_job_store()

    def on_progress(data: dict[str, Any]) -> None:
        job_store.set(INSURANCE_NS, job_id, {"status": "processing", "progress": data}, org_id=org_id)
        publish(job_id, {"type": "progress", **data})

    try:
        from insureflow.api import SubmissionRequest

        req = SubmissionRequest(**request_data)
        # Same call as the in-process path (api/main.py::_run_pipeline_task).
        result = run_submission(req, job_id, org_id, progress_callback=on_progress)
        job_store.set(INSURANCE_NS, job_id, {"status": "completed", "results": result, "state_code": req.state_code}, org_id=org_id)
        publish(job_id, {"type": "status", "status": "completed", "job_id": job_id})
        return {"status": "completed", "job_id": job_id}

    except Exception as exc:
        if _is_infrastructure_error(exc) and self.request.retries < self.max_retries:
            logger.warning("Pipeline job %s hit an infrastructure error, retrying: %s", job_id, exc)
            raise self.retry(exc=exc)
        logger.exception("Pipeline run failed for job %s", job_id)
        try:
            job_store.set(INSURANCE_NS, job_id, {"status": "failed", "error": str(exc)}, org_id=org_id)
            publish(job_id, {"type": "status", "status": "failed", "job_id": job_id})
        except Exception:
            logger.exception("Could not record failure for job %s", job_id)
        return {"status": "failed", "error": str(exc), "job_id": job_id}
