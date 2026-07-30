from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, cast

logger = logging.getLogger(__name__)


class JobStore(ABC):
    @abstractmethod
    def set(self, namespace: str, job_id: str, data: dict[str, Any], org_id: str = "default") -> None: ...

    @abstractmethod
    def get(self, namespace: str, job_id: str, org_id: str = "default") -> dict[str, Any] | None: ...

    @abstractmethod
    def delete(self, namespace: str, job_id: str, org_id: str = "default") -> bool: ...

    @abstractmethod
    def list_ids(self, namespace: str, org_id: str = "default") -> list[str]: ...


class MemoryJobStore(JobStore):
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def _key(self, namespace: str, job_id: str, org_id: str) -> str:
        return f"{org_id}:{namespace}:{job_id}"

    def set(self, namespace: str, job_id: str, data: dict[str, Any], org_id: str = "default") -> None:
        data = {**data, "org_id": org_id, "updated_at": datetime.now(tz=timezone.utc).isoformat()}
        self._store[self._key(namespace, job_id, org_id)] = data

    def get(self, namespace: str, job_id: str, org_id: str = "default") -> dict[str, Any] | None:
        return self._store.get(self._key(namespace, job_id, org_id))

    def delete(self, namespace: str, job_id: str, org_id: str = "default") -> bool:
        key = self._key(namespace, job_id, org_id)
        if key in self._store:
            del self._store[key]
            return True
        return False

    def list_ids(self, namespace: str, org_id: str = "default") -> list[str]:
        prefix = f"{org_id}:{namespace}:"
        return [k.split(":")[-1] for k in self._store if k.startswith(prefix)]


class RedisJobStore(JobStore):
    def __init__(self, url: str, ttl_seconds: int = 86400 * 7) -> None:
        import redis

        self.client = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        self.ttl = ttl_seconds

    def _key(self, namespace: str, job_id: str, org_id: str) -> str:
        return f"insureflow:{org_id}:{namespace}:job:{job_id}"

    def _index_key(self, namespace: str, org_id: str) -> str:
        return f"insureflow:{org_id}:{namespace}:index"

    def set(self, namespace: str, job_id: str, data: dict[str, Any], org_id: str = "default") -> None:
        data = {**data, "org_id": org_id, "updated_at": datetime.now(tz=timezone.utc).isoformat()}
        key = self._key(namespace, job_id, org_id)
        self.client.setex(key, self.ttl, json.dumps(data, default=str))
        self.client.sadd(self._index_key(namespace, org_id), job_id)
        self.client.expire(self._index_key(namespace, org_id), self.ttl)

    def get(self, namespace: str, job_id: str, org_id: str = "default") -> dict[str, Any] | None:
        raw = self.client.get(self._key(namespace, job_id, org_id))
        if not raw:
            return None
        return cast(dict[str, Any], json.loads(raw))

    def delete(self, namespace: str, job_id: str, org_id: str = "default") -> bool:
        key = self._key(namespace, job_id, org_id)
        removed = self.client.delete(key)
        self.client.srem(self._index_key(namespace, org_id), job_id)
        return bool(removed)

    def list_ids(self, namespace: str, org_id: str = "default") -> list[str]:
        return sorted(cast(set[Any], self.client.smembers(self._index_key(namespace, org_id))))


def get_job_store() -> JobStore:
    import os

    from insureflow.security.posture import resolve_security_posture

    redis_url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "")
    backend = os.getenv("JOB_STORE_BACKEND", "auto").strip().lower()
    hardened = resolve_security_posture().is_hardened

    if backend == "memory":
        if hardened:
            raise RuntimeError("JOB_STORE_BACKEND=memory is not allowed in BANK_MODE/production. Configure REDIS_URL and JOB_STORE_BACKEND=redis|auto.")
        logger.warning("Using in-memory job store — state is lost on restart")
        return MemoryJobStore()

    if backend == "file":
        from insureflow.storage.file_job_store import FileJobStore

        root = os.getenv("JOB_STORE_PATH") or ""
        store = FileJobStore(root or None)
        logger.info("Using file job store at %s", store.root)
        return store

    if backend == "redis" or (backend == "auto" and redis_url and redis_url.startswith("redis")):
        try:
            redis_store = RedisJobStore(redis_url or "")
            redis_store.client.ping()
            logger.info("Using Redis job store at %s", redis_url)
            return redis_store
        except Exception as exc:
            if hardened or backend == "redis":
                raise RuntimeError(f"Redis job store required but unavailable ({exc}). Fix REDIS_URL or set JOB_STORE_BACKEND=file for durable local storage.") from exc
            logger.warning("Redis unavailable (%s), falling back to file job store", exc)
            from insureflow.storage.file_job_store import FileJobStore

            return FileJobStore()

    if hardened:
        raise RuntimeError("BANK_MODE/production requires a reachable Redis job store (REDIS_URL / CELERY_BROKER_URL).")

    # Default durable path for local/dev — never silent memory
    from insureflow.storage.file_job_store import FileJobStore

    logger.info("Using file job store (no Redis configured)")
    return FileJobStore()
