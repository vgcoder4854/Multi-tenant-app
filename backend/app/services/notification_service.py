"""In-app notifications (Module 5).

Other services call ``notify(...)`` *inside their own transaction*, so a rolled-back
business action never leaves a notification behind. ``notify`` skips the actor (you
are not notified about your own action) and de-duplicates recipients.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy.orm import Session

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
