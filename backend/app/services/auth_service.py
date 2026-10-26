"""Authentication service: register, login, and "me"."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models.enums import MemberStatus
from app.models.identity import Membership, Organization, User
from app.schemas.auth import MeOut, MembershipOut


def get_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()


def register(db: Session, *, email: str, password: str, full_name: str) -> User:
    """Create a user. 409 if the email already exists."""
    email = email.strip().lower()
    if get_by_email(db, email) is not None:
        raise ConflictError("An account with this email already exists", code="EMAIL_TAKEN")
    user = User(
        email=email,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    """Verify credentials. Same 401 message for unknown email and wrong password."""
    user = get_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        # Deliberately identical message to avoid leaking which emails exist.
        raise UnauthorizedError("Invalid email or password", code="INVALID_CREDENTIALS")
    if not user.is_active:
        raise UnauthorizedError("This account is inactive", code="USER_INACTIVE")
    return user


def build_me(db: Session, user: User) -> MeOut:
    """User profile plus their active memberships (for the workspace picker)."""
    rows = db.execute(
        select(Membership, Organization)
        .join(Organization, Membership.org_id == Organization.id)
        .where(Membership.user_id == user.id, Membership.status == MemberStatus.active)
        .order_by(Organization.name)
    ).all()
    memberships = [
        MembershipOut(
            org_id=org.id,
            org_name=org.name,
            org_slug=org.slug,
            role=membership.role,
            status=membership.status,
        )
        for membership, org in rows
    ]
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_platform_admin=user.is_platform_admin,
        is_active=user.is_active,
        created_at=user.created_at,
        memberships=memberships,
    )
