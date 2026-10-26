"""Project service (Module 3, part 1).

Rules:
- org_admin creates/updates/archives projects and manages project members.
- Visibility: org_admin sees every org project; managers/employees only projects
  they are members of (otherwise 404, so existence is not leaked).
- Archived projects are read-only (enforced in the task service too).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.enums import MemberStatus, ProjectStatus
from app.models.identity import Membership, User
from app.models.work import Project, ProjectMember
from app.schemas.task import ProjectMemberOut
from app.services import audit_service
from app.services.tenant import get_in_org


def _is_admin(ctx) -> bool:
    from app.models.enums import MemberRole

    return ctx.role == MemberRole.org_admin


def member_project_ids(db: Session, org_id: uuid.UUID, user_id: uuid.UUID):
    """Subquery of project ids the user is a member of."""
    return select(ProjectMember.project_id).where(
        ProjectMember.org_id == org_id, ProjectMember.user_id == user_id
    )


def _visible_project(db: Session, ctx, project_id: uuid.UUID) -> Project:
    project = get_in_org(db, Project, project_id, ctx.org_id)
    if _is_admin(ctx):
        return project
    is_member = db.execute(
        select(ProjectMember.id).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == ctx.user.id
        )
    ).first()
    if not is_member:
        # Hide existence from non-members.
        raise NotFoundError("Project not found")
    return project


def create_project(db: Session, ctx, *, name: str, description: str | None) -> Project:
    name = name.strip()
    duplicate = db.execute(
        select(Project.id).where(Project.org_id == ctx.org_id, Project.name == name)
    ).first()
    if duplicate:
        raise ConflictError("A project with this name already exists", code="PROJECT_NAME_TAKEN")

    project = Project(
        org_id=ctx.org_id, name=name, description=description,
        status=ProjectStatus.active, created_by=ctx.user.id,
    )
    db.add(project)
    db.flush()
    # The creator is added as a member so managers can see it immediately.
    db.add(ProjectMember(org_id=ctx.org_id, project_id=project.id, user_id=ctx.user.id))
    audit_service.record(
        db, ctx, audit_service.PROJECT_CREATED, "project", project.id, {"name": name}
    )
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session, ctx) -> list[Project]:
    stmt = select(Project).where(Project.org_id == ctx.org_id)
    if not _is_admin(ctx):
        stmt = stmt.where(Project.id.in_(member_project_ids(db, ctx.org_id, ctx.user.id)))
    return list(db.execute(stmt.order_by(Project.name)).scalars().all())


def get_project(db: Session, ctx, project_id: uuid.UUID) -> Project:
    return _visible_project(db, ctx, project_id)


def update_project(
    db: Session, ctx, project_id: uuid.UUID, *, name: str | None, description: str | None
) -> Project:
    project = get_in_org(db, Project, project_id, ctx.org_id)
    if name is not None:
        name = name.strip()
        duplicate = db.execute(
            select(Project.id).where(
                Project.org_id == ctx.org_id, Project.name == name, Project.id != project.id
            )
        ).first()
        if duplicate:
            raise ConflictError("A project with this name already exists", code="PROJECT_NAME_TAKEN")
        project.name = name
    if description is not None:
        project.description = description
    audit_service.record(
        db, ctx, audit_service.PROJECT_UPDATED, "project", project.id, {"name": project.name}
    )
    db.commit()
    db.refresh(project)
    return project


def archive_project(db: Session, ctx, project_id: uuid.UUID) -> Project:
    project = get_in_org(db, Project, project_id, ctx.org_id)
    if project.status == ProjectStatus.archived:
        raise ConflictError("Project is already archived", code="ALREADY_ARCHIVED")
    project.status = ProjectStatus.archived
    audit_service.record(db, ctx, audit_service.PROJECT_ARCHIVED, "project", project.id)
    db.commit()
    db.refresh(project)
    return project


# --------------------------------------------------------------------------- #
# Members
# --------------------------------------------------------------------------- #
def list_project_members(db: Session, ctx, project_id: uuid.UUID) -> list[ProjectMemberOut]:
    project = _visible_project(db, ctx, project_id)
    rows = db.execute(
        select(ProjectMember, User)
        .join(User, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project.id)
        .order_by(User.full_name)
    ).all()
    return [
        ProjectMemberOut(user_id=user.id, full_name=user.full_name, email=user.email)
        for _pm, user in rows
    ]


def add_project_member(db: Session, ctx, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
    project = get_in_org(db, Project, project_id, ctx.org_id)

    # The user must be an active member of the same organization.
    membership = db.execute(
        select(Membership).where(
            Membership.org_id == ctx.org_id,
            Membership.user_id == user_id,
            Membership.status == MemberStatus.active,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise ValidationError("User is not an active member of this organization",
                              code="USER_NOT_IN_ORG")

    existing = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == user_id
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("User is already a project member", code="ALREADY_PROJECT_MEMBER")

    db.add(ProjectMember(org_id=ctx.org_id, project_id=project.id, user_id=user_id))
    audit_service.record(
        db, ctx, audit_service.PROJECT_MEMBER_ADDED, "project", project.id, {"user_id": str(user_id)}
    )
    db.commit()


def remove_project_member(db: Session, ctx, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
    project = get_in_org(db, Project, project_id, ctx.org_id)
    pm = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == user_id
        )
    ).scalar_one_or_none()
    if pm is None:
        raise NotFoundError("Project member not found")
    db.delete(pm)
    audit_service.record(
        db, ctx, audit_service.PROJECT_MEMBER_REMOVED, "project", project.id,
        {"user_id": str(user_id)},
    )
    db.commit()
