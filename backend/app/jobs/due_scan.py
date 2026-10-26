"""Due / overdue scan job (Module 5).

Finds tasks that are due within the next 24 hours or already overdue and not
completed, and creates one notification per task per day for the assignee. The
"per day" rule is enforced with ``already_notified`` (type + resource + today).

Run manually:
    python -m app.jobs.due_scan            # all organizations
    python -m app.jobs.due_scan --org <id> # one organization

In production this would be scheduled (cron, Celery beat, APScheduler); the CLI is
just a convenient entry point.
"""
from __future__ import annotations

import argparse
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import NotificationType, TaskStatus
from app.models.work import Task
from app.services import notification_service


def _start_of_today_utc() -> datetime:
    return datetime.combine(date.today(), time.min, tzinfo=timezone.utc)


def run(db: Session, org_id: uuid.UUID | None = None) -> dict[str, int]:
    """Scan tasks and create due/overdue notifications. Returns counts."""
    today = date.today()
    horizon = today + timedelta(days=1)

    stmt = select(Task).where(
        Task.status != TaskStatus.completed,
        Task.due_date.is_not(None),
        Task.due_date <= horizon,
    )
    if org_id is not None:
        stmt = stmt.where(Task.org_id == org_id)
    tasks = list(db.execute(stmt).scalars().all())

    since = _start_of_today_utc()
    notified = 0
    for task in tasks:
        if task.assignee_id is None:
            continue
        ntype = NotificationType.task_overdue if task.due_date < today else NotificationType.task_due_soon
        if notification_service.already_notified(
            db, user_id=task.assignee_id, type=ntype, resource_id=task.id, since=since
        ):
            continue
        title = (
            f"Task overdue: {task.title}"
            if ntype == NotificationType.task_overdue
            else f"Task due soon: {task.title}"
        )
        notification_service.notify(
            db,
            org_id=task.org_id,
            user_ids=[task.assignee_id],
            type=ntype,
            title=title,
            body=f"Due {task.due_date.isoformat()}",
            resource_type="task",
            resource_id=task.id,
        )
        notified += 1

    db.commit()
    return {"scanned": len(tasks), "notified": notified}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the due/overdue scan")
    parser.add_argument("--org", default=None, help="organization id (optional)")
    args = parser.parse_args()

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        result = run(db, uuid.UUID(args.org) if args.org else None)
        print(f"due_scan: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
