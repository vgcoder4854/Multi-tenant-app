"""Authentication endpoints: register, login, me, switch-organization."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.auth import (
    LoginRequest,
    MeOut,
    RegisterRequest,
    SwitchOrganizationRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service, org_service

router = APIRouter(prefix="/auth", tags=["auth"])

Db = Annotated[Session, Depends(get_db)]


def _token_response(user_id, org_id=None) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id, org_id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register(payload: RegisterRequest, db: Db) -> UserOut:
    """Create an account. 409 if the email is already registered."""
    user = auth_service.register(
        db, email=payload.email, password=payload.password, full_name=payload.full_name
    )
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Db) -> TokenResponse:
    """Exchange email + password for an access token (identity only)."""
    user = auth_service.authenticate(db, email=payload.email, password=payload.password)
    return _token_response(user.id)


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser, db: Db) -> MeOut:
    """Current user plus their active memberships (for the workspace picker)."""
    return auth_service.build_me(db, user)


@router.post("/switch-organization", response_model=TokenResponse)
def switch_organization(payload: SwitchOrganizationRequest, user: CurrentUser, db: Db) -> TokenResponse:
    """Return a new token scoped to ``org_id`` (403 if not an active member)."""
    org = org_service.switch_organization(db, user, payload.org_id)
    return _token_response(user.id, org.id)
