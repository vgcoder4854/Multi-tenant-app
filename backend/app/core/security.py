"""Password hashing, JWT access tokens and invitation tokens.

- Passwords are stored only as Argon2 hashes (via ``pwdlib``); plaintext never
  touches the database or the logs.
- Access tokens are short-lived HS256 JWTs. The token carries the user id in
  ``sub`` and, once a workspace is chosen, ``org_id``. The backend still re-checks
  the membership in the database on every request — it never trusts these claims
  on their own.
- Invitation tokens are random URL-safe strings; only their SHA-256 hash is stored.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import settings
from app.core.errors import UnauthorizedError

# Argon2id (recommended) password hasher.
_password_hasher = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    """Hash a plaintext password. Returns an Argon2 hash string."""
    return _password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if ``plain`` matches ``hashed``; never raises on bad input."""
    try:
        return _password_hasher.verify(plain, hashed)
    except (UnknownHashError, ValueError):
        return False


def create_access_token(user_id: uuid.UUID | str, org_id: uuid.UUID | str | None = None) -> str:
    """Create a signed access token.

    Args:
        user_id: the authenticated user's id (becomes the ``sub`` claim).
        org_id: optional active organization id (added once a workspace is chosen).

    Returns:
        A signed JWT string (HS256).
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if org_id is not None:
        payload["org_id"] = str(org_id)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT.

    Raises:
        UnauthorizedError: if the token is expired, malformed or has a bad signature.
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired", code="TOKEN_EXPIRED") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid authentication token", code="TOKEN_INVALID") from exc


def generate_invite_token() -> tuple[str, str]:
    """Generate a single-use invitation token.

    Returns:
        ``(raw, token_hash)`` — send ``raw`` to the invitee, store only ``token_hash``.
    """
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    """SHA-256 hash of a token, used for lookups (never store the raw token)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
