from __future__ import annotations

import os

from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
BACKEND_URL = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "insureflow",
    broker=BROKER_URL,
    backend=BACKEND_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=360,
    result_expires=86400,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.task_routes = {
    "insureflow.tasks.agent_tasks.*": {"queue": "agents"},
    "insureflow.tasks.pipeline_tasks.*": {"queue": "pipeline"},
}

import insureflow.tasks.agent_tasks  # noqa: E402,F401
