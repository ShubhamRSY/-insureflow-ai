"""Upload screening off the event loop, real retry, encrypted job records, bundle
runs through Celery, shared rate-limit counters, and automatic Celery choice."""

from __future__ import annotations

import asyncio
import base64
import json
import shutil
import socket
import subprocess
import time
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from insureflow.api import main as api_main
from insureflow.api.main import InsuranceDocumentPayload, SubmissionRequest
from insureflow.api.upload_screening import ScreenedRoute
from insureflow.auth import Role
from insureflow.auth.dependencies import get_current_user
from insureflow.auth.models import TokenData
from insureflow.tasks import dispatch

PDF = base64.b64encode(b"%PDF-1.4 scanned loss run").decode()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("INSURANCE_USE_CELERY", "0")
    api_main.app.dependency_overrides[get_current_user] = lambda: TokenData(username="t", role=Role.ADMIN, org_id="org-fix")
    yield TestClient(api_main.app, raise_server_exceptions=False)
    api_main.app.dependency_overrides.clear()


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, SubmissionRequest]]:
    runs: list[tuple[str, SubmissionRequest]] = []
    monkeypatch.setattr(api_main, "_run_pipeline_task", lambda job_id, req, org_id: runs.append((job_id, req)))
    return runs


# ── 1. Virus scan runs in a thread, before the route, on every upload route ──


@pytest.fixture
def scans(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    import insureflow.ingestion.intake as intake

    calls: list[dict[str, Any]] = []

    def fake_scan(data: bytes) -> str | None:
        try:
            asyncio.get_running_loop()
            on_loop = True
        except RuntimeError:
            on_loop = False
        calls.append({"on_loop": on_loop, "data": data})
        return "Eicar-Test-Signature" if b"EICAR" in data else None

    monkeypatch.setenv("CLAMAV_HOST", "clamav")
    monkeypatch.setattr(intake, "scan_for_malware", fake_scan)
    return calls


def test_upload_scan_runs_off_the_event_loop(client: TestClient, captured: list[Any], scans: list[dict[str, Any]]) -> None:
    r = client.post("/pipeline/run", json={"documents": [{"filename": "a.pdf", "content": PDF, "encoding": "base64"}]})
    assert r.status_code == 202, r.text
    assert len(scans) == 1
    assert scans[0]["on_loop"] is False


def test_infected_upload_is_still_rejected_before_the_route_runs(client: TestClient, captured: list[Any], scans: list[dict[str, Any]]) -> None:
    bad = base64.b64encode(b"X5O!P%@AP EICAR test").decode()
    r = client.post("/pipeline/run", json={"documents": [{"filename": "evil.pdf", "content": bad, "encoding": "base64"}]})
    assert r.status_code == 422
    assert "antivirus" in r.json()["detail"]
    assert captured == []  # the route never ran, so nothing was queued


def test_documents_built_outside_a_request_are_scanned_immediately(scans: list[dict[str, Any]]) -> None:
    InsuranceDocumentPayload(filename="a.pdf", content=PDF, encoding="base64")
    assert len(scans) == 1


def test_every_route_that_accepts_uploads_screens_them() -> None:
    def takes_uploads(route: APIRoute) -> bool:
        if route.body_field is None:
            return False
        ann = route.body_field.field_info.annotation
        if ann is None:
            return False
        schema = json.dumps(TypeAdapter(ann).json_schema())
        return "InsuranceDocumentPayload" in schema or "MortgageDocumentPayload" in schema

    upload_routes = [r for r in api_main.app.routes if isinstance(r, APIRoute) and takes_uploads(r)]
    assert upload_routes, "expected at least /pipeline/run"
    assert [r.path for r in upload_routes if not isinstance(r, ScreenedRoute)] == []


# ── 2. Retry re-runs the original submission ──


def test_retry_reruns_the_original_submission(client: TestClient, captured: list[tuple[str, SubmissionRequest]]) -> None:
    body = {"documents": [{"filename": "a.pdf", "content": PDF, "encoding": "base64"}], "state_code": "IL", "commercial_product_id": "property_bi"}
    job_id = client.post("/pipeline/run", json=body).json()["job_id"]
    r = client.post(f"/pipeline/jobs/{job_id}/retry")
    assert r.status_code == 202, r.text
    assert r.json()["retry_of"] == job_id
    (_, original), (_, rerun) = captured
    assert rerun.model_dump() == original.model_dump()
    assert rerun.state_code == "IL" and rerun.documents and rerun.documents[0].filename == "a.pdf"


def test_retry_without_a_saved_submission_says_so(client: TestClient, captured: list[Any]) -> None:
    api_main.job_store.set(api_main.INSURANCE_NS, "job-old", {"status": "failed"}, org_id="org-fix")
    r = client.post("/pipeline/jobs/job-old/retry")
    assert r.status_code == 409
    assert "submit the documents again" in r.json()["detail"]
    assert captured == []


# ── 3. Job records are encrypted at rest ──


KEY = Fernet.generate_key().decode()  # generated per run; never a real key


def test_file_job_store_encrypts_records_and_reads_old_ones(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from insureflow.storage.file_job_store import FileJobStore

    monkeypatch.setenv("ENCRYPTION_KEY", KEY)
    store = FileJobStore(tmp_path)
    store.set("insurance", "job-1", {"status": "completed", "results": {"named_insured": "Northwind Logistics LLC"}}, org_id="o")
    raw = next(tmp_path.rglob("job-1*")).read_text()
    assert raw.startswith("ENC:v1:") and "Northwind" not in raw
    record = store.get("insurance", "job-1", org_id="o")
    assert record is not None
    assert record["results"]["named_insured"] == "Northwind Logistics LLC"
    # a record written before encryption existed still reads
    next(tmp_path.rglob("job-1*")).write_text(json.dumps({"status": "completed"}))
    assert store.get("insurance", "job-1", org_id="o") == {"status": "completed"}


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


def test_redis_job_store_encrypts_records(redis_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    import redis

    from insureflow.storage.job_store import RedisJobStore

    monkeypatch.setenv("ENCRYPTION_KEY", KEY)
    store = RedisJobStore(redis_url)
    store.set("insurance", "job-2", {"results": {"named_insured": "Northwind Logistics LLC"}}, org_id="o")
    raw = redis.from_url(redis_url, decode_responses=True).get("insureflow:o:insurance:job:job-2")
    assert isinstance(raw, str)
    assert raw.startswith("ENC:v1:") and "Northwind" not in raw
    record = store.get("insurance", "job-2", org_id="o")
    assert record is not None
    assert record["results"]["named_insured"] == "Northwind Logistics LLC"


# ── 4. Dashboard bundle runs go through the same dispatch (Celery when available) ──


def test_bundle_run_uses_the_shared_dispatch(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import insureflow.storage.draft_bundle_store as dbs
    from tests.conftest import SAMPLE_ACORD_XML

    class FakeStore:
        _store = api_main.job_store

        def to_pipeline_documents(self, bundle_id: str, org_id: str) -> list[dict[str, str]]:
            return [{"filename": "acord.xml", "content": SAMPLE_ACORD_XML, "encoding": "utf-8"}]

        def get(self, bundle_id: str, org_id: str) -> None:
            return None

    sent: list[str] = []

    def _send(job_id: str, data: object, org_id: str) -> str:
        sent.append(job_id)
        return "celery-task-1"

    monkeypatch.setattr(dbs, "get_draft_bundle_store", lambda: FakeStore())
    monkeypatch.setenv("INSURANCE_USE_CELERY", "1")
    monkeypatch.setattr(dispatch, "send_pipeline_task", _send)
    r = client.post("/pipeline/bundles/b1/run")
    assert r.status_code == 202, r.text
    job = api_main.job_store.get(api_main.INSURANCE_NS, r.json()["job_id"], org_id="org-fix")
    assert job is not None
    assert sent == [r.json()["job_id"]]
    assert job["backend"] == "celery"


# ── 5. Rate-limit counters are shared across processes ──


def test_rate_limit_storage_follows_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RATE_LIMIT_STORAGE_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    assert api_main._rate_limit_storage_uri() == "redis://redis:6379/0"
    monkeypatch.delenv("REDIS_URL")
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    assert api_main._rate_limit_storage_uri() == "memory://"


def test_two_workers_share_one_redis_counter(redis_url: str) -> None:
    from limits import parse
    from limits.storage import storage_from_string
    from limits.strategies import FixedWindowRateLimiter

    limit = parse("2/minute")
    worker_a = FixedWindowRateLimiter(storage_from_string(redis_url))
    worker_b = FixedWindowRateLimiter(storage_from_string(redis_url))  # a second uvicorn process
    assert worker_a.hit(limit, "client-1")
    assert worker_b.hit(limit, "client-1")
    assert not worker_a.hit(limit, "client-1")  # third hit refused, whichever worker gets it


# ── 6. use_celery=None decides automatically, and only uses Celery if a worker listens ──


def test_use_celery_defaults_to_automatic() -> None:
    assert SubmissionRequest().use_celery is None


@pytest.mark.parametrize(
    ("env", "requested", "broker", "worker", "expected"),
    [
        ("", None, True, True, True),  # auto: broker up and a worker listens
        ("", None, True, False, False),  # auto: Redis up but no worker → never strand the job
        ("", None, False, True, False),  # auto: no broker
        ("", True, False, False, True),  # explicit request wins
        ("", False, True, True, False),
        ("1", False, False, False, True),  # env wins over everything
        ("0", True, True, True, False),
    ],
)
def test_should_use_celery(monkeypatch: pytest.MonkeyPatch, env: str, requested: bool | None, broker: bool, worker: bool, expected: bool) -> None:
    monkeypatch.setenv("INSURANCE_USE_CELERY", env)
    monkeypatch.delenv("INSURANCE_IN_PROCESS", raising=False)
    monkeypatch.setattr(dispatch, "broker_reachable", lambda: broker)
    monkeypatch.setattr(dispatch, "worker_listening", lambda queue: worker)
    assert dispatch.should_use_celery(requested, queue="pipeline") is expected


def test_worker_check_is_per_queue_and_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def _queues() -> set[str]:
        calls.append(1)
        return {"pipeline", "agents"}

    monkeypatch.setattr(dispatch, "_worker_cache", {})
    monkeypatch.setattr(dispatch, "_queues_with_workers", _queues)
    assert dispatch.worker_listening("pipeline") is True
    assert dispatch.worker_listening("pipeline-large") is False  # nobody serves the large queue
    assert dispatch.worker_listening("pipeline") is True
    assert len(calls) == 2  # first two asked Celery; the third came from the 15 s cache
