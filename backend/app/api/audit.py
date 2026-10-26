"""Audit log endpoints (Module 6)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import OrgContext, PlatformAdmin, require_roles
from app.core.database import get_db
from app.models.enums import MemberRole
from app.schemas.audit import AuditLogOut
from app.schemas.common import Page
from app.services import audit_service

Db = Annotated[Session, Depends(get_db)]
AdminCtx = Annotated[OrgContext, Depends(require_roles(MemberRole.org_admin))]

router = APIRouter(prefix="/audit-logs", tags=["audit"])
platform_router = APIRouter(prefix="/platform/audit-logs", tags=["platform-admin"])


@router.get("", response_model=Page[AuditLogOut])
def list_audit_logs(
    ctx: AdminCtx,
    db: Db,
    actor_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[AuditLogOut]:
    """The active organization's audit log (org_admin only), newest first."""
    items, total = audit_service.list_audit_logs(
        db, org_id=ctx.org_id, actor_id=actor_id, action=action, resource_type=resource_type,
        date_from=date_from, date_to=date_to, page=page, page_size=page_size,
    )
    return Page[AuditLogOut](
        items=[AuditLogOut.model_validate(i) for i in items],
        total=total, page=page, page_size=page_size,
    )


@platform_router.get("", response_model=Page[AuditLogOut])
def list_platform_audit_logs(
    _: PlatformAdmin,
    db: Db,
    org_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[AuditLogOut]:
    """Platform-wide audit log (platform admin), optionally filtered by org."""
    items, total = audit_service.list_audit_logs(
        db, org_id=org_id, actor_id=actor_id, action=action, resource_type=resource_type,
        date_from=date_from, date_to=date_to, page=page, page_size=page_size,
    )
    return Page[AuditLogOut](
        items=[AuditLogOut.model_validate(i) for i in items],
        total=total, page=page, page_size=page_size,
    )
