"""Database setup with SQLAlchemy.

SQLAlchemy lets the same Python code talk to SQLite (local development and
tests) and PostgreSQL (production). Only the DATABASE_URL changes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import DateTime, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator):
    """Store every datetime in UTC and always read it back timezone-aware.

    Flight times arrive with a timezone ("2026-12-12T09:30-08:00"). SQLite
    can't store timezones and returns naive datetimes, which would make
    comparisons ambiguous. So we convert to UTC on the way in and re-attach
    UTC on the way out. Postgres behaves the same way through this type.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Refusing to store a datetime without a timezone")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def make_engine(url: str) -> Engine:
    if url == "sqlite://":
        # In-memory SQLite (tests): one shared connection, or each new
        # connection would get its own empty database.
        return create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """One database session per request, always closed afterwards."""
    db = factory()
    try:
        yield db
    finally:
        db.close()
