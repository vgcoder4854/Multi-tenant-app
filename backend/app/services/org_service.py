"""Organization management service (Module 1).

Covers creating an organization, listing a user's workspaces, switching workspace,
inviting/revoking/accepting invitations, and managing members. Every multi-record
change runs in one transaction; the caller (router) never commits.

Rule enforced here: an organization must always keep **at least one active
org_admin** — demoting or removing the last one is a 409.
"""
from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import generate_invite_token, hash_token
from app.models.enums import InvitationStatus, MemberRole, MemberStatus, OrgStatus
from app.models.identity import Invitation, Membership, Organization, User
from app.schemas.org import InvitationOut, MemberOut, MyOrganizationOut
from app.services import audit_service, email_service
from app.services.tenant import get_in_org

INVITATION_EXPIRE_DAYS = 7


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    while db.execute(select(Organization.id).where(Organization.slug == slug)).first():
        slug = f"{base}-{secrets.token_hex(2)}"
    return slug


# --------------------------------------------------------------------------- #
# Organizations
# --------------------------------------------------------------------------- #
def create_organization(
    db: Session, user: User, *, name: str, slug: str | None = None
) -> Organization:
    """Create an org, make the creator its org_admin, and audit it — atomically."""
    name = name.strip()
    if slug:
        desired = _slugify(slug)
        if db.execute(select(Organization.id).where(Organization.slug == desired)).first():
            raise ConflictError("That slug is already taken", code="SLUG_TAKEN")
        final_slug = desired
    else:
        final_slug = _unique_slug(db, _slugify(name))

    org = Organization(name=name, slug=final_slug, status=OrgStatus.active)
    db.add(org)
    db.flush()

    membership = Membership(
        org_id=org.id, user_id=user.id, role=MemberRole.org_admin, status=MemberStatus.active
    )
    db.add(membership)
    audit_service.record(
        db, user, audit_service.ORG_CREATED, "organization", org.id,
        {"name": org.name, "slug": org.slug}, org_id=org.id,
    )
    db.commit()
    db.refresh(org)
    return org


def list_my_organizations(db: Session, user: User) -> list[MyOrganizationOut]:
    rows = db.execute(
        select(Organization, Membership.role)
        .join(Membership, Membership.org_id == Organization.id)
        .where(Membership.user_id == user.id, Membership.status == MemberStatus.active)
        .order_by(Organization.name)
    ).all()
    return [
        MyOrganizationOut(
            id=org.id, name=org.name, slug=org.slug, status=org.status,
            created_at=org.created_at, role=role,
        )
        for org, role in rows
    ]


def get_active_membership(db: Session, user: User, org_id: uuid.UUID) -> Membership:
    """Return the user's active membership in ``org_id`` or raise 403."""
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
    return membership


def switch_organization(db: Session, user: User, org_id: uuid.UUID) -> Organization:
    """Verify active membership before issuing a new org-scoped token.

    We deliberately do NOT block a suspended org here: the user may still switch in
    and will see a clear "suspended" message; tenant endpoints are blocked by
    ``get_org_context`` (ORG_SUSPENDED).
    """
    membership = get_active_membership(db, user, org_id)
    org = db.get(Organization, membership.org_id)
    if org is None:
        raise ForbiddenError("Organization not found", code="NOT_A_MEMBER")
    return org


# --------------------------------------------------------------------------- #
# Invitations
# --------------------------------------------------------------------------- #
def invite_member(
    db: Session, *, org: Organization, actor: User, email: str, role: MemberRole
) -> tuple[Invitation, str]:
    email = email.strip().lower()

    existing_user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing_user is not None:
        already = db.execute(
            select(Membership).where(
                Membership.org_id == org.id,
                Membership.user_id == existing_user.id,
                Membership.status == MemberStatus.active,
            )
        ).scalar_one_or_none()
        if already is not None:
            raise ConflictError("That user is already a member", code="ALREADY_MEMBER")

    pending = db.execute(
        select(Invitation).where(
            Invitation.org_id == org.id,
            Invitation.email == email,
            Invitation.status == InvitationStatus.pending,
        )
    ).scalar_one_or_none()
    if pending is not None:
        raise ConflictError("A pending invitation already exists for this email",
                            code="INVITATION_EXISTS")

    raw, token_hash = generate_invite_token()
    invitation = Invitation(
        org_id=org.id,
        email=email,
        role=role,
        token_hash=token_hash,
        status=InvitationStatus.pending,
        invited_by=actor.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRE_DAYS),
    )
    db.add(invitation)
    db.flush()
    audit_service.record(
        db, None, audit_service.INVITATION_CREATED, "invitation", invitation.id,
        {"email": email, "role": role.value}, org_id=org.id, actor_id=actor.id,
    )
    email_service.send_invitation_email(
        to_email=email, org_name=org.name, role=role.value, raw_token=raw
    )
    db.commit()
    db.refresh(invitation)
    return invitation, raw


def list_invitations(db: Session, org_id: uuid.UUID) -> list[InvitationOut]:
    rows = db.execute(
        select(Invitation)
        .where(Invitation.org_id == org_id)
        .order_by(Invitation.created_at.desc())
    ).scalars().all()
    return [InvitationOut.model_validate(r) for r in rows]


def revoke_invitation(db: Session, *, org_id: uuid.UUID, invitation_id: uuid.UUID, actor: User) -> None:
    invitation = get_in_org(db, Invitation, invitation_id, org_id)
    if invitation.status != InvitationStatus.pending:
        raise ConflictError("Only pending invitations can be revoked",
                            code="INVITATION_NOT_PENDING")
    invitation.status = InvitationStatus.revoked
    audit_service.record(
        db, None, audit_service.INVITATION_REVOKED, "invitation", invitation.id,
        {"email": invitation.email}, org_id=org_id, actor_id=actor.id,
    )
    db.commit()


def accept_invitation(db: Session, user: User, raw_token: str) -> Membership:
    """Accept an invitation: validate hash/status/expiry, create membership atomically."""
    invitation = db.execute(
        select(Invitation).where(Invitation.token_hash == hash_token(raw_token))
    ).scalar_one_or_none()
    if invitation is None:
        raise NotFoundError("Invitation not found", code="INVITATION_NOT_FOUND")
    if invitation.status != InvitationStatus.pending:
        raise ConflictError("This invitation is no longer valid", code="INVITATION_NOT_PENDING")
    if invitation.expires_at <= datetime.now(timezone.utc):
        invitation.status = InvitationStatus.expired
        db.commit()
        raise ValidationError("This invitation has expired", code="INVITATION_EXPIRED")

    # Email must match the invitee.
    if invitation.email != user.email.strip().lower():
        raise ForbiddenError("This invitation was issued to a different email",
                             code="INVITATION_EMAIL_MISMATCH")

    existing = db.execute(
        select(Membership).where(
            Membership.org_id == invitation.org_id, Membership.user_id == user.id
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.status == MemberStatus.active:
            raise ConflictError("You are already a member", code="ALREADY_MEMBER")
        # Re-activate a previously removed membership.
        existing.status = MemberStatus.active
        existing.role = invitation.role
        membership = existing
    else:
        membership = Membership(
            org_id=invitation.org_id, user_id=user.id,
            role=invitation.role, status=MemberStatus.active,
        )
        db.add(membership)

    invitation.status = InvitationStatus.accepted
    db.flush()
    audit_service.record(
        db, None, audit_service.INVITATION_ACCEPTED, "invitation", invitation.id,
        {"user_id": str(user.id), "role": invitation.role.value},
        org_id=invitation.org_id, actor_id=user.id,
    )
    db.commit()
    return membership


# --------------------------------------------------------------------------- #
# Members
# --------------------------------------------------------------------------- #
def list_members(db: Session, org_id: uuid.UUID) -> list[MemberOut]:
    rows = db.execute(
        select(Membership, User)
        .join(User, Membership.user_id == User.id)
        .where(Membership.org_id == org_id)
        .order_by(User.full_name)
    ).all()
    return [
        MemberOut(
            user_id=user.id, email=user.email, full_name=user.full_name,
            role=membership.role, status=membership.status, created_at=membership.created_at,
        )
        for membership, user in rows
    ]


def _active_admin_count(db: Session, org_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(Membership)
        .where(
            Membership.org_id == org_id,
            Membership.role == MemberRole.org_admin,
            Membership.status == MemberStatus.active,
        )
    ).scalar_one()


def _membership_in_org(db: Session, org_id: uuid.UUID, user_id: uuid.UUID) -> Membership:
    membership = db.execute(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
    ).scalar_one_or_none()
    if membership is None:
        raise NotFoundError("Member not found")
    return membership


def change_member_role(
    db: Session, *, org_id: uuid.UUID, user_id: uuid.UUID, role: MemberRole, actor: User
) -> Membership:
    membership = _membership_in_org(db, org_id, user_id)
    if membership.status != MemberStatus.active:
        raise ConflictError("This member is not active", code="MEMBER_NOT_ACTIVE")
    if (
        membership.role == MemberRole.org_admin
        and role != MemberRole.org_admin
        and _active_admin_count(db, org_id) <= 1
    ):
        raise ConflictError(
            "An organization must keep at least one active org_admin",
            code="LAST_ADMIN",
        )
    old_role = membership.role
    membership.role = role
    audit_service.record(
        db, None, audit_service.MEMBER_ROLE_CHANGED, "membership", membership.id,
        {"user_id": str(user_id), "from": old_role.value, "to": role.value},
        org_id=org_id, actor_id=actor.id,
    )
    db.commit()
    db.refresh(membership)
    return membership


def remove_member(db: Session, *, org_id: uuid.UUID, user_id: uuid.UUID, actor: User) -> None:
    membership = _membership_in_org(db, org_id, user_id)
    if membership.status != MemberStatus.active:
        raise ConflictError("This member is not active", code="MEMBER_NOT_ACTIVE")
    if membership.role == MemberRole.org_admin and _active_admin_count(db, org_id) <= 1:
        raise ConflictError(
            "An organization must keep at least one active org_admin", code="LAST_ADMIN"
        )
    membership.status = MemberStatus.removed
    audit_service.record(
        db, None, audit_service.MEMBER_REMOVED, "membership", membership.id,
        {"user_id": str(user_id)}, org_id=org_id, actor_id=actor.id,
    )
    db.commit()
