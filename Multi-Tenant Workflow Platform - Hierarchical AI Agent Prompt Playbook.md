# Multi-Tenant Workflow Platform: Hierarchical AI Agent Prompt Playbook

*A step-by-step prompt system to build the whole assessment project from scratch with an AI coding agent (Claude Code, Cursor, Copilot Agent, etc.).*

## 1. How This Playbook Works

The project is split into levels. Every level has a **Main Prompt** (gives the agent context and a plan) and **Implementing Prompts** (make the agent write code).

| Level | Meaning | Example |
| --- | --- | --- |
| L0 | Master prompt: whole project and workflow, creates AGENT.md | Section 3 |
| L1 | Area prompt: Backend, Frontend, DevOps | Section 4, 6, 7 |
| L2 | Subtask prompt: one module or layer | Database Schema, Auth, Tasks |
| L3 | Implementing prompts: the exact small jobs | Create the `tasks` table, write the task service |

**Rhythm for every prompt (do not skip):**

1. Paste the prompt into the agent.
2. Read what it produced. Run it. Run the tests.
3. Commit to git (`git commit -m 'step 4.2.1 users and orgs tables'`).
4. Ask: *Update AGENT.md for what you just built.* (Every prompt below already includes this via the DOC-RULE.)
5. Move to the next prompt.

**Build order (follow it exactly):**

1. L0 Master prompt, then DevOps skeleton (Docker, Postgres up)
2. Backend: scaffold, Database, Auth, Tenancy/RBAC, Projects/Tasks, Workflow, Notifications, Audit, Dashboard, Backend tests
3. Frontend: scaffold, API layer, Auth/Workspace, Pages, Frontend tests
4. Seed data, docs, screenshots, README, final review

Backend first, because the assignment grades authorization, tenant isolation and business logic on the backend. The frontend is only a client of those rules.

## 2. The Tech Stack: What Each Tool Does and How It Fits

Read this once so you understand what the agent is building.

| Tool | What it is | How it is used here | How it connects |
| --- | --- | --- | --- |
| **FastAPI** | Python web framework | Defines REST endpoints (`@router.get('/tasks')`), auto-generates Swagger docs at `/docs` | Routes call services; uses `Depends()` to inject DB session and current user |
| **Pydantic** | Data validation | Schemas for request and response bodies (`TaskCreate`, `TaskOut`) | FastAPI validates input automatically and returns 422 on bad data |
| **SQLAlchemy 2.0** | ORM | Python classes for tables (`class Task(Base)`) and queries (`select(Task).where(...)`) | Services use a `Session` to read and write; the session is created per request |
| **Alembic** | Migration tool | Versioned schema changes (`alembic revision --autogenerate`, `alembic upgrade head`) | Reads SQLAlchemy models, produces migration files; run on container start |
| **PostgreSQL** | Database | One shared database and schema; every tenant row has `org_id` | Reached through the `DATABASE_URL` env variable |
| **JWT (PyJWT) + bcrypt/argon2** | Token auth and password hashing | Login returns a signed token; passwords stored as hashes | A `get_current_user` dependency decodes the token on every protected route |
| **Pytest + httpx TestClient** | Backend testing | Integration tests call the API and then inspect the DB | Uses a separate test database and fixtures for orgs and users |
| **Docker + Compose** | Containers | Runs `db`, `backend`, `frontend` with one command | Services talk on a Compose network; env from `.env` |
| **React + TypeScript (Vite)** | Frontend UI | Pages and reusable components with typed API responses | Calls the backend through one API client module |
| **Tailwind CSS** | Utility styling | Class-based styling, no custom CSS files needed | Configured in `tailwind.config` and imported in `index.css` |
| **React Router** | Client routing | `/login`, `/dashboard`, `/tasks`, protected routes | Route guard checks auth state and role |
| **TanStack Query** | Server-state fetching | Fetch, cache, paginate, refetch after mutations | Wraps the API client in hooks like `useTasks()` |
| **React Hook Form + Zod** | Forms and validation | Typed forms with client-side validation | Same rules as backend schemas, but backend stays the authority |
| **Vitest + React Testing Library** | Frontend tests | Test components, role-based UI, forms | Run with `npm test` |

(Next.js is an allowed alternative to Vite and React Router. This playbook uses Vite to keep things simple. If you prefer Next.js, tell the agent in the Master prompt.)

**Key design decision (tenancy and auth flow):**

- The user logs in and gets an **access token** (identity only).
- The user picks a workspace. The frontend calls `POST /auth/switch-organization` and receives a new token containing `org_id`.
- On every request the backend checks the token, then **re-checks in the database** that the user has an active membership in that organization and that the organization is active. It never trusts the token claim alone.
- Every query on tenant data filters by `org_id` from this verified context, never from the request body.

## 3. LEVEL 0: Master Prompt (Start Here)

Paste this first in a brand-new empty repository. It gives the agent the whole picture and makes it create AGENT.md.

```
You are a senior full-stack engineer and my pair-programmer. We will build a complete application from scratch, step by step. I will give you one task at a time. Do only the task I give; do not build ahead.

PROJECT: Multi-Tenant Workflow Management Platform (enterprise SaaS).
Multiple organizations use one app to manage projects, tasks, sequential approval workflows, notifications and audit history. Each organization is logically isolated: users from Org A must never see or change Org B data, even by guessing IDs.

STACK: React + TypeScript (Vite) + Tailwind; FastAPI (Python 3.12); PostgreSQL; SQLAlchemy 2.0 + Alembic; JWT auth with bcrypt/argon2 password hashing; Pytest; Vitest; Docker + Docker Compose.

ROLES:
- Platform Administrator: manage organizations (activate/suspend), see platform stats.
- Organization Administrator: manage workspace, users, roles, projects, workflow templates, approval steps, org reports.
- Manager: view authorized projects and members, create/assign tasks, approve/reject requests when authorized.
- Employee: view assigned projects/tasks, update task progress, submit approval requests, see own request history and notifications.

MODULES:
1 Auth and organization management (register, login, JWT, orgs, memberships, invitations, role assignment, workspace switching, suspend/activate)
2 Multi-tenant isolation (org_id on every tenant record, membership + permission check on every backend operation, no cross-org access, tenant-safe search/filter/export/dashboard)
3 Projects and tasks (CRUD, archive, members; priorities Low/Medium/High/Critical; statuses To Do/In Progress/Blocked/Completed; filter, search, paginate; status history)
4 Workflow and approvals (templates with ordered steps, responsible role or user per step, submit request, only the authorized approver decides the current step, no decisions on finished requests, full history)
5 Notifications (in-app: assignments, status changes, approval requests, decisions, due/overdue; list, read/unread, mark as read; email optional and mocked)
6 Audit trail (append-only: actor, organization, action, resource, timestamp)
7 Dashboard and reporting (computed from the database with SQL aggregates, tenant-scoped, with filters)

NON-NEGOTIABLE RULES:
- Authorization and tenant isolation are enforced on the BACKEND on every endpoint.
- Layered architecture: routers (HTTP only) -> services (business logic) -> models (DB). Pydantic schemas separate from ORM models.
- Use DB transactions for multi-record changes; foreign keys, unique constraints and indexes everywhere they make sense.
- Secrets only from environment variables. Synthetic data only.
- Meaningful error responses with correct HTTP status codes (401, 403, 404, 409, 422).
- Return 404 (not 403) when a resource exists in another organization, so IDs cannot be probed.
- Tests must verify persisted database state, not only status codes.

FOLDER LAYOUT (create now, empty placeholders are fine):
/backend (app/api, app/services, app/models, app/schemas, app/core, alembic, tests)
/frontend (src/api, src/components, src/pages, src/hooks, src/lib, src/types)
/docs, docker-compose.yml, .env.example, README.md, AGENT.md

FIRST TASK: create the folder layout and create AGENT.md following the AGENT.md SPECIFICATION below. Then stop and wait for my next task.

AGENT.md SPECIFICATION - this file is the living knowledge base of the project. Create it with these sections:
1. Project Overview (what, why, who uses it) - 10 lines max
2. Architecture and Folder Map - what each folder is for
3. Concepts - each key concept in 2-3 simple sentences (multi-tenancy, RBAC, JWT, workflow state machine, audit trail, etc.)
4. Modules and Libraries Used - each library, why it was chosen, where it is used
5. Code Reference - for every important module/function/class: purpose, parameters, return value, and a 1-3 line plain-English explanation of how it works
6. Business Logic and Rules - what each rule is, why it exists, and how the code enforces it
7. Database Notes - tables, relationships, constraints, indexes and why
8. API Reference Summary - method, path, role required, status codes
9. How to Run and Test
10. Decisions Log - decision, alternatives, reason
11. Known Limitations and Future Improvements
12. Change Log - one line per completed step

DOC-RULE (applies to EVERY task I give you from now on, even if I do not repeat it): after finishing a task, update the relevant AGENT.md sections. Keep explanations as short and simple as possible: plain English, no filler, explain WHY and HOW, and show tiny code samples only when they clarify. Add a Change Log line. Then give me a 5-line summary: what you built, files touched, how to run it, how to test it, what is next.
```

**What you should see:** the folder tree plus a populated AGENT.md skeleton. Commit it. From now on, if the agent forgets context, say: *Re-read AGENT.md and continue.*

## 4. LEVEL 1: Backend

### 4.0 Backend Main Prompt

```
Read AGENT.md. We are starting the BACKEND. Context: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL. The backend is the security boundary of the whole product: it must authenticate every request, resolve the active organization, verify membership and role, and scope every query by org_id.

Backend will be built in this order, one subtask at a time (I will prompt each):
4.1 Project scaffold and configuration
4.2 Database schema and migrations
4.3 Authentication and organization management
4.4 Tenancy and RBAC (permission layer)
4.5 Projects and tasks
4.6 Workflow and approvals
4.7 Notifications
4.8 Audit trail
4.9 Dashboard and reporting
4.10 Backend automated tests

Conventions to follow everywhere:
- Routers only parse HTTP and call services. Services hold business logic and receive the db session, the acting user and org_id explicitly. Never read org_id from a request body.
- Every tenant query goes through helper functions that always add org_id filtering.
- Standard error JSON: {"detail": "message", "code": "MACHINE_CODE"}.
- Pagination: query params page and page_size, response {items, total, page, page_size}.
- UUID primary keys, timezone-aware UTC timestamps (created_at, updated_at).

Acknowledge, add the conventions to AGENT.md (Decisions Log and Architecture), and wait for 4.1.
```

### 4.1 Subtask: Project Scaffold and Configuration

**Main prompt**

```
Subtask 4.1: backend scaffold. Goal: a running FastAPI app connected to PostgreSQL with clean configuration, ready for features. Nothing else yet. Explain in AGENT.md how config, DB sessions and dependency injection work.
```

**Implementing prompts**

*4.1.1 Dependencies and config*

```
Create backend/pyproject.toml or requirements.txt with: fastapi, uvicorn[standard], sqlalchemy>=2, psycopg[binary], alembic, pydantic-settings, pyjwt, passlib[bcrypt] (or argon2-cffi), email-validator, pytest, httpx, pytest-cov. Create app/core/config.py using pydantic-settings Settings (DATABASE_URL, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ENVIRONMENT) read from env. Create .env.example with placeholder values only. Document each setting in AGENT.md.
```

*4.1.2 Database session*

```
Create app/core/database.py with the SQLAlchemy engine, SessionLocal, a DeclarativeBase called Base, and a get_db() FastAPI dependency that yields a session and always closes it. Document in AGENT.md how a request gets its session and when commits/rollbacks happen.
```

*4.1.3 App entry*

```
Create app/main.py: FastAPI app with title, version, CORS configured from env (allow the frontend origin), a /health endpoint that also checks DB connectivity, a global exception handler that returns the standard error JSON, and an api_router mounted at /api/v1. Run it and show me /docs working.
```

### 4.2 Subtask: Database Schema and Migrations

**Main prompt (explains the whole schema)**

```
Subtask 4.2: database design. Read this overall schema carefully before writing any code.

MODEL: shared PostgreSQL database, shared schema, row-level tenancy. Every tenant-owned table has org_id (NOT NULL, FK to organizations, indexed). Global tables: users and organizations.

TABLE GROUPS:
A) Identity and tenancy: users, organizations, memberships, invitations
B) Work management: projects, project_members, tasks, task_status_history
C) Workflow: workflow_templates, workflow_steps, approval_requests, approval_decisions
D) Communication and compliance: notifications, audit_logs

RELATIONSHIP SUMMARY:
- users <-> organizations is many-to-many through memberships (a user can belong to several orgs with a different role in each)
- organization 1-N projects, tasks, templates, requests, notifications, audit_logs
- project 1-N tasks; project N-N users through project_members
- workflow_template 1-N workflow_steps (ordered by step_order)
- approval_request N-1 template; 1-N approval_decisions (one per step decided)

INTEGRITY GOALS:
- Foreign keys everywhere; unique constraints to stop duplicate memberships/invitations/step orders
- Enums as PostgreSQL enums or CHECK-constrained strings for roles, priorities, statuses
- Tenant consistency: a task's project, a project member's user, a request's template must all belong to the SAME org. Enforce in service code AND, where practical, with composite unique keys (org_id, id) and composite foreign keys.
- Indexes for the common queries: tasks by (org_id, status), (org_id, assignee_id), (org_id, project_id), (org_id, due_date); notifications by (user_id, is_read, created_at); audit_logs by (org_id, created_at); approval_requests by (org_id, status)
- audit_logs is append-only (we will enforce with a DB trigger)

We will build the schema in sub-steps 4.2.1 to 4.2.5, each with its own Alembic migration. Add an ER-style description of this overall schema to AGENT.md section 7 and a Mermaid ER diagram to docs/er-diagram.md. Then wait.
```

**Implementing prompts**

*4.2.1 Identity and tenancy tables*

```
Create SQLAlchemy 2.0 models (typed Mapped[] style, one file per group in app/models) for:
- users: id UUID pk, email (unique, stored lowercase), full_name, password_hash, is_platform_admin bool default false, is_active bool default true, created_at
- organizations: id, name, slug (unique), status enum(active, suspended) default active, created_at
- memberships: id, org_id FK, user_id FK, role enum(org_admin, manager, employee), status enum(active, removed), created_at; UNIQUE(org_id, user_id)
- invitations: id, org_id FK, email, role enum, token_hash, status enum(pending, accepted, revoked, expired), invited_by FK users, expires_at, created_at; partial unique index on (org_id, lower(email)) WHERE status='pending'
Store only a hash of invitation tokens. Generate the Alembic migration, apply it, and verify tables with psql. Document each table and constraint (and why) in AGENT.md.
```

*4.2.2 Projects and tasks tables*

```
Create models: projects (id, org_id, name, description, status enum active/archived, created_by, created_at, updated_at; UNIQUE(org_id, name)); project_members (id, org_id, project_id, user_id; UNIQUE(project_id, user_id)); tasks (id, org_id, project_id, title, description, priority enum low/medium/high/critical, status enum todo/in_progress/blocked/completed, assignee_id nullable FK users, created_by, due_date nullable, created_at, updated_at); task_status_history (id, org_id, task_id, from_status nullable, to_status, changed_by, changed_at). Add all the indexes listed in the 4.2 main prompt. Generate and apply the migration. Document in AGENT.md.
```

*4.2.3 Workflow tables*

```
Create models: workflow_templates (id, org_id, name, description, is_active, created_by, created_at; UNIQUE(org_id, name)); workflow_steps (id, org_id, template_id FK cascade, step_order int >= 1, name, approver_type enum(role, user), approver_role nullable enum(org_admin, manager), approver_user_id nullable FK users; UNIQUE(template_id, step_order); CHECK that exactly the right approver column is filled for the approver_type); approval_requests (id, org_id, template_id, requester_id, title, details JSONB, status enum(pending, approved, rejected, cancelled), current_step_order int, submitted_at, completed_at nullable, version int default 1 for optimistic locking); approval_decisions (id, org_id, request_id, step_id, step_order, decided_by, decision enum(approved, rejected), comment, decided_at; UNIQUE(request_id, step_order)). Generate and apply the migration. Document the state machine (pending -> approved | rejected | cancelled; no transitions out of a final state) in AGENT.md.
```

*4.2.4 Notifications and audit tables*

```
Create models: notifications (id, org_id, user_id, type enum, title, body, resource_type, resource_id, is_read default false, created_at, read_at nullable) and audit_logs (id, org_id nullable for platform-level actions, actor_id nullable FK users, action string, resource_type, resource_id, metadata JSONB, created_at). In the same migration add a PostgreSQL trigger function that RAISES EXCEPTION on UPDATE or DELETE of audit_logs, so history cannot be altered even by application bugs. Apply it and prove it works by trying an UPDATE in psql. Document in AGENT.md.
```

*4.2.5 Verification*

```
Run alembic upgrade head on an empty database, then alembic downgrade base and upgrade head again to prove migrations are reversible. Generate the Mermaid ER diagram in docs/er-diagram.md from the real models. List every index and constraint in AGENT.md section 7 with a one-line reason each.
```

### 4.3 Subtask: Authentication and Organization Management

**Main prompt**

```
Subtask 4.3: authentication and organization management (Module 1). Concepts to implement: (1) users register and log in with email + password; passwords are stored only as bcrypt/argon2 hashes; (2) login returns a short-lived JWT access token with claims sub (user id), exp, and optionally org_id; (3) a user can create an organization and becomes its org_admin; (4) org admins invite people by email with a role; invitations are single-use, expiring and unique per pending email; (5) a user in several organizations switches workspace by requesting a new token scoped to one org; (6) platform admins can list organizations and activate/suspend them; a suspended organization blocks all its tenant endpoints.
Files: app/core/security.py, app/schemas/auth.py, app/schemas/org.py, app/services/auth_service.py, app/services/org_service.py, app/api/auth.py, app/api/organizations.py. Build in the order of 4.3.1 to 4.3.5. Explain JWT, password hashing and the invitation flow in AGENT.md Concepts.
```

**Implementing prompts**

*4.3.1 Security utilities*

```
In app/core/security.py implement: hash_password(plain)->str, verify_password(plain, hashed)->bool, create_access_token(user_id, org_id=None)->str (HS256, SECRET_KEY from settings, exp from settings), decode_token(token)->dict raising a clear error on expired/invalid tokens, and generate_invite_token()->(raw, hash) using secrets.token_urlsafe and SHA-256. Add unit tests for each. Document parameters and returns in AGENT.md Code Reference.
```

*4.3.2 Register, login, me*

```
Implement POST /api/v1/auth/register (email, password min 8, full_name -> 201, 409 if the email exists), POST /api/v1/auth/login (-> {access_token, token_type}; same 401 message for wrong email or wrong password; reject inactive users), GET /api/v1/auth/me (current user plus list of active memberships with org name and role). Emails are normalized to lowercase. Never return password_hash. Add Pydantic schemas with validation.
```

*4.3.3 Organizations and switching*

```
Implement in one DB transaction: POST /api/v1/organizations (creates organization + admin membership for the creator + an audit entry -> 201). GET /api/v1/organizations/mine (the user's orgs). POST /api/v1/auth/switch-organization {org_id}: verify an active membership and an active organization, then return a new token containing org_id; otherwise 403. Rollback everything if any step fails.
```

*4.3.4 Invitations and members*

```
Implement (org_admin only): POST /api/v1/org/invitations {email, role} -> creates a pending invitation (409 if a pending one exists or the user is already a member), returns the raw token once (in development also log it through a mocked email service in app/services/email_service.py). GET /api/v1/org/invitations, DELETE /api/v1/org/invitations/{id} (revoke). POST /api/v1/invitations/accept {token} (authenticated user; validates hash, expiry, status; creates membership in one transaction; marks the invitation accepted). GET /api/v1/org/members, PATCH /api/v1/org/members/{user_id}/role, DELETE /api/v1/org/members/{user_id}. Rule: an organization must always keep at least one active org_admin (block demoting or removing the last one with 409).
```

*4.3.5 Platform admin*

```
Implement platform-admin-only endpoints (is_platform_admin required, no org context needed): GET /api/v1/platform/organizations (paginated, filter by status and name), PATCH /api/v1/platform/organizations/{id}/status {status: active|suspended}, GET /api/v1/platform/stats (counts of orgs, users, projects, tasks computed with SQL COUNT). Write an audit entry for each status change. Document in AGENT.md what suspension blocks and where that check lives.
```

### 4.4 Subtask: Tenancy and RBAC (Permission Layer)

**Main prompt**

```
Subtask 4.4: the security core (Module 2). Build ONE reusable permission layer that every later endpoint uses, so tenant isolation cannot be forgotten. Design:
- get_current_user: decodes the JWT, loads the user, rejects inactive users (401).
- get_org_context: reads org_id from the verified token, loads the active membership and the organization from the DB, rejects suspended organizations (403 ORG_SUSPENDED) and missing membership (403). Returns an OrgContext(user, org_id, role).
- require_roles(*roles): dependency factory that checks ctx.role against the allowed roles (403 otherwise).
- require_platform_admin dependency.
- Tenant-safe repository helpers: get_in_org(db, Model, id, org_id) returns the row only if it belongs to org_id, else raises 404 (never 403) so IDs cannot be probed.
Explain in AGENT.md, in plain words, why we re-check membership in the DB instead of trusting the token, and show a 5-line example of a protected route.
```

**Implementing prompts**

*4.4.1 Dependencies*

```
Create app/api/deps.py with get_current_user, get_org_context, require_roles, require_platform_admin and the OrgContext dataclass. Use OAuth2PasswordBearer or HTTPBearer so Swagger shows the Authorize button. Missing/invalid token -> 401 with WWW-Authenticate header.
```

*4.4.2 Tenant-safe helpers*

```
Create app/services/tenant.py with get_in_org(), list_query(Model, org_id) that returns a select() already filtered by org_id, and assert_same_org(org_id, *objects) that raises if any related object (project, assignee, template) belongs to another organization. Unit test them with two organizations.
```

*4.4.3 Permission matrix*

```
Create app/core/permissions.py containing a single dict PERMISSIONS mapping action names (project.create, task.assign, workflow.manage, request.submit, request.decide, audit.view, report.view, member.manage) to the allowed roles. Routers call require_roles using these constants instead of hard-coded role strings. Write the matrix as a table in AGENT.md.
```

### 4.5 Subtask: Projects and Tasks

**Main prompt**

```
Subtask 4.5: projects and tasks (Module 3). Permission rules: org_admin creates, updates and archives projects and manages project members; managers can create and assign tasks in projects they belong to; employees see only projects they are members of and tasks assigned to them or in their projects, and may update status/progress only on tasks assigned to them. Archived projects are read-only. A task assignee must be an active member of the same organization (and, preferably, of the project). Every status change writes a task_status_history row, creates notifications and an audit entry inside the same transaction. Files: schemas/project.py, schemas/task.py, services/project_service.py, services/task_service.py, api/projects.py, api/tasks.py. Build in order 4.5.1 to 4.5.4.
```

**Implementing prompts**

*4.5.1 Project service and endpoints*

```
Implement POST/GET(list, detail)/PATCH /api/v1/projects, POST /api/v1/projects/{id}/archive, and POST/DELETE/GET /api/v1/projects/{id}/members. Visibility: org_admin sees all org projects; manager and employee only projects where they are members. 409 on a duplicate project name in the org. Audit every change.
```

*4.5.2 Task create and assign*

```
Implement POST /api/v1/tasks and PATCH /api/v1/tasks/{id}. Validate: project belongs to the org and is active; assignee is an active member of the org (else 422 ASSIGNEE_NOT_IN_ORG); due_date is a valid date; priority and status come from the enums. On assignment or reassignment create a notification for the new assignee and an audit entry. Do it in one transaction.
```

*4.5.3 Task status and history*

```
Implement PATCH /api/v1/tasks/{id}/status {status}. Allowed actors: assignee, managers, org_admin. Write a task_status_history row (from, to, changed_by) and notify the creator and assignee when relevant. GET /api/v1/tasks/{id} returns details plus history. Add the allowed-transition rules to AGENT.md (decide and document whether Completed can reopen).
```

*4.5.4 List, search, filter, paginate*

```
Implement GET /api/v1/tasks with filters project_id, status, priority, assignee_id, due_from, due_to, search (ILIKE on title and description), sort_by, sort_dir, page, page_size (max 100). The query always starts from the org-scoped helper and applies role visibility. Use COUNT for total and LIMIT/OFFSET for the page; never load all rows. Verify indexes are used with EXPLAIN and note it in AGENT.md.
```

### 4.6 Subtask: Workflow and Approvals

**Main prompt**

```
Subtask 4.6: workflow templates and approval requests (Module 4). Concepts: a template is an ordered list of steps (1..N). Each step names the approver as a ROLE (e.g. manager) or a specific USER. An employee submits a request from a template; the request starts at step 1 with status pending. Only a user who matches the current step's approver may decide it, and never the requester themselves. Approve -> move to the next step, or finish as approved after the last step. Reject -> request finishes as rejected immediately. Final requests (approved, rejected, cancelled) can never be decided again. Every decision is recorded (who, when, comment, step) and the requester is notified. All state changes are atomic and use optimistic locking (version) or SELECT ... FOR UPDATE to stop two approvers deciding at once. Build the pure state-machine logic first and test it alone, then the endpoints. Order: 4.6.1 to 4.6.4.
```

**Implementing prompts**

*4.6.1 Templates (org\_admin)*

```
Implement POST/GET/PATCH /api/v1/workflow-templates and deactivation. A template and its steps are created in one transaction. Validate: at least 1 step, step_order contiguous from 1, each step has a valid approver (role or user who is an active org member with a role that can approve). Templates used by existing requests cannot have steps deleted: deactivate instead.
```

*4.6.2 State machine*

```
Create app/services/workflow_engine.py with pure functions: can_decide(request, step, user_ctx)->(bool, reason), next_state(request, steps, decision)->NewState. No DB calls inside, so they are easy to unit test. Rules: request.status must be pending; user matches step approver (role or user id); user is not the requester; decision in {approved, rejected}. Raise typed errors: RequestNotPending (409), NotAuthorizedApprover (403).
```

*4.6.3 Submit request*

```
Implement POST /api/v1/approval-requests {template_id, title, details}. Template must be active and in the org. In one transaction: create the request (current_step_order=1, status pending), notify the approver(s) of step 1, write an audit entry. GET /api/v1/approval-requests/mine (requester history), GET /api/v1/approval-requests/{id} (detail with steps, current step, status, and full decision history; visible to requester, org_admin and eligible approvers only).
```

*4.6.4 Decide*

```
Implement POST /api/v1/approval-requests/{id}/decision {decision, comment}. In ONE transaction: lock the request row (with_for_update), re-check status and approver via the engine, insert approval_decisions, update current step or final status and completed_at, notify the requester (and next approver if it advances), write the audit entry. On any exception roll back so no partial records remain. Also implement GET /api/v1/approval-requests/pending-for-me (requests awaiting the current user's decision) and POST /api/v1/approval-requests/{id}/cancel (requester only, while pending).
```

### 4.7 Subtask: Notifications

**Main prompt**

```
Subtask 4.7: in-app notifications (Module 5). Concept: notifications are rows addressed to one user inside one organization. Other services never insert rows directly; they call notification_service.notify(...) INSIDE their transaction so a rolled-back business action never leaves a notification. Types: task_assigned, task_status_changed, approval_requested, approval_decided, task_due_soon, task_overdue. Email is optional: use a mocked EmailService that logs to console. Files: models/notification.py (done), services/notification_service.py, api/notifications.py, services/due_scan.py.
```

**Implementing prompts**

*4.7.1 Notify service and API*

```
Implement notify(db, org_id, user_ids, type, title, body, resource_type, resource_id) which skips the actor and duplicates. Endpoints: GET /api/v1/notifications (paginated, filter unread, only the caller's rows in the active org), GET /api/v1/notifications/unread-count, POST /api/v1/notifications/{id}/read, POST /api/v1/notifications/read-all. Marking someone else's notification returns 404.
```

*4.7.2 Due and overdue scan*

```
Implement due_scan.run(db): find tasks due within 24 hours or overdue and not completed, and create one notification per task per day (avoid duplicates with a check on type + resource_id + date). Expose it as a CLI command (python -m app.jobs.due_scan) and an org_admin-only POST /api/v1/admin/run-due-scan for demos. Explain in AGENT.md that production would run it with a scheduler (cron or Celery beat).
```

### 4.8 Subtask: Audit Trail

**Main prompt**

```
Subtask 4.8: audit trail (Module 6). Concept: an append-only log of important actions. One function audit_service.record(db, ctx, action, resource_type, resource_id, metadata) is called inside the same transaction as the action it describes. Actions to cover: org.created, invitation.created/revoked/accepted, member.role_changed/removed, project.created/updated/archived, task.created/updated/status_changed/assigned, workflow.template_created, request.submitted, request.approved/rejected/cancelled, org.suspended/activated. No update or delete endpoints exist, and the DB trigger from 4.2.4 blocks changes. Only org_admin can read the org's audit log.
```

**Implementing prompts**

*4.8.1 Record function*

```
Implement audit_service.record() capturing actor_id, org_id, action, resource_type, resource_id, and a metadata dict (store only safe fields, never passwords or tokens). Go through every service built so far and add the missing calls. Produce a table of action names in AGENT.md.
```

*4.8.2 Read endpoint*

```
Implement GET /api/v1/audit-logs (org_admin only) with filters actor_id, action, resource_type, date range and pagination, sorted newest first and always scoped to the active org. Platform admin gets GET /api/v1/platform/audit-logs for org-level actions.
```

### 4.9 Subtask: Dashboard and Reporting

**Main prompt**

```
Subtask 4.9: dashboard (Module 7). Concept: every number is computed in PostgreSQL with aggregate queries (COUNT, GROUP BY, FILTER), never by loading rows into Python. Everything is scoped to the active org and to what the caller's role may see (employees see their own numbers, managers their projects, org_admin the whole org). Optional filters: project_id, assignee_id, status, date_from, date_to. Metrics: total projects, active projects, tasks grouped by status, tasks assigned to me, overdue tasks (due_date < today and status != completed), pending approval requests, requests awaiting my action. Files: services/dashboard_service.py, schemas/dashboard.py, api/dashboard.py.
```

**Implementing prompts**

*4.9.1 Task and project metrics*

```
Implement GET /api/v1/dashboard/summary returning one consistent JSON object with projects {total, active, archived}, tasks_by_status {todo, in_progress, blocked, completed}, my_tasks, overdue_tasks. Use a single GROUP BY query for status counts. Apply the filters. Verify indexes with EXPLAIN.
```

*4.9.2 Approval metrics*

```
Add approvals {pending_total, awaiting_my_action, my_submitted_pending} to the summary using aggregate queries. awaiting_my_action must use the exact same eligibility rule as the decide endpoint (reuse the function from workflow_engine, do not copy the logic). Add GET /api/v1/dashboard/export.csv (org_admin and manager) streaming filtered tasks as CSV, with the same tenant scoping and a row limit.
```

### 4.10 Subtask: Backend Automated Tests

**Main prompt**

```
Subtask 4.10: automated tests. The assignment REQUIRES tests that verify authorization AND persisted database state, not only status codes. Setup: pytest + FastAPI TestClient/httpx against a separate PostgreSQL test database; each test runs in a transaction rolled back at the end, or the schema is recreated per session. Build reusable fixtures in tests/conftest.py: db session, client, factory helpers (create_user, create_org, add_member, login_as, create_project, create_task, create_template), and two ready tenants: org_a (admin_a, manager_a, employee_a) and org_b (admin_b, employee_b). Mandatory scenarios (each is its own test with a clear name):
1 unauthenticated user gets 401 on every protected endpoint (parametrize over all routes)
2 user of Org A requests Org B's task by ID -> 404 and nothing leaks
3 employee calls an admin-only action -> 403 and no row changed
4 a user who is not the authorized approver tries to approve -> 403, request state unchanged
5 approved or rejected request cannot be decided again -> 409, history length unchanged
6 assigning a task to a non-member of the org -> 422, task assignee unchanged
7 a submitted request records approval history correctly (decision row, decider, timestamp, comment, step)
8 a failed operation leaves no partial workflow records (force an exception mid-transaction and assert counts of requests, decisions, notifications, audit rows are all unchanged)
9 notifications are created for the intended recipients only (and not for the actor)
10 audit history records actor, org, action and resource
Extra: suspended org blocked, last org_admin cannot be removed, duplicate invitation 409, pagination and filters respect tenants, audit rows cannot be updated or deleted at the DB level.
```

**Implementing prompts**

*4.10.1 Fixtures*

```
Create tests/conftest.py and tests/factories.py as described. Provide a helper auth_headers(user, org) that logs in and switches workspace. Run an example test to prove the fixtures work. Document how to run tests (pytest -q, pytest --cov) in AGENT.md.
```

*4.10.2 Isolation and authorization tests*

```
Write tests/test_security.py covering scenarios 1, 2, 3 plus cross-tenant attempts for update, delete, list and search endpoints for projects, tasks, workflows, notifications and audit logs. After each forbidden call, query the database and assert the target row is unchanged.
```

*4.10.3 Workflow tests*

```
Write tests/test_workflow.py covering scenarios 4, 5, 7, 8: multi-step approval success path, reject path, wrong approver, requester approving own request, concurrent double decision (second must fail with 409), and a rollback test that monkeypatches the notification service to raise and asserts nothing was persisted.
```

*4.10.4 Tasks, notifications, audit tests*

```
Write tests/test_tasks.py (scenario 6, status history, filters, pagination), tests/test_notifications.py (scenario 9, read/unread, mark-as-read ownership) and tests/test_audit.py (scenario 10, append-only enforced by the trigger). Run the full suite, report coverage, and fix any real bugs the tests reveal in the services, not by weakening the tests.
```

## 5. LEVEL 1: Frontend

### 5.0 Frontend Main Prompt

```
Read AGENT.md. We now build the FRONTEND, a React + TypeScript (Vite) + Tailwind app that consumes the finished backend API at /api/v1. Important: the UI hides things by role for usability only; the backend remains the real security layer, and the UI must correctly show 401/403/404/409/422 errors returned by the API.
Screens: Login/Register, Workspace picker/switcher, Dashboard, Projects (list, detail, members), Tasks (filter, search, paginate, detail with history), Workflow templates (admin), Requests (submit, my history, pending for me, decide), Notifications, Members and invitations (admin), Audit log (admin), Platform admin (organizations).
Tools: React Router (routes + guards), TanStack Query (server state), React Hook Form + Zod (forms), Tailwind (styling), Vitest + React Testing Library (tests).
Principles: reusable components, typed API layer generated from backend schemas, no business logic copied from the backend, loading/empty/error states everywhere.
Order: 5.1 scaffold, 5.2 API layer and auth state, 5.3 shared components, 5.4 workspace and layout, 5.5 feature pages, 5.6 frontend tests. Add a Frontend section to AGENT.md (folder map, data flow, state strategy) and wait for 5.1.
```

### 5.1 Subtask: Frontend Scaffold

**Main prompt**

```
Subtask 5.1: scaffold the frontend with Vite + React + TypeScript (strict), Tailwind, React Router, TanStack Query, React Hook Form, Zod, Vitest. Explain in AGENT.md what each tool does and how they connect (router wraps pages, QueryClientProvider wraps the app, Tailwind scans src files).
```

**Implementing prompts**

*5.1.1 Project init*

```
In /frontend run the Vite React-TS template, install tailwindcss, react-router-dom, @tanstack/react-query, react-hook-form, zod, @hookform/resolvers, vitest, @testing-library/react, @testing-library/jest-dom, jsdom. Configure Tailwind, path alias @/, and VITE_API_URL in .env.example. Show the dev server running.
```

*5.1.2 App shell*

```
Create main.tsx with QueryClientProvider and BrowserRouter, App.tsx with a route table (public: /login, /register, /accept-invite; protected: all others, inside a Layout), and placeholder pages. Add a NotFound page.
```

### 5.2 Subtask: API Layer and Auth State

**Main prompt**

```
Subtask 5.2: the single gateway to the backend. Concept: one api client module adds the Authorization header, parses the standard error JSON into an ApiError(status, code, message), and logs the user out on 401. Auth state (token, user, memberships, active org and role) lives in an AuthContext. Server data uses TanStack Query hooks so components never call fetch directly.
```

**Implementing prompts**

*5.2.1 API client and types*

```
Create src/api/client.ts (fetch wrapper: base URL, JSON, bearer token, ApiError) and src/types/*.ts for User, Membership, Organization, Project, Task, WorkflowTemplate, ApprovalRequest, Notification, AuditLog, Page<T>. Mirror the backend Pydantic schemas exactly.
```

*5.2.2 Auth context*

```
Create src/lib/auth.tsx with AuthProvider and useAuth(): login, register, logout, switchOrganization, current user, active org, role, hasRole(...roles). Store the token in memory plus sessionStorage for reload persistence. Document the security trade-off of storing tokens in the browser in AGENT.md Known Limitations.
```

*5.2.3 Query hooks*

```
Create hooks per feature (useTasks(filters), useCreateTask, useProjects, useWorkflowTemplates, useApprovalRequests, useDecideRequest, useNotifications, useDashboard, ...). Include the active org id in every query key so the cache never mixes workspaces, and invalidate the right keys after each mutation. After switching workspace, clear the whole query cache.
```

### 5.3 Subtask: Shared Components

**Main prompt**

```
Subtask 5.3: a small reusable component library styled with Tailwind. These are used by every page, so keep them generic, typed and accessible.
```

**Implementing prompts**

*5.3.1 Primitives*

```
Create src/components/ui: Button (variants, loading), Input, Select, Textarea, Modal, Badge (status and priority colors), Card, Table, Pagination, Spinner, EmptyState, ErrorBanner, Toast. Each takes typed props and forwards refs where useful.
```

*5.3.2 Form and guard components*

```
Create FormField (label + error from React Hook Form), ProtectedRoute (redirects to /login when no token), RoleGate (renders children only for allowed roles), ConfirmDialog, FilterBar (project, status, priority, assignee, date range, search with debounce).
```

### 5.4 Subtask: Workspace and Layout

**Main prompt**

```
Subtask 5.4: layout and workspace switching. After login the user with several memberships chooses an organization (workspace picker). The layout shows a sidebar whose items depend on the role, a top bar with the workspace switcher, notification bell with unread count, and a user menu. A suspended-organization error (ORG_SUSPENDED) shows a clear full-page message.
```

**Implementing prompts**

*5.4.1 Workspace picker and switcher*

```
Create WorkspacePicker page and a WorkspaceSwitcher dropdown that calls switchOrganization and navigates to the dashboard. Handle users with zero organizations by offering Create Organization.
```

*5.4.2 Layout*

```
Create Layout with role-based Sidebar, Topbar, NotificationBell (polls unread-count every 30 seconds via TanStack Query refetchInterval) and responsive behavior.
```

### 5.5 Subtask: Feature Pages

**Main prompt**

```
Subtask 5.5: feature pages. Each page uses the query hooks, shared components, loading/empty/error states, and shows the backend's validation messages next to the right field. Build in this order, one prompt per page, testing in the browser with the seeded users from the backend: 5.5.1 Auth pages, 5.5.2 Dashboard, 5.5.3 Projects, 5.5.4 Tasks, 5.5.5 Workflows and requests, 5.5.6 Notifications, 5.5.7 Admin pages.
```

**Implementing prompts**

*5.5.1 Auth pages*

```
Build Login, Register and AcceptInvite pages with React Hook Form + Zod (email format, password min 8). Show server errors (401, 409). After login go to the workspace picker or dashboard.
```

*5.5.2 Dashboard*

```
Build Dashboard: stat cards (total/active projects, my tasks, overdue), tasks-by-status bar chart (simple CSS bars or a light chart library), pending approvals and awaiting-my-action lists, and a FilterBar for project, assignee, status and date range that re-queries /dashboard/summary.
```

*5.5.3 Projects*

```
Build Projects list (admin sees Create and Archive buttons through RoleGate), Project detail (tasks of the project and a members panel to add/remove members), and a Create/Edit project modal.
```

*5.5.4 Tasks*

```
Build Tasks page with FilterBar, server-side pagination, create/edit modal (assignee dropdown listing only org members), inline status change for the assignee, and Task detail drawer showing status history. Archived-project tasks are read-only.
```

*5.5.5 Workflows and requests*

```
Build: (a) Workflow Templates page for org_admin to create templates with an ordered, reorderable list of steps and approver (role or user); (b) New Request form choosing a template; (c) My Requests with a step progress indicator and status badge; (d) Pending For Me with Approve/Reject buttons and a required comment on reject; (e) Request detail with the full approval history timeline. Display 409 (already decided) clearly and refresh the data.
```

*5.5.6 Notifications*

```
Build the Notifications page: list with unread styling, filter unread, mark one as read, mark all as read, and clicking an item navigates to the related task or request.
```

*5.5.7 Admin pages*

```
Build Members (invite by email and role, revoke, change role, remove), Audit Log (filters, pagination, read-only table), and Platform Admin Organizations (search, suspend/activate with a confirm dialog) visible only to the right roles.
```

### 5.6 Subtask: Frontend Tests

**Main prompt**

```
Subtask 5.6: frontend tests with Vitest and React Testing Library. Mock the API layer, not the components. Focus on behavior: role-based rendering, form validation, error display, and the approval flow.
```

**Implementing prompts**

*5.6.1 Setup and utilities*

```
Configure Vitest with jsdom and a test util renderWithProviders(ui, {role, route}) that wraps Router, QueryClient and a fake AuthContext.
```

*5.6.2 Tests*

```
Write tests for: ProtectedRoute redirect, RoleGate hides admin buttons from employees, Login form validation and server error display, Task filter bar updates the query, Pending-for-me Approve button calls the decision API and shows the 409 message, Notification bell shows the unread count. Run npm test and fix failures.
```

## 6. LEVEL 1: DevOps and Docker

*Do 6.1 right after the Master prompt (before backend work) and 6.2 after the frontend is done.*

### 6.0 DevOps Main Prompt

```
Read AGENT.md. Goal: the whole system runs locally with ONE command: docker compose up --build. Services: db (postgres:16 with a named volume and healthcheck), backend (FastAPI, waits for db, runs alembic upgrade head on start), frontend (Vite dev server or nginx static build), optional mailhog for dev email. All configuration comes from .env (copied from .env.example). Explain in AGENT.md how containers, networks, volumes and env vars work together in this project.
```

### 6.1 Database and Backend Containers

```
Create docker-compose.yml with the db service (healthcheck pg_isready, POSTGRES_* from env, volume pgdata) and backend service (build ./backend, depends_on db with condition service_healthy, ports 8000:8000, env DATABASE_URL pointing to host db). Create backend/Dockerfile (python:3.12-slim, install requirements, non-root user, CMD runs migrations then uvicorn). Create backend/entrypoint.sh if needed. Prove it: docker compose up, then open http://localhost:8000/docs.
```

### 6.2 Frontend Container and Final Compose

```
Create frontend/Dockerfile (multi-stage: node build, then nginx serving dist with SPA fallback to index.html). Add the frontend service on port 3000 with VITE_API_URL build arg. Add a separate test database service or a docker compose profile 'test' so pytest can run in a container with: docker compose run --rm backend pytest. Add a Makefile with up, down, test, seed, migrate shortcuts.
```

## 7. LEVEL 1: Seed Data, Documentation and Deliverables

### 7.0 Main Prompt

```
Read AGENT.md. Final phase: make the project reviewable. Everything must be synthetic (no real names, emails or secrets). Deliverables: seed script, README, architecture overview, API documentation, ER diagram, known limitations, screenshots. Do each in the order of 7.1 to 7.5.
```

### 7.1 Seed Data

```
Create backend/app/seed.py (idempotent, run with python -m app.seed). Create: 1 platform admin; Org 'Acme Leave Co' (purchase/leave workflows) and Org 'Globex Purchasing' each with 1 org_admin, 2 managers, 3 employees; one user who belongs to BOTH orgs with different roles (to demo workspace switching); 2 projects per org, 10+ tasks with mixed statuses, priorities, overdue ones; workflow templates ('Leave Approval' 1 step by manager, 'Purchase Request' 2 steps manager then org_admin); a few requests in different states; notifications and audit rows created through the real services. Print a table of demo logins (all using the same fake password, e.g. Password123!) in the console and in README.
```

### 7.2 README and Architecture Overview

```
Write README.md: what the product is, features by module, tech stack, prerequisites, setup (docker compose up --build), how to run migrations, seed and tests, demo accounts, URLs (frontend, API docs), project structure. Write docs/architecture.md (max 2 pages): layered architecture, request flow diagram (Mermaid) from browser to DB, tenancy model, auth and permission flow, workflow state machine diagram (Mermaid), transaction strategy, and these design decisions: why shared schema with org_id, why 404 instead of 403 for cross-tenant IDs, why DB-level audit trigger, why pessimistic lock on decisions. Include a section explaining how stronger isolation can be added later: PostgreSQL Row Level Security with SET app.current_org, schema-per-tenant, or database-per-tenant for enterprise customers, with the trade-offs.
```

### 7.3 API Documentation

```
Improve FastAPI OpenAPI metadata: tags per module, summary and description per endpoint, response_model and responses={...} for 401/403/404/409/422, examples in Pydantic schemas. Create docs/api.md as a table of every endpoint: method, path, role required, request body, success code, error codes, validation rules. Export docs/openapi.json.
```

### 7.4 Requirement Traceability Check

```
Create docs/requirements-checklist.md mapping each requirement and each of the 10 mandatory test scenarios in the assignment to the code file, endpoint and test name that satisfies it. Find and list any gap. Fix gaps before we continue.
```

### 7.5 Limitations and Improvements

```
Add 'Known Limitations and Proposed Improvements' to README and AGENT.md: for example no refresh tokens, mocked email, polling instead of websockets, simple sequential workflow only, no file attachments, in-process due-date scanning, token stored in browser storage. For each, state the proposed improvement and rough effort. Finalize AGENT.md: re-read every section, remove outdated text, and ensure the Code Reference matches the code.
```

## 8. Guide: How to Implement This Successfully

### 8.1 Setup Before You Start

1. Install: Git, Docker Desktop, Python 3.12, Node 20+, an AI coding agent, and a DB client (psql or DBeaver).
2. Create an empty folder, run `git init`, open it in your agent.
3. Paste the **L0 Master Prompt** (Section 3). Commit.
4. Do **6.1** (Docker + Postgres) so the database exists from day one.

### 8.2 Working Method That Prevents Most Failures

- **One prompt, one commit.** If a step breaks, you can revert to the last good commit instead of untangling a big mess.
- **Main prompt first, then implementing prompts.** The main prompt gives the agent the concept; the implementing prompts keep each change small enough to review.
- **Always run it.** After every step: start the server or run the test. Never stack a new prompt on top of unverified code.
- **Review security-sensitive code yourself.** Read the dependencies (4.4), the decide endpoint (4.6.4), and every query to confirm each one filters by `org_id`.
- **Re-anchor the agent often.** Start a long session with *Re-read AGENT.md, then do this task.* AGENT.md is the agent's memory.
- **Fix bugs by pasting evidence:** *Here is the failing test output and the file. Find the root cause and fix the code, do not change the test unless the test is wrong, and explain why.*
- **Keep scope tight.** The assignment says correct business logic, authorization, integrity and tests matter more than visual polish. Do not add branching workflows, a visual designer or complex email.

### 8.3 How the Pieces Integrate (End-to-End Picture)

1. **Browser (React)** calls the API client with `Authorization: Bearer <token>`.
2. **FastAPI router** receives the call; Pydantic validates the body (422 if bad).
3. **Dependencies** run: `get_current_user` (token to user), `get_org_context` (membership, active org, role), `require_roles` (permission).
4. **Service** runs business logic inside one SQLAlchemy session and transaction: query by `org_id`, change data, write history, notifications and audit.
5. **PostgreSQL** enforces foreign keys, unique constraints and the audit trigger as the last safety net. The transaction commits, or rolls back entirely on any error.
6. **Response** returns using `response_model`, and the frontend's TanStack Query updates the cache and the UI.
7. **Alembic** keeps the schema versioned; **Docker Compose** runs db, backend and frontend together; **Pytest** proves it all, including the stored database state.

### 8.4 Common Problems and Fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Backend cannot connect to DB in Docker | Using `localhost` as host | Use the service name `db` in `DATABASE_URL` |
| Alembic autogenerate shows nothing | Models not imported in `env.py` | Import all models in `alembic/env.py` and set `target_metadata = Base.metadata` |
| Cross-tenant test returns 403 or 200 | Query not using the org-scoped helper | Route all reads through `get_in_org`; expect 404 |
| Rollback test still finds rows | Service commits early | Commit only once at the end of the service or request, never inside helpers |
| Double approval both succeed | No row lock or version check | Use `with_for_update()` in the decide service |
| CORS error in browser | Origin not allowed | Add the frontend URL to the backend CORS env setting |
| Stale data after switching workspace | Query cache shared | Include `org_id` in query keys and clear the cache on switch |
| Tests pollute each other | No rollback or cleanup | Use transaction-per-test fixture or recreate the schema |

### 8.5 Final Review Prompt (Run Last)

```
Act as a strict code reviewer for this assessment. Review the whole repository against: tenant isolation on every endpoint, role checks on every endpoint, transactions around every multi-record change, valid workflow state transitions, input validation, no secrets in code, indexes for common queries, test coverage of the 10 mandatory scenarios with DB-state assertions, README accuracy, and AGENT.md accuracy. Produce a list of concrete defects with file and line, sorted by severity. Then fix the high-severity ones, run all tests, and update AGENT.md.
```

### 8.6 Submission Checklist

- [ ] Frontend and backend source in Git with a clear history
- [ ] `docker compose up --build` works on a clean machine
- [ ] Migrations and seed data run cleanly
- [ ] All tests pass, including the 10 mandatory scenarios
- [ ] Swagger UI at `/docs` plus `docs/api.md`
- [ ] ER diagram, architecture overview and design decisions
- [ ] README with setup and demo accounts
- [ ] Screenshots or a short screen recording of: login and workspace switch, task filtering, request submit, approve and reject, notifications, audit log, dashboard
- [ ] Known limitations and improvements documented
- [ ] AGENT.md complete and consistent with the code
