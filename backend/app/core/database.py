"""Database engine, session factory and the FastAPI ``get_db`` dependency.

A request gets its own short-lived ``Session`` from ``get_db``. Services do the
work and call ``db.commit()`` exactly once at the end; if anything raises, the
dependency rolls back, so a failed action never leaves partial rows behind.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _engine_kwargs(url: str) -> dict[str, Any]:
    if url.startswith("sqlite"):
        # SQLite is used for local dev/tests; a file DB needs this flag because
        # TestClient runs requests across threads.
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))


if settings.is_sqlite:
    # pysqlite's default "implicit BEGIN" behaviour breaks explicit transactions and
    # SAVEPOINTs (so per-test rollback would not work). This is the SQLAlchemy-
    # documented recipe: disable pysqlite's own transaction handling and emit BEGIN
    # ourselves. It also gives us proper transactional behaviour in dev.
    @event.listens_for(engine, "connect")
    def _sqlite_disable_implicit_begin(dbapi_connection, _record):  # pragma: no cover
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _sqlite_emit_begin(conn):  # pragma: no cover
        conn.exec_driver_sql("BEGIN")

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yield a session, roll back on error, always close."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
