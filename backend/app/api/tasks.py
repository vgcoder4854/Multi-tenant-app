"""Task endpoints (Module 3)."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import OrgContext, OrgCtx, require_roles
from app.core.database import get_db
from app.models.enums import MemberRole, TaskPriority, TaskStatus
from app.schemas.common import Page
from app.schemas.task import (
    TaskCreate,
    TaskDetailOut,
    TaskOut,
    TaskStatusHistoryOut,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])

Db = Annotated[Session, Depends(get_db)]
WriterCtx = Annotated[OrgContext, Depends(require_roles(MemberRole.org_admin, MemberRole.manager))]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TaskOut)
def create_task(payload: TaskCreate, ctx: WriterCtx, db: Db) -> TaskOut:
    return TaskOut.model_validate(task_service.create_task(db, ctx, payload))


@router.get("", response_model=Page[TaskOut])
def list_tasks(
    ctx: OrgCtx,
    db: Db,
    project_id: uuid.UUID | None = None,
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    priority: TaskPriority | None = None,
    assignee_id: uuid.UUID | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_dir: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[TaskOut]:
    items, total = task_service.list_tasks(
        db, ctx, project_id=project_id, status=status_filter, priority=priority,
        assignee_id=assignee_id, due_from=due_from, due_to=due_to, search=search,
        sort_by=sort_by, sort_dir=sort_dir, page=page, page_size=page_size,
    )
    return Page[TaskOut](
        items=[TaskOut.model_validate(t) for t in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskDetailOut)
def get_task(task_id: uuid.UUID, ctx: OrgCtx, db: Db) -> TaskDetailOut:
    task, history = task_service.get_task(db, ctx, task_id)
    detail = TaskDetailOut.model_validate(task)
    detail.history = [TaskStatusHistoryOut.model_validate(h) for h in history]
    return detail


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: uuid.UUID, payload: TaskUpdate, ctx: WriterCtx, db: Db) -> TaskOut:
    return TaskOut.model_validate(task_service.update_task(db, ctx, task_id, payload))


@router.patch("/{task_id}/status", response_model=TaskOut)
def change_status(task_id: uuid.UUID, payload: TaskStatusUpdate, ctx: OrgCtx, db: Db) -> TaskOut:
    return TaskOut.model_validate(task_service.change_status(db, ctx, task_id, payload.status))
