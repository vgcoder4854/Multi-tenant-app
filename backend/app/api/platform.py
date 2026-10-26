"""Platform-administrator endpoints (no organization context required)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PlatformAdmin
from app.core.database import get_db
from app.models.enums import OrgStatus
from app.schemas.common import Page
from app.schemas.org import OrganizationOut, OrganizationStatusUpdate
from app.services import platform_service

router = APIRouter(prefix="/platform", tags=["platform-admin"])

Db = Annotated[Session, Depends(get_db)]


@router.get("/organizations", response_model=Page[OrganizationOut])
def list_organizations(
    _: PlatformAdmin,
    db: Db,
    status: OrgStatus | None = None,
    name: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[OrganizationOut]:
    """Paginated organizations, filterable by status and name."""
    items, total = platform_service.list_organizations(
        db, status=status, name=name, page=page, page_size=page_size
    )
    return Page[OrganizationOut](
        items=[OrganizationOut.model_validate(o) for o in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/organizations/{org_id}/status", response_model=OrganizationOut)
def set_organization_status(
    org_id: uuid.UUID, payload: OrganizationStatusUpdate, actor: PlatformAdmin, db: Db
) -> OrganizationOut:
    """Activate or suspend an organization (audited). Suspension blocks its endpoints."""
    org = platform_service.set_organization_status(
        db, org_id=org_id, status=payload.status, actor=actor
    )
    return OrganizationOut.model_validate(org)


@router.get("/stats")
def platform_stats(_: PlatformAdmin, db: Db) -> dict[str, int]:
    """Platform-wide counts (organizations, users, projects, tasks, audit events)."""
    return platform_service.stats(db)
