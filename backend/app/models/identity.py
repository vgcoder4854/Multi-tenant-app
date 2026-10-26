"""Identity and tenancy tables (group A).

users, organizations, memberships, invitations.

A user belongs to many organizations through ``memberships`` (with a different
role in each). ``invitations`` store only a hash of the single-use token.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.enums import InvitationStatus, MemberRole, MemberStatus, OrgStatus
from app.models.mixins import CreatedAtMixin, TZDateTime, UUIDMixin, enum_col


class User(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_platform_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @validates("email")
    def _lower_email(self, _key: str, value: str) -> str:
        """Always store emails lowercased so uniqueness is case-insensitive."""
        return value.strip().lower()


class Organization(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    status: Mapped[OrgStatus] = mapped_column(
        enum_col(OrgStatus, "org_status"), default=OrgStatus.active, nullable=False
    )


class Membership(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "memberships"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MemberRole] = mapped_column(enum_col(MemberRole, "member_role"), nullable=False)
    status: Mapped[MemberStatus] = mapped_column(
        enum_col(MemberStatus, "member_status"), default=MemberStatus.active, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship()

    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_membership_org_user"),
        # Target for composite FKs that keep related rows in the same org.
        UniqueConstraint("org_id", "id", name="uq_membership_org_id_id"),
        Index("ix_membership_org_status", "org_id", "status"),
    )


class Invitation(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "invitations"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[MemberRole] = mapped_column(enum_col(MemberRole, "member_role"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[InvitationStatus] = mapped_column(
        enum_col(InvitationStatus, "invitation_status"),
        default=InvitationStatus.pending,
        nullable=False,
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)

    __table_args__ = (
        # One pending invitation per email per org. Emails are stored lowercased,
        # so a plain partial unique index is equivalent to lower(email).
        Index(
            "uq_pending_invitation_email",
            "org_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    @validates("email")
    def _lower_email(self, _key: str, value: str) -> str:
        return value.strip().lower()
