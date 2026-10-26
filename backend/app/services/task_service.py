"""Task service (Module 3, part 2).

Rules:
- Managers may create/assign tasks only in projects they belong to; org_admin anywhere.
- An assignee must be an active member of the same organization (422 ASSIGNEE_NOT_IN_ORG).
- Archived projects are read-only.
- Every status change writes a ``task_status_history`` row, notifies the creator and
  assignee, and writes an audit entry — all inside one transaction.
- Visibility: org_admin sees all org tasks; managers see their projects' tasks;
  employees see tasks assigned to them or in their projects.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.enums import (
    MemberRole,
    MemberStatus,
    NotificationType,
    ProjectStatus,
    TaskPriority,
    TaskStatus,
)
from app.models.identity import Membership
from app.models.work import Project, Task, TaskStatusHistory
from app.schemas.task import TaskCreate, TaskUpdate
from app.services import audit_service, notification_service
from app.services.project_service import member_project_ids
from app.services.tenant import get_in_org

# Allowed status transitions. Completed tasks MAY be reopened (documented in AGENT.md).
ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.todo: {TaskStatus.in_progress, TaskStatus.blocked, TaskStatus.completed},
    TaskStatus.in_progress: {TaskStatus.todo, TaskStatus.blocked, TaskStatus.completed},
    TaskStatus.blocked: {TaskStatus.todo, TaskStatus.in_progress, TaskStatus.completed},
    TaskStatus.completed: {TaskStatus.todo, TaskStatus.in_progress},
}

SORTABLE = {"created_at", "updated_at", "due_date", "priority", "status", "title"}


def _is_admin(ctx) -> bool:
    return ctx.role == MemberRole.org_admin


def _validate_assignee(db: Session, org_id: uuid.UUID, assignee_id: uuid.UUID | None) -> None:
    if assignee_id is None:
        return
    membership = db.execute(
        select(Membership).where(
            Membership.org_id == org_id,
            Membership.user_id == assignee_id,
            Membership.status == MemberStatus.active,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise ValidationError("The assignee is not an active member of this organization",
                              code="ASSIGNEE_NOT_IN_ORG")


def _visible_tasks_stmt(db: Session, ctx):
    stmt = select(Task).where(Task.org_id == ctx.org_id)
    if _is_admin(ctx):
        return stmt
    project_ids = member_project_ids(db, ctx.org_id, ctx.user.id)
    if ctx.role == MemberRole.manager:
        return stmt.where(Task.project_id.in_(project_ids))
    # employee: assigned to me OR in my projects
    return stmt.where(or_(Task.assignee_id == ctx.user.id, Task.project_id.in_(project_ids)))


def _get_task_visible(db: Session, ctx, task_id: uuid.UUID) -> Task:
    task = db.execute(
        _visible_tasks_stmt(db, ctx).where(Task.id == task_id)
    ).scalar_one_or_none()
    if task is None:
        raise NotFoundError("Task not found")
    return task


def _assert_writable(db: Session, ctx, project: Project) -> None:
    if project.status == ProjectStatus.archived:
        raise ConflictError("This project is archived and read-only", code="PROJECT_ARCHIVED")
    if not _is_admin(ctx):
        is_member = db.execute(
            select(Project.id).where(
                Project.id == project.id,
                Project.id.in_(member_project_ids(db, ctx.org_id, ctx.user.id)),
            )
        ).first()
        if not is_member:
            raise ForbiddenError("You are not a member of this project", code="NOT_PROJECT_MEMBER")


def create_task(db: Session, ctx, payload: TaskCreate) -> Task:
    project = get_in_org(db, Project, payload.project_id, ctx.org_id)
    _assert_writable(db, ctx, project)
    _validate_assignee(db, ctx.org_id, payload.assignee_id)

    task = Task(
        org_id=ctx.org_id,
        project_id=project.id,
        title=payload.title.strip(),
        description=payload.description,
        priority=payload.priority,
        status=payload.status,
        assignee_id=payload.assignee_id,
        created_by=ctx.user.id,
        due_date=payload.due_date,
    )
    db.add(task)
    db.flush()

    # Initial history row (from_status NULL -> initial status).
    db.add(
        TaskStatusHistory(
            org_id=ctx.org_id, task_id=task.id, from_status=None,
            to_status=task.status, changed_by=ctx.user.id,
        )
    )
    if task.assignee_id:
        notification_service.notify(
            db, org_id=ctx.org_id, user_ids=[task.assignee_id],
            type=NotificationType.task_assigned, title=f"You were assigned: {task.title}",
            resource_type="task", resource_id=task.id, actor_id=ctx.user.id,
        )
    audit_service.record(
        db, ctx, audit_service.TASK_CREATED, "task", task.id,
        {"title": task.title, "project_id": str(project.id)},
    )
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, ctx, task_id: uuid.UUID, payload: TaskUpdate) -> Task:
    task = get_in_org(db, Task, task_id, ctx.org_id)
    project = get_in_org(db, Project, task.project_id, ctx.org_id)
    _assert_writable(db, ctx, project)

    if payload.assignee_id is not None and payload.assignee_id != task.assignee_id:
        _validate_assignee(db, ctx.org_id, payload.assignee_id)
        task.assignee_id = payload.assignee_id
        notification_service.notify(
            db, org_id=ctx.org_id, user_ids=[payload.assignee_id],
            type=NotificationType.task_assigned, title=f"You were assigned: {task.title}",
            resource_type="task", resource_id=task.id, actor_id=ctx.user.id,
        )
        audit_service.record(db, ctx, audit_service.TASK_ASSIGNED, "task", task.id)

    if payload.title is not None:
        task.title = payload.title.strip()
    if payload.description is not None:
        task.description = payload.description
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.due_date is not None:
        task.due_date = payload.due_date

    audit_service.record(db, ctx, audit_service.TASK_UPDATED, "task", task.id)
    db.commit()
    db.refresh(task)
    return task


def change_status(db: Session, ctx, task_id: uuid.UUID, new_status: TaskStatus) -> Task:
    task = get_in_org(db, Task, task_id, ctx.org_id)
    project = get_in_org(db, Project, task.project_id, ctx.org_id)
    if project.status == ProjectStatus.archived:
        raise ConflictError("This project is archived and read-only", code="PROJECT_ARCHIVED")

    # Who may change status: the assignee, a manager in the project, or org_admin.
    if not _is_admin(ctx) and ctx.user.id != task.assignee_id:
        is_member = db.execute(
            select(Project.id).where(
                Project.id == project.id,
                Project.id.in_(member_project_ids(db, ctx.org_id, ctx.user.id)),
            )
        ).first()
        if not is_member:
            raise ForbiddenError(
                "Only the assignee or a project manager can change this task's status",
                code="NOT_ALLOWED",
            )

    if new_status == task.status:
        raise ConflictError("The task already has this status", code="SAME_STATUS")
    if new_status not in ALLOWED_TRANSITIONS[task.status]:
        raise ConflictError(
            f"Cannot move from {task.status.value} to {new_status.value}",
            code="INVALID_TRANSITION",
        )

    old_status = task.status
    task.status = new_status
    db.add(
        TaskStatusHistory(
            org_id=ctx.org_id, task_id=task.id, from_status=old_status,
            to_status=new_status, changed_by=ctx.user.id,
        )
    )
    notification_service.notify(
        db, org_id=ctx.org_id, user_ids=[task.assignee_id, task.created_by],
        type=NotificationType.task_status_changed,
        title=f"Task '{task.title}' is now {new_status.value}",
        resource_type="task", resource_id=task.id, actor_id=ctx.user.id,
    )
    audit_service.record(
        db, ctx, audit_service.TASK_STATUS_CHANGED, "task", task.id,
        {"from": old_status.value, "to": new_status.value},
    )
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, ctx, task_id: uuid.UUID) -> tuple[Task, list[TaskStatusHistory]]:
    task = _get_task_visible(db, ctx, task_id)
    history = list(
        db.execute(
            select(TaskStatusHistory)
            .where(TaskStatusHistory.task_id == task.id)
            .order_by(TaskStatusHistory.changed_at)
        ).scalars().all()
    )
    return task, history


def list_tasks(
    db: Session,
    ctx,
    *,
    project_id: uuid.UUID | None = None,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: uuid.UUID | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Task], int]:
    stmt = _visible_tasks_stmt(db, ctx)
    count_stmt = select(func.count()).select_from(stmt.subquery())

    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if due_from is not None:
        stmt = stmt.where(Task.due_date >= due_from)
    if due_to is not None:
        stmt = stmt.where(Task.due_date <= due_to)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(func.lower(Task.title).like(like), func.lower(Task.description).like(like))
        )

    # Rebuild count from the filtered statement.
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    column = getattr(Task, sort_by if sort_by in SORTABLE else "created_at")
    order = column.desc() if sort_dir.lower() == "desc" else column.asc()
    rows = (
        db.execute(stmt.order_by(order).limit(page_size).offset((page - 1) * page_size))
        .scalars()
        .all()
    )
    return list(rows), total
