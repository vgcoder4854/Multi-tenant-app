"""Notification endpoints (Module 5)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import OrgCtx
from app.core.database import get_db
from app.schemas.common import Page
from app.schemas.notification import NotificationOut, UnreadCountOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])

Db = Annotated[Session, Depends(get_db)]


@router.get("", response_model=Page[NotificationOut])
def list_notifications(
    ctx: OrgCtx,
    db: Db,
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[NotificationOut]:
    """The caller's notifications in the active org (newest first)."""
    items, total = notification_service.list_notifications(
        db, org_id=ctx.org_id, user_id=ctx.user.id,
        unread_only=unread_only, page=page, page_size=page_size,
    )
    return Page[NotificationOut](
        items=[NotificationOut.model_validate(n) for n in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/unread-count", response_model=UnreadCountOut)
def unread_count(ctx: OrgCtx, db: Db) -> UnreadCountOut:
    return UnreadCountOut(
        unread=notification_service.unread_count(db, org_id=ctx.org_id, user_id=ctx.user.id)
    )


@router.post("/read-all", response_model=UnreadCountOut)
def mark_all_read(ctx: OrgCtx, db: Db) -> UnreadCountOut:
    """Mark all of the caller's notifications as read."""
    notification_service.mark_all_read(db, org_id=ctx.org_id, user_id=ctx.user.id)
    return UnreadCountOut(
        unread=notification_service.unread_count(db, org_id=ctx.org_id, user_id=ctx.user.id)
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: uuid.UUID, ctx: OrgCtx, db: Db) -> NotificationOut:
    """Mark one notification as read. Someone else's notification -> 404."""
    n = notification_service.mark_read(
        db, org_id=ctx.org_id, user_id=ctx.user.id, notification_id=notification_id
    )
    return NotificationOut.model_validate(n)
