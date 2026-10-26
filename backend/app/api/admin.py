"""Administrative/demo endpoints (Module 5)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import OrgContext, require_roles
from app.core.database import get_db
from app.jobs import due_scan
from app.models.enums import MemberRole

router = APIRouter(prefix="/admin", tags=["admin"])

Db = Annotated[Session, Depends(get_db)]
AdminCtx = Annotated[OrgContext, Depends(require_roles(MemberRole.org_admin))]


@router.post("/run-due-scan")
def run_due_scan(ctx: AdminCtx, db: Db) -> dict[str, int]:
    """Run the due/overdue scan for the active organization (demo/manual trigger).

    In production a scheduler runs ``python -m app.jobs.due_scan`` instead.
    """
    return due_scan.run(db, ctx.org_id)
