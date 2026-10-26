"""Reusable column mixins and portable column types.

Keeping these in one place makes the schema consistent and keeps it portable
between SQLite and PostgreSQL (see AGENT.md section 4).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum as SAEnum, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC now (used as a Python-side default)."""
    return datetime.now(timezone.utc)


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
