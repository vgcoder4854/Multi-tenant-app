"""Tenant-safe repository helpers.

Every read/write of tenant data goes through these helpers so ``org_id`` filtering
can never be forgotten. A row that exists but belongs to another organization is
reported as **404 Not Found** (never 403) so IDs cannot be probed across tenants.
"""
from __future__ import annotations

import uuid
from typing import Any, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.errors import NotFoundError

ModelT = TypeVar("ModelT", bound=Base)


def list_query(model: type[ModelT], org_id: uuid.UUID) -> Select[tuple[ModelT]]:
    """Return a SELECT already filtered to the given organization."""
    return select(model).where(model.org_id == org_id)  # type: ignore[attr-defined]


def get_in_org(db: Session, model: type[ModelT], obj_id: uuid.UUID, org_id: uuid.UUID) -> ModelT:
    """Fetch one row by id **within** ``org_id`` or raise 404.

    A row belonging to another org is indistinguishable from a missing row.
    """
    obj = db.execute(
        select(model).where(model.id == obj_id, model.org_id == org_id)  # type: ignore[attr-defined]
    ).scalar_one_or_none()
    if obj is None:
        raise NotFoundError(f"{model.__name__} not found")
    return obj


def assert_same_org(org_id: uuid.UUID, *objects: Any) -> None:
    """Raise 404 if any related object belongs to a different organization.

    Use when a related row (project, assignee, template) must be in the same org.
    ``None`` values are ignored (e.g. an optional assignee).
    """
    for obj in objects:
        if obj is None:
            continue
        if getattr(obj, "org_id", None) != org_id:
            raise NotFoundError("Related resource not found")
