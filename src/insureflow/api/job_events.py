"""Live job events for the SSE and WebSocket streams.

Progress used to be pushed into ``asyncio.Queue``s kept in the API process's
memory, straight from the worker thread running the job. That reached nobody
when the job ran in a Celery worker or on another uvicorn worker, and
``asyncio.Queue`` is not thread-safe, so even same-process events could sit
unseen until the next heartbeat.

Now:
- With a Redis job store (every deployment), events go through Redis pub/sub,
  so any process can publish and any API worker's stream receives them.
- Without Redis (tests, single-process dev), events go to local subscribers via
  ``loop.call_soon_threadsafe``, which is safe from any thread.

Callers never send to a channel without first checking the job belongs to the
caller's org; the channel name is only the job id.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 30.0
_QUEUE_SIZE = 100

_local_lock = threading.Lock()
_local_subscribers: dict[str, set[tuple[asyncio.AbstractEventLoop, asyncio.Queue[str]]]] = defaultdict(set)


def channel_name(job_id: str) -> str:
    return f"insureflow:job-events:{job_id}"


_UNSET = object()
_cached_url: Any = _UNSET
_clients: dict[str, Any] = {}


def _redis_url() -> str | None:
    """The shared Redis URL when the job store is Redis (so every process sees it).

    Resolved once per process, like the module-level job store in api/main.py.
    """
    global _cached_url
    if _cached_url is _UNSET:
        from insureflow.storage.job_store import RedisJobStore, get_job_store

        store = get_job_store()
        _cached_url = getattr(store, "url", None) if isinstance(store, RedisJobStore) else None
    return _cached_url  # type: ignore[no-any-return]


def reset_for_tests() -> None:
    global _cached_url
    _cached_url = _UNSET
    _clients.clear()


def _sync_client(url: str) -> Any:
    client = _clients.get(url)
    if client is None:
        import redis

        client = _clients[url] = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    return client


def _put(queue: asyncio.Queue[str], payload: str) -> None:
    try:
        queue.put_nowait(payload)
    except asyncio.QueueFull:
        pass


def _publish_local(job_id: str, payload: str) -> None:
    with _local_lock:
        subscribers = list(_local_subscribers.get(job_id, ()))
    for loop, queue in subscribers:
        try:
            loop.call_soon_threadsafe(_put, queue, payload)
        except RuntimeError:  # loop already closed
            pass


def publish(job_id: str, data: dict[str, Any], *, redis_url: str | None = None) -> None:
    """Send one event to every stream watching ``job_id``. Safe from any thread or process."""
    payload = json.dumps(data, default=str)
    url = redis_url if redis_url is not None else _redis_url()
    if url:
        try:
            _sync_client(url).publish(channel_name(job_id), payload)
            return
        except Exception as exc:  # a lost event is fine: clients also poll the job record
            logger.warning("Could not publish job event for %s: %s", job_id, exc)
            return
    _publish_local(job_id, payload)


async def subscribe(job_id: str, *, redis_url: str | None = None) -> AsyncGenerator[str | None, None]:
    """Yield event payloads for ``job_id``; yields ``None`` after each quiet heartbeat interval."""
    url = redis_url if redis_url is not None else await asyncio.to_thread(_redis_url)
    if url:
        import redis.asyncio as aioredis

        client = aioredis.from_url(url)
        pubsub = client.pubsub()
        await pubsub.subscribe(channel_name(job_id))
        try:
            loop = asyncio.get_running_loop()
            quiet_since = loop.time()
            while True:
                remaining = HEARTBEAT_SECONDS - (loop.time() - quiet_since)
                if remaining <= 0:
                    quiet_since = loop.time()
                    yield None
                    continue
                # Also returns None early for the swallowed "subscribed" confirmation,
                # so only the clock decides when a heartbeat is due.
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=remaining)
                if msg is None or msg.get("type") != "message":
                    continue
                quiet_since = loop.time()
                data = msg.get("data")
                yield data.decode() if isinstance(data, bytes) else str(data)
        finally:
            await pubsub.unsubscribe(channel_name(job_id))
            await pubsub.aclose()  # type: ignore[no-untyped-call]
            await client.aclose()
    else:
        entry = (asyncio.get_running_loop(), asyncio.Queue[str](maxsize=_QUEUE_SIZE))
        with _local_lock:
            _local_subscribers[job_id].add(entry)
        try:
            while True:
                try:
                    yield await asyncio.wait_for(entry[1].get(), timeout=HEARTBEAT_SECONDS)
                except asyncio.TimeoutError:
                    yield None
        finally:
            with _local_lock:
                _local_subscribers[job_id].discard(entry)
                if not _local_subscribers[job_id]:
                    del _local_subscribers[job_id]
