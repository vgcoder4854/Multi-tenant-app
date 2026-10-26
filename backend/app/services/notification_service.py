"""In-app notifications (Module 5).

Other services call ``notify(...)`` *inside their own transaction*, so a rolled-back
business action never leaves a notification behind. ``notify`` skips the actor (you
are not notified about your own action) and de-duplicates recipients.

This module also holds the read/list helpers used by the notifications API.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.comms import Notification
from app.models.enums import NotificationType


def notify(
    db: Session,
    *,
    org_id: uuid.UUID,
    user_ids: Iterable[uuid.UUID | None],
    type: NotificationType,
    title: str,
    body: str | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
) -> list[Notification]:
    """Create one notification row per recipient (excluding the actor and Nones).

    Does not commit; the caller's transaction commits once at the end.
    """
    recipients = {uid for uid in user_ids if uid is not None and uid != actor_id}
    created: list[Notification] = []
    for uid in recipients:
        n = Notification(
            org_id=org_id,
            user_id=uid,
            type=type,
            title=title,
            body=body,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        db.add(n)
        created.append(n)
    db.flush()
    return created


# --------------------------------------------------------------------------- #
# Read helpers (used by the notifications API)
# --------------------------------------------------------------------------- #
def list_notifications(
    db: Session,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    unread_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Notification], int]:
    stmt = select(Notification).where(
        Notification.org_id == org_id, Notification.user_id == user_id
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(Notification.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).scalars().all()
    )
    return list(rows), total


def unread_count(db: Session, *, org_id: uuid.UUID, user_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.org_id == org_id,
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    ).scalar_one()


def mark_read(
    db: Session, *, org_id: uuid.UUID, user_id: uuid.UUID, notification_id: uuid.UUID
) -> Notification:
    """Mark one notification as read. Someone else's notification is a 404."""
    n = db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.org_id == org_id,
            Notification.user_id == user_id,
        )
    ).scalar_one_or_none()
    if n is None:
        raise NotFoundError("Notification not found")
    if not n.is_read:
        n.is_read = True
        n.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(n)
    return n


def mark_all_read(db: Session, *, org_id: uuid.UUID, user_id: uuid.UUID) -> int:
    """Mark every unread notification of the caller as read; returns how many."""
    rows = db.execute(
        select(Notification).where(
            Notification.org_id == org_id,
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    ).scalars().all()
    now = datetime.now(timezone.utc)
    for n in rows:
        n.is_read = True
        n.read_at = now
    db.commit()
    return len(rows)


def already_notified(
    db: Session,
    *,
    user_id: uuid.UUID,
    type: NotificationType,
    resource_id: uuid.UUID,
    since: datetime,
) -> bool:
    """True if a notification of this type/resource already exists for the user today."""
    return db.execute(
        select(Notification.id)
        .where(
            Notification.user_id == user_id,
            Notification.type == type,
            Notification.resource_id == resource_id,
            Notification.created_at >= since,
        )
        .limit(1)
    ).first() is not None
