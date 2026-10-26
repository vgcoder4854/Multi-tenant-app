"""Versioned API router.

Every feature module contributes a router that is included here under ``/api/v1``.
Routers only parse HTTP and call services — no business logic lives here.
"""
from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()

# Feature routers are registered here as each module is built (4.3+).
