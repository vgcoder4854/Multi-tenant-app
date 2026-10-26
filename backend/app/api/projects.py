"""Project endpoints (Module 3)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import OrgContext, OrgCtx, require_roles
from app.core.database import get_db
from app.models.enums import MemberRole
from app.schemas.task import (
    ProjectCreate,
    ProjectDetailOut,
    ProjectMemberAdd,
    ProjectMemberOut,
    ProjectOut,
    ProjectUpdate,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])

Db = Annotated[Session, Depends(get_db)]
AdminCtx = Annotated[OrgContext, Depends(require_roles(MemberRole.org_admin))]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectOut)
def create_project(payload: ProjectCreate, ctx: AdminCtx, db: Db) -> ProjectOut:
    project = project_service.create_project(
        db, ctx, name=payload.name, description=payload.description
    )
    return ProjectOut.model_validate(project)


@router.get("", response_model=list[ProjectOut])
def list_projects(ctx: OrgCtx, db: Db) -> list[ProjectOut]:
    return [ProjectOut.model_validate(p) for p in project_service.list_projects(db, ctx)]


@router.get("/{project_id}", response_model=ProjectDetailOut)
def get_project(project_id: uuid.UUID, ctx: OrgCtx, db: Db) -> ProjectDetailOut:
    project = project_service.get_project(db, ctx, project_id)
    members = project_service.list_project_members(db, ctx, project_id)
    detail = ProjectDetailOut.model_validate(project)
    detail.members = members
    return detail


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: uuid.UUID, payload: ProjectUpdate, ctx: AdminCtx, db: Db) -> ProjectOut:
    project = project_service.update_project(
        db, ctx, project_id, name=payload.name, description=payload.description
    )
    return ProjectOut.model_validate(project)


@router.post("/{project_id}/archive", response_model=ProjectOut)
def archive_project(project_id: uuid.UUID, ctx: AdminCtx, db: Db) -> ProjectOut:
    return ProjectOut.model_validate(project_service.archive_project(db, ctx, project_id))


@router.get("/{project_id}/members", response_model=list[ProjectMemberOut])
def list_members(project_id: uuid.UUID, ctx: OrgCtx, db: Db) -> list[ProjectMemberOut]:
    return project_service.list_project_members(db, ctx, project_id)


@router.post("/{project_id}/members", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def add_member(project_id: uuid.UUID, payload: ProjectMemberAdd, ctx: AdminCtx, db: Db) -> None:
    project_service.add_project_member(db, ctx, project_id, payload.user_id)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def remove_member(project_id: uuid.UUID, user_id: uuid.UUID, ctx: AdminCtx, db: Db) -> None:
    project_service.remove_project_member(db, ctx, project_id, user_id)
