"""FastAPI auth/permission dependencies.

The security core (Module 2). Every protected route depends on these, so tenant
isolation and role checks cannot be forgotten:

- ``get_current_user``  — decode the JWT, load the user, reject inactive users (401).
- ``get_org_context``   — read ``org_id`` from the token, then **re-check in the DB**
  that the user has an *active* membership in an *active* organization (403 otherwise,
  ``ORG_SUSPENDED`` for suspended orgs). Returns an ``OrgContext``.
- ``require_roles(*roles)`` — dependency factory; 403 if the caller's role is not allowed.
- ``require_platform_admin`` — 403 unless ``is_platform_admin``.

Why re-check in the DB instead of trusting the token: a token can outlive a
membership change (removed member, suspended org, changed role). Re-reading the
membership row on every request means a revocation takes effect immediately.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ForbiddenError, OrgSuspendedError, UnauthorizedError
from app.core.security import decode_token
from app.models.enums import MemberRole, MemberStatus, OrgStatus
from app.models.identity import Membership, Organization, User

# auto_error=False so we can return our own 401 with a WWW-Authenticate header.
_bearer = HTTPBearer(auto_error=False, description="Paste the access token from /auth/login")

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


@dataclass
class OrgContext:
    """The verified tenant context for a request."""

    user: User
    org_id: uuid.UUID
    role: MemberRole
    organization: Organization


def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    """Decode the bearer token. 401 if missing or invalid."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError(
            "Not authenticated", code="NOT_AUTHENTICATED", headers=_UNAUTHORIZED_HEADERS
        )
    return decode_token(credentials.credentials)


def get_current_user(
    payload: Annotated[dict, Depends(get_token_payload)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Load the authenticated user from the token's ``sub`` claim."""
    sub = payload.get("sub")
    try:
        user_id = uuid.UUID(str(sub))
    except (TypeError, ValueError):
        raise UnauthorizedError("Invalid authentication token", code="TOKEN_INVALID",
                                headers=_UNAUTHORIZED_HEADERS) from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive", code="USER_INACTIVE",
                                headers=_UNAUTHORIZED_HEADERS)
    return user


def get_org_context(
    payload: Annotated[dict, Depends(get_token_payload)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OrgContext:
    """Resolve and verify the active organization for the request."""
    org_id_raw = payload.get("org_id")
    if not org_id_raw:
        raise ForbiddenError(
            "No active workspace. Choose an organization first.",
            code="NO_ORG_CONTEXT",
        )
    try:
        org_id = uuid.UUID(str(org_id_raw))
    except ValueError:
        raise ForbiddenError("Invalid workspace", code="NO_ORG_CONTEXT") from None

    membership = db.execute(
        select(Membership).where(
            Membership.org_id == org_id,
            Membership.user_id == user.id,
            Membership.status == MemberStatus.active,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise ForbiddenError("You are not an active member of this organization",
                             code="NOT_A_MEMBER")

    org = db.get(Organization, org_id)
    if org is None:
        raise ForbiddenError("Organization not found", code="NOT_A_MEMBER")
    if org.status != OrgStatus.active:
        raise OrgSuspendedError("This organization is suspended", code="ORG_SUSPENDED")

    return OrgContext(user=user, org_id=org_id, role=membership.role, organization=org)


def require_roles(*roles: MemberRole):
    """Dependency factory: allow only the given roles (403 otherwise)."""

    def _dep(ctx: Annotated[OrgContext, Depends(get_org_context)]) -> OrgContext:
        if ctx.role not in roles:
            raise ForbiddenError(
                f"Role '{ctx.role.value}' is not allowed to perform this action",
                code="INSUFFICIENT_ROLE",
            )
        return ctx

    return _dep


def require_platform_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Allow only platform administrators."""
    if not user.is_platform_admin:
        raise ForbiddenError("Platform administrator access required", code="NOT_PLATFORM_ADMIN")
    return user


# Handy type aliases for router signatures.
CurrentUser = Annotated[User, Depends(get_current_user)]
OrgCtx = Annotated[OrgContext, Depends(get_org_context)]
PlatformAdmin = Annotated[User, Depends(require_platform_admin)]
