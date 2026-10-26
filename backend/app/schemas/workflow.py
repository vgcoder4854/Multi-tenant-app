"""Workflow and approval schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    ApproverType,
    DecisionType,
    MemberRole,
    RequestStatus,
)


# --------------------------------------------------------------------------- #
# Templates and steps
# --------------------------------------------------------------------------- #
class WorkflowStepIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    approver_type: ApproverType
    approver_role: MemberRole | None = None
    approver_user_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _check_approver(self) -> "WorkflowStepIn":
        if self.approver_type == ApproverType.role:
            if self.approver_role is None or self.approver_user_id is not None:
                raise ValueError("role steps need approver_role and no approver_user_id")
        else:
            if self.approver_user_id is None or self.approver_role is not None:
                raise ValueError("user steps need approver_user_id and no approver_role")
        return self


class WorkflowTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    steps: list[WorkflowStepIn] = Field(min_length=1)


class WorkflowTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None
    steps: list[WorkflowStepIn] | None = Field(default=None, min_length=1)


class WorkflowStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    step_order: int
    name: str
    approver_type: ApproverType
    approver_role: MemberRole | None
    approver_user_id: uuid.UUID | None


class WorkflowTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    steps: list[WorkflowStepOut] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Approval requests
# --------------------------------------------------------------------------- #
class ApprovalRequestCreate(BaseModel):
    template_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    details: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    template_id: uuid.UUID
    template_name: str
    requester_id: uuid.UUID
    requester_name: str
    title: str
    details: dict[str, Any]
    status: RequestStatus
    current_step_order: int
    submitted_at: datetime
    completed_at: datetime | None


class ApprovalDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    step_order: int
    step_id: uuid.UUID | None
    decided_by: uuid.UUID | None
    decision: DecisionType
    comment: str | None
    decided_at: datetime


class ApprovalRequestDetailOut(ApprovalRequestOut):
    steps: list[WorkflowStepOut] = Field(default_factory=list)
    decisions: list[ApprovalDecisionOut] = Field(default_factory=list)
    current_step: WorkflowStepOut | None = None
    can_decide: bool = False


class ApprovalDecisionIn(BaseModel):
    decision: DecisionType
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _comment_required_on_reject(self) -> "ApprovalDecisionIn":
        if self.decision == DecisionType.rejected and not (self.comment or "").strip():
            raise ValueError("A comment is required when rejecting")
        return self
