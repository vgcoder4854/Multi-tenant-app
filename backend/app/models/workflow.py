"""Workflow tables (group C).

workflow_templates, workflow_steps, approval_requests, approval_decisions.

A template is an ordered list of steps. Each step names its approver as a ROLE or
a specific USER (enforced by a CHECK constraint). A request walks the steps in
order; every decision is recorded once per step (UNIQUE(request_id, step_order)).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ApproverType, DecisionType, MemberRole, RequestStatus
from app.models.mixins import CreatedAtMixin, JSONType, TimestampMixin, UUIDMixin, enum_col, utcnow


class WorkflowTemplate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workflow_templates"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.step_order",
    )

    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_template_org_name"),
        UniqueConstraint("org_id", "id", name="uq_template_org_id_id"),
    )


class WorkflowStep(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "workflow_steps"

    org_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    approver_type: Mapped[ApproverType] = mapped_column(
        enum_col(ApproverType, "approver_type"), nullable=False
    )
    approver_role: Mapped[MemberRole | None] = mapped_column(
        enum_col(MemberRole, "member_role"), nullable=True
    )
    approver_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    template: Mapped[WorkflowTemplate] = relationship(back_populates="steps")

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "template_id"],
            ["workflow_templates.org_id", "workflow_templates.id"],
            name="fk_workflow_steps_template_org",
            ondelete="CASCADE",
        ),
        UniqueConstraint("template_id", "step_order", name="uq_template_step_order"),
        CheckConstraint("step_order >= 1", name="ck_workflow_step_order_positive"),
        CheckConstraint(
            "(approver_type = 'role' AND approver_role IS NOT NULL AND approver_user_id IS NULL) "
            "OR (approver_type = 'user' AND approver_user_id IS NOT NULL AND approver_role IS NULL)",
            name="ck_workflow_step_approver",
        ),
    )


class ApprovalRequest(Base, UUIDMixin):
    __tablename__ = "approval_requests"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        enum_col(RequestStatus, "request_status"),
        default=RequestStatus.pending,
        nullable=False,
    )
    current_step_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Optimistic locking: two approvers cannot both advance the same version.
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    decisions: Mapped[list["ApprovalDecision"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="ApprovalDecision.step_order",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "template_id"],
            ["workflow_templates.org_id", "workflow_templates.id"],
            name="fk_approval_requests_template_org",
        ),
        UniqueConstraint("org_id", "id", name="uq_request_org_id_id"),
        Index("ix_request_org_status", "org_id", "status"),
        Index("ix_request_org_requester", "org_id", "requester_id"),
    )


class ApprovalDecision(Base, UUIDMixin):
    __tablename__ = "approval_decisions"

    org_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    step_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_steps.id", ondelete="SET NULL"), nullable=True
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    decided_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision: Mapped[DecisionType] = mapped_column(enum_col(DecisionType, "decision_type"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    request: Mapped[ApprovalRequest] = relationship(back_populates="decisions")

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "request_id"],
            ["approval_requests.org_id", "approval_requests.id"],
            name="fk_approval_decisions_request_org",
            ondelete="CASCADE",
        ),
        UniqueConstraint("request_id", "step_order", name="uq_decision_request_step"),
        Index("ix_decision_org_request", "org_id", "request_id"),
    )
