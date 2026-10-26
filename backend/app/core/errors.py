"""Application-wide error types and the standard error JSON shape.

Every error response looks like:
    {"detail": "human readable message", "code": "MACHINE_CODE"}

Services raise these typed errors; a single handler in ``app.main`` turns them
into HTTP responses with the right status code. This keeps routers thin and makes
error handling consistent everywhere.
"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for expected, business-level errors."""

    status_code: int = 400
    code: str = "ERROR"

    def __init__(
        self,
        detail: str | None = None,
        *,
        status_code: int | None = None,
        code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.__class__.__doc__ or "Error"
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.extra = extra or {}
        super().__init__(self.detail)


class UnauthorizedError(AppError):
    """Authentication required or invalid credentials."""

    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    """Authenticated but not allowed to perform this action."""

    status_code = 403
    code = "FORBIDDEN"


class OrgSuspendedError(ForbiddenError):
    """This organization is suspended; tenant endpoints are blocked."""

    code = "ORG_SUSPENDED"


class NotFoundError(AppError):
    """Resource not found in the current organization."""

    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    """The action conflicts with the current state of the resource."""

    status_code = 409
    code = "CONFLICT"


class ValidationError(AppError):
    """The request is syntactically valid but fails a business rule."""

    status_code = 422
    code = "VALIDATION_ERROR"
