"""Versioned API router.

Every feature module contributes a router that is included here under ``/api/v1``.
Routers only parse HTTP and call services — no business logic lives here.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    admin,
    approvals,
    audit,
    auth,
    dashboard,
    notifications,
    organizations,
    platform,
    projects,
    tasks,
    workflows,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(organizations.organizations_router)
api_router.include_router(organizations.org_router)
api_router.include_router(organizations.invitations_router)
api_router.include_router(platform.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(workflows.router)
api_router.include_router(approvals.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
api_router.include_router(audit.router)
api_router.include_router(audit.platform_router)
api_router.include_router(dashboard.router)
