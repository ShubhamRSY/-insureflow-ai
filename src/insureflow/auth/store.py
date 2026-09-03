from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from collections.abc import ItemsView, Mapping
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from insureflow.auth.models import Organization, User
from insureflow.storage.lock import FileLock, atomic_write

logger = logging.getLogger(__name__)


def _test_namespace() -> bool:
    """Tests run against an isolated store so they can never wipe real credentials."""
    return os.environ.get("INSUREFLOW_AUTH_TESTING") == "1"


def _default_path() -> Path:
    if os.environ.get("INSUREFLOW_AUTH_STORE_PATH"):
        return Path(os.environ["INSUREFLOW_AUTH_STORE_PATH"])
    if _test_namespace():
        return Path(tempfile.gettempdir()) / "insureflow_test" / "auth_users.json"
    return Path.cwd() / ".insureflow" / "auth_users.json"


_DEFAULT_PATH = _default_path()

_REDIS_KEY = "rytera:auth:users"
_TEST_REDIS_KEY = "rytera:auth:users:test"


def _get_redis_client() -> Any:
    redis_url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "")
    if not redis_url or not redis_url.startswith("redis"):
        return None
    try:
        import redis as _redis

        client = _redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
        client.ping()
        return client
    except Exception as exc:
        logger.warning("Redis unavailable for user store: %s", exc)
        return None


def _row_to_user(row: Any) -> User:
    from insureflow.auth import Role

    try:
        role = Role(row.role)
    except (ValueError, KeyError):
        role = Role.VIEWER
    return User(
        username=row.username,
        email=row.email or "",
        hashed_password=row.hashed_password,
        role=role,
        disabled=bool(row.disabled),
        org_id=row.org_id or "default",
        company_name=row.company_name or "",
        department=row.department or "",
        team=row.team or "",
        office_location=row.office_location or "",
        full_name=row.full_name or "",
    )


class PostgresUserStore:
    """PostgreSQL-backed user store — primary when DATABASE_URL is set."""

    def __init__(self) -> None:
        from insureflow.auth.db import OrgRow, UserRow, get_db_session, get_engine

        self._UserRow = UserRow
        self._OrgRow = OrgRow
        self._get_session = get_db_session
        self._engine = get_engine()

    def _session(self) -> Any:
        return self._get_session()

    def get(self, username: str) -> User | None:
        session = self._session()
        try:
            row = session.execute(select(self._UserRow).where(self._UserRow.username == username)).scalar_one_or_none()
            return _row_to_user(row) if row else None
        except SQLAlchemyError as exc:
            logger.warning("Postgres get failed: %s", exc)
            return None
        finally:
            session.close()

    def resolve_user(self, identifier: str) -> User | None:
        key = identifier.strip()
        if not key:
            return None
        session = self._session()
        try:
            row = session.execute(select(self._UserRow).where(self._UserRow.username == key)).scalar_one_or_none()
            if row:
                return _row_to_user(row)
            lower = key.lower()
            row = session.execute(select(self._UserRow).where(self._UserRow.username.ilike(lower))).scalar_one_or_none()
            if row:
                return _row_to_user(row)
            row = session.execute(select(self._UserRow).where(self._UserRow.email.ilike(lower))).scalar_one_or_none()
            return _row_to_user(row) if row else None
        except SQLAlchemyError as exc:
            logger.warning("Postgres resolve_user failed: %s", exc)
            return None
        finally:
            session.close()

    def __contains__(self, username: str) -> bool:
        return self.get(username) is not None

    def __bool__(self) -> bool:
        session = self._session()
        try:
            from sqlalchemy import func as sa_func

            count = session.execute(select(sa_func.count()).select_from(self._UserRow)).scalar()
            return bool(count and count > 0)
        except SQLAlchemyError:
            return False
        finally:
            session.close()

    def __len__(self) -> int:
        session = self._session()
        try:
            from sqlalchemy import func as sa_func

            count = session.execute(select(sa_func.count()).select_from(self._UserRow)).scalar()
            return int(count or 0)
        except SQLAlchemyError:
            return 0
        finally:
            session.close()

    def items(self) -> Mapping[str, User]:
        session = self._session()
        try:
            from insureflow.auth.db import UserRow

            rows = session.execute(select(UserRow)).scalars().all()
            result: dict[str, User] = {r.username: _row_to_user(r) for r in rows}
            return result
        except SQLAlchemyError as exc:
            logger.warning("Postgres items failed: %s", exc)
            empty: dict[str, User] = {}
            return empty
        finally:
            session.close()

    def __setitem__(self, username: str, user: User) -> None:
        session = self._session()
        try:
            if user.org_id and user.org_id != "default":
                org = session.execute(select(self._OrgRow).where(self._OrgRow.id == user.org_id)).scalar_one_or_none()
                if org is None:
                    org = session.execute(select(self._OrgRow).where(self._OrgRow.name == user.org_id)).scalar_one_or_none()
                    if org is None:
                        new_org = self._OrgRow(name=user.org_id)
                        session.add(new_org)
                        session.flush()
                        user.org_id = str(new_org.id)
                    else:
                        user.org_id = str(org.id)
            existing = session.execute(select(self._UserRow).where(self._UserRow.username == username)).scalar_one_or_none()
            if existing:
                existing.email = user.email
                existing.hashed_password = user.hashed_password
                existing.role = user.role.value
                existing.disabled = user.disabled
                existing.org_id = user.org_id
                existing.company_name = user.company_name
                existing.department = user.department
                existing.team = user.team
                existing.office_location = user.office_location
                existing.full_name = user.full_name
            else:
                new_row = self._UserRow(
                    username=username,
                    email=user.email,
                    hashed_password=user.hashed_password,
                    role=user.role.value,
                    disabled=user.disabled,
                    org_id=user.org_id,
                    company_name=user.company_name,
                    department=user.department,
                    team=user.team,
                    office_location=user.office_location,
                    full_name=user.full_name,
                )
                session.add(new_row)
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            logger.warning("Postgres save user failed: %s", exc)
        finally:
            session.close()

    def clear(self) -> int:
        from sqlalchemy import delete

        session = self._session()
        try:
            count = session.execute(select(self._UserRow)).scalars().count() if False else 0
            rows = session.execute(select(self._UserRow)).scalars().all()
            count = len(rows)
            session.execute(delete(self._UserRow))
            session.commit()
            return count
        except SQLAlchemyError as exc:
            session.rollback()
            logger.warning("Postgres clear failed: %s", exc)
            return 0
        finally:
            session.close()

    def get_or_create_org(self, name: str) -> str:
        session = self._session()
        try:
            name = name.strip()
            org = session.execute(select(self._OrgRow).where(self._OrgRow.name == name)).scalar_one_or_none()
            if org:
                return str(org.id)
            new_org = self._OrgRow(name=name)
            session.add(new_org)
            session.flush()
            org_id = str(new_org.id)
            session.commit()
            return org_id
        except SQLAlchemyError as exc:
            session.rollback()
            logger.warning("Postgres get_or_create_org failed: %s", exc)
            return ""
        finally:
            session.close()

    def get_all_orgs(self) -> list[Organization]:
        session = self._session()
        try:
            rows = session.execute(select(self._OrgRow)).scalars().all()
            return [Organization(id=str(r.id), name=r.name) for r in rows]
        except SQLAlchemyError:
            return []
        finally:
            session.close()


class UserStore:
    """Redis-backed user store with file fallback — survives container redeploys."""

    def __init__(self, path: Path | None = None) -> None:
        self._users: dict[str, User] = {}
        self._lock = threading.RLock()
        self._redis = _get_redis_client()
        self._redis_key = _TEST_REDIS_KEY if _test_namespace() else _REDIS_KEY
        self._path = path or _DEFAULT_PATH
        self.load()

    def load(self) -> None:
        with self._lock:
            self._load_locked()

    def _load_locked(self) -> None:
        if self._redis:
            try:
                raw = self._redis.get(self._redis_key)
                if raw:
                    data = json.loads(raw)
                    self._users = {k: User.model_validate(v) for k, v in data.items()}
                    logger.info("Loaded %d users from Redis", len(self._users))
                    return
            except Exception as exc:
                logger.warning("Redis load failed, trying file: %s", exc)

        if self._path.exists():
            try:
                with FileLock(str(self._path) + ".lock"):
                    raw = self._path.read_text(encoding="utf-8")
                self._users = {k: User.model_validate(v) for k, v in json.loads(raw).items()}
            except (json.JSONDecodeError, OSError, ValueError):
                self._users = {}
        else:
            self._users = {}

    def save(self) -> None:
        with self._lock:
            self._save_locked()

    def _save_locked(self) -> None:
        payload = {k: v.model_dump(mode="json") for k, v in self._users.items()}
        data = json.dumps(payload, indent=2)

        if self._redis:
            try:
                self._redis.set(self._redis_key, data)
            except Exception as exc:
                logger.warning("Redis save failed: %s", exc)

        try:
            with FileLock(str(self._path) + ".lock"):
                atomic_write(self._path, data)
        except OSError:
            pass

    def get(self, username: str) -> User | None:
        return self._users.get(username)

    def resolve_user(self, identifier: str) -> User | None:
        """Match by username key, then case-insensitive username/email lookup."""
        key = identifier.strip()
        if not key:
            return None
        user = self._users.get(key)
        if user:
            return user
        lower = key.lower()
        for candidate in self._users.values():
            if candidate.username.lower() == lower:
                return candidate
            if candidate.email and candidate.email.lower() == lower:
                return candidate
        return None

    def __contains__(self, username: str) -> bool:
        return username in self._users

    def __bool__(self) -> bool:
        return bool(self._users)

    def __len__(self) -> int:
        return len(self._users)

    def items(self) -> ItemsView[str, User]:
        return self._users.items()

    def __setitem__(self, username: str, user: User) -> None:
        with self._lock:
            self._users[username] = user
            self._save_locked()

    def clear(self) -> int:
        with self._lock:
            count = len(self._users)
            self._users.clear()
            if self._redis:
                try:
                    self._redis.delete(self._redis_key)
                except Exception:
                    pass
            if self._path.exists():
                try:
                    backup = self._path.with_suffix(".json.bak")
                    self._path.rename(backup)
                except OSError:
                    pass
            return count


_pg_store: PostgresUserStore | None = None
_file_store: UserStore | None = None


def _init_pg_store() -> PostgresUserStore | None:
    global _pg_store
    if _pg_store is not None:
        return _pg_store
    from insureflow.auth.db import get_engine

    if get_engine() is None:
        return None
    try:
        from insureflow.auth.db import init_db

        init_db()
        _pg_store = PostgresUserStore()
        logger.info("PostgreSQL user store initialized")
    except Exception as exc:
        logger.warning("Failed to init PostgreSQL user store: %s", exc)
        _pg_store = None
    return _pg_store


def get_user_store() -> PostgresUserStore | UserStore:
    global _file_store
    pg = _init_pg_store()
    if pg is not None:
        return pg
    if _file_store is None:
        _file_store = UserStore()
    return _file_store


def clear_user_store() -> int:
    pg = _init_pg_store()
    if pg is not None:
        return pg.clear()
    if _file_store is not None:
        return _file_store.clear()
    return 0
