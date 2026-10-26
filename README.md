# Multi-Tenant Workflow Platform

An enterprise SaaS workflow platform where multiple organizations share one app but
stay logically isolated. Manage projects, tasks, sequential approval workflows,
in-app notifications and an audit trail.

> Full setup, features, demo accounts and architecture are documented in
> `README.md` (written in phase 7) and `AGENT.md`. This file is expanded at the end.

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
# frontend: http://localhost:3000   API docs: http://localhost:8000/docs
```

## Quick start (local, no Docker — SQLite)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

See `AGENT.md` for architecture, concepts and decisions.
