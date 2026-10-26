"""Integration tests for workflow templates and approvals (Module 4).

Covers assignment scenarios 4, 5, 7 and 8: wrong approver blocked, no re-deciding
final requests, correct approval history, and a mid-transaction rollback leaving no
partial records.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.models.comms import AuditLog, Notification
from app.models.enums import DecisionType, MemberRole, NotificationType, RequestStatus
from app.models.workflow import ApprovalDecision, ApprovalRequest
from app.services import notification_service
from tests.factories import add_member, create_template, create_user, make_tenant


def _tenant(client, db, label, login):
    t = make_tenant(
        db, label,
        {"admin": MemberRole.org_admin, "manager": MemberRole.manager, "employee": MemberRole.employee},
    )
    t["headers"] = {
        k: login(f"{k}_{label}@example.com", org_id=t["org"].id) for k in ("admin", "manager", "employee")
    }
    return t


def _make_two_step_template(client, t, name="Leave Approval"):
    payload = {
        "name": name,
        "description": "manager then admin",
        "steps": [
            {"name": "Manager", "approver_type": "role", "approver_role": "manager"},
            {"name": "Admin", "approver_type": "role", "approver_role": "org_admin"},
        ],
    }
    r = client.post("/api/v1/workflow-templates", json=payload, headers=t["headers"]["admin"])
    assert r.status_code == 201, r.text
    return r.json()


def test_template_validation_and_creation(client, db, login):
    t = _tenant(client, db, "a", login)
    # employee cannot create templates
    r = client.post(
        "/api/v1/workflow-templates",
        json={"name": "X", "steps": [{"name": "s", "approver_type": "role", "approver_role": "manager"}]},
        headers=t["headers"]["employee"],
    )
    assert r.status_code == 403

    # role approver must be org_admin or manager
    r = client.post(
        "/api/v1/workflow-templates",
        json={"name": "Bad", "steps": [{"name": "s", "approver_type": "role", "approver_role": "employee"}]},
        headers=t["headers"]["admin"],
    )
    assert r.status_code == 422 and r.json()["code"] == "INVALID_APPROVER"

    tmpl = _make_two_step_template(client, t)
    assert [s["step_order"] for s in tmpl["steps"]] == [1, 2]


def test_two_step_approval_success_and_history(client, db, login):
    t = _tenant(client, db, "a", login)
    tmpl = _make_two_step_template(client, t)

    # employee submits
    r = client.post(
        "/api/v1/approval-requests",
        json={"template_id": tmpl["id"], "title": "Vacation", "details": {"days": 3}},
        headers=t["headers"]["employee"],
    )
    assert r.status_code == 201, r.text
    req_id = r.json()["id"]
    assert r.json()["status"] == "pending" and r.json()["current_step_order"] == 1

    # manager sees it in pending-for-me; employee does not
    assert len(client.get("/api/v1/approval-requests/pending-for-me", headers=t["headers"]["manager"]).json()) == 1
    assert client.get("/api/v1/approval-requests/pending-for-me", headers=t["headers"]["employee"]).json() == []

    # employee (wrong approver) cannot decide -> 403, state unchanged
    r = client.post(
        f"/api/v1/approval-requests/{req_id}/decision",
        json={"decision": "approved"}, headers=t["headers"]["employee"],
    )
    assert r.status_code == 403 and r.json()["code"] == "NOT_AUTHORIZED_APPROVER"
    db.expire_all()
    assert db.get(ApprovalRequest, uuid.UUID(req_id)).status == RequestStatus.pending

    # manager approves step 1 -> advances to step 2
    r = client.post(
        f"/api/v1/approval-requests/{req_id}/decision",
        json={"decision": "approved", "comment": "ok by manager"}, headers=t["headers"]["manager"],
    )
    assert r.status_code == 200 and r.json()["status"] == "pending" and r.json()["current_step_order"] == 2

    # admin approves step 2 -> final approved
    r = client.post(
        f"/api/v1/approval-requests/{req_id}/decision",
        json={"decision": "approved", "comment": "ok by admin"}, headers=t["headers"]["admin"],
    )
    assert r.status_code == 200 and r.json()["status"] == "approved" and r.json()["completed_at"]

    # history: two decisions with decider, comment, step order
    decisions = db.execute(
        select(ApprovalDecision).where(ApprovalDecision.request_id == uuid.UUID(req_id)).order_by(ApprovalDecision.step_order)
    ).scalars().all()
    assert [d.step_order for d in decisions] == [1, 2]
    assert decisions[0].decided_by == t["users"]["manager"].id
    assert decisions[1].decided_by == t["users"]["admin"].id
    assert decisions[0].comment == "ok by manager"
    assert all(d.decided_at is not None for d in decisions)

    # re-deciding a final request -> 409, history unchanged
    r = client.post(
        f"/api/v1/approval-requests/{req_id}/decision",
        json={"decision": "rejected", "comment": "late"}, headers=t["headers"]["admin"],
    )
    assert r.status_code == 409 and r.json()["code"] == "REQUEST_NOT_PENDING"
    count = db.execute(select(func.count()).select_from(ApprovalDecision)).scalar_one()
    assert count == 2


def test_reject_path_and_comment_required(client, db, login):
    t = _tenant(client, db, "a", login)
    tmpl = _make_two_step_template(client, t)
    req_id = client.post(
        "/api/v1/approval-requests",
        json={"template_id": tmpl["id"], "title": "Purchase"},
        headers=t["headers"]["employee"],
    ).json()["id"]

    # reject without a comment -> 422
    r = client.post(
        f"/api/v1/approval-requests/{req_id}/decision",
        json={"decision": "rejected"}, headers=t["headers"]["manager"],
    )
    assert r.status_code == 422

    # reject with comment -> final rejected
    r = client.post(
        f"/api/v1/approval-requests/{req_id}/decision",
        json={"decision": "rejected", "comment": "not allowed"}, headers=t["headers"]["manager"],
    )
    assert r.status_code == 200 and r.json()["status"] == "rejected"

    # requester was notified
    notifs = db.execute(
        select(Notification).where(Notification.user_id == t["users"]["employee"].id)
    ).scalars().all()
    assert any(n.type == NotificationType.approval_decided for n in notifs)


def test_requester_cannot_approve_own_request(client, db, login):
    t = _tenant(client, db, "a", login)
    tmpl = _make_two_step_template(client, t)
    # the manager submits their own request; step 1 is a manager step
    req_id = client.post(
        "/api/v1/approval-requests",
        json={"template_id": tmpl["id"], "title": "Self"},
        headers=t["headers"]["manager"],
    ).json()["id"]
    r = client.post(
        f"/api/v1/approval-requests/{req_id}/decision",
        json={"decision": "approved"}, headers=t["headers"]["manager"],
    )
    assert r.status_code == 403 and r.json()["code"] == "NOT_AUTHORIZED_APPROVER"


def test_double_decision_second_fails_with_409(client, db, login):
    t = _tenant(client, db, "a", login)
    # single-step template approved by any manager
    tmpl = _make_two_step_template(client, t)
    # add a second manager
    m2 = create_user(db, email="manager2_a@example.com")
    add_member(db, t["org"], m2, MemberRole.manager)
    m2_headers = login("manager2_a@example.com", org_id=t["org"].id)

    # single-step template so both managers are valid approvers of step 1
    single = client.post(
        "/api/v1/workflow-templates",
        json={"name": "One Step", "steps": [{"name": "M", "approver_type": "role", "approver_role": "manager"}]},
        headers=t["headers"]["admin"],
    ).json()
    req_id = client.post(
        "/api/v1/approval-requests",
        json={"template_id": single["id"], "title": "Once"},
        headers=t["headers"]["employee"],
    ).json()["id"]

    r1 = client.post(
        f"/api/v1/approval-requests/{req_id}/decision",
        json={"decision": "approved"}, headers=t["headers"]["manager"],
    )
    assert r1.status_code == 200 and r1.json()["status"] == "approved"

    # the second manager tries the same step -> already final -> 409
    r2 = client.post(
        f"/api/v1/approval-requests/{req_id}/decision",
        json={"decision": "approved"}, headers=m2_headers,
    )
    assert r2.status_code == 409 and r2.json()["code"] == "REQUEST_NOT_PENDING"


def test_rollback_leaves_no_partial_records(client, db, login, monkeypatch):
    t = _tenant(client, db, "a", login)
    tmpl = _make_two_step_template(client, t)
    req_id = client.post(
        "/api/v1/approval-requests",
        json={"template_id": tmpl["id"], "title": "Atomic"},
        headers=t["headers"]["employee"],
    ).json()["id"]

    def boom(*_args, **_kwargs):
        raise RuntimeError("notification failure")

    monkeypatch.setattr(notification_service, "notify", boom)

    decisions_before = db.execute(select(func.count()).select_from(ApprovalDecision)).scalar_one()
    audits_before = db.execute(select(func.count()).select_from(AuditLog)).scalar_one()

    # The server exception surfaces because TestClient re-raises by default.
    with pytest.raises(RuntimeError):
        client.post(
            f"/api/v1/approval-requests/{req_id}/decision",
            json={"decision": "approved"}, headers=t["headers"]["manager"],
        )

    db.expire_all()
    # nothing partial persisted: still pending, no new decision, no new audit row
    req = db.get(ApprovalRequest, uuid.UUID(req_id))
    assert req.status == RequestStatus.pending and req.current_step_order == 1
    assert db.execute(select(func.count()).select_from(ApprovalDecision)).scalar_one() == decisions_before
    assert db.execute(select(func.count()).select_from(AuditLog)).scalar_one() == audits_before


def test_request_visibility_and_cross_tenant(client, db, login):
    a = _tenant(client, db, "a", login)
    b = _tenant(client, db, "b", login)
    tmpl = _make_two_step_template(client, a)
    req_id = client.post(
        "/api/v1/approval-requests",
        json={"template_id": tmpl["id"], "title": "Private"},
        headers=a["headers"]["employee"],
    ).json()["id"]

    # requester and approvers can see it
    assert client.get(f"/api/v1/approval-requests/{req_id}", headers=a["headers"]["employee"]).status_code == 200
    assert client.get(f"/api/v1/approval-requests/{req_id}", headers=a["headers"]["manager"]).status_code == 200
    # a plain employee of the same org cannot
    other = create_user(db, email="bystander_a@example.com")
    add_member(db, a["org"], other, MemberRole.employee)
    assert client.get(
        f"/api/v1/approval-requests/{req_id}",
        headers=login("bystander_a@example.com", org_id=a["org"].id),
    ).status_code == 404
    # another org sees 404
    assert client.get(f"/api/v1/approval-requests/{req_id}", headers=b["headers"]["admin"]).status_code == 404


def test_cancel_requester_only(client, db, login):
    t = _tenant(client, db, "a", login)
    tmpl = _make_two_step_template(client, t)
    req_id = client.post(
        "/api/v1/approval-requests",
        json={"template_id": tmpl["id"], "title": "Cancel me"},
        headers=t["headers"]["employee"],
    ).json()["id"]

    # a non-requester cannot cancel (404 - hidden)
    assert client.post(
        f"/api/v1/approval-requests/{req_id}/cancel", headers=t["headers"]["manager"]
    ).status_code == 404

    r = client.post(f"/api/v1/approval-requests/{req_id}/cancel", headers=t["headers"]["employee"])
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
