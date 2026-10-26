"""End-to-end smoke test against PostgreSQL (embedded pgserver).

Run with:
  DATABASE_URL='postgresql+psycopg://postgres@/postgres?host=/tmp/opencode/pg_mt' \
    backend/.venv/bin/python scripts/pg_smoke.py
"""
import os
import uuid

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
suffix = uuid.uuid4().hex[:8]

def h(tok):
    return {"Authorization": f"Bearer {tok}"}

# register + login
r = c.post("/api/v1/auth/register", json={"email": f"admin_{suffix}@ex.com", "password": "Password123!", "full_name": "Admin"})
assert r.status_code == 201, r.text
r = c.post("/api/v1/auth/login", json={"email": f"admin_{suffix}@ex.com", "password": "Password123!"})
tok = r.json()["access_token"]

# org
r = c.post("/api/v1/organizations", json={"name": f"Smoke {suffix}"}, headers=h(tok))
assert r.status_code == 201, r.text
org_id = r.json()["id"]
r = c.post("/api/v1/auth/switch-organization", json={"org_id": org_id}, headers=h(tok))
tok = r.json()["access_token"]

# project + task
r = c.post("/api/v1/projects", json={"name": f"Proj {suffix}"}, headers=h(tok))
assert r.status_code == 201, r.text
pid = r.json()["id"]
me = c.get("/api/v1/auth/me", headers=h(tok)).json()
r = c.post("/api/v1/tasks", json={"project_id": pid, "title": "Smoke task", "assignee_id": me["id"]}, headers=h(tok))
assert r.status_code == 201, r.text
tid = r.json()["id"]
r = c.patch(f"/api/v1/tasks/{tid}/status", json={"status": "in_progress"}, headers=h(tok))
assert r.status_code == 200 and r.json()["status"] == "in_progress", r.text

# workflow: template (role manager) -> submit -> admin is not manager so use user approver = me
r = c.post("/api/v1/workflow-templates", json={
    "name": f"Tpl {suffix}",
    "steps": [{"name": "Admin", "approver_type": "user", "approver_user_id": me["id"]}],
}, headers=h(tok))
assert r.status_code == 201, r.text
tpl = r.json()["id"]
# requester cannot approve own request
r = c.post("/api/v1/approval-requests", json={"template_id": tpl, "title": "Smoke request"}, headers=h(tok))
assert r.status_code == 201, r.text
req = r.json()["id"]
r = c.post(f"/api/v1/approval-requests/{req}/decision", json={"decision": "approved"}, headers=h(tok))
assert r.status_code == 403, r.text  # self-approval blocked

# dashboard + audit + notifications
r = c.get("/api/v1/dashboard/summary", headers=h(tok))
assert r.status_code == 200 and r.json()["tasks_by_status"]["in_progress"] == 1, r.text
r = c.get("/api/v1/audit-logs", headers=h(tok))
assert r.status_code == 200 and r.json()["total"] > 0, r.text
r = c.get("/api/v1/notifications", headers=h(tok))
assert r.status_code == 200, r.text

# audit is append-only at the DB level
from app.core.database import engine
from sqlalchemy import text
try:
    with engine.begin() as conn:
        conn.execute(text("UPDATE audit_logs SET action='x'"))
    raise SystemExit("BUG: audit update was not blocked")
except Exception as exc:
    assert "append-only" in str(exc), exc

print("POSTGRES SMOKE TEST: OK")
print("  org:", org_id, "project:", pid, "task:", tid, "request:", req)
