"""Seed the database with synthetic demo data.

Idempotent: if the demo organizations already exist, it does nothing.
Run with:  python -m app.seed

Everything is fake (no real names/emails/secrets). Most rows are created through
the *real services*, so audit entries and notifications are generated the same way
the API does it.

All demo accounts share the password:  Password123!
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import OrgContext
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import (
    ApproverType,
    DecisionType,
    MemberRole,
    MemberStatus,
    TaskPriority,
    TaskStatus,
)
from app.models.identity import Membership, Organization, User
from app.schemas.task import TaskCreate
from app.schemas.workflow import (
    ApprovalDecisionIn,
    ApprovalRequestCreate,
    WorkflowStepIn,
    WorkflowTemplateCreate,
)
from app.services import project_service, task_service, workflow_service

PASSWORD = "Password123!"
ACME_SLUG = "acme-leave-co"
GLOBEX_SLUG = "globex-purchasing"


def _user(db: Session, email: str, full_name: str, *, platform_admin: bool = False) -> User:
    user = User(
        email=email.lower(),
        full_name=full_name,
        password_hash=hash_password(PASSWORD),
        is_platform_admin=platform_admin,
    )
    db.add(user)
    db.flush()
    return user


def _member(db: Session, org: Organization, user: User, role: MemberRole) -> Membership:
    m = Membership(org_id=org.id, user_id=user.id, role=role, status=MemberStatus.active)
    db.add(m)
    db.flush()
    return m


def _ctx(user: User, org: Organization, role: MemberRole) -> OrgContext:
    return OrgContext(user=user, org_id=org.id, role=role, organization=org)


def seed(db: Session) -> None:
    existing = db.execute(select(Organization).where(Organization.slug == ACME_SLUG)).scalar_one_or_none()
    if existing is not None:
        print("Database already seeded (found 'acme-leave-co'). Nothing to do.")
        return

    # --- Platform admin ---
    _user(db, "platform@demo.test", "Pat Platform", platform_admin=True)

    # --- Organizations ---
    acme = Organization(name="Acme Leave Co", slug=ACME_SLUG)
    globex = Organization(name="Globex Purchasing", slug=GLOBEX_SLUG)
    db.add_all([acme, globex])
    db.flush()

    # --- Users per org ---
    def make_team(prefix: str) -> dict[str, User]:
        return {
            "admin": _user(db, f"admin.{prefix}@demo.test", f"{prefix.title()} Admin"),
            "manager1": _user(db, f"manager1.{prefix}@demo.test", f"{prefix.title()} Manager One"),
            "manager2": _user(db, f"manager2.{prefix}@demo.test", f"{prefix.title()} Manager Two"),
            "emp1": _user(db, f"emp1.{prefix}@demo.test", f"{prefix.title()} Employee One"),
            "emp2": _user(db, f"emp2.{prefix}@demo.test", f"{prefix.title()} Employee Two"),
            "emp3": _user(db, f"emp3.{prefix}@demo.test", f"{prefix.title()} Employee Three"),
        }

    acme_team = make_team("acme")
    globex_team = make_team("globex")

    # A user who belongs to BOTH orgs with different roles (workspace-switch demo).
    shared = _user(db, "shared.user@demo.test", "Sam Shared")

    for org, team in ((acme, acme_team), (globex, globex_team)):
        _member(db, org, team["admin"], MemberRole.org_admin)
        _member(db, org, team["manager1"], MemberRole.manager)
        _member(db, org, team["manager2"], MemberRole.manager)
        _member(db, org, team["emp1"], MemberRole.employee)
        _member(db, org, team["emp2"], MemberRole.employee)
        _member(db, org, team["emp3"], MemberRole.employee)

    _member(db, acme, shared, MemberRole.manager)
    _member(db, globex, shared, MemberRole.employee)
    db.commit()

    # --- Projects (via service -> audited) ---
    def new_project(org, admin_user, name, description):
        ctx = _ctx(admin_user, org, MemberRole.org_admin)
        return project_service.create_project(db, ctx, name=name, description=description)

    a_p1 = new_project(acme, acme_team["admin"], "Q3 Hiring", "Hiring pipeline for Q3")
    a_p2 = new_project(acme, acme_team["admin"], "Office Move", "Relocate the Lisbon office")
    g_p1 = new_project(globex, globex_team["admin"], "Vendor Onboarding", "New supplier onboarding")
    g_p2 = new_project(globex, globex_team["admin"], "Budget Planning", "FY budget preparation")

    # Add project members so managers may create tasks.
    for project, users in (
        (a_p1, [acme_team["manager1"], acme_team["manager2"], acme_team["emp1"], acme_team["emp2"], shared]),
        (a_p2, [acme_team["manager1"], acme_team["manager2"], acme_team["emp1"], acme_team["emp2"]]),
        (g_p1, [globex_team["manager1"], globex_team["manager2"], globex_team["emp1"], shared]),
        (g_p2, [globex_team["manager1"], globex_team["manager2"], globex_team["emp2"]]),
    ):
        org = acme if project.org_id == acme.id else globex
        admin = acme_team["admin"] if org is acme else globex_team["admin"]
        ctx = _ctx(admin, org, MemberRole.org_admin)
        for u in users:
            project_service.add_project_member(db, ctx, project.id, u.id)

    # --- Tasks (via service -> history + notifications + audit) ---
    today = date.today()

    def new_task(org, manager, project, title, assignee, priority, status, due):
        ctx = _ctx(manager, org, MemberRole.manager)
        task = task_service.create_task(
            db, ctx,
            TaskCreate(project_id=project.id, title=title, priority=priority, assignee_id=assignee.id, due_date=due),
        )
        if status != TaskStatus.todo:
            # walk the state machine to the target status (generates history/notifications)
            path = {
                TaskStatus.in_progress: [TaskStatus.in_progress],
                TaskStatus.blocked: [TaskStatus.in_progress, TaskStatus.blocked],
                TaskStatus.completed: [TaskStatus.in_progress, TaskStatus.completed],
            }[status]
            for s in path:
                task = task_service.change_status(db, ctx, task.id, s)
        return task

    new_task(acme, acme_team["manager1"], a_p1, "Write job descriptions", acme_team["emp1"], TaskPriority.high, TaskStatus.in_progress, today + timedelta(days=3))
    new_task(acme, acme_team["manager1"], a_p1, "Screen CVs", acme_team["emp2"], TaskPriority.medium, TaskStatus.todo, today + timedelta(days=10))
    new_task(acme, acme_team["manager1"], a_p1, "Schedule interviews", shared, TaskPriority.low, TaskStatus.todo, today - timedelta(days=2))
    new_task(acme, acme_team["manager2"], a_p2, "Book movers", acme_team["emp2"], TaskPriority.critical, TaskStatus.blocked, today + timedelta(days=5))
    new_task(acme, acme_team["manager2"], a_p2, "Update address records", acme_team["emp1"], TaskPriority.medium, TaskStatus.completed, today - timedelta(days=1))
    new_task(acme, acme_team["manager2"], a_p2, "Order new furniture", acme_team["emp1"], TaskPriority.high, TaskStatus.todo, today + timedelta(days=20))

    new_task(globex, globex_team["manager1"], g_p1, "Collect W-9 forms", globex_team["emp1"], TaskPriority.high, TaskStatus.in_progress, today + timedelta(days=4))
    new_task(globex, globex_team["manager1"], g_p1, "Verify insurance", globex_team["emp1"], TaskPriority.medium, TaskStatus.todo, today - timedelta(days=3))
    new_task(globex, globex_team["manager1"], g_p1, "Sign agreements", shared, TaskPriority.critical, TaskStatus.todo, today + timedelta(days=2))
    new_task(globex, globex_team["manager2"], g_p2, "Draft department budgets", globex_team["emp2"], TaskPriority.high, TaskStatus.in_progress, today + timedelta(days=7))
    new_task(globex, globex_team["manager2"], g_p2, "Review with finance", globex_team["emp2"], TaskPriority.medium, TaskStatus.completed, today - timedelta(days=5))
    new_task(globex, globex_team["manager2"], g_p2, "Publish final budget", globex_team["emp1"], TaskPriority.low, TaskStatus.todo, today + timedelta(days=30))

    # --- Workflow templates ---
    leave_tpl = workflow_service.create_template(
        db, _ctx(acme_team["admin"], acme, MemberRole.org_admin),
        WorkflowTemplateCreate(
            name="Leave Approval",
            description="Manager approves leave requests",
            steps=[WorkflowStepIn(name="Manager approval", approver_type=ApproverType.role, approver_role=MemberRole.manager)],
        ),
    )
    purchase_tpl = workflow_service.create_template(
        db, _ctx(globex_team["admin"], globex, MemberRole.org_admin),
        WorkflowTemplateCreate(
            name="Purchase Request",
            description="Manager then org admin approval",
            steps=[
                WorkflowStepIn(name="Manager approval", approver_type=ApproverType.role, approver_role=MemberRole.manager),
                WorkflowStepIn(name="Admin approval", approver_type=ApproverType.role, approver_role=MemberRole.org_admin),
            ],
        ),
    )

    # --- Approval requests in different states ---
    def submit(org, requester, template, title, details):
        return workflow_service.submit_request(
            db, _ctx(requester, org, MemberRole.employee),
            ApprovalRequestCreate(template_id=template.id, title=title, details=details),
        )

    r1 = submit(acme, acme_team["emp1"], leave_tpl, "Annual leave 12–16 May", {"days": 5})
    workflow_service.decide(
        db, _ctx(acme_team["manager1"], acme, MemberRole.manager), r1.id,
        ApprovalDecisionIn(decision=DecisionType.approved, comment="Enjoy!"),
    )

    r2 = submit(acme, acme_team["emp2"], leave_tpl, "Sick leave", {"days": 1})
    workflow_service.decide(
        db, _ctx(acme_team["manager1"], acme, MemberRole.manager), r2.id,
        ApprovalDecisionIn(decision=DecisionType.rejected, comment="Too many absences"),
    )

    submit(acme, acme_team["emp3"], leave_tpl, "Leave in July", {"days": 3})  # stays pending

    r4 = submit(globex, globex_team["emp1"], purchase_tpl, "New laptops", {"amount": 4200})
    workflow_service.decide(
        db, _ctx(globex_team["manager1"], globex, MemberRole.manager), r4.id,
        ApprovalDecisionIn(decision=DecisionType.approved, comment="Justified"),
    )
    # now awaiting admin at step 2

    submit(globex, globex_team["emp2"], purchase_tpl, "Conference tickets", {"amount": 900})  # pending step 1

    print("\nSeed complete.\n")
    print("Demo logins (password for all accounts: Password123!)\n")
    print(f"{'Email':<32}{'Role / Org'}")
    print("-" * 60)
    rows = [
        ("platform@demo.test", "Platform Administrator"),
        ("admin.acme@demo.test", "org_admin @ Acme Leave Co"),
        ("manager1.acme@demo.test", "manager @ Acme Leave Co"),
        ("manager2.acme@demo.test", "manager @ Acme Leave Co"),
        ("emp1.acme@demo.test", "employee @ Acme Leave Co"),
        ("emp2.acme@demo.test", "employee @ Acme Leave Co"),
        ("emp3.acme@demo.test", "employee @ Acme Leave Co"),
        ("admin.globex@demo.test", "org_admin @ Globex Purchasing"),
        ("manager1.globex@demo.test", "manager @ Globex Purchasing"),
        ("manager2.globex@demo.test", "manager @ Globex Purchasing"),
        ("emp1.globex@demo.test", "employee @ Globex Purchasing"),
        ("emp2.globex@demo.test", "employee @ Globex Purchasing"),
        ("emp3.globex@demo.test", "employee @ Globex Purchasing"),
        ("shared.user@demo.test", "manager @ Acme  +  employee @ Globex (switch demo)"),
    ]
    for email, role in rows:
        print(f"{email:<32}{role}")


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
