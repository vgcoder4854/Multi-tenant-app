"""Work-management tables (group B).

projects, project_members, tasks, task_status_history.

Composite foreign keys ``(org_id, <parent_id>)`` reference ``(org_id, id)`` on the
parent, so the database itself guarantees a task's project and a member's user all
live in the SAME organization as the task/member row.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ProjectStatus, TaskPriority, TaskStatus
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDMixin, enum_col, utcnow


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        enum_col(ProjectStatus, "project_status"), default=ProjectStatus.active, nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_project_org_name"),
        UniqueConstraint("org_id", "id", name="uq_project_org_id_id"),
        Index("ix_project_org_status", "org_id", "status"),
    )


class ProjectMember(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "project_members"

    org_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "project_id"],
            ["projects.org_id", "projects.id"],
            name="fk_project_members_project_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["org_id", "user_id"],
            ["memberships.org_id", "memberships.user_id"],
            name="fk_project_members_membership_org",
            ondelete="CASCADE",
        ),
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
        Index("ix_project_member_org_project", "org_id", "project_id"),
    )


class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(
        enum_col(TaskPriority, "task_priority"), default=TaskPriority.medium, nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        enum_col(TaskStatus, "task_status"), default=TaskStatus.todo, nullable=False
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        # Composite FKs keep the project and the assignee in the same org.
        ForeignKeyConstraint(
            ["org_id", "project_id"],
            ["projects.org_id", "projects.id"],
            name="fk_tasks_project_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["org_id", "assignee_id"],
            ["memberships.org_id", "memberships.user_id"],
            name="fk_tasks_assignee_org",
            ondelete="SET NULL",
        ),
        UniqueConstraint("org_id", "id", name="uq_task_org_id_id"),
        # Indexes for the common filters.
        Index("ix_task_org_status", "org_id", "status"),
        Index("ix_task_org_assignee", "org_id", "assignee_id"),
        Index("ix_task_org_project", "org_id", "project_id"),
        Index("ix_task_org_due", "org_id", "due_date"),
    )


class TaskStatusHistory(Base, UUIDMixin):
    __tablename__ = "task_status_history"

    org_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    from_status: Mapped[TaskStatus | None] = mapped_column(
        enum_col(TaskStatus, "task_status"), nullable=True
    )
    to_status: Mapped[TaskStatus] = mapped_column(enum_col(TaskStatus, "task_status"), nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "task_id"],
            ["tasks.org_id", "tasks.id"],
            name="fk_task_history_task_org",
            ondelete="CASCADE",
        ),
        Index("ix_task_history_org_task", "org_id", "task_id", "changed_at"),
    )
