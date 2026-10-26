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
            "isolation enforced on the backend."
        ),
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
        # Normalise FastAPI's default validation error into our standard shape.
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error",
                "code": "VALIDATION_ERROR",
                "errors": exc.errors(),
            },
        )

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        """Liveness + DB connectivity check."""
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception as exc:  # noqa: BLE001
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
