"""Append-only audit trail (Module 6).

``record`` writes one audit row inside the *same transaction* as the action it
describes, so a rolled-back action never leaves an audit row (and vice versa).
The database trigger installed in migration 4.2.4 blocks any UPDATE/DELETE, so the
log cannot be altered even by a bug.

Store only safe metadata (ids, names, statuses) — never passwords or tokens.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.comms import AuditLog


def record(
    db: Session,
    ctx: Any,
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
    *,
    org_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
) -> AuditLog:
    """Insert an audit row (does not commit; the caller's transaction does).

    ``ctx`` may be an ``OrgContext`` (org_id + user), a ``User``, or ``None``.
    Explicit ``org_id`` / ``actor_id`` override what is derived from ``ctx``.
    """
    derived_org = getattr(ctx, "org_id", None)
    user = getattr(ctx, "user", ctx)
    derived_actor = getattr(user, "id", None)

    log = AuditLog(
        org_id=org_id if org_id is not None else derived_org,
        actor_id=actor_id if actor_id is not None else derived_actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        meta=metadata or {},
    )
    db.add(log)
    db.flush()
    return log


# --- Action name constants (kept in one place; see AGENT.md action table) ---
ORG_CREATED = "org.created"
ORG_SUSPENDED = "org.suspended"
ORG_ACTIVATED = "org.activated"
INVITATION_CREATED = "invitation.created"
INVITATION_REVOKED = "invitation.revoked"
INVITATION_ACCEPTED = "invitation.accepted"
MEMBER_ROLE_CHANGED = "member.role_changed"
MEMBER_REMOVED = "member.removed"
PROJECT_CREATED = "project.created"
PROJECT_UPDATED = "project.updated"
PROJECT_ARCHIVED = "project.archived"
PROJECT_MEMBER_ADDED = "project.member_added"
PROJECT_MEMBER_REMOVED = "project.member_removed"
TASK_CREATED = "task.created"
TASK_UPDATED = "task.updated"
TASK_ASSIGNED = "task.assigned"
TASK_STATUS_CHANGED = "task.status_changed"
TEMPLATE_CREATED = "workflow.template_created"
TEMPLATE_UPDATED = "workflow.template_updated"
TEMPLATE_DEACTIVATED = "workflow.template_deactivated"
REQUEST_SUBMITTED = "request.submitted"
REQUEST_APPROVED = "request.approved"
REQUEST_REJECTED = "request.rejected"
REQUEST_CANCELLED = "request.cancelled"
