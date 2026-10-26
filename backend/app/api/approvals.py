"""Approval request endpoints (Module 4)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import OrgCtx
from app.core.database import get_db
from app.schemas.workflow import (
    ApprovalDecisionIn,
    ApprovalRequestCreate,
    ApprovalRequestDetailOut,
    ApprovalRequestOut,
)
from app.services import workflow_service

router = APIRouter(prefix="/approval-requests", tags=["approvals"])

Db = Annotated[Session, Depends(get_db)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApprovalRequestOut)
def submit_request(payload: ApprovalRequestCreate, ctx: OrgCtx, db: Db) -> ApprovalRequestOut:
    """Submit a request from an active template; it starts at step 1 (pending)."""
    request = workflow_service.submit_request(db, ctx, payload)
    return workflow_service.to_out(db, request)


@router.get("/mine", response_model=list[ApprovalRequestOut])
def my_requests(ctx: OrgCtx, db: Db) -> list[ApprovalRequestOut]:
    return workflow_service.list_my_requests(db, ctx)


@router.get("/pending-for-me", response_model=list[ApprovalRequestOut])
def pending_for_me(ctx: OrgCtx, db: Db) -> list[ApprovalRequestOut]:
    """Requests awaiting the current user's decision (same rule as the decide endpoint)."""
    return workflow_service.list_pending_for_me(db, ctx)


@router.get("/{request_id}", response_model=ApprovalRequestDetailOut)
def get_request(request_id: uuid.UUID, ctx: OrgCtx, db: Db) -> ApprovalRequestDetailOut:
    request, steps, decisions = workflow_service.get_request_detail(db, ctx, request_id)
    return ApprovalRequestDetailOut(
        **workflow_service.build_detail_out(db, request, steps, decisions, ctx)
    )


@router.post("/{request_id}/decision", response_model=ApprovalRequestOut)
def decide(request_id: uuid.UUID, payload: ApprovalDecisionIn, ctx: OrgCtx, db: Db) -> ApprovalRequestOut:
    """Approve or reject the current step. 409 if final, 403 if not the approver."""
    request = workflow_service.decide(db, ctx, request_id, payload)
    return workflow_service.to_out(db, request)


@router.post("/{request_id}/cancel", response_model=ApprovalRequestOut)
def cancel(request_id: uuid.UUID, ctx: OrgCtx, db: Db) -> ApprovalRequestOut:
    """Cancel a pending request (requester only)."""
    request = workflow_service.cancel_request(db, ctx, request_id)
    return workflow_service.to_out(db, request)
