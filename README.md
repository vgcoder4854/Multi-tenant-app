# Multi-Tenant Workflow Platform

An enterprise SaaS application where **multiple organizations share one app but stay
logically isolated**. Teams manage projects and tasks, run sequential approval
workflows, receive in-app notifications, and keep an append-only audit trail.

Authorization and tenant isolation are enforced **on the backend** on every endpoint;
the frontend is only a client of those rules.

---

## Features by module

1. **Auth & organization management** — register/login with JWT, create an organization,
   invite people by email with a role, accept invitations, switch workspace, platform
   admins can activate/suspend organizations.
2. **Multi-tenant isolation** — every tenant table carries `org_id`; every request
   re-checks membership in the database; cross-org IDs return **404** (not 403) so IDs
   cannot be probed. Composite foreign keys make the database refuse cross-org rows.
3. **Projects & tasks** — CRUD, archive (read-only), members; priorities
   (low/medium/high/critical) and statuses (to do / in progress / blocked / completed);
   filter, search, sort, paginate; full status history.
4. **Workflow & approvals** — ordered-step templates, submit a request, only the current
   step's approver can decide (never the requester), no decisions on finished requests,
   full decision history, optimistic locking so two approvers cannot both advance a step.
5. **Notifications** — in-app notifications for assignments, status changes, approval
   requests/decisions and due/overdue tasks; list, unread count, mark read / read-all.
6. **Audit trail** — append-only log (actor, org, action, resource, metadata), protected
   by a database trigger that blocks UPDATE/DELETE.
7. **Dashboard & reporting** — role-scoped metrics computed with SQL aggregates, plus a
   CSV export.

## Tech stack

| Layer | Tech |
| --- | --- |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PyJWT, Argon2 (pwdlib) |
| Database | PostgreSQL 16 (production/Docker) · SQLite (zero-setup local dev) |
| Frontend | React + TypeScript (Vite), Tailwind CSS, React Router, TanStack Query, React Hook Form + Zod |
| Tests | Pytest + httpx (backend), Vitest + React Testing Library (frontend) |
| Infra | Docker + Docker Compose, Makefile |

The models use portable SQLAlchemy types so the **same code runs on SQLite and
PostgreSQL**. The audit append-only rule is implemented per dialect (PL/pgSQL trigger on
PostgreSQL, `RAISE(ABORT)` on SQLite).

---

## Prerequisites

- Docker Desktop (recommended), **or**
- Python 3.12 and Node 20+ for local development without Docker.
- `git`.

## Quick start with Docker (one command)

```bash
cp .env.example .env          # adjust SECRET_KEY etc.
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs
- Database UI (pgAdmin): http://localhost:5050  (register server → host `db`, user `app`, password `app`, db `appdb`)
- The backend waits for PostgreSQL, runs `alembic upgrade head`, then starts.

Seed demo data (inside the running backend container):

```bash
docker compose exec backend python -m app.seed
```

## Local development without Docker (SQLite)

The backend defaults to a local SQLite file, so it runs with zero setup.

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env                 # DATABASE_URL=sqlite:///./dev.db by default
alembic upgrade head
python -m app.seed                      # optional demo data
uvicorn app.main:app --reload           # http://localhost:8000/docs

# frontend (new terminal)
cd frontend
npm install
cp .env.example .env                    # VITE_API_URL=http://localhost:8000/api/v1
npm run dev                             # http://localhost:5173
```

### Optional: real PostgreSQL without Docker

If you want the PostgreSQL code path but have no Docker, use the bundled helper:

```bash
pip install pgserver 'psycopg[binary]'      # needs Python <= 3.12
python scripts/dev_db.py                    # prints a DATABASE_URL
export DATABASE_URL='postgresql+psycopg://postgres@/postgres?host=/abs/.devdata/pgdata'
cd backend && alembic upgrade head
```

## Running the tests

```bash
# backend (SQLite test DB, transaction rolled back per test)
cd backend && pytest -q
pytest --cov=app --cov-report=term-missing

# frontend
cd frontend && npm test
```

Or with Make: `make test` (backend) and `make frontend-dev`.

---

## Demo accounts

All demo accounts use the password **`Password123!`** (synthetic data only).

| Email | Role |
| --- | --- |
| `platform@demo.example.com` | Platform Administrator |
| `admin.acme@demo.example.com` | org_admin @ Acme Leave Co |
| `manager1.acme@demo.example.com` / `manager2.acme@demo.example.com` | manager @ Acme Leave Co |
| `emp1.acme@demo.example.com` / `emp2.acme@demo.example.com` / `emp3.acme@demo.example.com` | employee @ Acme Leave Co |
| `admin.globex@demo.example.com` | org_admin @ Globex Purchasing |
| `manager1.globex@demo.example.com` / `manager2.globex@demo.example.com` | manager @ Globex Purchasing |
| `emp1.globex@demo.example.com` / `emp2.globex@demo.example.com` / `emp3.globex@demo.example.com` | employee @ Globex Purchasing |
| `shared.user@demo.example.com` | manager @ Acme **and** employee @ Globex (workspace-switch demo) |

## Project structure

```
backend/
  app/
    api/        routers (HTTP only)          services/  business logic + transactions
    models/     SQLAlchemy ORM models        schemas/   Pydantic request/response models
    core/       config, database, security, permissions, errors
    jobs/       due/overdue scan
  alembic/      migrations
  tests/        pytest suites + fixtures/factories
frontend/
  src/
    api/        single HTTP client + typed endpoints
    hooks/      TanStack Query hooks        pages/     route pages
    components/ ui primitives + layout + guards
    lib/        auth context                types/     TS mirror of backend schemas
docs/           ER diagram, architecture, API reference, checklists
docker-compose.yml, Makefile, .env.example, AGENT.md
```

## Documentation

- `AGENT.md` — living knowledge base: architecture, concepts, code reference, rules, DB notes, decisions.
- `docs/er-diagram.md` — entity-relationship diagram.
- `docs/architecture.md` — request flow, tenancy model, workflow state machine, decisions.
- `docs/api.md` — every endpoint with roles and status codes.
- `docs/requirements-checklist.md` — requirements ↔ code ↔ tests traceability.

## Known limitations

See the "Known Limitations and Proposed Improvements" section below and in `AGENT.md`.
Highlights: no refresh tokens, mocked email, polling instead of websockets, sequential
workflows only, no file attachments, in-process due-date scanning, token in browser
storage, and row-level (not schema/DB-level) isolation.

## Design decisions (short)

- **Shared schema + `org_id`** for simple, testable isolation; Row Level Security or
  schema-per-tenant can be layered later (see `docs/architecture.md`).
- **404 for cross-tenant IDs** so resource existence is never leaked.
- **DB-level append-only audit** so even an application bug cannot rewrite history.
- **`SELECT ... FOR UPDATE` + `version`** on decisions to prevent concurrent double approvals.
- **Portable types** so local dev needs no database server while production uses PostgreSQL.

---

## Known Limitations and Proposed Improvements

| # | Limitation | Impact | Proposed improvement | Effort |
| --- | --- | --- | --- | --- |
| 1 | No refresh tokens; short-lived access token only | Users re-login when it expires | Add refresh tokens + rotation | M |
| 2 | Token stored in `sessionStorage` | XSS could read it | Prefer httpOnly, secure cookies + CSRF protection | M |
| 3 | Email is mocked (logs to console) | No real emails | Plug in SMTP/SES behind `EmailService` | S |
| 4 | Notifications use polling (30s) | Slight delay | WebSockets / SSE push | M |
| 5 | Sequential workflows only | No branching/parallel steps | Add conditional/parallel steps to the engine | L |
| 6 | No file attachments on requests | Can't attach documents | Object storage + signed URLs | M |
| 7 | Due/overdue scan is in-process (`python -m app.jobs.due_scan`) | Needs a scheduler | Cron / Celery beat / APScheduler | S |
| 8 | Row-level isolation only (app-enforced) | A missed filter is a risk | Add PostgreSQL Row Level Security (`SET app.current_org`) | M |
| 9 | SQLite is the default local dev DB | Slightly different behaviour vs PG | Make PostgreSQL the default via Docker | S |
| 10 | No rate limiting / lockout on login | Brute-force risk | Add rate limiting + lockout | S |
| 11 | Enum columns are CHECK-constrained strings | Not native PG enums | Use native enums if PG-only | S |
| 12 | No pagination on some list endpoints (projects, members) | Large orgs | Add pagination | S |
| 13 | Single-language UI, no i18n | English only | Add i18n | M |
