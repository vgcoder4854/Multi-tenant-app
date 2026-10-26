"""End-to-end tests for auth + organization management (Module 1)."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.enums import MemberRole, MemberStatus, OrgStatus
from app.models.identity import Membership
from tests.factories import add_member, create_org, create_user


def test_register_login_me(client, db):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "Alice@Example.com", "password": "Password123!", "full_name": "Alice"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "alice@example.com"  # normalised
    assert "password_hash" not in r.json()

    # duplicate email -> 409
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "Password123!", "full_name": "Alice2"},
    )
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_TAKEN"

    # login
    r = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "Password123!"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"
    assert r.json()["memberships"] == []


def test_login_wrong_password_same_message(client, db):
    create_user(db, email="bob@example.com", password="Password123!")
    r1 = client.post("/api/v1/auth/login", json={"email": "bob@example.com", "password": "wrong"})
    r2 = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]  # no user enumeration


def test_protected_requires_token(client, db):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate") == "Bearer"


def test_create_org_and_switch(client, db, login):
    admin = create_user(db, email="admin1@example.com")
    r = client.post(
        "/api/v1/organizations",
        json={"name": "Acme"},
        headers=login("admin1@example.com"),
    )
    assert r.status_code == 201, r.text
    org_id = r.json()["id"]

    # creator is an active org_admin
    m = db.execute(select(Membership).where(Membership.org_id == uuid.UUID(org_id))).scalar_one()
    assert m.role == MemberRole.org_admin and m.status == MemberStatus.active

    # mine lists it
    r = client.get("/api/v1/organizations/mine", headers=login("admin1@example.com"))
    assert [o["id"] for o in r.json()] == [org_id]

    # switch to it -> token with org_id works on an org endpoint
    headers = login("admin1@example.com", org_id=org_id)
    r = client.get("/api/v1/org/members", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1


def test_switch_to_foreign_org_is_403(client, db, login):
    user = create_user(db, email="u@example.com")
    org = create_org(db)  # user is NOT a member
    r = client.post(
        "/api/v1/auth/switch-organization",
        json={"org_id": str(org.id)},
        headers=login("u@example.com"),
    )
    assert r.status_code == 403


def test_invitation_flow(client, db, login):
    admin = create_user(db, email="admin2@example.com")
    r = client.post("/api/v1/organizations", json={"name": "InviteOrg"}, headers=login("admin2@example.com"))
    org_id = r.json()["id"]
    admin_headers = login("admin2@example.com", org_id=org_id)

    # invite
    r = client.post(
        "/api/v1/org/invitations",
        json={"email": "newbie@example.com", "role": "employee"},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    token = r.json()["token"]
    assert token and r.json()["status"] == "pending"

    # duplicate pending -> 409
    r = client.post(
        "/api/v1/org/invitations",
        json={"email": "newbie@example.com", "role": "employee"},
        headers=admin_headers,
    )
    assert r.status_code == 409

    # accept
    invitee = create_user(db, email="newbie@example.com")
    r = client.post(
        "/api/v1/invitations/accept",
        json={"token": token},
        headers=login("newbie@example.com"),
    )
    assert r.status_code == 200, r.text
    assert r.json()["id"] == org_id

    # membership persisted
    m = db.execute(
        select(Membership).where(
            Membership.org_id == uuid.UUID(org_id), Membership.user_id == invitee.id
        )
    ).scalar_one()
    assert m.status == MemberStatus.active and m.role == MemberRole.employee

    # second accept -> 409 (single-use)
    r = client.post(
        "/api/v1/invitations/accept",
        json={"token": token},
        headers=login("newbie@example.com"),
    )
    assert r.status_code == 409


def test_last_admin_cannot_be_demoted_or_removed(client, db, login):
    admin = create_user(db, email="solo@example.com")
    r = client.post("/api/v1/organizations", json={"name": "SoloOrg"}, headers=login("solo@example.com"))
    org_id = r.json()["id"]
    headers = login("solo@example.com", org_id=org_id)

    r = client.patch(
        f"/api/v1/org/members/{admin.id}/role",
        json={"role": "manager"},
        headers=headers,
    )
    assert r.status_code == 409 and r.json()["code"] == "LAST_ADMIN"

    r = client.delete(f"/api/v1/org/members/{admin.id}", headers=headers)
    assert r.status_code == 409 and r.json()["code"] == "LAST_ADMIN"


def test_platform_admin_stats_and_suspension_blocks_org(client, db, login):
    pa = create_user(db, email="platform@example.com", is_platform_admin=True)
    admin = create_user(db, email="owner@example.com")
    r = client.post("/api/v1/organizations", json={"name": "SuspendMe"}, headers=login("owner@example.com"))
    org_id = r.json()["id"]

    pa_headers = login("platform@example.com")
    r = client.get("/api/v1/platform/stats", headers=pa_headers)
    assert r.status_code == 200 and r.json()["organizations"] >= 1

    # non-platform admin blocked
    assert client.get("/api/v1/platform/stats", headers=login("owner@example.com")).status_code == 403

    # suspend
    r = client.patch(
        f"/api/v1/platform/organizations/{org_id}/status",
        json={"status": "suspended"},
        headers=pa_headers,
    )
    assert r.status_code == 200 and r.json()["status"] == "suspended"

    # org member is now blocked on tenant endpoints
    r = client.get("/api/v1/org/members", headers=login("owner@example.com", org_id=org_id))
    assert r.status_code == 403 and r.json()["code"] == "ORG_SUSPENDED"

    # re-activate
    client.patch(
        f"/api/v1/platform/organizations/{org_id}/status",
        json={"status": "active"},
        headers=pa_headers,
    )
    assert client.get("/api/v1/org/members", headers=login("owner@example.com", org_id=org_id)).status_code == 200
