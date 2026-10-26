"""Pure unit tests for the workflow state machine (no DB)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import pytest

from app.models.enums import ApproverType, DecisionType, MemberRole, RequestStatus
from app.services import workflow_engine as eng
from app.services.workflow_engine import NotAuthorizedApprover, RequestNotPending


@dataclass
class Step:
    step_order: int
    approver_type: ApproverType
    approver_role: MemberRole | None = None
    approver_user_id: uuid.UUID | None = None


@dataclass
class Request:
    status: RequestStatus = RequestStatus.pending
    current_step_order: int = 1
    requester_id: uuid.UUID = field(default_factory=uuid.uuid4)


def _role_step(order=1, role=MemberRole.manager):
    return Step(order, ApproverType.role, approver_role=role)


def _user_step(order, uid):
    return Step(order, ApproverType.user, approver_user_id=uid)


def test_role_approver_can_decide():
    req = Request()
    ok, reason = eng.can_decide(req, _role_step(), user_id=uuid.uuid4(), role=MemberRole.manager)
    assert ok and reason == ""


def test_wrong_role_cannot_decide():
    req = Request()
    ok, _reason = eng.can_decide(req, _role_step(), user_id=uuid.uuid4(), role=MemberRole.employee)
    assert not ok


def test_requester_cannot_decide_own_request():
    uid = uuid.uuid4()
    req = Request(requester_id=uid)
    ok, _ = eng.can_decide(req, _user_step(1, uid), user_id=uid, role=MemberRole.manager)
    assert not ok


def test_final_request_cannot_be_decided():
    req = Request(status=RequestStatus.approved)
    ok, _ = eng.can_decide(req, _role_step(), user_id=uuid.uuid4(), role=MemberRole.manager)
    assert not ok
    with pytest.raises(RequestNotPending):
        eng.assert_can_decide(req, _role_step(), user_id=uuid.uuid4(), role=MemberRole.manager)


def test_assert_raises_not_authorized():
    req = Request()
    with pytest.raises(NotAuthorizedApprover):
        eng.assert_can_decide(req, _role_step(), user_id=uuid.uuid4(), role=MemberRole.employee)


def test_next_state_advances_then_finishes():
    steps = [_role_step(1, MemberRole.manager), _role_step(2, MemberRole.org_admin)]
    req = Request(current_step_order=1)
    nxt = eng.next_state(req, steps, DecisionType.approved)
    assert nxt.status == RequestStatus.pending and nxt.next_step_order == 2

    req2 = Request(current_step_order=2)
    fin = eng.next_state(req2, steps, DecisionType.approved)
    assert fin.status == RequestStatus.approved and fin.next_step_order is None


def test_next_state_reject_is_final():
    steps = [_role_step(1), _role_step(2, MemberRole.org_admin)]
    nxt = eng.next_state(Request(), steps, DecisionType.rejected)
    assert nxt.status == RequestStatus.rejected and nxt.next_step_order is None
