"""Application entry point.

Wires CORS, the standard error handler, a ``/health`` endpoint (which also checks
DB connectivity) and the versioned API router at ``/api/v1``.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import api_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import AppError


def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Tenant Workflow Platform",
        version="1.0.0",
        description=(
            "Enterprise SaaS workflow platform: projects, tasks, sequential "
            "approvals, notifications and audit — with strict per-organization "
            "isolation enforced on the backend.\n\n"
            "**Authentication:** call `/auth/login`, then `/auth/switch-organization` "
            "to get a token scoped to one organization. Send it as `Authorization: Bearer <token>`.\n\n"
            "**Errors:** every error is `{\"detail\": str, \"code\": str}`. Cross-tenant "
            "IDs return 404."
        ),
        openapi_tags=[
            {"name": "meta", "description": "Health and root."},
            {"name": "auth", "description": "Register, login, current user, workspace switching."},
            {"name": "organizations", "description": "Create and list organizations."},
            {"name": "org", "description": "Invitations and members of the active organization."},
            {"name": "invitations", "description": "Accept an invitation."},
            {"name": "platform-admin", "description": "Platform-wide administration (requires is_platform_admin)."},
            {"name": "projects", "description": "Projects and project members."},
            {"name": "tasks", "description": "Tasks, assignment and status history."},
            {"name": "workflow-templates", "description": "Ordered approval templates (org_admin)."},
            {"name": "approvals", "description": "Submit, decide and cancel approval requests."},
            {"name": "notifications", "description": "In-app notifications."},
            {"name": "admin", "description": "Administrative/demo actions."},
            {"name": "audit", "description": "Append-only audit trail (org_admin)."},
            {"name": "dashboard", "description": "Role-scoped metrics and CSV export."},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Standard error JSON: {"detail": ..., "code": ...} ---
    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        body: dict = {"detail": exc.detail, "code": exc.code}
        body.update(exc.extra)
        return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers or None)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Normalise FastAPI's default validation error into our standard shape and
        # keep it JSON-serializable (Pydantic can attach a raw ValueError in ctx).
        import json

        def _safe(err: dict) -> dict:
            out = {
                "type": err.get("type"),
                "loc": list(err.get("loc", [])),
                "msg": err.get("msg"),
            }
            value = err.get("input")
            try:
                json.dumps(value)
                out["input"] = value
            except (TypeError, ValueError):
                out["input"] = str(value)
            return out

        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error",
                "code": "VALIDATION_ERROR",
                "errors": [_safe(e) for e in exc.errors()],
            },
        )

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        """Liveness + DB connectivity check."""
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception as exc:
            db_status = f"error: {exc}"
        finally:
            db.close()
        return {"status": "ok", "database": db_status, "environment": settings.environment}

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {
            "name": "Multi-Tenant Workflow Platform",
            "docs": "/docs",
            "api": "/api/v1",
        }

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
