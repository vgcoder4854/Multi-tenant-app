"""Organization, member and invitation endpoints (Module 1)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, OrgContext, OrgCtx, require_roles
from app.core.database import get_db
from app.models.enums import MemberRole
from app.models.identity import Organization
from app.schemas.org import (
    InvitationAccept,
    InvitationCreate,
    InvitationCreatedOut,
    InvitationOut,
    MemberOut,
    MemberRoleUpdate,
    MyOrganizationOut,
    OrganizationCreate,
    OrganizationOut,
)
from app.services import org_service

Db = Annotated[Session, Depends(get_db)]

# Only org_admin may manage members and invitations.
AdminCtx = Annotated[OrgContext, Depends(require_roles(MemberRole.org_admin))]

organizations_router = APIRouter(prefix="/organizations", tags=["organizations"])
org_router = APIRouter(prefix="/org", tags=["org"])
invitations_router = APIRouter(prefix="/invitations", tags=["invitations"])


# --------------------------------------------------------------------------- #
# Organizations
# --------------------------------------------------------------------------- #
@organizations_router.post("", status_code=status.HTTP_201_CREATED, response_model=OrganizationOut)
def create_organization(payload: OrganizationCreate, user: CurrentUser, db: Db) -> OrganizationOut:
    """Create an organization; the creator becomes its org_admin."""
    org = org_service.create_organization(db, user, name=payload.name, slug=payload.slug)
    return OrganizationOut.model_validate(org)


@organizations_router.get("/mine", response_model=list[MyOrganizationOut])
def my_organizations(user: CurrentUser, db: Db) -> list[MyOrganizationOut]:
    """The organizations the current user is an active member of."""
    return org_service.list_my_organizations(db, user)


# --------------------------------------------------------------------------- #
# Invitations (org_admin only)
# --------------------------------------------------------------------------- #
@org_router.post(
    "/invitations", status_code=status.HTTP_201_CREATED, response_model=InvitationCreatedOut
)
def create_invitation(payload: InvitationCreate, ctx: AdminCtx, db: Db) -> InvitationCreatedOut:
    """Invite someone by email. The raw token is returned once (also mocked-emailed)."""
    invitation, raw = org_service.invite_member(
        db, org=ctx.organization, actor=ctx.user, email=payload.email, role=payload.role
    )
    return InvitationCreatedOut(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        token=raw,
    )


@org_router.get("/invitations", response_model=list[InvitationOut])
def list_invitations(ctx: AdminCtx, db: Db) -> list[InvitationOut]:
    return org_service.list_invitations(db, ctx.org_id)


@org_router.delete(
    "/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def revoke_invitation(invitation_id: uuid.UUID, ctx: AdminCtx, db: Db) -> None:
    org_service.revoke_invitation(
        db, org_id=ctx.org_id, invitation_id=invitation_id, actor=ctx.user
    )


# --------------------------------------------------------------------------- #
# Members
# --------------------------------------------------------------------------- #
@org_router.get("/members", response_model=list[MemberOut])
def list_members(ctx: OrgCtx, db: Db) -> list[MemberOut]:
    """List members of the active org (readable by any member, for assignee pickers)."""
    return org_service.list_members(db, ctx.org_id)


@org_router.patch("/members/{user_id}/role", response_model=MemberOut)
def change_member_role(
    user_id: uuid.UUID, payload: MemberRoleUpdate, ctx: AdminCtx, db: Db
) -> MemberOut:
    org_service.change_member_role(
        db, org_id=ctx.org_id, user_id=user_id, role=payload.role, actor=ctx.user
    )
    return next(m for m in org_service.list_members(db, ctx.org_id) if m.user_id == user_id)


@org_router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def remove_member(user_id: uuid.UUID, ctx: AdminCtx, db: Db) -> None:
    org_service.remove_member(db, org_id=ctx.org_id, user_id=user_id, actor=ctx.user)


# --------------------------------------------------------------------------- #
# Accept invitation (authenticated user; no org context needed)
# --------------------------------------------------------------------------- #
@invitations_router.post("/accept", response_model=OrganizationOut)
def accept_invitation(payload: InvitationAccept, user: CurrentUser, db: Db) -> OrganizationOut:
    """Accept an invitation token; creates the membership and returns the org."""
    membership = org_service.accept_invitation(db, user, payload.token)
    org = db.get(Organization, membership.org_id)
    return OrganizationOut.model_validate(org)
