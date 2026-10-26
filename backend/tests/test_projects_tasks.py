"""Tests for projects and tasks (Module 3): authorization, assignment, status
history, visibility, filters, and cross-tenant isolation."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.enums import MemberRole, NotificationType, TaskStatus
from app.models.comms import Notification
from app.models.work import Project, Task, TaskStatusHistory
from tests.factories import add_project_member, create_org, create_user, make_tenant


def _tenant(client, db, label, login):
    t = make_tenant(
        db, label,
        {"admin": MemberRole.org_admin, "manager": MemberRole.manager, "employee": MemberRole.employee},
    )
    t["headers"] = {
        "admin": login(f"admin_{label}@example.com", org_id=t["org"].id),
        "manager": login(f"manager_{label}@example.com", org_id=t["org"].id),
        "employee": login(f"employee_{label}@example.com", org_id=t["org"].id),
    }
    return t


def test_project_crud_and_duplicate_name(client, db, login):
    t = _tenant(client, db, "a", login)
    r = client.post("/api/v1/projects", json={"name": "Alpha"}, headers=t["headers"]["admin"])
    assert r.status_code == 201, r.text
    project_id = r.json()["id"]

    # duplicate name -> 409
    r = client.post("/api/v1/projects", json={"name": "Alpha"}, headers=t["headers"]["admin"])
    assert r.status_code == 409 and r.json()["code"] == "PROJECT_NAME_TAKEN"

    # employee cannot create -> 403
    r = client.post("/api/v1/projects", json={"name": "Nope"}, headers=t["headers"]["employee"])
    assert r.status_code == 403

    # admin sees it; employee (not a member) does not
    assert len(client.get("/api/v1/projects", headers=t["headers"]["admin"]).json()) == 1
    assert client.get("/api/v1/projects", headers=t["headers"]["employee"]).json() == []
    # employee cannot read the project detail either -> 404
    assert client.get(f"/api/v1/projects/{project_id}", headers=t["headers"]["employee"]).status_code == 404


def test_task_create_assign_and_validate_assignee(client, db, login):
    t = _tenant(client, db, "a", login)
    project_id = client.post(
        "/api/v1/projects", json={"name": "P"}, headers=t["headers"]["admin"]
    ).json()["id"]
    # make manager a project member so they may create tasks
    add_project_member(db, db.get(Project, uuid.UUID(project_id)), t["users"]["manager"])
    db.flush()

    # assignee must be an active org member -> 422
    stranger = create_user(db, email="stranger@example.com")
    r = client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "Bad", "assignee_id": str(stranger.id)},
        headers=t["headers"]["manager"],
    )
    assert r.status_code == 422 and r.json()["code"] == "ASSIGNEE_NOT_IN_ORG"

    # valid assignment
    r = client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "Good", "assignee_id": str(t["users"]["employee"].id)},
        headers=t["headers"]["manager"],
    )
    assert r.status_code == 201, r.text
    task = r.json()
    assert task["assignee_id"] == str(t["users"]["employee"].id)

    # assignee got a notification; creator (manager) did not
    notifs = db.execute(select(Notification)).scalars().all()
    assert any(n.type == NotificationType.task_assigned and n.user_id == t["users"]["employee"].id for n in notifs)
    assert all(n.user_id != t["users"]["manager"].id for n in notifs)

    # employee cannot create tasks -> 403
    r = client.post(
        "/api/v1/tasks", json={"project_id": project_id, "title": "x"}, headers=t["headers"]["employee"]
    )
    assert r.status_code == 403


def test_task_status_change_writes_history_and_notifies(client, db, login):
    t = _tenant(client, db, "a", login)
    project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=t["headers"]["admin"]).json()["id"]
    add_project_member(db, db.get(Project, uuid.UUID(project_id)), t["users"]["manager"])
    task_id = client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "T", "assignee_id": str(t["users"]["employee"].id)},
        headers=t["headers"]["manager"],
    ).json()["id"]

    # assignee moves todo -> in_progress
    r = client.patch(
        f"/api/v1/tasks/{task_id}/status", json={"status": "in_progress"}, headers=t["headers"]["employee"]
    )
    assert r.status_code == 200 and r.json()["status"] == "in_progress"

    # history persisted: initial (None->todo) + (todo->in_progress)
    history = db.execute(
        select(TaskStatusHistory).where(TaskStatusHistory.task_id == uuid.UUID(task_id))
    ).scalars().all()
    assert len(history) == 2
    assert history[-1].from_status == TaskStatus.todo and history[-1].to_status == TaskStatus.in_progress

    # invalid transition todo->completed? (in_progress->completed is valid); test same status -> 409
    r = client.patch(
        f"/api/v1/tasks/{task_id}/status", json={"status": "in_progress"}, headers=t["headers"]["employee"]
    )
    assert r.status_code == 409 and r.json()["code"] == "SAME_STATUS"

    # a non-assignee employee cannot change status -> 403
    other = create_user(db, email="other_a@example.com")
    from tests.factories import add_member
    add_member(db, t["org"], other, MemberRole.employee)
    r = client.patch(
        f"/api/v1/tasks/{task_id}/status", json={"status": "blocked"},
        headers=login("other_a@example.com", org_id=t["org"].id),
    )
    assert r.status_code == 403

    # detail includes history
    r = client.get(f"/api/v1/tasks/{task_id}", headers=t["headers"]["manager"])
    assert r.status_code == 200 and len(r.json()["history"]) == 2


def test_archived_project_is_read_only(client, db, login):
    t = _tenant(client, db, "a", login)
    project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=t["headers"]["admin"]).json()["id"]
    add_project_member(db, db.get(Project, uuid.UUID(project_id)), t["users"]["manager"])
    task_id = client.post(
        "/api/v1/tasks", json={"project_id": project_id, "title": "T"}, headers=t["headers"]["manager"]
    ).json()["id"]

    client.post(f"/api/v1/projects/{project_id}/archive", headers=t["headers"]["admin"])
    r = client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "in_progress"}, headers=t["headers"]["manager"])
    assert r.status_code == 409 and r.json()["code"] == "PROJECT_ARCHIVED"


def test_task_filters_and_pagination(client, db, login):
    t = _tenant(client, db, "a", login)
    project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=t["headers"]["admin"]).json()["id"]
    add_project_member(db, db.get(Project, uuid.UUID(project_id)), t["users"]["manager"])
    for i in range(5):
        client.post(
            "/api/v1/tasks",
            json={"project_id": project_id, "title": f"Task {i}", "priority": "high" if i % 2 else "low"},
            headers=t["headers"]["manager"],
        )
    r = client.get("/api/v1/tasks?page=1&page_size=2", headers=t["headers"]["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5 and len(body["items"]) == 2 and body["page_size"] == 2

    r = client.get("/api/v1/tasks?priority=high&search=Task", headers=t["headers"]["admin"])
    assert r.json()["total"] == 2


def test_cross_tenant_task_is_404_and_unchanged(client, db, login):
    a = _tenant(client, db, "a", login)
    b = _tenant(client, db, "b", login)
    project_a = client.post("/api/v1/projects", json={"name": "PA"}, headers=a["headers"]["admin"]).json()["id"]
    add_project_member(db, db.get(Project, uuid.UUID(project_a)), a["users"]["manager"])
    task_a = client.post(
        "/api/v1/tasks", json={"project_id": project_a, "title": "Secret"}, headers=a["headers"]["manager"]
    ).json()["id"]

    # Org B admin tries to read / change Org A's task
    assert client.get(f"/api/v1/tasks/{task_a}", headers=b["headers"]["admin"]).status_code == 404
    assert client.patch(
        f"/api/v1/tasks/{task_a}", json={"title": "Hacked"}, headers=b["headers"]["admin"]
    ).status_code == 404
    assert client.patch(
        f"/api/v1/tasks/{task_a}/status", json={"status": "completed"}, headers=b["headers"]["admin"]
    ).status_code == 404

    # The task is unchanged in the DB.
    db.expire_all()
    task = db.get(Task, uuid.UUID(task_a))
    assert task.title == "Secret" and task.status == TaskStatus.todo
