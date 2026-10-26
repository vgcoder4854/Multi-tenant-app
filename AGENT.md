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
| `app/services/notification_service.py` | In-app notifications | `notify()` |
| `app/services/workflow_engine.py` | Pure state machine | `can_decide`, `next_state` |

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

*(Exact transition rules and matrix tables added in later steps.)*

---

## 7. Database Notes

**Groups:** A) identity/tenancy (`users`, `organizations`, `memberships`, `invitations`);
B) work (`projects`, `project_members`, `tasks`, `task_status_history`);
C) workflow (`workflow_templates`, `workflow_steps`, `approval_requests`, `approval_decisions`);
D) comms/compliance (`notifications`, `audit_logs`).

*(Full ER description, index list and constraint reasons added in step 4.2.)*

---

## 8. API Reference Summary

*(Full table in `docs/api.md`; built in steps 4.3–4.9.)*

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
cd backend && pytest -q            # all suites
pytest --cov=app --cov-report=term-missing
```

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

---

## 11. Known Limitations and Future Improvements

*(Filled in step 7.5.)*

---

## 12. Change Log

- **L0** — repo initialised, folder layout created, `.gitignore`, `.env.example`, `AGENT.md` skeleton.
