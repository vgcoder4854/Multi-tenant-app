"""Pure workflow state machine.

No database calls live here, so the rules are trivial to unit-test. The service
layer passes plain objects/values in and gets a decision back.

State machine:
    pending --approve(last step)--> approved
    pending --approve(not last)--> pending (current_step_order advances)
    pending --reject--> rejected
    pending --cancel--> cancelled
    approved | rejected | cancelled are FINAL: no transitions out of them.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.core.errors import ConflictError, ForbiddenError
from app.models.enums import ApproverType, DecisionType, MemberRole, RequestStatus


class RequestNotPending(ConflictError):
    """The request is in a final state and cannot be decided."""

    def __init__(self, detail: str = "This request has already been decided"):
        super().__init__(detail, code="REQUEST_NOT_PENDING")


class NotAuthorizedApprover(ForbiddenError):
    """The user is not the approver for the current step."""

    def __init__(self, detail: str = "You are not the approver for the current step"):
        super().__init__(detail, code="NOT_AUTHORIZED_APPROVER")


class _RequestLike(Protocol):
    status: RequestStatus
    current_step_order: int
    requester_id: uuid.UUID


class _StepLike(Protocol):
    step_order: int
    approver_type: ApproverType
    approver_role: MemberRole | None
    approver_user_id: uuid.UUID | None


FINAL_STATUSES = {RequestStatus.approved, RequestStatus.rejected, RequestStatus.cancelled}


def is_final(status: RequestStatus) -> bool:
    return status in FINAL_STATUSES


def current_step(steps: Sequence[_StepLike], order: int) -> _StepLike | None:
    for step in steps:
        if step.step_order == order:
            return step
    return None


def can_decide(
    request: _RequestLike,
    step: _StepLike | None,
    *,
    user_id: uuid.UUID,
    role: MemberRole,
) -> tuple[bool, str]:
    """Return ``(allowed, reason)`` — reason is empty when allowed."""
    if request.status != RequestStatus.pending:
        return False, "This request has already been decided"
    if step is None:
        return False, "No approval step is currently active"
    if request.requester_id == user_id:
        return False, "You cannot decide your own request"
    if step.approver_type == ApproverType.role:
        if step.approver_role != role:
            return False, "You are not the approver for the current step"
    else:
        if step.approver_user_id != user_id:
            return False, "You are not the approver for the current step"
    return True, ""


def assert_can_decide(
    request: _RequestLike,
    step: _StepLike | None,
    *,
    user_id: uuid.UUID,
    role: MemberRole,
) -> None:
    """Raise the appropriate typed error if the decision is not allowed."""
    if request.status != RequestStatus.pending:
        raise RequestNotPending()
    allowed, _reason = can_decide(request, step, user_id=user_id, role=role)
    if not allowed:
        raise NotAuthorizedApprover()


@dataclass(frozen=True)
class NewState:
    status: RequestStatus
    next_step_order: int | None


def next_state(
    request: _RequestLike,
    steps: Sequence[_StepLike],
    decision: DecisionType,
) -> NewState:
    """Compute the state after a decision.

    Approve -> advance to the next step, or finish ``approved`` after the last step.
    Reject  -> finish ``rejected`` immediately.
    """
    if decision == DecisionType.rejected:
        return NewState(RequestStatus.rejected, None)

    ordered = sorted(steps, key=lambda s: s.step_order)
    index = next(
        (i for i, s in enumerate(ordered) if s.step_order == request.current_step_order), None
    )
    if index is None:
        # Defensive: current step not found; treat as final approval.
        return NewState(RequestStatus.approved, None)
    if index == len(ordered) - 1:
        return NewState(RequestStatus.approved, None)
    return NewState(RequestStatus.pending, ordered[index + 1].step_order)
