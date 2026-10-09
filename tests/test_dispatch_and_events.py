"""Both pipeline backends make the same call; live events cross threads and
processes; a Redis outage is a clear 503; async routes never hide blocking work."""

from __future__ import annotations

import asyncio
import base64
import inspect
import shutil
import socket
import subprocess
import threading
import time
from typing import Any

import pytest
from fastapi.routing import APIRoute, APIWebSocketRoute
from fastapi.testclient import TestClient

from insureflow.api import job_events
from insureflow.api import main as api_main
from insureflow.api.main import InsuranceDocumentPayload, SubmissionRequest
from insureflow.auth import Role
from insureflow.auth.dependencies import get_current_user
from insureflow.auth.models import TokenData


class _FakePipeline:
    calls: list[dict[str, Any]] = []

    def __init__(self, org_id: str = "default", use_llm: bool = True) -> None:
        self.org_id = org_id

    def run(self, **kwargs: Any) -> dict[str, Any]:
        cb = kwargs.pop("progress_callback", None)
        if cb:
            cb({"stage": "parse"})
        _FakePipeline.calls.append(kwargs)
        return {"outcome": "refer"}


@pytest.fixture
def fake_pipeline(monkeypatch: pytest.MonkeyPatch) -> type[_FakePipeline]:
    import insureflow.insurance.pipeline as ip

    _FakePipeline.calls = []
    monkeypatch.setattr(ip, "InsurancePipeline", _FakePipeline)
    monkeypatch.setattr(api_main, "InsurancePipeline", _FakePipeline)  # v2 task uses main's import
    monkeypatch.setenv("JOB_STORE_BACKEND", "memory")
    monkeypatch.delenv("CLAMAV_HOST", raising=False)
    monkeypatch.setattr(job_events, "_redis_url", lambda: None)
    return _FakePipeline


def _request() -> SubmissionRequest:
    pdf = base64.b64encode(b"%PDF-1.4 scanned loss run").decode()
    return SubmissionRequest(
        documents=[
            InsuranceDocumentPayload(filename="loss_run.pdf", content=pdf, encoding="base64"),
            InsuranceDocumentPayload(filename="big.pdf", content="draft-uploads/org-a/big.pdf", encoding="s3_ref"),
            InsuranceDocumentPayload(filename="sov.md", content="SOV text"),
        ],
        state_code="IL",
        insurance_company_id="carrier-1",
        insurance_line="commercial_property",
        commercial_product_id="property_bi",
    )


def test_celery_task_and_in_process_path_make_the_same_pipeline_call(fake_pipeline: type[_FakePipeline]) -> None:
    from insureflow.tasks.pipeline_tasks import run_pipeline

    req = _request()
    api_main._run_pipeline_task("job-a", req, "org-a")
    run_pipeline("job-a", req.model_dump(), "org-a")  # bound Celery task, called synchronously

    in_process, celery = fake_pipeline.calls
    assert in_process == celery
    assert [d["encoding"] for d in celery["documents"]] == ["base64", "s3_ref", "utf-8"]
    assert celery["state_code"] == "IL"
    assert celery["insurance_company_id"] == "carrier-1"


def test_v2_task_keeps_document_encoding(fake_pipeline: type[_FakePipeline]) -> None:
    req = api_main.PipelineConfigRequest(documents=[InsuranceDocumentPayload(filename="a.pdf", content=base64.b64encode(b"x").decode(), encoding="base64")])
    api_main._run_pipeline_v2_task("job-v2", req, "org-a")
    assert fake_pipeline.calls[0]["documents"][0]["encoding"] == "base64"


async def _first_event(job_id: str, publish_from_thread: Any, redis_url: str | None) -> str | None:
    events = job_events.subscribe(job_id, redis_url=redis_url)
    first = asyncio.ensure_future(events.__anext__())
    await asyncio.sleep(0.3)  # let the subscription register
    threading.Thread(target=publish_from_thread).start()
    try:
        return await asyncio.wait_for(first, timeout=3)
    finally:
        await events.aclose()


def test_local_events_from_a_worker_thread_arrive_promptly(monkeypatch: pytest.MonkeyPatch) -> None:
    started = time.monotonic()
    msg = asyncio.run(_first_event("job-local", lambda: job_events.publish("job-local", {"type": "progress"}, redis_url=""), redis_url=""))
    assert msg is not None and '"progress"' in msg
    assert time.monotonic() - started < 2  # not the 30 s heartbeat


@pytest.fixture
def redis_url() -> Any:
    if not shutil.which("redis-server"):
        pytest.skip("redis-server not installed")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(["redis-server", "--port", str(port), "--save", "", "--appendonly", "no"], stdout=subprocess.DEVNULL)
    url = f"redis://127.0.0.1:{port}/0"
    import redis

    for _ in range(50):
        try:
            redis.from_url(url).ping()
            break
        except Exception:
            time.sleep(0.1)
    yield url
    proc.terminate()
    proc.wait()
    job_events.reset_for_tests()


def test_redis_events_reach_a_stream_in_another_process(redis_url: str) -> None:
    # The publisher only shares the Redis URL with the subscriber, like a Celery worker.
    msg = asyncio.run(_first_event("job-r", lambda: job_events.publish("job-r", {"type": "status", "status": "completed"}, redis_url=redis_url), redis_url=redis_url))
    assert msg is not None and '"completed"' in msg


@pytest.fixture
def client() -> Any:
    api_main.app.dependency_overrides[get_current_user] = lambda: TokenData(username="t", role=Role.ADMIN, org_id="org-a")
    yield TestClient(api_main.app, raise_server_exceptions=False)
    api_main.app.dependency_overrides.clear()


def test_redis_outage_returns_503_not_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import redis.exceptions

    def down(*_a: Any, **_k: Any) -> None:
        raise redis.exceptions.ConnectionError("Connection refused")

    monkeypatch.setattr(api_main.job_store, "set", down)
    r = client.post("/pipeline/run", json={"acord_xml": "<ACORD/>"})
    assert r.status_code == 503
    assert r.headers["Retry-After"] == "30"
    assert "temporarily unavailable" in r.json()["detail"]


def test_download_route_strips_internal_fields(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    job = {"status": "completed", "results": {"memo": {}, "shadow_eval": {"x": 1}, "zta_report": {}, "audit_paths": ["/a"]}}
    monkeypatch.setattr(api_main.job_store, "get", lambda *_a, **_k: job)
    results = client.get("/pipeline/jobs/job-x/download").json()["results"]
    assert "memo" in results
    assert not {"shadow_eval", "zta_report", "audit_paths"} & results.keys()


def test_no_async_route_without_an_await() -> None:
    """An ``async def`` route runs on the event loop. If it never awaits, it gains
    nothing from being async and any blocking call in it stalls the whole worker,
    so it must be a plain ``def`` (FastAPI then runs it in the threadpool)."""
    offenders = []
    for route in api_main.app.routes:
        if isinstance(route, (APIRoute, APIWebSocketRoute)) and inspect.iscoroutinefunction(route.endpoint):
            src = inspect.getsource(route.endpoint)
            if "await " not in src and "async for" not in src:
                offenders.append(route.path)
    assert offenders == []


def test_celery_task_surfaces_redis_errors_for_retry(fake_pipeline: type[_FakePipeline], monkeypatch: pytest.MonkeyPatch) -> None:
    """Infrastructure errors must reach Celery (which retries them) instead of being
    swallowed into a "failed" record; called directly, Celery re-raises them."""
    import redis.exceptions

    import insureflow.tasks.submission_runner as runner
    from insureflow.tasks.pipeline_tasks import run_pipeline

    def boom(*_a: Any, **_k: Any) -> dict[str, Any]:
        raise redis.exceptions.ConnectionError("Connection refused")

    monkeypatch.setattr(runner, "run_submission", boom)
    with pytest.raises(redis.exceptions.ConnectionError):
        run_pipeline("job-r", _request().model_dump(), "org-a")


def test_celery_task_marks_pipeline_errors_failed(fake_pipeline: type[_FakePipeline], monkeypatch: pytest.MonkeyPatch) -> None:
    import insureflow.tasks.submission_runner as runner
    from insureflow.tasks.pipeline_tasks import run_pipeline

    def bad(*_a: Any, **_k: Any) -> dict[str, Any]:
        raise ValueError("unparseable ACORD")

    monkeypatch.setattr(runner, "run_submission", bad)
    assert run_pipeline("job-f", _request().model_dump(), "org-a")["status"] == "failed"
