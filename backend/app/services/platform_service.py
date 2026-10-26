"""Platform-administrator service: list orgs, activate/suspend, platform stats."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.comms import AuditLog
from app.models.enums import OrgStatus
from app.models.identity import Organization, User
from app.models.work import Project, Task
from app.services import audit_service


def list_organizations(
    db: Session,
    *,
    status: OrgStatus | None = None,
    name: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Organization], int]:
    stmt = select(Organization)
    count_stmt = select(func.count()).select_from(Organization)
    if status is not None:
        stmt = stmt.where(Organization.status == status)
        count_stmt = count_stmt.where(Organization.status == status)
    if name:
        like = f"%{name.lower()}%"
        stmt = stmt.where(func.lower(Organization.name).like(like))
        count_stmt = count_stmt.where(func.lower(Organization.name).like(like))

    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(Organization.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        .scalars()
        .all()
    )
    return list(rows), total


def set_organization_status(
    db: Session, *, org_id: uuid.UUID, status: OrgStatus, actor: User
) -> Organization:
    org = db.get(Organization, org_id)
    if org is None:
        raise NotFoundError("Organization not found")
    org.status = status
    action = (
        audit_service.ORG_SUSPENDED if status == OrgStatus.suspended else audit_service.ORG_ACTIVATED
    )
    audit_service.record(
        db, None, action, "organization", org.id, {"status": status.value},
        org_id=org.id, actor_id=actor.id,
    )
    db.commit()
    db.refresh(org)
    return org


def stats(db: Session) -> dict[str, int]:
    """Platform-wide counts, computed with SQL COUNT (no rows loaded)."""

    def count(model) -> int:
        return db.execute(select(func.count()).select_from(model)).scalar_one()

    return {
        "organizations": count(Organization),
        "active_organizations": db.execute(
            select(func.count()).select_from(Organization).where(Organization.status == OrgStatus.active)
        ).scalar_one(),
        "users": count(User),
        "projects": count(Project),
        "tasks": count(Task),
        "audit_events": db.execute(select(func.count()).select_from(AuditLog)).scalar_one(),
    }
