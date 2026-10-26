"""Permission matrix.

One place that maps an action name to the organization roles allowed to perform
it. Routers pass these constants to ``require_roles`` instead of hard-coding role
strings, so the policy is reviewable in a single table (see AGENT.md).
"""
from __future__ import annotations

from app.models.enums import MemberRole

# --- Action names ---
PROJECT_CREATE = "project.create"
PROJECT_UPDATE = "project.update"
PROJECT_ARCHIVE = "project.archive"
PROJECT_MEMBER_MANAGE = "project.member.manage"
TASK_CREATE = "task.create"
TASK_ASSIGN = "task.assign"
TASK_UPDATE = "task.update"
TASK_STATUS_CHANGE = "task.status_change"
WORKFLOW_MANAGE = "workflow.manage"
REQUEST_SUBMIT = "request.submit"
REQUEST_DECIDE = "request.decide"
AUDIT_VIEW = "audit.view"
REPORT_VIEW = "report.view"
MEMBER_MANAGE = "member.manage"
DASHBOARD_VIEW = "dashboard.view"
NOTIFICATION_VIEW = "notification.view"

_ADMIN = (MemberRole.org_admin,)
_ADMIN_MANAGER = (MemberRole.org_admin, MemberRole.manager)
_EVERYONE = (MemberRole.org_admin, MemberRole.manager, MemberRole.employee)

PERMISSIONS: dict[str, tuple[MemberRole, ...]] = {
    PROJECT_CREATE: _ADMIN,
    PROJECT_UPDATE: _ADMIN,
    PROJECT_ARCHIVE: _ADMIN,
    PROJECT_MEMBER_MANAGE: _ADMIN,
    TASK_CREATE: _ADMIN_MANAGER,
    TASK_ASSIGN: _ADMIN_MANAGER,
    TASK_UPDATE: _ADMIN_MANAGER,
    # Everyone may change status, but the service still limits it to the assignee.
    TASK_STATUS_CHANGE: _EVERYONE,
    WORKFLOW_MANAGE: _ADMIN,
    REQUEST_SUBMIT: _EVERYONE,
    # Real per-step authorization happens in workflow_engine; this entry documents
    # which roles can ever be approvers.
    REQUEST_DECIDE: _ADMIN_MANAGER,
    AUDIT_VIEW: _ADMIN,
    REPORT_VIEW: _ADMIN_MANAGER,
    MEMBER_MANAGE: _ADMIN,
    DASHBOARD_VIEW: _EVERYONE,
    NOTIFICATION_VIEW: _EVERYONE,
}
