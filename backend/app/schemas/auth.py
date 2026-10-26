"""Auth request/response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import MemberRole, MemberStatus


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: uuid.UUID
    org_name: str
    org_slug: str
    role: MemberRole
    status: MemberStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_platform_admin: bool
    is_active: bool
    created_at: datetime


class MeOut(UserOut):
    memberships: list[MembershipOut] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class SwitchOrganizationRequest(BaseModel):
    org_id: uuid.UUID
