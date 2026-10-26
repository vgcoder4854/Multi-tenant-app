"""Dashboard endpoints (Module 7)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import OrgContext, OrgCtx, require_roles
from app.core.database import get_db
from app.models.enums import MemberRole, TaskStatus
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

Db = Annotated[Session, Depends(get_db)]
ReportCtx = Annotated[OrgContext, Depends(require_roles(MemberRole.org_admin, MemberRole.manager))]


@router.get("/summary", response_model=DashboardSummary)
def summary(
    ctx: OrgCtx,
    db: Db,
    project_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    status: TaskStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DashboardSummary:
    """One consistent JSON object of role-scoped, tenant-scoped metrics."""
    return dashboard_service.summary(
        db, ctx, project_id=project_id, assignee_id=assignee_id,
        status=status, date_from=date_from, date_to=date_to,
    )


@router.get("/export.csv", response_class=PlainTextResponse)
def export_csv(
    ctx: ReportCtx,
    db: Db,
    project_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    status: TaskStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> PlainTextResponse:
    """Filtered tasks as CSV (org_admin and manager), same tenant scoping."""
    csv_text = dashboard_service.export_tasks_csv(
        db, ctx, project_id=project_id, assignee_id=assignee_id,
        status=status, date_from=date_from, date_to=date_to,
    )
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tasks.csv"},
    )
