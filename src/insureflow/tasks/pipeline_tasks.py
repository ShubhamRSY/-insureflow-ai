from __future__ import annotations

import logging
from typing import Any

from insureflow.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

INSURANCE_NS = "insurance"


@celery_app.task(  # type: ignore
    bind=True,
    name="insureflow.tasks.pipeline_tasks.run_pipeline",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def run_pipeline(self: Any, job_id: str, request_data: dict[str, Any], org_id: str) -> dict[str, Any]:
    from insureflow.storage.job_store import get_job_store

    job_store = get_job_store()

    try:
        from insureflow.api import SubmissionRequest

        req = SubmissionRequest(**request_data)

        pipeline: Any
        if req.use_legacy_pipeline:
            from insureflow.pipeline import UnderwritingPipeline

            pipeline = UnderwritingPipeline()
            result = pipeline.run(
                acord_xml=req.acord_xml,
                inspection_reports=req.inspection_reports,
                supplemental_docs=req.supplemental_docs,
                bundle_id=req.bundle_id or job_id,
            )
        else:
            from insureflow.insurance.pipeline import InsurancePipeline

            docs = [{"filename": d.filename, "content": d.content} for d in req.documents] if req.documents else None
            pipeline = InsurancePipeline(org_id=org_id, use_llm=req.use_llm)

            def on_progress(data: dict) -> None:
                job_store.set(
                    INSURANCE_NS,
                    job_id,
                    {"status": "processing", "progress": data},
                    org_id=org_id,
                )

            result = pipeline.run(
                acord_xml=req.acord_xml,
                inspection_reports=req.inspection_reports,
                supplemental_docs=req.supplemental_docs,
                json_payload=req.json_payload,
                loss_run=req.loss_run,
                schedule_of_values=req.schedule_of_values,
                documents=docs,
                pdf_paths=req.pdf_paths,
                bundle_id=req.bundle_id or job_id,
                progress_callback=on_progress,
            )

        job_store.set(INSURANCE_NS, job_id, {"status": "completed", "results": result}, org_id=org_id)
        return {"status": "completed", "job_id": job_id}

    except Exception as exc:
        logger.exception("Pipeline run failed for job %s", job_id)
        job_store.set(INSURANCE_NS, job_id, {"status": "failed", "error": str(exc)}, org_id=org_id)
        return {"status": "failed", "error": str(exc), "job_id": job_id}
