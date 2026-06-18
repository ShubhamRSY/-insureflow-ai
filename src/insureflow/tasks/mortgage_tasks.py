from __future__ import annotations

from typing import Any
from uuid import uuid4

from insureflow.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="insureflow.tasks.mortgage_tasks.run_mortgage_pipeline",
    max_retries=3,
    default_retry_delay=10,
)
def run_mortgage_pipeline(
    self,
    documents_data: list[dict[str, str]],
    bundle_id: str | None = None,
    product_line: str = "residential_mortgage",
    use_llm: bool = True,
    borrower_id: str | None = None,
) -> dict[str, Any]:
    from insureflow.models.mortgage import ProductLine
    from insureflow.mortgage.pipeline import MortgagePipeline

    docs: list[dict[str, str]] = [
        {"filename": d["filename"], "content": d["content"]}
        for d in documents_data
    ]

    pipeline = MortgagePipeline(use_llm=use_llm)
    result = pipeline.run_from_texts(
        docs,
        bundle_id=bundle_id,
        product_line=ProductLine(product_line),
        borrower_id=borrower_id,
    )
    return result


@celery_app.task(
    bind=True,
    name="insureflow.tasks.mortgage_tasks.run_mortgage_directory",
)
def run_mortgage_directory(
    self,
    directory: str,
    bundle_id: str | None = None,
    product_line: str | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    from insureflow.models.mortgage import ProductLine
    from insureflow.mortgage.pipeline import MortgagePipeline

    pipeline = MortgagePipeline(use_llm=use_llm)
    pl = ProductLine(product_line) if product_line else None
    result = pipeline.run_from_directory(
        directory,
        bundle_id=bundle_id,
        product_line=pl,
    )
    return result


@celery_app.task(
    bind=True,
    name="insureflow.tasks.mortgage_tasks.run_mortgage_per_borrower",
)
def run_mortgage_per_borrower(
    self,
    directory: str,
    product_line: str | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    from insureflow.models.mortgage import ProductLine
    from insureflow.mortgage.pipeline import MortgagePipeline

    pipeline = MortgagePipeline(use_llm=use_llm)
    pl = ProductLine(product_line) if product_line else None
    result = pipeline.run_per_borrower(
        directory,
        product_line=pl,
    )
    return result


@celery_app.task(
    bind=True,
    name="insureflow.tasks.mortgage_tasks.run_mortgage_langgraph",
    max_retries=2,
)
def run_mortgage_langgraph(
    self,
    documents_data: list[dict[str, str]],
    bundle_id: str | None = None,
) -> dict[str, Any]:
    from insureflow.mortgage.graph import build_mortgage_pipeline_graph

    raw_documents = [
        {"filename": d["filename"], "content": d["content"]}
        for d in documents_data
    ]

    initial_state: dict[str, Any] = {
        "raw_documents": raw_documents,
        "bundle_id": bundle_id or f"mortgage-{uuid4().hex[:12]}",
    }
    graph = build_mortgage_pipeline_graph()
    result = graph.run(initial_state)
    return result
