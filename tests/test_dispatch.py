from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

from insureflow.tasks import dispatch


def test_large_file_submission_routes_to_large_queue_with_extended_time_limit() -> None:
    fake_celery = MagicMock()
    fake_celery.send_task.return_value = MagicMock(id="task-1")
    request_data = {"documents": [{"filename": "huge.pdf", "content": "draft-uploads/org/b1/huge.pdf", "encoding": "s3_ref"}]}

    with patch("insureflow.tasks.celery_app.celery_app", fake_celery):
        dispatch.send_pipeline_task("job-1", request_data, "org1")

    kwargs = fake_celery.send_task.call_args.kwargs
    assert kwargs["queue"] == dispatch.LARGE_FILE_QUEUE
    assert kwargs["soft_time_limit"] == dispatch._LARGE_FILE_SOFT_TIME_LIMIT
    assert kwargs["time_limit"] == dispatch._LARGE_FILE_TIME_LIMIT


def test_small_submission_routes_to_default_pipeline_queue() -> None:
    fake_celery = MagicMock()
    fake_celery.send_task.return_value = MagicMock(id="task-2")
    request_data = {"documents": [{"filename": "small.txt", "content": "aGVsbG8=", "encoding": "base64"}]}

    with patch("insureflow.tasks.celery_app.celery_app", fake_celery):
        dispatch.send_pipeline_task("job-2", request_data, "org1")

    kwargs = fake_celery.send_task.call_args.kwargs
    assert kwargs["queue"] == "pipeline"
    assert "soft_time_limit" not in kwargs
    assert "time_limit" not in kwargs


def test_in_process_job_slot_bounds_concurrency() -> None:
    """Bound to INSURANCE_MAX_INPROCESS_JOBS: a job past the cap must block
    until a running one releases its slot, not run alongside it unbounded."""
    limit = dispatch._MAX_INPROCESS_JOBS
    started = threading.Semaphore(0)
    release = threading.Event()
    concurrent_count = 0
    max_concurrent = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal concurrent_count, max_concurrent
        with dispatch.in_process_job_slot():
            with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            started.release()
            release.wait(timeout=5)
            with lock:
                concurrent_count -= 1

    threads = [threading.Thread(target=worker) for _ in range(limit + 2)]
    for t in threads:
        t.start()

    for _ in range(limit):
        assert started.acquire(timeout=5)

    time.sleep(0.1)
    assert max_concurrent == limit

    release.set()
    for t in threads:
        t.join(timeout=5)

    assert max_concurrent == limit
