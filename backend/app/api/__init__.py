"""Versioned API router.

Every feature module contributes a router that is included here under ``/api/v1``.
Routers only parse HTTP and call services — no business logic lives here.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api import auth, organizations, platform, projects, tasks

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(organizations.organizations_router)
api_router.include_router(organizations.org_router)
api_router.include_router(organizations.invitations_router)
api_router.include_router(platform.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
