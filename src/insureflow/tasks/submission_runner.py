"""The one place that turns a SubmissionRequest into a pipeline run.

The Celery task (``tasks/pipeline_tasks.py``) and the in-process fallback
(``api/main.py::_run_pipeline_task``) used to build the ``InsurancePipeline.run()``
call by hand, and the copies drifted: the Celery copy dropped each document's
``encoding`` (so base64 PDFs and ``s3_ref`` uploads were parsed as text) and
never passed ``state_code`` or the insurance company. Both paths now call
``run_submission`` so they cannot disagree again.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

ProgressCallback = Callable[[dict[str, Any]], None]


def documents_payload(documents: Optional[list[Any]]) -> list[dict[str, str]] | None:
    """Uploaded documents as the loader expects them, keeping each one's encoding."""
    if not documents:
        return None
    out: list[dict[str, str]] = []
    for d in documents:
        if isinstance(d, dict):
            filename, content, encoding = d.get("filename", ""), d.get("content", ""), d.get("encoding")
        else:
            filename, content, encoding = d.filename, d.content, getattr(d, "encoding", None)
        out.append({"filename": filename, "content": content, "encoding": encoding or "utf-8"})
    return out


def insurance_run_kwargs(req: Any, job_id: str) -> dict[str, Any]:
    """Keyword arguments for ``InsurancePipeline.run`` built from a SubmissionRequest."""
    return {
        "acord_xml": req.acord_xml,
        "inspection_reports": req.inspection_reports,
        "supplemental_docs": req.supplemental_docs,
        "json_payload": req.json_payload,
        "loss_run": req.loss_run,
        "schedule_of_values": req.schedule_of_values,
        "documents": documents_payload(req.documents),
        "pdf_paths": req.pdf_paths,
        "bundle_id": req.bundle_id or job_id,
        "insurance_line": req.insurance_line,
        "commercial_product_id": req.commercial_product_id,
        "life_product_id": req.life_product_id,
        "life_coverage_id": req.life_coverage_id,
        "health_product_id": req.health_product_id,
        "health_coverage_id": req.health_coverage_id,
        "general_product_id": req.general_product_id,
        "general_coverage_id": req.general_coverage_id,
        "commercial_coverage_id": req.commercial_coverage_id,
        "commercial_product_name": req.commercial_product_name,
        "commercial_coverage_name": req.commercial_coverage_name,
        "commercial_category_id": req.commercial_category_id,
        "insurance_company_id": req.insurance_company_id,
        "insurance_company_name": req.insurance_company_name,
        "state_code": req.state_code or "",
    }


def run_submission(req: Any, job_id: str, org_id: str, progress_callback: ProgressCallback | None = None) -> dict[str, Any]:
    """Run one insurance submission and return the pipeline result."""
    if req.use_legacy_pipeline:
        from insureflow.pipeline import UnderwritingPipeline

        return UnderwritingPipeline().run(
            acord_xml=req.acord_xml,
            inspection_reports=req.inspection_reports,
            supplemental_docs=req.supplemental_docs,
            bundle_id=req.bundle_id or job_id,
        )

    from insureflow.insurance.pipeline import InsurancePipeline

    pipeline = InsurancePipeline(org_id=org_id, use_llm=req.use_llm)
    return pipeline.run(**insurance_run_kwargs(req, job_id), progress_callback=progress_callback)
