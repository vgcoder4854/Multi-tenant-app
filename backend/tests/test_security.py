"""Security suite: the assignment's mandatory scenarios 1, 2 and 3, plus
cross-tenant attempts for update/delete/list/search across modules.

Every forbidden call is followed by a database check that the target row is
unchanged.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.comms import Notification
from app.models.enums import MemberRole, ProjectStatus, TaskStatus
from app.models.work import Project, Task
from app.models.workflow import WorkflowTemplate
from tests.factories import (
    add_project_member,
    create_project,
    create_task,
    create_template,
    make_tenant,
)

DUMMY = uuid.uuid4()

# Every protected endpoint, with a valid body where one is required.
PROTECTED_ENDPOINTS = [
    ("GET", "/api/v1/auth/me", None),
    ("POST", "/api/v1/auth/switch-organization", {"org_id": str(DUMMY)}),
    ("POST", "/api/v1/organizations", {"name": "X"}),
    ("GET", "/api/v1/organizations/mine", None),
    ("POST", "/api/v1/org/invitations", {"email": "a@b.com", "role": "employee"}),
    ("GET", "/api/v1/org/invitations", None),
    ("DELETE", f"/api/v1/org/invitations/{DUMMY}", None),
    ("GET", "/api/v1/org/members", None),
    ("PATCH", f"/api/v1/org/members/{DUMMY}/role", {"role": "manager"}),
    ("DELETE", f"/api/v1/org/members/{DUMMY}", None),
    ("POST", "/api/v1/invitations/accept", {"token": "x" * 20}),
    ("GET", "/api/v1/platform/organizations", None),
    ("PATCH", f"/api/v1/platform/organizations/{DUMMY}/status", {"status": "active"}),
    ("GET", "/api/v1/platform/stats", None),
    ("GET", "/api/v1/platform/audit-logs", None),
    ("POST", "/api/v1/projects", {"name": "P"}),
    ("GET", "/api/v1/projects", None),
    ("GET", f"/api/v1/projects/{DUMMY}", None),
    ("PATCH", f"/api/v1/projects/{DUMMY}", {"name": "N"}),
    ("POST", f"/api/v1/projects/{DUMMY}/archive", None),
    ("GET", f"/api/v1/projects/{DUMMY}/members", None),
    ("POST", f"/api/v1/projects/{DUMMY}/members", {"user_id": str(DUMMY)}),
    ("DELETE", f"/api/v1/projects/{DUMMY}/members/{DUMMY}", None),
    ("POST", "/api/v1/tasks", {"project_id": str(DUMMY), "title": "t"}),
    ("GET", "/api/v1/tasks", None),
    ("GET", f"/api/v1/tasks/{DUMMY}", None),
    ("PATCH", f"/api/v1/tasks/{DUMMY}", {"title": "x"}),
    ("PATCH", f"/api/v1/tasks/{DUMMY}/status", {"status": "todo"}),
    ("POST", "/api/v1/workflow-templates", {"name": "T", "steps": [{"name": "s", "approver_type": "role", "approver_role": "manager"}]}),
    ("GET", "/api/v1/workflow-templates", None),
    ("GET", f"/api/v1/workflow-templates/{DUMMY}", None),
    ("PATCH", f"/api/v1/workflow-templates/{DUMMY}", {"name": "x"}),
    ("POST", f"/api/v1/workflow-templates/{DUMMY}/deactivate", None),
    ("POST", "/api/v1/approval-requests", {"template_id": str(DUMMY), "title": "t"}),
    ("GET", "/api/v1/approval-requests/mine", None),
    ("GET", "/api/v1/approval-requests/pending-for-me", None),
    ("GET", f"/api/v1/approval-requests/{DUMMY}", None),
    ("POST", f"/api/v1/approval-requests/{DUMMY}/decision", {"decision": "approved"}),
    ("POST", f"/api/v1/approval-requests/{DUMMY}/cancel", None),
    ("GET", "/api/v1/notifications", None),
    ("GET", "/api/v1/notifications/unread-count", None),
    ("POST", f"/api/v1/notifications/{DUMMY}/read", None),
    ("POST", "/api/v1/notifications/read-all", None),
    ("POST", "/api/v1/admin/run-due-scan", None),
    ("GET", "/api/v1/audit-logs", None),
    ("GET", "/api/v1/dashboard/summary", None),
    ("GET", "/api/v1/dashboard/export.csv", None),
]


@pytest.mark.parametrize("method,path,body", PROTECTED_ENDPOINTS)
def test_scenario1_unauthenticated_is_401(client, method, path, body):
    resp = client.request(method, path, json=body)
    assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}"
    assert resp.headers.get("WWW-Authenticate") == "Bearer"
    assert resp.json()["code"] in {"NOT_AUTHENTICATED", "TOKEN_INVALID", "TOKEN_EXPIRED"}


def _tenant(client, db, label, login):
    t = make_tenant(
        db, label,
        {"admin": MemberRole.org_admin, "manager": MemberRole.manager, "employee": MemberRole.employee},
    )
    t["headers"] = {
        k: login(f"{k}_{label}@example.com", org_id=t["org"].id) for k in ("admin", "manager", "employee")
    }
    return t


def test_scenario2_cross_tenant_reads_are_404(client, db, login):
    a = _tenant(client, db, "a", login)
    b = _tenant(client, db, "b", login)

    project = create_project(db, a["org"], created_by=a["users"]["admin"])
    task = create_task(db, a["org"], project, title="Secret", assignee=a["users"]["employee"])
    template = create_template(db, a["org"], created_by=a["users"]["admin"])

    bh = b["headers"]["admin"]
    assert client.get(f"/api/v1/projects/{project.id}", headers=bh).status_code == 404
    assert client.get(f"/api/v1/projects/{project.id}/members", headers=bh).status_code == 404
    assert client.get(f"/api/v1/tasks/{task.id}", headers=bh).status_code == 404
    assert client.get(f"/api/v1/workflow-templates/{template.id}", headers=bh).status_code == 404

    # list/search endpoints never return another org's rows
    assert client.get("/api/v1/projects", headers=bh).json() == []
    assert client.get("/api/v1/tasks", headers=bh).json()["total"] == 0
    assert client.get("/api/v1/tasks?search=Secret", headers=bh).json()["total"] == 0


def test_scenario2_cross_tenant_writes_are_404_and_no_change(client, db, login):
    a = _tenant(client, db, "a", login)
    b = _tenant(client, db, "b", login)
    project = create_project(db, a["org"], created_by=a["users"]["admin"])
    task = create_task(db, a["org"], project, title="Secret", assignee=a["users"]["employee"])
    template = create_template(db, a["org"], created_by=a["users"]["admin"])

    bh = b["headers"]["admin"]
    assert client.patch(f"/api/v1/projects/{project.id}", json={"name": "Hacked"}, headers=bh).status_code == 404
    assert client.post(f"/api/v1/projects/{project.id}/archive", headers=bh).status_code == 404
    assert client.patch(f"/api/v1/tasks/{task.id}", json={"title": "Hacked"}, headers=bh).status_code == 404
    assert client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "completed"}, headers=bh).status_code == 404
    assert client.patch(f"/api/v1/workflow-templates/{template.id}", json={"name": "Hacked"}, headers=bh).status_code == 404
    assert client.delete(f"/api/v1/projects/{project.id}/members/{a['users']['employee'].id}", headers=bh).status_code == 404

    db.expire_all()
    assert db.get(Project, project.id).name == project.name
    assert db.get(Project, project.id).status == ProjectStatus.active
    assert db.get(Task, task.id).title == "Secret"
    assert db.get(Task, task.id).status == TaskStatus.todo
    assert db.get(WorkflowTemplate, template.id).name == template.name


def test_scenario2_cross_tenant_notifications_404(client, db, login):
    a = _tenant(client, db, "a", login)
    b = _tenant(client, db, "b", login)
    project = create_project(db, a["org"], created_by=a["users"]["admin"])
    add_project_member(db, project, a["users"]["manager"])
    client.post(
        "/api/v1/tasks",
        json={"project_id": str(project.id), "title": "T", "assignee_id": str(a["users"]["employee"].id)},
        headers=a["headers"]["manager"],
    )
    nid = db.execute(select(Notification)).scalar_one().id

    assert client.post(f"/api/v1/notifications/{nid}/read", headers=b["headers"]["employee"]).status_code == 404
    assert client.get("/api/v1/notifications", headers=b["headers"]["employee"]).json()["total"] == 0


def test_scenario3_employee_admin_actions_are_403_and_no_change(client, db, login):
    t = _tenant(client, db, "a", login)
    eh = t["headers"]["employee"]

    projects_before = db.execute(select(Project)).scalars().all().__len__()
    templates_before = db.execute(select(WorkflowTemplate)).scalars().all().__len__()

    assert client.post("/api/v1/projects", json={"name": "Nope"}, headers=eh).status_code == 403
    assert client.post(
        "/api/v1/workflow-templates",
        json={"name": "Nope", "steps": [{"name": "s", "approver_type": "role", "approver_role": "manager"}]},
        headers=eh,
    ).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=eh).status_code == 403
    assert client.post("/api/v1/org/invitations", json={"email": "x@y.com", "role": "employee"}, headers=eh).status_code == 403
    assert client.post("/api/v1/admin/run-due-scan", headers=eh).status_code == 403

    assert db.execute(select(Project)).scalars().all().__len__() == projects_before
    assert db.execute(select(WorkflowTemplate)).scalars().all().__len__() == templates_before
