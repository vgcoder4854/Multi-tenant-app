"""Workflow template and approval-request service (Module 4).

Templates are org_admin-only. Requests are submitted by any member and decided by
the current step's approver (never the requester). Decisions run under a row lock
plus an optimistic ``version`` bump so two approvers cannot both advance the same
step.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.enums import (
    ApproverType,
    DecisionType,
    MemberRole,
    MemberStatus,
    NotificationType,
    RequestStatus,
)
from app.models.identity import Membership, User
from app.models.workflow import (
    ApprovalDecision,
    ApprovalRequest,
    WorkflowStep,
    WorkflowTemplate,
)
from app.schemas.workflow import (
    ApprovalDecisionOut,
    ApprovalRequestOut,
    WorkflowStepOut,
    WorkflowTemplateCreate,
    WorkflowTemplateUpdate,
)
from app.services import audit_service, notification_service, workflow_engine
from app.services.tenant import get_in_org

APPROVER_ROLES = {MemberRole.org_admin, MemberRole.manager}


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #
def _validate_steps(db: Session, org_id: uuid.UUID, steps) -> None:
    if not steps:
        raise ValidationError("A template needs at least one step", code="NO_STEPS")
    for step in steps:
        if step.approver_type == ApproverType.role:
            if step.approver_role not in APPROVER_ROLES:
                raise ValidationError(
                    "A role approver must be org_admin or manager", code="INVALID_APPROVER"
                )
        else:
            membership = db.execute(
                select(Membership).where(
                    Membership.org_id == org_id,
                    Membership.user_id == step.approver_user_id,
                    Membership.status == MemberStatus.active,
                )
            ).scalar_one_or_none()
            if membership is None:
                raise ValidationError(
                    "A user approver must be an active member of this organization",
                    code="INVALID_APPROVER",
                )


def _replace_steps(db: Session, template: WorkflowTemplate, steps) -> None:
    for existing in list(template.steps):
        db.delete(existing)
    db.flush()
    for order, spec in enumerate(steps, start=1):
        db.add(
            WorkflowStep(
                org_id=template.org_id,
                template_id=template.id,
                step_order=order,
                name=spec.name,
                approver_type=spec.approver_type,
                approver_role=spec.approver_role,
                approver_user_id=spec.approver_user_id,
            )
        )
    db.flush()


def _template_has_requests(db: Session, template_id: uuid.UUID) -> bool:
    return db.execute(
        select(ApprovalRequest.id).where(ApprovalRequest.template_id == template_id).limit(1)
    ).first() is not None


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #
def create_template(db: Session, ctx, payload: WorkflowTemplateCreate) -> WorkflowTemplate:
    _validate_steps(db, ctx.org_id, payload.steps)
    duplicate = db.execute(
        select(WorkflowTemplate.id).where(
            WorkflowTemplate.org_id == ctx.org_id, WorkflowTemplate.name == payload.name.strip()
        )
    ).first()
    if duplicate:
        raise ConflictError("A template with this name already exists", code="TEMPLATE_NAME_TAKEN")

    template = WorkflowTemplate(
        org_id=ctx.org_id, name=payload.name.strip(), description=payload.description,
        is_active=True, created_by=ctx.user.id,
    )
    db.add(template)
    db.flush()
    _replace_steps(db, template, payload.steps)
    audit_service.record(db, ctx, audit_service.TEMPLATE_CREATED, "workflow_template", template.id)
    db.commit()
    db.refresh(template)
    return template


def list_templates(db: Session, ctx) -> list[WorkflowTemplate]:
    return list(
        db.execute(
            select(WorkflowTemplate)
            .where(WorkflowTemplate.org_id == ctx.org_id)
            .order_by(WorkflowTemplate.name)
        ).scalars().all()
    )


def get_template(db: Session, ctx, template_id: uuid.UUID) -> WorkflowTemplate:
    return get_in_org(db, WorkflowTemplate, template_id, ctx.org_id)


def update_template(
    db: Session, ctx, template_id: uuid.UUID, payload: WorkflowTemplateUpdate
) -> WorkflowTemplate:
    template = get_in_org(db, WorkflowTemplate, template_id, ctx.org_id)

    if payload.name is not None:
        name = payload.name.strip()
        duplicate = db.execute(
            select(WorkflowTemplate.id).where(
                WorkflowTemplate.org_id == ctx.org_id,
                WorkflowTemplate.name == name,
                WorkflowTemplate.id != template.id,
            )
        ).first()
        if duplicate:
            raise ConflictError("A template with this name already exists", code="TEMPLATE_NAME_TAKEN")
        template.name = name
    if payload.description is not None:
        template.description = payload.description
    if payload.is_active is not None:
        template.is_active = payload.is_active

    if payload.steps is not None:
        if _template_has_requests(db, template.id):
            raise ConflictError(
                "This template is used by existing requests; deactivate it instead of editing steps",
                code="TEMPLATE_IN_USE",
            )
        _validate_steps(db, ctx.org_id, payload.steps)
        _replace_steps(db, template, payload.steps)

    audit_service.record(db, ctx, audit_service.TEMPLATE_UPDATED, "workflow_template", template.id)
    db.commit()
    db.refresh(template)
    return template


def deactivate_template(db: Session, ctx, template_id: uuid.UUID) -> WorkflowTemplate:
    template = get_in_org(db, WorkflowTemplate, template_id, ctx.org_id)
    template.is_active = False
    audit_service.record(db, ctx, audit_service.TEMPLATE_DEACTIVATED, "workflow_template", template.id)
    db.commit()
    db.refresh(template)
    return template


# --------------------------------------------------------------------------- #
# Approver resolution
# --------------------------------------------------------------------------- #
def _approver_user_ids(db: Session, org_id: uuid.UUID, step: WorkflowStep) -> list[uuid.UUID]:
    if step.approver_type == ApproverType.user:
        return [step.approver_user_id] if step.approver_user_id else []
    rows = db.execute(
        select(Membership.user_id).where(
            Membership.org_id == org_id,
            Membership.role == step.approver_role,
            Membership.status == MemberStatus.active,
        )
    ).scalars().all()
    return list(rows)


def _user_matches_step(step: WorkflowStep, *, user_id: uuid.UUID, role: MemberRole) -> bool:
    if step.approver_type == ApproverType.role:
        return step.approver_role == role
    return step.approver_user_id == user_id


# --------------------------------------------------------------------------- #
# Serialisation
# --------------------------------------------------------------------------- #
def to_out(db: Session, request: ApprovalRequest) -> ApprovalRequestOut:
    template = db.get(WorkflowTemplate, request.template_id)
    requester = db.get(User, request.requester_id)
    return ApprovalRequestOut(
        id=request.id,
        org_id=request.org_id,
        template_id=request.template_id,
        template_name=template.name if template else "",
        requester_id=request.requester_id,
        requester_name=requester.full_name if requester else "",
        title=request.title,
        details=request.details or {},
        status=request.status,
        current_step_order=request.current_step_order,
        submitted_at=request.submitted_at,
        completed_at=request.completed_at,
    )


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
def submit_request(db: Session, ctx, payload) -> ApprovalRequest:
    template = get_in_org(db, WorkflowTemplate, payload.template_id, ctx.org_id)
    if not template.is_active:
        raise ConflictError("This workflow template is not active", code="TEMPLATE_INACTIVE")
    steps = sorted(template.steps, key=lambda s: s.step_order)
    if not steps:
        raise ValidationError("This template has no steps", code="NO_STEPS")

    request = ApprovalRequest(
        org_id=ctx.org_id,
        template_id=template.id,
        requester_id=ctx.user.id,
        title=payload.title.strip(),
        details=payload.details or {},
        status=RequestStatus.pending,
        current_step_order=steps[0].step_order,
    )
    db.add(request)
    db.flush()

    notification_service.notify(
        db, org_id=ctx.org_id, user_ids=_approver_user_ids(db, ctx.org_id, steps[0]),
        type=NotificationType.approval_requested,
        title=f"Approval requested: {request.title}",
        resource_type="approval_request", resource_id=request.id, actor_id=ctx.user.id,
    )
    audit_service.record(db, ctx, audit_service.REQUEST_SUBMITTED, "approval_request", request.id)
    db.commit()
    db.refresh(request)
    return request


def get_request(db: Session, ctx, request_id: uuid.UUID) -> ApprovalRequest:
    request = get_in_org(db, ApprovalRequest, request_id, ctx.org_id)
    if ctx.role == MemberRole.org_admin or request.requester_id == ctx.user.id:
        return request
    # Eligible approvers may view it.
    template = db.get(WorkflowTemplate, request.template_id)
    if template and any(
        _user_matches_step(step, user_id=ctx.user.id, role=ctx.role) for step in template.steps
    ):
        return request
    raise NotFoundError("Approval request not found")


def get_request_detail(db: Session, ctx, request_id: uuid.UUID):
    request = get_request(db, ctx, request_id)
    template = db.get(WorkflowTemplate, request.template_id)
    steps = sorted(template.steps, key=lambda s: s.step_order) if template else []
    decisions = list(
        db.execute(
            select(ApprovalDecision)
            .where(ApprovalDecision.request_id == request.id)
            .order_by(ApprovalDecision.step_order)
        ).scalars().all()
    )
    return request, steps, decisions


def list_my_requests(db: Session, ctx) -> list[ApprovalRequestOut]:
    rows = db.execute(
        select(ApprovalRequest)
        .where(ApprovalRequest.org_id == ctx.org_id, ApprovalRequest.requester_id == ctx.user.id)
        .order_by(ApprovalRequest.submitted_at.desc())
    ).scalars().all()
    return [to_out(db, r) for r in rows]


def list_pending_for_me(db: Session, ctx) -> list[ApprovalRequestOut]:
    step = WorkflowStep
    stmt = (
        select(ApprovalRequest)
        .join(
            step,
            (step.template_id == ApprovalRequest.template_id)
            & (step.step_order == ApprovalRequest.current_step_order),
        )
        .where(
            ApprovalRequest.org_id == ctx.org_id,
            ApprovalRequest.status == RequestStatus.pending,
            ApprovalRequest.requester_id != ctx.user.id,
            or_(
                (step.approver_type == ApproverType.role) & (step.approver_role == ctx.role),
                (step.approver_type == ApproverType.user)
                & (step.approver_user_id == ctx.user.id),
            ),
        )
        .order_by(ApprovalRequest.submitted_at.desc())
    )
    rows = db.execute(stmt).scalars().all()
    return [to_out(db, r) for r in rows]


def decide(db: Session, ctx, request_id: uuid.UUID, payload) -> ApprovalRequest:
    # Lock the row (PostgreSQL: FOR UPDATE; SQLite ignores it but serialises writes).
    request = db.execute(
        select(ApprovalRequest)
        .where(ApprovalRequest.id == request_id, ApprovalRequest.org_id == ctx.org_id)
        .with_for_update()
    ).scalar_one_or_none()
    if request is None:
        raise NotFoundError("Approval request not found")

    template = db.get(WorkflowTemplate, request.template_id)
    steps = sorted(template.steps, key=lambda s: s.step_order) if template else []
    step = workflow_engine.current_step(steps, request.current_step_order)

    # Raises RequestNotPending (409) or NotAuthorizedApprover (403).
    workflow_engine.assert_can_decide(request, step, user_id=ctx.user.id, role=ctx.role)

    new = workflow_engine.next_state(request, steps, payload.decision)

    db.add(
        ApprovalDecision(
            org_id=ctx.org_id,
            request_id=request.id,
            step_id=step.id if step else None,
            step_order=request.current_step_order,
            decided_by=ctx.user.id,
            decision=payload.decision,
            comment=payload.comment,
        )
    )

    if new.status == RequestStatus.pending:
        request.current_step_order = new.next_step_order or request.current_step_order
        action = audit_service.REQUEST_STEP_APPROVED
        # Notify the approvers of the next step.
        next_step = workflow_engine.current_step(steps, request.current_step_order)
        if next_step is not None:
            notification_service.notify(
                db, org_id=ctx.org_id, user_ids=_approver_user_ids(db, ctx.org_id, next_step),
                type=NotificationType.approval_requested,
                title=f"Approval requested: {request.title}",
                resource_type="approval_request", resource_id=request.id, actor_id=ctx.user.id,
            )
    else:
        request.status = new.status
        request.completed_at = datetime.now(timezone.utc)
        action = (
            audit_service.REQUEST_APPROVED
            if new.status == RequestStatus.approved
            else audit_service.REQUEST_REJECTED
        )

    request.version += 1

    # Notify the requester of the decision.
    notification_service.notify(
        db, org_id=ctx.org_id, user_ids=[request.requester_id],
        type=NotificationType.approval_decided,
        title=f"Your request '{request.title}' was {payload.decision.value}",
        resource_type="approval_request", resource_id=request.id, actor_id=ctx.user.id,
    )
    audit_service.record(
        db, ctx, action, "approval_request", request.id,
        {"step_order": request.current_step_order, "decision": payload.decision.value},
    )
    db.commit()
    db.refresh(request)
    return request


def cancel_request(db: Session, ctx, request_id: uuid.UUID) -> ApprovalRequest:
    request = get_in_org(db, ApprovalRequest, request_id, ctx.org_id)
    if request.requester_id != ctx.user.id:
        raise NotFoundError("Approval request not found")
    if request.status != RequestStatus.pending:
        raise ConflictError("Only pending requests can be cancelled", code="REQUEST_NOT_PENDING")
    request.status = RequestStatus.cancelled
    request.completed_at = datetime.now(timezone.utc)
    request.version += 1
    audit_service.record(db, ctx, audit_service.REQUEST_CANCELLED, "approval_request", request.id)
    db.commit()
    db.refresh(request)
    return request


def count_pending_for_me(db: Session, org_id: uuid.UUID, user_id: uuid.UUID, role: MemberRole) -> int:
    """Reuse the pending-for-me eligibility rule for dashboard metrics."""
    step = WorkflowStep
    return db.execute(
        select(func.count())
        .select_from(ApprovalRequest)
        .join(
            step,
            (step.template_id == ApprovalRequest.template_id)
            & (step.step_order == ApprovalRequest.current_step_order),
        )
        .where(
            ApprovalRequest.org_id == org_id,
            ApprovalRequest.status == RequestStatus.pending,
            ApprovalRequest.requester_id != user_id,
            or_(
                (step.approver_type == ApproverType.role) & (step.approver_role == role),
                (step.approver_type == ApproverType.user) & (step.approver_user_id == user_id),
            ),
        )
    ).scalar_one()


def build_detail_out(db: Session, request: ApprovalRequest, steps, decisions, ctx) -> dict:
    """Assemble the detail response dict (steps, decisions, current step, can_decide)."""
    base = to_out(db, request)
    current = workflow_engine.current_step(steps, request.current_step_order)
    allowed, _ = (
        workflow_engine.can_decide(request, current, user_id=ctx.user.id, role=ctx.role)
        if current is not None
        else (False, "")
    )
    return {
        **base.model_dump(),
        "steps": [WorkflowStepOut.model_validate(s) for s in steps],
        "decisions": [ApprovalDecisionOut.model_validate(d) for d in decisions],
        "current_step": WorkflowStepOut.model_validate(current) if current else None,
        "can_decide": allowed,
    }
