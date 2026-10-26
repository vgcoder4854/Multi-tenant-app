"""Dashboard schemas."""
from __future__ import annotations

from pydantic import BaseModel


class ProjectsSummary(BaseModel):
    total: int
    active: int
    archived: int


class TasksByStatus(BaseModel):
    todo: int = 0
    in_progress: int = 0
    blocked: int = 0
    completed: int = 0


class ApprovalsSummary(BaseModel):
    pending_total: int
    awaiting_my_action: int
    my_submitted_pending: int


class DashboardSummary(BaseModel):
    projects: ProjectsSummary
    tasks_by_status: TasksByStatus
    my_tasks: int
    overdue_tasks: int
    approvals: ApprovalsSummary
