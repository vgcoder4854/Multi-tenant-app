"""Unit tests for the security helpers (no database needed)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core import security
from app.core.config import settings
from app.core.errors import UnauthorizedError


def test_hash_and_verify_password_roundtrip():
    hashed = security.hash_password("Password123!")
    assert hashed != "Password123!"
    assert security.verify_password("Password123!", hashed) is True
    assert security.verify_password("wrong-password", hashed) is False


def test_hash_is_salted():
    assert security.hash_password("same") != security.hash_password("same")


def test_verify_password_bad_hash_returns_false():
    assert security.verify_password("x", "not-a-real-hash") is False


def test_access_token_roundtrip_without_org():
    uid = uuid.uuid4()
    token = security.create_access_token(uid)
    payload = security.decode_token(token)
    assert payload["sub"] == str(uid)
    assert "org_id" not in payload


def test_access_token_carries_org():
    uid, oid = uuid.uuid4(), uuid.uuid4()
    payload = security.decode_token(security.create_access_token(uid, oid))
    assert payload["org_id"] == str(oid)


def test_decode_expired_token_raises():
    expired = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(UnauthorizedError) as exc:
        security.decode_token(expired)
    assert exc.value.code == "TOKEN_EXPIRED"


def test_decode_invalid_token_raises():
    with pytest.raises(UnauthorizedError) as exc:
        security.decode_token("not.a.jwt")
    assert exc.value.code == "TOKEN_INVALID"


def test_invite_token_is_random_and_hashed():
    raw1, hash1 = security.generate_invite_token()
    raw2, hash2 = security.generate_invite_token()
    assert raw1 != raw2
    assert hash1 == security.hash_token(raw1)
    assert hash1 != raw1  # only the hash is ever stored
