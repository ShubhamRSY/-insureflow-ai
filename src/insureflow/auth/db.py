from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, text
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from insureflow.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class OrgRow(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, server_default=text("gen_random_uuid()::text"))
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list[UserRow]] = relationship("UserRow", back_populates="org", lazy="selectin")


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, server_default=text("gen_random_uuid()::text"))
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, server_default="viewer")
    org_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    department: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    team: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    office_location: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    created_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    org: Mapped[Optional[OrgRow]] = relationship("OrgRow", back_populates="users", lazy="selectin")


_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker[Session]] = None


def _build_database_url() -> str:
    url = settings.database_url
    if not url:
        url = os.getenv("DATABASE_URL", "")
    if not url:
        return ""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def get_engine() -> Optional[Engine]:
    global _engine
    if _engine is not None:
        return _engine
    url = _build_database_url()
    if not url:
        return None
    try:
        _engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("PostgreSQL connected")
    except Exception as exc:
        logger.warning("PostgreSQL unavailable (auth will fall back to Redis/file): %s", exc)
        _engine = None
    return _engine


def get_session_factory() -> Optional[sessionmaker[Session]]:
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory
    engine = get_engine()
    if engine is None:
        return None
    _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)
    return _SessionFactory


def get_db_session() -> Optional[Session]:
    factory = get_session_factory()
    if factory is None:
        return None
    return factory()


def init_db() -> bool:
    engine = get_engine()
    if engine is None:
        return False
    Base.metadata.create_all(engine)
    logger.info("PostgreSQL tables created/verified")
    return True
