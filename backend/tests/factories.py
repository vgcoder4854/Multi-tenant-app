"""Factory helpers for tests: build users, orgs, memberships, projects, tasks,
workflow templates quickly. All use the test session and flush (no commit needed).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import (
    ApproverType,
    MemberRole,
    MemberStatus,
    OrgStatus,
    ProjectStatus,
    TaskPriority,
    TaskStatus,
)
from app.models.identity import Membership, Organization, User
from app.models.work import Project, ProjectMember, Task
from app.models.workflow import WorkflowStep, WorkflowTemplate

DEFAULT_PASSWORD = "Password123!"


def create_user(
    db: Session,
    *,
    email: str | None = None,
    password: str = DEFAULT_PASSWORD,
    full_name: str = "Test User",
    is_platform_admin: bool = False,
    is_active: bool = True,
) -> User:
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email.lower(),
        full_name=full_name,
        password_hash=hash_password(password),
        is_platform_admin=is_platform_admin,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    return user


def create_org(db: Session, *, name: str | None = None, status: OrgStatus = OrgStatus.active) -> Organization:
    name = name or f"Org {uuid.uuid4().hex[:6]}"
    org = Organization(name=name, slug=f"org-{uuid.uuid4().hex[:8]}", status=status)
    db.add(org)
    db.commit()
    return org


def add_member(
    db: Session,
    org: Organization,
    user: User,
    role: MemberRole = MemberRole.employee,
    status: MemberStatus = MemberStatus.active,
) -> Membership:
    membership = Membership(org_id=org.id, user_id=user.id, role=role, status=status)
    db.add(membership)
    db.commit()
    return membership


def create_project(
    db: Session,
    org: Organization,
    *,
    name: str | None = None,
    created_by: User | None = None,
    status: ProjectStatus = ProjectStatus.active,
) -> Project:
    project = Project(
        org_id=org.id,
        name=name or f"Project {uuid.uuid4().hex[:6]}",
        status=status,
        created_by=created_by.id if created_by else None,
    )
    db.add(project)
    db.commit()
    return project


def add_project_member(db: Session, project: Project, user: User) -> ProjectMember:
    member = ProjectMember(org_id=project.org_id, project_id=project.id, user_id=user.id)
    db.add(member)
    db.commit()
    return member


def create_task(
    db: Session,
    org: Organization,
    project: Project,
    *,
    title: str = "Task",
    assignee: User | None = None,
    created_by: User | None = None,
    priority: TaskPriority = TaskPriority.medium,
    status: TaskStatus = TaskStatus.todo,
    due_date: date | None = None,
) -> Task:
    task = Task(
        org_id=org.id,
        project_id=project.id,
        title=title,
        priority=priority,
        status=status,
        assignee_id=assignee.id if assignee else None,
        created_by=created_by.id if created_by else None,
        due_date=due_date or (date.today() + timedelta(days=7)),
    )
    db.add(task)
    db.commit()
    return task


def create_template(
    db: Session,
    org: Organization,
    *,
    name: str | None = None,
    steps: list[dict] | None = None,
    created_by: User | None = None,
    is_active: bool = True,
) -> WorkflowTemplate:
    """Create a template with ordered steps.

    ``steps`` items: {"name": str, "approver_type": ApproverType, "role": MemberRole|None,
    "user_id": uuid|None}. Defaults to a single manager step.
    """
    template = WorkflowTemplate(
        org_id=org.id,
        name=name or f"Template {uuid.uuid4().hex[:6]}",
        is_active=is_active,
        created_by=created_by.id if created_by else None,
    )
    db.add(template)
    db.commit()

    steps = steps or [{"name": "Manager approval", "approver_type": ApproverType.role, "role": MemberRole.manager}]
    for order, spec in enumerate(steps, start=1):
        db.add(
            WorkflowStep(
                org_id=org.id,
                template_id=template.id,
                step_order=order,
                name=spec.get("name", f"Step {order}"),
                approver_type=spec["approver_type"],
                approver_role=spec.get("role"),
                approver_user_id=spec.get("user_id"),
            )
        )
    db.commit()
    return template


def make_tenant(db: Session, label: str, roles: dict[str, MemberRole]) -> dict:
    """Create an org with users for each role key. Returns handles.

    Example: make_tenant(db, "a", {"admin": org_admin, "manager": manager, "employee": employee})
    """
    org = create_org(db, name=f"Org {label.upper()}")
    users = {}
    for key, role in roles.items():
        user = create_user(db, email=f"{key}_{label}@example.com", full_name=f"{key.title()} {label.upper()}")
        add_member(db, org, user, role)
        users[key] = user
    return {"org": org, "users": users}
