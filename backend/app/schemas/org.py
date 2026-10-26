"""Organization, invitation and membership schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import InvitationStatus, MemberRole, MemberStatus, OrgStatus


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str | None = Field(default=None, max_length=120)


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: OrgStatus
    created_at: datetime


class MyOrganizationOut(OrganizationOut):
    role: MemberRole


class InvitationCreate(BaseModel):
    email: EmailStr
    role: MemberRole


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: MemberRole
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime


class InvitationCreatedOut(InvitationOut):
    # The raw token is returned exactly once (also logged by the mocked email service).
    token: str


class InvitationAccept(BaseModel):
    token: str = Field(min_length=10)


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: MemberRole
    status: MemberStatus
    created_at: datetime


class MemberRoleUpdate(BaseModel):
    role: MemberRole


class OrganizationStatusUpdate(BaseModel):
    status: OrgStatus
