"""Workflow template endpoints (Module 4)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import OrgContext, OrgCtx, require_roles
from app.core.database import get_db
from app.models.enums import MemberRole
from app.schemas.workflow import (
    WorkflowTemplateCreate,
    WorkflowTemplateOut,
    WorkflowTemplateUpdate,
)
from app.services import workflow_service

router = APIRouter(prefix="/workflow-templates", tags=["workflow-templates"])

Db = Annotated[Session, Depends(get_db)]
AdminCtx = Annotated[OrgContext, Depends(require_roles(MemberRole.org_admin))]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=WorkflowTemplateOut)
def create_template(payload: WorkflowTemplateCreate, ctx: AdminCtx, db: Db) -> WorkflowTemplateOut:
    return WorkflowTemplateOut.model_validate(workflow_service.create_template(db, ctx, payload))


@router.get("", response_model=list[WorkflowTemplateOut])
def list_templates(ctx: OrgCtx, db: Db) -> list[WorkflowTemplateOut]:
    return [WorkflowTemplateOut.model_validate(t) for t in workflow_service.list_templates(db, ctx)]


@router.get("/{template_id}", response_model=WorkflowTemplateOut)
def get_template(template_id: uuid.UUID, ctx: OrgCtx, db: Db) -> WorkflowTemplateOut:
    return WorkflowTemplateOut.model_validate(workflow_service.get_template(db, ctx, template_id))


@router.patch("/{template_id}", response_model=WorkflowTemplateOut)
def update_template(
    template_id: uuid.UUID, payload: WorkflowTemplateUpdate, ctx: AdminCtx, db: Db
) -> WorkflowTemplateOut:
    return WorkflowTemplateOut.model_validate(
        workflow_service.update_template(db, ctx, template_id, payload)
    )


@router.post("/{template_id}/deactivate", response_model=WorkflowTemplateOut)
def deactivate_template(template_id: uuid.UUID, ctx: AdminCtx, db: Db) -> WorkflowTemplateOut:
    return WorkflowTemplateOut.model_validate(
        workflow_service.deactivate_template(db, ctx, template_id)
    )
