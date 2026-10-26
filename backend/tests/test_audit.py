"""Tests for the audit trail (Module 6): scenario 10 (actor/org/action/resource),
org_admin-only access, tenant scoping, and DB-level append-only enforcement."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.models.comms import AuditLog
from app.models.enums import MemberRole
from tests.factories import create_user, make_tenant


def _tenant(client, db, label, login):
    t = make_tenant(
        db, label,
        {"admin": MemberRole.org_admin, "manager": MemberRole.manager, "employee": MemberRole.employee},
    )
    t["headers"] = {
        k: login(f"{k}_{label}@example.com", org_id=t["org"].id) for k in ("admin", "manager", "employee")
    }
    return t


def test_audit_records_actor_org_action_resource(client, db, login):
    t = _tenant(client, db, "a", login)
    r = client.post("/api/v1/projects", json={"name": "Audited"}, headers=t["headers"]["admin"])
    project_id = r.json()["id"]

    log = db.execute(
        select(AuditLog).where(AuditLog.action == "project.created")
    ).scalar_one()
    assert log.org_id == t["org"].id
    assert log.actor_id == t["users"]["admin"].id
    assert log.resource_type == "project"
    assert log.resource_id == uuid.UUID(project_id)
    assert log.meta.get("name") == "Audited"


def test_audit_read_is_admin_only(client, db, login):
    t = _tenant(client, db, "a", login)
    client.post("/api/v1/projects", json={"name": "P"}, headers=t["headers"]["admin"])

    assert client.get("/api/v1/audit-logs", headers=t["headers"]["employee"]).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=t["headers"]["manager"]).status_code == 403
    r = client.get("/api/v1/audit-logs", headers=t["headers"]["admin"])
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    # metadata is exposed under the "metadata" key
    assert "metadata" in r.json()["items"][0]


def test_audit_is_tenant_scoped(client, db, login):
    a = _tenant(client, db, "a", login)
    b = _tenant(client, db, "b", login)
    client.post("/api/v1/projects", json={"name": "A-project"}, headers=a["headers"]["admin"])
    client.post("/api/v1/projects", json={"name": "B-project"}, headers=b["headers"]["admin"])

    logs_a = client.get("/api/v1/audit-logs", headers=a["headers"]["admin"]).json()["items"]
    assert logs_a and all(row["org_id"] == str(a["org"].id) for row in logs_a)


def test_audit_is_append_only_at_db_level(client, db, login):
    t = _tenant(client, db, "a", login)
    client.post("/api/v1/projects", json={"name": "P"}, headers=t["headers"]["admin"])
    log_id = db.execute(select(AuditLog.id)).scalars().first()

    with pytest.raises(Exception):
        db.execute(text("UPDATE audit_logs SET action='tampered' WHERE id=:i"), {"i": log_id.hex})
        db.flush()
    db.rollback()

    with pytest.raises(Exception):
        db.execute(text("DELETE FROM audit_logs WHERE id=:i"), {"i": log_id.hex})
        db.flush()
    db.rollback()

    # the original row is still intact
    row = db.execute(text("SELECT action FROM audit_logs WHERE id=:i"), {"i": log_id.hex}).first()
    assert row is not None and row[0] == "project.created"


def test_platform_admin_sees_all_audit_logs(client, db, login):
    pa = create_user(db, email="pa@example.com", is_platform_admin=True)
    t = _tenant(client, db, "a", login)
    client.post("/api/v1/projects", json={"name": "P"}, headers=t["headers"]["admin"])

    r = client.get("/api/v1/platform/audit-logs", headers=login("pa@example.com"))
    assert r.status_code == 200 and r.json()["total"] >= 1
    # non-platform user blocked
    assert client.get("/api/v1/platform/audit-logs", headers=t["headers"]["admin"]).status_code == 403
