"""Reusable column mixins and portable column types.

Keeping these in one place makes the schema consistent and keeps it portable
between SQLite and PostgreSQL (see AGENT.md section 4).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum as SAEnum, TypeDecorator, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC now (used as a Python-side default)."""
    return datetime.now(timezone.utc)


class TZDateTime(TypeDecorator):
    """A timezone-aware DateTime that is UTC-aware on every dialect.

    PostgreSQL ``timestamptz`` already round-trips aware values; SQLite drops the
    offset, so this decorator re-attaches UTC on read and coerces on write. This
    keeps comparisons like ``row.expires_at <= utcnow()`` correct everywhere.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


# JSON on SQLite, JSONB on PostgreSQL (better indexing/operators on PG).
JSONType = JSON().with_variant(JSONB, "postgresql")


def enum_col(enum_cls: type[enum.Enum], name: str, length: int = 32) -> SAEnum:
    """A portable Enum column: VARCHAR + CHECK constraint on every dialect."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        validate_strings=True,
        length=length,
        values_callable=lambda e: [member.value for member in e],
    )


class UUIDMixin:
    """UUID primary key (native UUID on PG, CHAR(32) elsewhere)."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, nullable=False)


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
