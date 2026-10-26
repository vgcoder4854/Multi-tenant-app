"""Tests for notifications (Module 5) and the due/overdue scan.

Covers scenario 9: notifications go only to the intended recipients and never to
the actor.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select

from app.models.comms import Notification
from app.models.enums import MemberRole, NotificationType, TaskStatus
from app.jobs import due_scan
from tests.factories import add_member, add_project_member, create_project, create_task, create_user, make_tenant


def _tenant(client, db, label, login):
    t = make_tenant(
        db, label,
        {"admin": MemberRole.org_admin, "manager": MemberRole.manager, "employee": MemberRole.employee},
    )
    t["headers"] = {
        k: login(f"{k}_{label}@example.com", org_id=t["org"].id) for k in ("admin", "manager", "employee")
    }
    return t


def test_assignment_notifies_assignee_not_actor(client, db, login):
    t = _tenant(client, db, "a", login)
    project = create_project(db, t["org"], created_by=t["users"]["admin"])
    add_project_member(db, project, t["users"]["manager"])

    task_id = client.post(
        "/api/v1/tasks",
        json={"project_id": str(project.id), "title": "Do it", "assignee_id": str(t["users"]["employee"].id)},
        headers=t["headers"]["manager"],
    ).json()["id"]

    notifs = db.execute(select(Notification)).scalars().all()
    assert len(notifs) == 1
    assert notifs[0].user_id == t["users"]["employee"].id
    assert notifs[0].type == NotificationType.task_assigned

    # assignee sees it in the list; manager (actor) does not
    r = client.get("/api/v1/notifications", headers=t["headers"]["employee"])
    assert r.json()["total"] == 1
    assert client.get("/api/v1/notifications", headers=t["headers"]["manager"]).json()["total"] == 0

    # unread count + mark read
    assert client.get("/api/v1/notifications/unread-count", headers=t["headers"]["employee"]).json()["unread"] == 1
    nid = r.json()["items"][0]["id"]
    r = client.post(f"/api/v1/notifications/{nid}/read", headers=t["headers"]["employee"])
    assert r.status_code == 200 and r.json()["is_read"] is True
    assert client.get("/api/v1/notifications/unread-count", headers=t["headers"]["employee"]).json()["unread"] == 0


def test_cannot_read_someone_elses_notification(client, db, login):
    t = _tenant(client, db, "a", login)
    project = create_project(db, t["org"], created_by=t["users"]["admin"])
    add_project_member(db, project, t["users"]["manager"])
    client.post(
        "/api/v1/tasks",
        json={"project_id": str(project.id), "title": "T", "assignee_id": str(t["users"]["employee"].id)},
        headers=t["headers"]["manager"],
    )
    nid = db.execute(select(Notification)).scalar_one().id

    # the manager tries to read the employee's notification -> 404
    r = client.post(f"/api/v1/notifications/{nid}/read", headers=t["headers"]["manager"])
    assert r.status_code == 404


def test_mark_all_read(client, db, login):
    t = _tenant(client, db, "a", login)
    project = create_project(db, t["org"], created_by=t["users"]["admin"])
    add_project_member(db, project, t["users"]["manager"])
    for i in range(3):
        client.post(
            "/api/v1/tasks",
            json={"project_id": str(project.id), "title": f"T{i}", "assignee_id": str(t["users"]["employee"].id)},
            headers=t["headers"]["manager"],
        )
    assert client.get("/api/v1/notifications/unread-count", headers=t["headers"]["employee"]).json()["unread"] == 3
    client.post("/api/v1/notifications/read-all", headers=t["headers"]["employee"])
    assert client.get("/api/v1/notifications/unread-count", headers=t["headers"]["employee"]).json()["unread"] == 0


def test_notifications_are_tenant_scoped(client, db, login):
    a = _tenant(client, db, "a", login)
    b = _tenant(client, db, "b", login)
    project_a = create_project(db, a["org"], created_by=a["users"]["admin"])
    add_project_member(db, project_a, a["users"]["manager"])
    client.post(
        "/api/v1/tasks",
        json={"project_id": str(project_a.id), "title": "T", "assignee_id": str(a["users"]["employee"].id)},
        headers=a["headers"]["manager"],
    )
    # Org B employee sees nothing even though the query runs in their org
    assert client.get("/api/v1/notifications", headers=b["headers"]["employee"]).json()["total"] == 0


def test_due_scan_creates_one_notification_per_task_per_day(client, db, login):
    t = _tenant(client, db, "a", login)
    project = create_project(db, t["org"], created_by=t["users"]["admin"])
    # overdue task and a due-soon task, both assigned
    create_task(db, t["org"], project, title="Overdue", assignee=t["users"]["employee"],
                due_date=date.today() - timedelta(days=2))
    create_task(db, t["org"], project, title="Soon", assignee=t["users"]["employee"],
                due_date=date.today() + timedelta(hours=12))
    create_task(db, t["org"], project, title="Done", assignee=t["users"]["employee"],
                due_date=date.today() - timedelta(days=1), status=TaskStatus.completed)

    result = due_scan.run(db, t["org"].id)
    assert result["scanned"] == 2 and result["notified"] == 2

    types = {n.type for n in db.execute(select(Notification)).scalars().all()}
    assert types == {NotificationType.task_overdue, NotificationType.task_due_soon}

    # running again the same day does not duplicate
    result2 = due_scan.run(db, t["org"].id)
    assert result2["notified"] == 0
    assert db.execute(select(Notification)).scalars().all().__len__() == 2


def test_run_due_scan_endpoint_is_admin_only(client, db, login):
    t = _tenant(client, db, "a", login)
    assert client.post("/api/v1/admin/run-due-scan", headers=t["headers"]["employee"]).status_code == 403
    assert client.post("/api/v1/admin/run-due-scan", headers=t["headers"]["admin"]).status_code == 200
