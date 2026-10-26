"""Enumerations shared across models and schemas.

Stored as CHECK-constrained strings (``native_enum=False``) so the same schema
works on SQLite (dev) and PostgreSQL (prod). The playbook explicitly allows
"CHECK-constrained strings" instead of native PostgreSQL enum types.
"""
from __future__ import annotations

import enum


class OrgStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"


class MemberRole(str, enum.Enum):
    org_admin = "org_admin"
    manager = "manager"
    employee = "employee"


class MemberStatus(str, enum.Enum):
    active = "active"
    removed = "removed"


class InvitationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    revoked = "revoked"
    expired = "expired"


class ProjectStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    completed = "completed"


class ApproverType(str, enum.Enum):
    role = "role"
    user = "user"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class DecisionType(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"


class NotificationType(str, enum.Enum):
    task_assigned = "task_assigned"
    task_status_changed = "task_status_changed"
    approval_requested = "approval_requested"
    approval_decided = "approval_decided"
    task_due_soon = "task_due_soon"
    task_overdue = "task_overdue"
