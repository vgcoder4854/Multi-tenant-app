# AGENT.md — Multi-Tenant Workflow Platform (living knowledge base)

> This file is the project's memory. It is updated after **every** step (DOC-RULE).
> If the agent loses context: *Re-read AGENT.md and continue.*

---

## 1. Project Overview

An enterprise SaaS **workflow management platform**. Several organizations (tenants)
share one application to manage projects, tasks, sequential approval workflows,
in-app notifications and an audit trail. Each organization is **logically isolated**:
a user of Org A must never read or change Org B data, even by guessing IDs.

Users: Platform Administrator, Organization Administrator, Manager, Employee.
Built as a graded assessment: correct **authorization**, **tenant isolation**,
**business logic**, **integrity** and **tests** matter more than visual polish.

---

## 2. Architecture and Folder Map

Layered backend (HTTP → business logic → DB) + React SPA frontend.

```
/backend
  app/
    api/         Routers: parse HTTP, call services. No business logic.
    services/    Business logic + transactions. Receive db session, user, org_id.
    models/      SQLAlchemy 2.0 ORM models (one file per table group).
    schemas/     Pydantic request/response models (separate from ORM).
    core/        config, database, security, permissions, errors.
    jobs/        Standalone jobs (due/overdue scan).
  alembic/       Migration environment + versioned migrations.
  tests/         Pytest suites (fixtures, factories, security/workflow/... tests).
/frontend
  src/
    api/         Single HTTP client + typed endpoint functions.
    components/  ui/ primitives, layout/ shell, shared guards & forms.
    pages/       Route-level pages (auth, dashboard, projects, tasks, ...).
    hooks/       TanStack Query hooks (one per feature).
    lib/         Auth context, helpers.
    types/       TypeScript types mirroring backend Pydantic schemas.
/docs            ER diagram, architecture, API reference, checklists.
/docker-compose.yml, .env.example, Makefile, README.md, AGENT.md
```

**Request flow:** browser → API client (Bearer token) → router → Pydantic validation →
dependencies (`get_current_user` → `get_org_context` → `require_roles`) → service
(one DB transaction, always filtered by `org_id`) → PostgreSQL constraints/triggers →
`response_model` → TanStack Query cache → UI.

---

## 3. Concepts

- **Multi-tenancy (row-level):** one database, one schema. Every tenant-owned table
  has `org_id` (NOT NULL, FK, indexed). Queries always filter by the `org_id` that was
  **verified from the token + DB membership**, never from the request body.
- **RBAC:** a user has a role *per organization* via `memberships`
  (`org_admin`, `manager`, `employee`), plus a global `is_platform_admin` flag.
- **JWT:** login returns a signed token (identity). Choosing a workspace returns a new
  token carrying `org_id`. The backend still re-checks membership on every request.
- **Workflow state machine:** a request is `pending → approved | rejected | cancelled`.
  Final states never transition again. Approvals walk ordered steps; rejection ends it.
- **Audit trail:** append-only log (actor, org, action, resource, metadata). A DB trigger
  blocks UPDATE/DELETE so history cannot be altered even by an application bug.
- **Optimistic locking:** `approval_requests.version` + `SELECT ... FOR UPDATE` prevent two
  approvers deciding the same step at once.

*(Detailed JWT / password-hashing / invitation-flow notes added in step 4.3.)*

- **Password hashing:** Argon2id via `pwdlib`. `hash_password` / `verify_password`
  never log or return the plaintext; an unknown hash simply fails verification.
- **JWT flow:** `create_access_token(user_id, org_id=None)` signs an HS256 token with
  `sub`, `iat`, `exp` and (after workspace selection) `org_id`. `decode_token` raises a
  typed 401 (`TOKEN_EXPIRED` / `TOKEN_INVALID`).
- **Invitation flow:** `generate_invite_token()` returns `(raw, hash)`. Only the SHA-256
  `hash` is stored; the `raw` token is shown once. Accepting an invite matches the hash,
  checks status/expiry, and creates the membership in one transaction.
- **Why re-check membership in the DB:** a JWT is a *snapshot*. If an admin removes a
  member or suspends an org, the old token would still say "member". So `get_org_context`
  re-reads the active membership and the org status on every request — revocation is
  immediate.

A protected route in full:

```python
@router.get("/projects")
def list_projects(ctx: OrgCtx, db: Session = Depends(get_db)):
    return project_service.list_projects(db, ctx)   # ctx.org_id is verified, never from the body
```

---

## 4. Modules and Libraries Used

| Library | Why | Where |
| --- | --- | --- |
| FastAPI | Typed REST + auto Swagger | `app/api/*` |
| Pydantic v2 / pydantic-settings | Validation + env config | `app/schemas/*`, `app/core/config.py` |
| SQLAlchemy 2.0 | Typed ORM + Core queries | `app/models/*`, `app/services/*` |
| Alembic | Versioned schema | `backend/alembic/*` |
| PostgreSQL | Production DB | `DATABASE_URL` |
| SQLite | Zero-setup local dev/test fallback | `DATABASE_URL=sqlite:///...` |
| PyJWT | Signed access tokens | `app/core/security.py` |
| argon2-cffi (pwdlib/argon2) | Password hashing | `app/core/security.py` |
| Pytest + httpx | API integration tests w/ DB assertions | `backend/tests/*` |
| React + TS (Vite) | SPA UI | `frontend/src/*` |
| Tailwind | Utility styling | `frontend/src/index.css` |
| React Router | Client routes + guards | `frontend/src/App.tsx` |
| TanStack Query | Server-state cache | `frontend/src/hooks/*` |
| React Hook Form + Zod | Typed forms | `frontend/src/pages/*` |
| Vitest + RTL | Frontend tests | `frontend/src/**/*.test.tsx` |

**Portability note:** models use portable SQLAlchemy types so the *same* code runs on
SQLite (dev) and PostgreSQL (prod): `Uuid`, `JSON` (JSONB variant on PG), `Enum(native_enum=False)`
(CHECK-constrained — the playbook explicitly allows "CHECK-constrained strings").
The audit append-only rule is enforced by a trigger written per-dialect (PL/pgSQL on
PostgreSQL, `RAISE(ABORT)` on SQLite).

---

## 5. Code Reference

*(Filled in as modules are built — see per-step Change Log entries.)*

| Module | Purpose | Key callables |
| --- | --- | --- |
| `app/core/config.py` | Env-driven settings | `Settings`, `get_settings()` |
| `app/core/database.py` | Engine, session factory, `Base` | `get_db()` |
| `app/main.py` | App factory, CORS, error handler | `app`, `create_app()` |
| `app/core/security.py` | Hashing + JWT | `hash_password`, `verify_password`, `create_access_token`, `decode_token`, `generate_invite_token` |
| `app/api/deps.py` | Auth dependencies | `get_current_user`, `get_org_context`, `require_roles`, `require_platform_admin` |
| `app/services/tenant.py` | Tenant-safe helpers | `get_in_org`, `list_query`, `assert_same_org` |
| `app/core/permissions.py` | Permission matrix | `PERMISSIONS` |
| `app/services/audit_service.py` | Append-only audit | `record()` |
| `app/services/workflow_engine.py` | Pure state machine | `can_decide`, `next_state` |
| `app/models/mixins.py` | Shared columns/types | `UUIDMixin`, `CreatedAtMixin`, `TimestampMixin`, `enum_col`, `JSONType`, `utcnow` |
| `app/models/identity.py` | Group A tables | `User`, `Organization`, `Membership`, `Invitation` |
| `app/models/work.py` | Group B tables | `Project`, `ProjectMember`, `Task`, `TaskStatusHistory` |
| `app/models/workflow.py` | Group C tables | `WorkflowTemplate`, `WorkflowStep`, `ApprovalRequest`, `ApprovalDecision` |
| `app/models/comms.py` | Group D tables | `Notification`, `AuditLog` |
| `app/models/registry.py` | Registers every model | imported by Alembic |
| `app/core/errors.py` | Typed business errors | `AppError`, `UnauthorizedError`, `ForbiddenError`, `OrgSuspendedError`, `NotFoundError`, `ConflictError`, `ValidationError` |
| `app/services/auth_service.py` | Register / login / me | `register`, `authenticate`, `build_me` |
| `app/services/org_service.py` | Orgs, invitations, members | `create_organization`, `list_my_organizations`, `switch_organization`, `invite_member`, `accept_invitation`, `change_member_role`, `remove_member` |
| `app/services/platform_service.py` | Platform admin | `list_organizations`, `set_organization_status`, `stats` |
| `app/services/email_service.py` | Mocked email | `send_invitation_email` |
| `app/services/project_service.py` | Projects + members | `create_project`, `list_projects`, `get_project`, `update_project`, `archive_project`, `add/remove/list_project_members` |
| `app/services/task_service.py` | Tasks + status history | `create_task`, `update_task`, `change_status`, `get_task`, `list_tasks`, `ALLOWED_TRANSITIONS` |
| `app/services/notification_service.py` | In-app notifications | `notify()` |
| `app/services/workflow_engine.py` | Pure state machine (no DB) | `can_decide`, `assert_can_decide`, `next_state`, `current_step`, `RequestNotPending`, `NotAuthorizedApprover` |
| `app/services/workflow_service.py` | Templates + requests | `create_template`, `update_template`, `deactivate_template`, `submit_request`, `decide`, `cancel_request`, `list_pending_for_me`, `count_pending_for_me` |
| `app/services/dashboard_service.py` | SQL-aggregate metrics + CSV | `summary`, `export_tasks_csv` |

---

## 6. Business Logic and Rules

- **Tenant isolation:** every read/write goes through org-scoped helpers
  (`app/services/tenant.py`). Cross-tenant resource IDs return **404** (not 403) so IDs
  cannot be probed.
- **Auth:** passwords only stored hashed; same 401 message for wrong email or password;
  inactive users rejected.
- **Workspaces:** a suspended organization blocks all its tenant endpoints (403
  `ORG_SUSPENDED`), enforced in `get_org_context`.
- **At least one org_admin:** demoting/removing the last active `org_admin` is blocked (409).
- **Projects/tasks:** archived projects are read-only; a task assignee must be an active
  member of the same org; every status change writes `task_status_history`.
- **Workflow:** only the current step's approver may decide; never the requester; final
  requests cannot be decided again (409); all changes atomic under a row lock.
- **Audit:** append-only; every important action recorded in the same transaction.

**Permission matrix** (`app/core/permissions.py`):

| Action | org_admin | manager | employee |
| --- | :-: | :-: | :-: |
| project.create / update / archive | ✅ | | |
| project.member.manage | ✅ | | |
| task.create / assign / update | ✅ | ✅ | |
| task.status_change | ✅ | ✅ | ✅ (own tasks only) |
| workflow.manage | ✅ | | |
| request.submit | ✅ | ✅ | ✅ |
| request.decide | ✅ | ✅ | (per-step check in engine) |
| audit.view | ✅ | | |
| report.view | ✅ | ✅ | |
| member.manage | ✅ | | |
| dashboard.view | ✅ | ✅ | ✅ |

**Task status transitions** (`app/services/task_service.py::ALLOWED_TRANSITIONS`):

```
todo        -> in_progress | blocked | completed
in_progress -> todo | blocked | completed
blocked     -> todo | in_progress | completed
completed   -> todo | in_progress        # reopening is allowed (iterative work)
```

Same status or any other move → 409 `SAME_STATUS` / `INVALID_TRANSITION`. Only the
assignee, a manager who is a project member, or an org_admin may change status.
Archived projects are read-only (409 `PROJECT_ARCHIVED`).

*(Exact transition rules and matrix tables added in later steps.)*

---

## 7. Database Notes

**Groups:** A) identity/tenancy (`users`, `organizations`, `memberships`, `invitations`);
B) work (`projects`, `project_members`, `tasks`, `task_status_history`);
C) workflow (`workflow_templates`, `workflow_steps`, `approval_requests`, `approval_decisions`);
D) comms/compliance (`notifications`, `audit_logs`).

Full ER diagram: `docs/er-diagram.md`.

**Migrations** (`backend/alembic/versions/`, applied with `alembic upgrade head`):

| Rev | Step | Tables |
| --- | --- | --- |
| `7dc57edff646` | 4.2.1 | users, organizations, memberships, invitations |
| `ee8978ef4f55` | 4.2.2 | projects, project_members, tasks, task_status_history |
| `1a56dc8b2ff7` | 4.2.3 | workflow_templates, workflow_steps, approval_requests, approval_decisions |
| `37108ea71cca` | 4.2.4 | notifications, audit_logs + append-only trigger |

Verified reversible: `alembic downgrade base` then `alembic upgrade head` both succeed
on SQLite **and** PostgreSQL 16.

**Constraints and indexes (and why):**

| Object | Reason |
| --- | --- |
| `organizations.slug` UNIQUE | human-friendly unique handle |
| `users.email` UNIQUE (+ lowercased on write) | one account per email, case-insensitive |
| `memberships` UNIQUE(org_id, user_id) | no duplicate membership |
| `memberships` UNIQUE(org_id, id) | target for composite FKs |
| `invitations` partial UNIQUE(org_id, email) WHERE status='pending' | one pending invite per email/org |
| `projects` UNIQUE(org_id, name) | no duplicate project names within an org |
| `tasks/projects/templates/requests` UNIQUE(org_id, id) | targets for composite FKs |
| `tasks` FK(org_id, project_id)→projects(org_id,id) | task's project is same-org (DB-enforced) |
| `tasks` FK(org_id, assignee_id)→memberships(org_id,user_id) | assignee is a same-org member |
| `project_members` FK(org_id, project_id), FK(org_id, user_id) | member + project same-org |
| `task_status_history` FK(org_id, task_id) | history row same-org as its task |
| `workflow_steps` UNIQUE(template_id, step_order), CHECK step_order>=1, CHECK approver column matches type | contiguous ordered steps; exactly one approver source |
| `approval_requests` FK(org_id, template_id), `version` | same-org template; optimistic lock |
| `approval_decisions` UNIQUE(request_id, step_order) | one decision per step |
| `audit_logs` trigger | append-only (no UPDATE/DELETE) |
| Indexes | `tasks(org_id,status)`, `(org_id,assignee_id)`, `(org_id,project_id)`, `(org_id,due_date)`; `notifications(user_id,is_read,created_at)`; `audit_logs(org_id,created_at)`; `approval_requests(org_id,status)` — all match the common query filters. |

---

## 8. API Reference Summary

All paths are under `/api/v1`. Full table in `docs/api.md`.

### Auth (tag `auth`)
| Method | Path | Auth | Success | Errors |
| --- | --- | --- | --- | --- |
| POST | `/auth/register` | none | 201 UserOut | 409 EMAIL_TAKEN, 422 |
| POST | `/auth/login` | none | 200 TokenResponse | 401 INVALID_CREDENTIALS / USER_INACTIVE |
| GET | `/auth/me` | token | 200 MeOut | 401 |
| POST | `/auth/switch-organization` | token | 200 TokenResponse | 401, 403 NOT_A_MEMBER |

### Organizations / members / invitations
| Method | Path | Role | Success | Errors |
| --- | --- | --- | --- | --- |
| POST | `/organizations` | any user | 201 OrganizationOut | 409 SLUG_TAKEN |
| GET | `/organizations/mine` | any user | 200 [MyOrganizationOut] | 401 |
| POST | `/org/invitations` | org_admin | 201 InvitationCreatedOut (with raw token) | 409 ALREADY_MEMBER / INVITATION_EXISTS |
| GET | `/org/invitations` | org_admin | 200 [InvitationOut] | 403 |
| DELETE | `/org/invitations/{id}` | org_admin | 204 | 404, 409 INVITATION_NOT_PENDING |
| GET | `/org/members` | any member | 200 [MemberOut] | 403 |
| PATCH | `/org/members/{user_id}/role` | org_admin | 200 MemberOut | 404, 409 LAST_ADMIN |
| DELETE | `/org/members/{user_id}` | org_admin | 204 | 404, 409 LAST_ADMIN |
| POST | `/invitations/accept` | token | 200 OrganizationOut | 403 EMAIL_MISMATCH, 404, 409, 422 EXPIRED |

### Platform admin (tag `platform-admin`)
| Method | Path | Auth | Success |
| --- | --- | --- | --- |
| GET | `/platform/organizations` | platform admin | 200 Page[OrganizationOut] (filter status, name) |
| PATCH | `/platform/organizations/{id}/status` | platform admin | 200 OrganizationOut (audited) |
| GET | `/platform/stats` | platform admin | 200 counts |

**Where suspension is enforced:** `get_org_context` (`app/api/deps.py`) rejects a
suspended org with 403 `ORG_SUSPENDED` on every tenant endpoint. `switch-organization`
still succeeds (so the UI can show a clear "suspended" page).

### Workflow templates (tag `workflow-templates`)
| Method | Path | Role | Success | Errors |
| --- | --- | --- | --- | --- |
| POST | `/workflow-templates` | org_admin | 201 (with ordered steps) | 409 TEMPLATE_NAME_TAKEN, 422 INVALID_APPROVER / NO_STEPS |
| GET | `/workflow-templates` | any member | 200 list | 403 |
| GET | `/workflow-templates/{id}` | any member | 200 | 404 |
| PATCH | `/workflow-templates/{id}` | org_admin | 200 | 409 TEMPLATE_NAME_TAKEN / TEMPLATE_IN_USE, 422 |
| POST | `/workflow-templates/{id}/deactivate` | org_admin | 200 | 404 |

### Approval requests (tag `approvals`)
| Method | Path | Who | Success | Errors |
| --- | --- | --- | --- | --- |
| POST | `/approval-requests` | any member | 201 (starts step 1, pending) | 409 TEMPLATE_INACTIVE, 422 |
| GET | `/approval-requests/mine` | requester | 200 list | 403 |
| GET | `/approval-requests/pending-for-me` | approver | 200 list | 403 |
| GET | `/approval-requests/{id}` | requester/approver/org_admin | 200 detail (steps + decisions + can_decide) | 404 |
| POST | `/approval-requests/{id}/decision` | current approver | 200 | 403 NOT_AUTHORIZED_APPROVER, 409 REQUEST_NOT_PENDING |
| POST | `/approval-requests/{id}/cancel` | requester (pending only) | 200 | 404, 409 |

### Notifications (tag `notifications`) + admin
| Method | Path | Who | Success | Notes |
| --- | --- | --- | --- | --- |
| GET | `/notifications` | any member | 200 Page | caller's rows in active org; `unread_only`, pagination |
| GET | `/notifications/unread-count` | any member | 200 `{unread}` | bell badge |
| POST | `/notifications/{id}/read` | owner | 200 | someone else's row → 404 |
| POST | `/notifications/read-all` | any member | 200 `{unread}` | marks all caller's unread |
| POST | `/admin/run-due-scan` | org_admin | 200 counts | demo trigger; prod uses `python -m app.jobs.due_scan` |

### Audit (tag `audit` / `platform-admin`)
| Method | Path | Who | Success |
| --- | --- | --- | --- |
| GET | `/audit-logs` | org_admin | 200 Page (filters: actor_id, action, resource_type, date_from, date_to) |
| GET | `/platform/audit-logs` | platform admin | 200 Page (optional `org_id`) |

### Dashboard (tag `dashboard`)
| Method | Path | Who | Success |
| --- | --- | --- | --- |
| GET | `/dashboard/summary` | any member | 200 DashboardSummary (role-scoped; filters project_id, assignee_id, status, date_from, date_to) |
| GET | `/dashboard/export.csv` | org_admin, manager | 200 CSV (same scoping, row limit 5000) |

Summary shape: `projects {total, active, archived}`, `tasks_by_status {todo, in_progress, blocked, completed}`,
`my_tasks`, `overdue_tasks`, `approvals {pending_total, awaiting_my_action, my_submitted_pending}`.
`awaiting_my_action` reuses `workflow_service.count_pending_for_me` (same rule as the decide endpoint).

**Audit action names** (`app/services/audit_service.py`):
`org.created/suspended/activated`, `invitation.created/revoked/accepted`,
`member.role_changed/removed`, `project.created/updated/archived`,
`project.member_added/removed`, `task.created/updated/assigned/status_changed`,
`workflow.template_created/updated/deactivated`,
`request.submitted/step_approved/approved/rejected/cancelled`.

---

## 9. How to Run and Test

**Backend (local, SQLite — zero setup):**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Python 3.12
pip install -r requirements.txt
cp ../.env.example .env                              # defaults to SQLite
alembic upgrade head
uvicorn app.main:app --reload                        # http://localhost:8000/docs
```

**PostgreSQL path (Docker):**
```bash
cp .env.example .env
docker compose up --build            # db + backend (+ frontend)
```

**Embedded PostgreSQL (no Docker, no sudo):**
```bash
python scripts/dev_db.py             # prints a DATABASE_URL you can export
```

**Tests:**
```bash
cd backend && pytest -q            # all suites (SQLite test DB, per-test rollback)
pytest --cov=app --cov-report=term-missing
```

Test files: `test_security_utils.py`, `test_tenant_helpers.py`, `test_auth_org.py`,
`test_projects_tasks.py`, `test_workflow_engine.py`, `test_workflow.py`,
`test_notifications.py`, `test_audit.py`, `test_dashboard.py`, `test_security.py`.
Fixtures in `tests/conftest.py`, factories in `tests/factories.py`.

**Mandatory scenarios coverage** (from the assignment):

| # | Scenario | Test |
| --- | --- | --- |
| 1 | unauthenticated → 401 on every protected route | `test_security.py::test_scenario1_unauthenticated_is_401` (parametrized) |
| 2 | Org A requests Org B resource by id → 404, nothing leaks | `test_security.py::test_scenario2_*` |
| 3 | employee calls admin action → 403, no row changed | `test_security.py::test_scenario3_employee_admin_actions_are_403_and_no_change` |
| 4 | non-approver tries to approve → 403, state unchanged | `test_workflow.py::test_two_step_approval_success_and_history` |
| 5 | final request cannot be decided again → 409 | `test_workflow.py::test_two_step_approval_success_and_history` |
| 6 | assign non-member → 422, assignee unchanged | `test_projects_tasks.py::test_task_create_assign_and_validate_assignee` |
| 7 | approval history recorded correctly | `test_workflow.py::test_two_step_approval_success_and_history` |
| 8 | failed op leaves no partial records | `test_workflow.py::test_rollback_leaves_no_partial_records` |
| 9 | notifications only to intended recipients | `test_notifications.py::test_assignment_notifies_assignee_not_actor` |
| 10 | audit records actor/org/action/resource | `test_audit.py::test_audit_records_actor_org_action_resource` |
| extra | suspended org, last-admin, duplicate invite, audit append-only | `test_auth_org.py`, `test_audit.py` |

**Frontend:**
```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
npm test
```

---

## 10. Decisions Log

| # | Decision | Alternatives | Reason |
| --- | --- | --- | --- |
| 1 | Shared DB, shared schema, `org_id` on every tenant table | schema-per-tenant, db-per-tenant | Simplest, cheapest, easiest to prove isolation with tests; RLS can be layered later (see README). |
| 2 | 404 for cross-tenant IDs | 403 | 403 leaks existence; 404 makes IDs unprobeable. |
| 3 | DB trigger for append-only audit | app-level only | Safety net even against application bugs. |
| 4 | `SELECT ... FOR UPDATE` + `version` on decide | version only | Prevents concurrent double decisions; lock is simplest correct approach. |
| 5 | Portable types (SQLite dev, Postgres prod) | Postgres-only | Zero-setup local dev while keeping the real Postgres path for Docker/prod. Enums are CHECK-constrained strings (allowed by spec). |
| 6 | `org_id` never read from request body | trust token claim | Token claims are re-verified against the DB membership each request. |
| 7 | Four migrations, one per schema group | one big initial migration | Matches the playbook's 4.2.1–4.2.4 steps; easier to review; still fully reversible. |
| 8 | Normalise email to lowercase on write + plain partial unique index | functional `lower(email)` index | Equivalent result, portable to SQLite (functional indexes are fiddly there). |
| 9 | Composite `(org_id, id)` unique keys + composite FKs | app-level checks only | Lets the *database* refuse cross-org rows, not just the service layer. |
| 10 | `CORS_ORIGINS` parsed with pydantic-settings `NoDecode` + a comma-split validator | JSON list in env | pydantic-settings tries to JSON-decode list fields and crashes on `a,b`; `NoDecode` + split is friendlier for `.env`/compose. |

---

## 11. Known Limitations and Future Improvements

See the full table in `README.md`. Summary:

1. No refresh tokens (re-login on expiry). 2. Token in `sessionStorage` (XSS risk).
3. Mocked email. 4. Polling instead of websockets for notifications.
5. Sequential workflows only (no branching/parallel steps). 6. No file attachments.
7. In-process due-date scanning (needs a scheduler in prod). 8. Row-level isolation only
(add PostgreSQL RLS for defence-in-depth). 9. SQLite is the local-dev default (Docker uses
PostgreSQL). 10. No login rate limiting. 11. Enums are CHECK-constrained strings.
12. Some list endpoints are unpaginated. 13. English-only UI.

None of these affect the graded requirements (authorization, tenant isolation, business
logic, integrity, tests), which are implemented and covered by the test suite.

---

## 12. Change Log

- **L0** — repo initialised, folder layout created, `.gitignore`, `.env.example`, `AGENT.md` skeleton.
- **DevOps 6.1/6.2 (skeleton)** — `docker-compose.yml` (db+backend+frontend+mailhog), `backend/Dockerfile` + `entrypoint.sh` (waits for DB, runs migrations, starts uvicorn), `frontend/Dockerfile` + `nginx.conf` (SPA fallback), `Makefile`, `scripts/dev_db.py` (embedded PostgreSQL for no-Docker/no-sudo environments).
- **4.1** — backend scaffold: `app/core/config.py` (pydantic-settings), `app/core/database.py` (engine/SessionLocal/Base/`get_db`), `app/core/errors.py` (typed errors + standard JSON), `app/main.py` (CORS, error handlers, `/health`, `/api/v1`). Verified `/docs` and `/health`.
- **4.2** — database schema: 14 tables across 4 groups, composite same-org FKs, indexes, partial unique invitation index, append-only audit trigger; 4 Alembic migrations, verified reversible on SQLite and PostgreSQL 16; ER diagram in `docs/er-diagram.md`.
- **4.3.1** — `app/core/security.py`: Argon2 password hashing, HS256 JWT create/decode with typed errors, invite-token generate/hash. 8 unit tests.
- **4.4** — security core: `app/api/deps.py` (`get_current_user`, `get_org_context`, `require_roles`, `require_platform_admin`, `OrgContext`), `app/services/tenant.py` (`get_in_org`, `list_query`, `assert_same_org`), `app/core/permissions.py` (matrix). 5 tenant-helper unit tests (two orgs).
- **4.3.2–4.3.5** — auth & organization management: register/login/me, create org, workspace switching, invitations (invite/list/revoke/accept), members (list/role/remove with last-admin rule), platform admin (list/status/stats). Added `TZDateTime` portable type (UTC-aware on SQLite+PG). Test infra (`tests/conftest.py` transaction-per-test + `tests/factories.py`); `tests/test_auth_org.py` (8 tests). Full suite 21 passing.
- **4.5** — projects & tasks: project CRUD/archive/members with role visibility; task create/assign/update with assignee validation (`ASSIGNEE_NOT_IN_ORG`); status changes with transition rules, history rows, notifications and audit; task list with filters/search/sort/pagination. Fixed SQLite transaction handling (explicit BEGIN) so per-test rollback works. `tests/test_projects_tasks.py` (6 tests). Full suite 27 passing.
- **4.6** — workflow & approvals: org_admin templates with ordered/validated steps (no step edits once used — deactivate instead); pure `workflow_engine` state machine; submit/list/detail/cancel; decide under `SELECT ... FOR UPDATE` + version bump with per-step authorization, decision history, notifications and audit. `tests/test_workflow_engine.py` (7) + `tests/test_workflow.py` (7). Full suite 42 passing.
- **4.7** — notifications: list/unread-count/read/read-all (tenant + owner scoped), due/overdue scan (`app/jobs/due_scan.py`) with per-task-per-day de-duplication, org_admin `POST /admin/run-due-scan`. `tests/test_notifications.py` (6). Full suite 48 passing.
- **4.8** — audit trail: `record()` called from every service (all action names listed in AGENT.md §8), read endpoints `GET /audit-logs` (org_admin) and `GET /platform/audit-logs` (platform admin), append-only verified at DB level. `tests/test_audit.py` (5). Full suite 53 passing.
- **4.9** — dashboard & reporting: role-scoped SQL-aggregate summary (projects, tasks by status, my/overdue tasks, approvals) with filters, and a tenant-scoped CSV export. `tests/test_dashboard.py` (4). Full suite 57 passing.
- **4.10** — backend test suite complete: added `tests/test_security.py` (48 parametrized 401 checks + cross-tenant read/write/list/search + employee-403). Backend suite **108 tests, 88% coverage**, all mandatory scenarios mapped (see §9).
- **Backend verified on PostgreSQL 16** (embedded `pgserver`, no Docker): migrations, composite same-org FKs, PL/pgSQL audit trigger and a full end-to-end flow (register → org → project → task → workflow → dashboard → audit, self-approval blocked, audit append-only) all pass. See `scripts/pg_smoke.py`.
- **5.1–5.6** — frontend: Vite + React + TS (strict) + Tailwind + React Router + TanStack Query + RHF/Zod; single typed API client (Bearer token, `ApiError`, 401 logout); `AuthProvider` (token in sessionStorage, workspace switching clears the query cache); query hooks with `org_id` in every key; UI primitives; role-based layout (sidebar, workspace switcher, notification bell polling every 30s, suspended-workspace page); all feature pages (auth, dashboard, projects, tasks, workflows, requests, notifications, members, audit, platform admin). Typecheck + production build pass; **16 Vitest/RTL tests pass**.

---

## 13. Frontend

**Folder map** (`/frontend/src`): `api/` (single `client.ts` + typed endpoint modules),
`types/` (mirror of backend Pydantic schemas), `lib/auth.tsx` (AuthProvider/useAuth),
`hooks/` (TanStack Query hooks per feature), `components/ui` (primitives),
`components/layout` (Layout, Sidebar, Topbar, WorkspaceSwitcher, NotificationBell),
`components/` (FormField, ProtectedRoute, RoleGate, ConfirmDialog, FilterBar),
`pages/` (one file per route), `test/` (render utils).

**Data flow:** page → query hook → `api/*` → `client.ts` (adds Bearer token) → backend.
Mutations invalidate the right query keys. On a 401 the client calls the auth provider's
logout. After switching workspace the whole query cache is cleared.

**State strategy:**
- Server state: TanStack Query only. Every key includes `activeOrgId` so caches never
  mix workspaces.
- Auth/session state: React context (`AuthProvider`), token in memory + `sessionStorage`
  for reload persistence (documented trade-off in §11).
- Form state: React Hook Form + Zod; the backend stays the authority and its validation
  messages are shown next to the field / as an `ErrorBanner`.

**Role handling:** `RoleGate` hides UI by role for usability only; the backend enforces
authorization. `ProtectedRoute` redirects to `/login` (no session) or `/workspaces`
(no active workspace). A suspended workspace shows a full-page message.

**Errors:** `ApiError(status, code, message)` is rendered via `ErrorBanner`; 409/403/422
from the backend are surfaced (e.g. "already decided" refreshes the list).

- **7.1–7.5** — deliverables: idempotent seed (`app/seed.py`, 2 orgs + shared user + data, real services so audit/notifications are realistic); `README.md`; `docs/architecture.md` (request flow + workflow state machine Mermaid, decisions, stronger-isolation options); `docs/api.md` + `docs/openapi.json` (43 paths / 51 ops); `docs/requirements-checklist.md`; known limitations in README + AGENT.md.
- **Final review (8.5)** — strict pass: every tenant query confirmed org-scoped; no hardcoded secrets; ruff cleanliness fixes (unused imports, deprecated import, collapsed nested if); Docker `.dockerignore` added; re-verified backend (108 tests), frontend (tsc + 16 tests) and the PostgreSQL smoke test.
- **Docker verified end-to-end** — `docker compose up --build` runs db + backend + frontend + mailhog; backend waits for the DB, runs migrations on PostgreSQL 16, serves `/docs`; frontend serves the SPA on :3000 with the API URL baked in; seed runs in the container; live API round-trip (login → switch → projects/tasks/dashboard/audit → submit+approve a request) and cross-tenant 404s all confirmed.
  - Fixed: `CORS_ORIGINS` comma value crashed pydantic-settings (added `NoDecode` + split validator) — this had stopped the backend container.
  - Fixed: demo emails used the reserved `.test` TLD which `email-validator` rejects on login/register; changed to `@demo.example.com` (seed, README).
