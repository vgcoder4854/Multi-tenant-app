"""Dashboard and reporting service (Module 7).

Every number is computed in the database with aggregate queries (COUNT, GROUP BY),
never by loading rows into Python. All queries are scoped to the active org and to
what the caller's role may see:
- org_admin: the whole organization
- manager:   the projects they belong to
- employee:  their own tasks (assigned to them)
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import (
    ApproverType,
    MemberRole,
    ProjectStatus,
    RequestStatus,
    TaskStatus,
)
from app.models.work import Project, Task
from app.models.workflow import ApprovalRequest, WorkflowStep
from app.schemas.dashboard import (
    ApprovalsSummary,
    DashboardSummary,
    ProjectsSummary,
    TasksByStatus,
)
from app.services.project_service import member_project_ids
from app.services.workflow_service import count_pending_for_me


def _scoped_tasks(db: Session, ctx, *, project_id=None, assignee_id=None,
                  status=None, date_from=None, date_to=None):
    """A SELECT over tasks the caller may see, with optional filters applied."""
    stmt = select(Task).where(Task.org_id == ctx.org_id)
    if ctx.role == MemberRole.manager:
        stmt = stmt.where(Task.project_id.in_(member_project_ids(db, ctx.org_id, ctx.user.id)))
    elif ctx.role == MemberRole.employee:
        stmt = stmt.where(Task.assignee_id == ctx.user.id)

    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    if date_from is not None:
        stmt = stmt.where(Task.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Task.created_at <= date_to)
    return stmt


def _count(db: Session, stmt) -> int:
    return db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()


def summary(
    db: Session,
    ctx,
    *,
    project_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    status: TaskStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DashboardSummary:
    base = _scoped_tasks(
        db, ctx, project_id=project_id, assignee_id=assignee_id,
        status=status, date_from=date_from, date_to=date_to,
    )

    # --- tasks grouped by status in a single GROUP BY query ---
    grouped = base.subquery()
    rows = db.execute(
        select(grouped.c.status, func.count()).group_by(grouped.c.status)
    ).all()
    counts = {s: 0 for s in TaskStatus}
    for st, cnt in rows:
        counts[st] = cnt
    tasks_by_status = TasksByStatus(
        todo=counts[TaskStatus.todo],
        in_progress=counts[TaskStatus.in_progress],
        blocked=counts[TaskStatus.blocked],
        completed=counts[TaskStatus.completed],
    )

    my_tasks = _count(db, base.where(Task.assignee_id == ctx.user.id))
    overdue = _count(
        db,
        base.where(Task.due_date < date.today(), Task.status != TaskStatus.completed),
    )

    # --- projects ---
    pstmt = select(Project).where(Project.org_id == ctx.org_id)
    if ctx.role != MemberRole.org_admin:
        pstmt = pstmt.where(Project.id.in_(member_project_ids(db, ctx.org_id, ctx.user.id)))
    projects = ProjectsSummary(
        total=_count(db, pstmt),
        active=_count(db, pstmt.where(Project.status == ProjectStatus.active)),
        archived=_count(db, pstmt.where(Project.status == ProjectStatus.archived)),
    )

    # --- approvals ---
    awaiting = count_pending_for_me(db, ctx.org_id, ctx.user.id, ctx.role)
    my_submitted = db.execute(
        select(func.count())
        .select_from(ApprovalRequest)
        .where(
            ApprovalRequest.org_id == ctx.org_id,
            ApprovalRequest.requester_id == ctx.user.id,
            ApprovalRequest.status == RequestStatus.pending,
        )
    ).scalar_one()

    if ctx.role == MemberRole.org_admin:
        pending_total = db.execute(
            select(func.count())
            .select_from(ApprovalRequest)
            .where(
                ApprovalRequest.org_id == ctx.org_id,
                ApprovalRequest.status == RequestStatus.pending,
            )
        ).scalar_one()
    else:
        # pending requests the caller submitted or can act on
        pending_total = db.execute(
            select(func.count(func.distinct(ApprovalRequest.id)))
            .select_from(ApprovalRequest)
            .outerjoin(
                WorkflowStep,
                (WorkflowStep.template_id == ApprovalRequest.template_id)
                & (WorkflowStep.step_order == ApprovalRequest.current_step_order),
            )
            .where(
                ApprovalRequest.org_id == ctx.org_id,
                ApprovalRequest.status == RequestStatus.pending,
                or_(
                    ApprovalRequest.requester_id == ctx.user.id,
                    (WorkflowStep.approver_type == ApproverType.role)
                    & (WorkflowStep.approver_role == ctx.role),
                    (WorkflowStep.approver_type == ApproverType.user)
                    & (WorkflowStep.approver_user_id == ctx.user.id),
                ),
            )
        ).scalar_one()

    return DashboardSummary(
        projects=projects,
        tasks_by_status=tasks_by_status,
        my_tasks=my_tasks,
        overdue_tasks=overdue,
        approvals=ApprovalsSummary(
            pending_total=pending_total,
            awaiting_my_action=awaiting,
            my_submitted_pending=my_submitted,
        ),
    )


def export_tasks_csv(
    db: Session,
    ctx,
    *,
    project_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    status: TaskStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    row_limit: int = 5000,
) -> str:
    """Return filtered, tenant-scoped tasks as a CSV string (bounded row count)."""
    stmt = _scoped_tasks(
        db, ctx, project_id=project_id, assignee_id=assignee_id,
        status=status, date_from=date_from, date_to=date_to,
    ).order_by(Task.created_at.desc()).limit(row_limit)
    tasks = db.execute(stmt).scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "title", "project_id", "status", "priority", "assignee_id", "due_date", "created_at"])
    for t in tasks:
        writer.writerow([
            str(t.id), t.title, str(t.project_id), t.status.value, t.priority.value,
            str(t.assignee_id) if t.assignee_id else "", t.due_date.isoformat() if t.due_date else "",
            t.created_at.isoformat(),
        ])
    return buffer.getvalue()
