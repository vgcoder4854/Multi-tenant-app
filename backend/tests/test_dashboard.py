"""Tests for the dashboard/reporting module (Module 7)."""
from __future__ import annotations

from datetime import date, timedelta

from app.models.enums import ApproverType, MemberRole, TaskStatus
from tests.factories import (
    add_project_member,
    create_project,
    create_task,
    create_template,
    make_tenant,
)


def _tenant(client, db, label, login):
    t = make_tenant(
        db, label,
        {"admin": MemberRole.org_admin, "manager": MemberRole.manager, "employee": MemberRole.employee},
    )
    t["headers"] = {
        k: login(f"{k}_{label}@example.com", org_id=t["org"].id) for k in ("admin", "manager", "employee")
    }
    return t


def _seed(db, t):
    project = create_project(db, t["org"], created_by=t["users"]["admin"])
    add_project_member(db, project, t["users"]["manager"])
    create_task(db, t["org"], project, title="A", assignee=t["users"]["employee"], status=TaskStatus.todo)
    create_task(db, t["org"], project, title="B", assignee=t["users"]["employee"], status=TaskStatus.completed)
    create_task(db, t["org"], project, title="C", assignee=t["users"]["manager"], status=TaskStatus.in_progress)
    create_task(
        db, t["org"], project, title="Overdue", assignee=t["users"]["employee"],
        status=TaskStatus.todo, due_date=date.today() - timedelta(days=3),
    )
    return project


def test_summary_counts_for_admin(client, db, login):
    t = _tenant(client, db, "a", login)
    project = _seed(db, t)

    r = client.get("/api/v1/dashboard/summary", headers=t["headers"]["admin"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["projects"] == {"total": 1, "active": 1, "archived": 0}
    assert body["tasks_by_status"] == {"todo": 2, "in_progress": 1, "blocked": 0, "completed": 1}
    assert body["overdue_tasks"] == 1

    # project filter
    r = client.get(f"/api/v1/dashboard/summary?project_id={project.id}", headers=t["headers"]["admin"])
    assert r.json()["tasks_by_status"]["completed"] == 1


def test_employee_sees_only_own_tasks(client, db, login):
    t = _tenant(client, db, "a", login)
    _seed(db, t)
    body = client.get("/api/v1/dashboard/summary", headers=t["headers"]["employee"]).json()
    # employee: 3 tasks assigned to them (todo, completed, overdue)
    assert body["my_tasks"] == 3
    assert body["tasks_by_status"]["in_progress"] == 0  # that one belongs to the manager
    assert sum(body["tasks_by_status"].values()) == 3


def test_approvals_awaiting_my_action_matches_endpoint(client, db, login):
    t = _tenant(client, db, "a", login)
    create_template(
        db, t["org"],
        steps=[{"name": "M", "approver_type": ApproverType.role, "role": MemberRole.manager}],
        created_by=t["users"]["admin"],
    )
    # employee submits a request
    tmpl_id = client.get("/api/v1/workflow-templates", headers=t["headers"]["employee"]).json()[0]["id"]
    client.post(
        "/api/v1/approval-requests",
        json={"template_id": tmpl_id, "title": "R"}, headers=t["headers"]["employee"],
    )

    summary = client.get("/api/v1/dashboard/summary", headers=t["headers"]["manager"]).json()
    pending = client.get("/api/v1/approval-requests/pending-for-me", headers=t["headers"]["manager"]).json()
    assert summary["approvals"]["awaiting_my_action"] == len(pending) == 1
    assert summary["approvals"]["my_submitted_pending"] == 0

    emp = client.get("/api/v1/dashboard/summary", headers=t["headers"]["employee"]).json()
    assert emp["approvals"]["my_submitted_pending"] == 1


def test_export_csv_is_scoped_and_role_limited(client, db, login):
    a = _tenant(client, db, "a", login)
    b = _tenant(client, db, "b", login)
    _seed(db, a)
    project_b = create_project(db, b["org"], created_by=b["users"]["admin"])
    create_task(db, b["org"], project_b, title="B-only", assignee=b["users"]["employee"])

    r = client.get("/api/v1/dashboard/export.csv", headers=a["headers"]["admin"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "B-only" not in r.text
    assert "Overdue" in r.text

    # employee cannot export
    assert client.get("/api/v1/dashboard/export.csv", headers=a["headers"]["employee"]).status_code == 403
